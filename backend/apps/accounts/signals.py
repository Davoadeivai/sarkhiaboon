from django.dispatch import Signal

# Sent when a guest verifies a phone number that already belongs to an existing
# account. Receivers in other apps move the guest's data (try-ons, favorites,
# cart) to that account.  kwargs: guest, user
guest_merged = Signal()
