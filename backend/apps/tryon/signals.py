from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.accounts.signals import guest_merged

from .models import PersonPhoto, TryOnJob


@receiver(post_delete, sender=PersonPhoto)
def delete_person_photo_file(sender, instance, **kwargs):
    """Remove the file from storage whenever a photo row is deleted (any path: task, admin, user deletion)."""
    if instance.image.name:
        instance.image.storage.delete(instance.image.name)


@receiver(post_delete, sender=TryOnJob)
def delete_result_file(sender, instance, **kwargs):
    """Result files can be shared by cached jobs; delete only when no other job uses the file."""
    name = instance.result_image.name
    if name and not TryOnJob.objects.filter(result_image=name).exists():
        instance.result_image.storage.delete(name)


@receiver(guest_merged)
def move_guest_tryons(sender, guest, user, **kwargs):
    PersonPhoto.objects.filter(user=guest).update(user=user)
    TryOnJob.objects.filter(user=guest).update(user=user)
