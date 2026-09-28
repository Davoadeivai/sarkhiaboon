"""
The contract every try-on engine must follow.

The rest of the project only ever talks to `TryOnProvider`. Switching from a
ready-made API to RunPod, or to any future engine, means writing one new
subclass and changing TRYON_PROVIDER in the environment — nothing else.
"""
from dataclasses import dataclass, field


@dataclass
class TryOnRequest:
    person_image: bytes          # normalized JPEG of the customer
    garment_image: bytes         # clean product/garment image
    category: str                # upper_body | lower_body | dresses | shoes
    job_id: str                  # for tracing in provider logs


@dataclass
class TryOnResult:
    image: bytes
    extension: str = "jpg"       # jpg | png | webp
    inference_seconds: float | None = None
    meta: dict = field(default_factory=dict)


class ProviderError(Exception):
    """
    retryable=True  -> temporary problem (network, 5xx, provider busy): try again later
    retryable=False -> the request itself cannot succeed (bad input, auth, config)
    """

    def __init__(self, message, retryable=True):
        super().__init__(message)
        self.retryable = retryable


class TryOnProvider:
    #: Short identifier stored on each job (shows which engine produced a result)
    name = "base"
    #: Categories this engine can handle
    supported_categories = ("upper_body", "lower_body", "dresses")

    def generate(self, request: TryOnRequest) -> TryOnResult:
        raise NotImplementedError

    def supports(self, category):
        return category in self.supported_categories
