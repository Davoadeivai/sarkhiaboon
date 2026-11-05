"""What to tell the customer, and when. Delivery runs in Celery so a slow push service never blocks a request."""
from django.db import transaction

from .tasks import send_push_to_user

ORDER_MESSAGES = {
    "processing": ("سفارش شما در حال آماده‌سازی است", "سفارش {number} را آماده می‌کنیم."),
    "shipped": ("سفارش شما ارسال شد", "سفارش {number} ارسال شد.{tracking}"),
    "delivered": ("سفارش شما تحویل شد", "امیدواریم از خریدتان راضی باشید. سفارش {number}"),
    "expired": ("مهلت پرداخت تمام شد", "سفارش {number} پرداخت نشد و کالاها به موجودی برگشتند."),
    "cancelled": ("سفارش لغو شد", "سفارش {number} لغو شد."),
}


def notify(user_id, title, body, data):
    """Queue a push to all of the user's phones once the current transaction commits."""
    transaction.on_commit(lambda: send_push_to_user.delay(user_id, title, body, data))


def notify_tryon_finished(job):
    if job.status == "completed":
        title, body = "پرو مجازی آماده شد", f"«{job.product.name}» را روی خودتان ببینید."
    else:
        title, body = "پرو مجازی انجام نشد", job.error_message or "لطفاً دوباره تلاش کنید."
    notify(job.user_id, title, body, {"type": "tryon", "job_id": str(job.pk)})


def notify_order_status(order):
    template = ORDER_MESSAGES.get(order.status)
    if not template:
        return
    tracking = f" کد رهگیری: {order.tracking_code}" if getattr(order, "tracking_code", "") else ""
    title, body = template
    notify(order.user_id, title, body.format(number=order.number, tracking=tracking),
           {"type": "order", "order_number": order.number})
