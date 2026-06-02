"""Admin registration for the Profile model."""

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "location", "favorite_genre"]
    search_fields = ["user__username", "location"]
