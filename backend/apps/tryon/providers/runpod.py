"""
RunPod Serverless engine (e.g. CatVTON packaged in a Docker worker).

Flow: POST /run -> job id -> poll GET /status/<id> until finished.
The async /run + polling flow is used instead of /runsync because a cold
start (container boot + model load) can take longer than /runsync waits.

Worker contract — the GPU worker's handler must:
  receive  input = {"person_image": <base64 JPEG>, "garment_image": <base64>,
                    "category": "upper_body|lower_body|dresses", "job_id": "<uuid>"}
  return   {"image": <base64>, "format": "png"|"jpg"}      on success
       or  {"error": "<message>"}                          on failure
"""
import base64
import binascii
import logging
import time

import requests
from django.conf import settings

from .base import ProviderError, TryOnProvider, TryOnRequest, TryOnResult

logger = logging.getLogger(__name__)

_FINAL_FAILURES = {"FAILED", "CANCELLED", "TIMED_OUT"}
_RETRYABLE_HTTP = {408, 429, 500, 502, 503, 504}


class RunPodProvider(TryOnProvider):
    name = "runpod"

    def __init__(self, session=None, sleep=time.sleep, clock=time.monotonic):
        cfg = settings.TRYON
        self.endpoint_id = cfg["RUNPOD_ENDPOINT_ID"]
        self.api_key = cfg["RUNPOD_API_KEY"]
        self.base_url = cfg["RUNPOD_BASE_URL"].rstrip("/")
        self.poll_interval = cfg["RUNPOD_POLL_INTERVAL_SECONDS"]
        self.timeout = cfg["PROVIDER_TIMEOUT_SECONDS"]
        self.session = session or requests.Session()
        self._sleep = sleep
        self._clock = clock

    # -- helpers -----------------------------------------------------------
    def _url(self, path):
        return f"{self.base_url}/{self.endpoint_id}/{path}"

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _call(self, method, path, **kwargs):
        try:
            response = self.session.request(method, self._url(path), headers=self._headers(), timeout=30, **kwargs)
        except requests.RequestException as exc:
            raise ProviderError(f"RunPod network error: {exc}", retryable=True) from exc
        if response.status_code in (401, 403):
            raise ProviderError("RunPod rejected the API key.", retryable=False)
        if response.status_code in _RETRYABLE_HTTP:
            raise ProviderError(f"RunPod HTTP {response.status_code}", retryable=True)
        if response.status_code >= 400:
            raise ProviderError(f"RunPod HTTP {response.status_code}: {response.text[:300]}", retryable=False)
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError("RunPod returned invalid JSON.", retryable=True) from exc

    def _cancel(self, runpod_id):
        try:
            self._call("POST", f"cancel/{runpod_id}")
        except ProviderError:
            logger.warning("Could not cancel RunPod job %s", runpod_id)

    # -- main entry point ----------------------------------------------------
    def generate(self, request: TryOnRequest) -> TryOnResult:
        if not self.endpoint_id or not self.api_key:
            raise ProviderError("RUNPOD_ENDPOINT_ID / RUNPOD_API_KEY are not configured.", retryable=False)
        if not self.supports(request.category):
            raise ProviderError(f"Category '{request.category}' is not supported by the RunPod worker.", retryable=False)

        payload = {
            "input": {
                "person_image": base64.b64encode(request.person_image).decode(),
                "garment_image": base64.b64encode(request.garment_image).decode(),
                "category": request.category,
                "job_id": request.job_id,
            }
        }
        submitted = self._call("POST", "run", json=payload)
        runpod_id = submitted.get("id")
        if not runpod_id:
            raise ProviderError(f"RunPod did not return a job id: {submitted}", retryable=True)

        deadline = self._clock() + self.timeout
        status = submitted
        while status.get("status") not in ({"COMPLETED"} | _FINAL_FAILURES):
            if self._clock() >= deadline:
                self._cancel(runpod_id)
                raise ProviderError(f"RunPod job {runpod_id} timed out after {self.timeout}s", retryable=True)
            self._sleep(self.poll_interval)
            status = self._call("GET", f"status/{runpod_id}")

        if status["status"] in _FINAL_FAILURES:
            raise ProviderError(f"RunPod job {runpod_id} ended with {status['status']}: {status.get('error', '')}", retryable=True)

        output = status.get("output") or {}
        if "error" in output:
            # The worker ran but the model refused the input (e.g. no person detected)
            raise ProviderError(f"Worker error: {output['error']}", retryable=False)
        try:
            image = base64.b64decode(output["image"], validate=True)
        except (KeyError, TypeError, binascii.Error) as exc:
            raise ProviderError("RunPod output has no valid 'image' field.", retryable=False) from exc

        extension = {"jpeg": "jpg"}.get(output.get("format", "png").lower(), output.get("format", "png").lower())
        # RunPod reports times in milliseconds: delayTime covers waiting in the
        # queue plus any worker cold start, executionTime is the processing
        # itself. Stored on the job so real cold-start overhead and cost per
        # image can be measured instead of estimated.
        delay_ms, exec_ms = status.get("delayTime"), status.get("executionTime")
        return TryOnResult(
            image=image,
            extension=extension,
            inference_seconds=(exec_ms / 1000) if exec_ms is not None else None,
            meta={"runpod_id": runpod_id, "delay_ms": delay_ms, "execution_ms": exec_ms},
        )
