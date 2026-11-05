import logging

from celery import shared_task

from .backends import PushDeliveryError, PushMessage, get_push_backend
from .models import PushDevice

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_push_to_user(self, user_id, title, body, data):
    tokens = list(PushDevice.objects.filter(user_id=user_id, is_active=True).values_list("token", flat=True))
    if not tokens:
        return 0
    messages = [PushMessage(token=t, title=title, body=body, data=data) for t in tokens]
    try:
        dead = get_push_backend().send(messages)
    except PushDeliveryError as exc:
        logger.warning("Push delivery failed (user %s): %s", user_id, exc)
        raise self.retry(exc=exc)
    if dead:
        PushDevice.objects.filter(token__in=dead).update(is_active=False)
    return len(messages)
