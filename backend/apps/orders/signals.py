from django.dispatch import receiver

from apps.accounts.signals import guest_merged

from .models import CartItem


@receiver(guest_merged)
def merge_guest_cart(sender, guest, user, **kwargs):
    """Keep a guest's cart when they log into an existing account (quantities are combined)."""
    existing = {item.variant_id: item for item in CartItem.objects.filter(user=user)}
    for item in CartItem.objects.filter(user=guest):
        if item.variant_id in existing:
            target = existing[item.variant_id]
            target.quantity = min(target.quantity + item.quantity, max(target.variant.stock, target.quantity))
            target.save(update_fields=["quantity"])
            item.delete()
        else:
            item.user = user
            item.save(update_fields=["user"])
