from django.dispatch import receiver

from apps.accounts.signals import guest_merged

from .models import Favorite


@receiver(guest_merged)
def move_guest_favorites(sender, guest, user, **kwargs):
    """Keep a guest's favorites when they log into an existing account."""
    existing = set(Favorite.objects.filter(user=user).values_list("product_id", flat=True))
    Favorite.objects.filter(user=guest).exclude(product_id__in=existing).update(user=user)
    Favorite.objects.filter(user=guest).delete()
