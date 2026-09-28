import logging

from celery import shared_task
from django.utils import timezone

from .models import Order
from .services import OrderError, cancel_order

logger = logging.getLogger(__name__)


@shared_task
def release_unpaid_orders():
    """Expire orders whose payment deadline passed and put their stock back on sale."""
    overdue = Order.objects.filter(status=Order.Status.PENDING_PAYMENT, reserved_until__lt=timezone.now())
    count = 0
    for order in overdue:
        try:
            cancel_order(order, new_status=Order.Status.EXPIRED)
            count += 1
        except OrderError:
            pass  # paid in the meantime
    if count:
        logger.info("Expired %s unpaid orders", count)
    return count
