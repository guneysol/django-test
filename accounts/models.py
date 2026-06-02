"""User profile model.

Each Django ``User`` is paired with exactly one :class:`Profile` via a
one-to-one relationship. The profile is created automatically through a signal
(see :mod:`accounts.signals`) so it always exists for an authenticated user.
"""

from django.conf import settings
from django.db import models


class Profile(models.Model):
    """Extra, public-facing information attached to a user account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    favorite_genre = models.CharField(max_length=60, blank=True)
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"
