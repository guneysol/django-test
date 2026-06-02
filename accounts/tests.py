"""Tests for accounts: signup, profile auto-creation and auth flows."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Profile


class AccountTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user("newbie", password="pw12345!")
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_signup_creates_user_and_logs_in(self):
        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "fresh",
                "email": "fresh@example.com",
                "password1": "Sup3rStrongPw!",
                "password2": "Sup3rStrongPw!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(username="fresh").exists())
        # User is authenticated immediately after signup.
        self.assertIn("_auth_user_id", self.client.session)

    def test_duplicate_email_rejected(self):
        User.objects.create_user("a", email="dup@example.com", password="pw12345!")
        resp = self.client.post(
            reverse("accounts:signup"),
            {
                "username": "b",
                "email": "dup@example.com",
                "password1": "Sup3rStrongPw!",
                "password2": "Sup3rStrongPw!",
            },
        )
        self.assertEqual(resp.status_code, 200)  # re-renders with errors
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_login_and_logout(self):
        User.objects.create_user("logger", password="pw12345!")
        self.assertTrue(self.client.login(username="logger", password="pw12345!"))
        resp = self.client.post(reverse("logout"))
        self.assertEqual(resp.status_code, 302)

    def test_profile_page_loads(self):
        User.objects.create_user("viewme", password="pw12345!")
        resp = self.client.get(reverse("accounts:profile_detail", args=["viewme"]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "viewme")

    def test_profile_edit_requires_login(self):
        resp = self.client.get(reverse("accounts:profile_edit"))
        self.assertEqual(resp.status_code, 302)
