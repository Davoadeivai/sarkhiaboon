"""
Push notification delivery. The active backend is settings.PUSH_BACKEND, so a
different service (e.g. an Iranian push provider such as Pushe or Najva) is
added as a new class here and switched on in .env, without touching callers.
"""
import logging
from dataclasses import dataclass, field

import requests
from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


@dataclass
class PushMessage:
    token: str
    title: str
    body: str
    data: dict = field(default_factory=dict)


class PushDeliveryError(Exception):
    pass


class BasePushBackend:
    def send(self, messages):
        """Deliver messages; return the tokens the service reports as dead (app uninstalled)."""
        raise NotImplementedError


class LogPushBackend(BasePushBackend):
    """Development default: writes notifications to the server log."""

    def send(self, messages):
        for m in messages:
            logger.info("PUSH to %s…: %s — %s %s", m.token[:16], m.title, m.body, m.data)
        return []


class LocMemPushBackend(BasePushBackend):
    """Tests: keeps messages in LocMemPushBackend.outbox."""

    outbox = []
    dead_tokens = set()

    def send(self, messages):
        LocMemPushBackend.outbox.extend(messages)
        return [m.token for m in messages if m.token in LocMemPushBackend.dead_tokens]


class ExpoPushBackend(BasePushBackend):
    """
    Expo push service (one API for Android/FCM and iOS/APNs).
    Docs: https://docs.expo.dev/push-notifications/sending-notifications/
    Note: delivery to Android relies on Google FCM, which can be unreliable in Iran.
    """

    url = "https://exp.host/--/api/v2/push/send"
    batch_size = 100

    def send(self, messages):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if settings.EXPO_PUSH_ACCESS_TOKEN:
            headers["Authorization"] = f"Bearer {settings.EXPO_PUSH_ACCESS_TOKEN}"
        dead = []
        for start in range(0, len(messages), self.batch_size):
            batch = messages[start:start + self.batch_size]
            payload = [
                {"to": m.token, "title": m.title, "body": m.body, "data": m.data,
                 "sound": "default", "channelId": "default"}
                for m in batch
            ]
            try:
                response = requests.post(self.url, json=payload, headers=headers, timeout=15)
            except requests.RequestException as exc:
                raise PushDeliveryError(str(exc)) from exc
            if response.status_code != 200:
                raise PushDeliveryError(f"Expo returned HTTP {response.status_code}: {response.text[:200]}")
            tickets = response.json().get("data", [])
            for message, ticket in zip(batch, tickets):
                if ticket.get("status") == "error":
                    if (ticket.get("details") or {}).get("error") == "DeviceNotRegistered":
                        dead.append(message.token)
                    else:
                        logger.warning("Expo push error for %s…: %s", message.token[:16], ticket.get("message"))
        return dead


def get_push_backend():
    return import_string(settings.PUSH_BACKEND)()
