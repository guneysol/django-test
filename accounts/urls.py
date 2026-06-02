"""URL routes for the accounts app."""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("profile/edit/", views.profile_edit, name="profile_edit"),
    path("u/<str:username>/", views.profile_detail, name="profile_detail"),
]
