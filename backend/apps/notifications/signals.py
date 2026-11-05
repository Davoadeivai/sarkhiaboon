"""
Watch status changes on try-on jobs and orders and notify the customer.
Only real transitions of existing rows count: a job served instantly from the
cache (created already completed) does not send a push, the customer is
looking at it.
"""
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

from apps.accounts.signals import guest_merged
from apps.orders.models import Order
from apps.tryon.models import TryOnJob

from .models import PushDevice
from .services import notify_order_status, notify_tryon_finished


def _remember_status(sender, instance, **kwargs):
    # __dict__: never trigger a query for a deferred field (e.g. .only("id"))
    instance._status_at_load = instance.__dict__.get("status") if instance.pk else None


post_init.connect(_remember_status, sender=TryOnJob, dispatch_uid="push_tryon_status")
post_init.connect(_remember_status, sender=Order, dispatch_uid="push_order_status")


def _changed(instance, created):
    previous = getattr(instance, "_status_at_load", None)
    instance._status_at_load = instance.status  # a second save() must not notify again
    return not created and previous is not None and previous != instance.status


@receiver(post_save, sender=TryOnJob, dispatch_uid="push_tryon_finished")
def tryon_finished(sender, instance, created, **kwargs):
    if _changed(instance, created) and instance.status in (TryOnJob.Status.COMPLETED, TryOnJob.Status.FAILED):
        notify_tryon_finished(instance)


@receiver(post_save, sender=Order, dispatch_uid="push_order_status")
def order_status_changed(sender, instance, created, **kwargs):
    if _changed(instance, created):
        notify_order_status(instance)


@receiver(guest_merged, dispatch_uid="push_move_guest_devices")
def move_guest_devices(sender, guest, user, **kwargs):
    PushDevice.objects.filter(user=guest).update(user=user)
