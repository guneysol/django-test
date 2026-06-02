"""Signal handlers that keep a Profile in sync with its User."""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_or_update_profile(sender, instance, created, **kwargs):
    """Create a profile for new users; ensure existing users keep theirs."""
    if created:
        Profile.objects.create(user=instance)
    else:
        # get_or_create guards against users that predate the Profile model.
        Profile.objects.get_or_create(user=instance)
