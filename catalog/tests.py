"""Tests for the catalog app: models, views, permissions, search and API."""

from unittest.mock import patch

import requests
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Book, Genre, Review
from .services import OpenLibraryError, search_books


class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("reader", password="pw12345!")
        self.genre = Genre.objects.create(name="Science Fiction")
        self.book = Book.objects.create(
            title="Dune", author="Frank Herbert", genre=self.genre
        )

    def test_slugs_autogenerate(self):
        self.assertEqual(self.genre.slug, "science-fiction")
        self.assertTrue(self.book.slug.startswith("dune-frank-herbert"))

    def test_duplicate_book_titles_get_unique_slugs(self):
        other = Book.objects.create(title="Dune", author="Frank Herbert")
        self.assertNotEqual(self.book.slug, other.slug)

    def test_average_rating_and_count(self):
        self.assertIsNone(self.book.average_rating)
        u2 = User.objects.create_user("reader2", password="pw12345!")
        Review.objects.create(book=self.book, author=self.user, rating=4, headline="h", body="b")
        Review.objects.create(book=self.book, author=u2, rating=2, headline="h", body="b")
        self.assertEqual(self.book.average_rating, 3.0)
        self.assertEqual(self.book.review_count, 2)

    def test_one_review_per_user_per_book(self):
        Review.objects.create(book=self.book, author=self.user, rating=4, headline="h", body="b")
        with self.assertRaises(IntegrityError):
            Review.objects.create(book=self.book, author=self.user, rating=1, headline="x", body="y")


class ViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw12345!")
        self.other = User.objects.create_user("other", password="pw12345!")
        self.genre = Genre.objects.create(name="Fantasy")
        self.book = Book.objects.create(
            title="The Hobbit", author="Tolkien", genre=self.genre, added_by=self.owner
        )

    def test_book_list_loads(self):
        resp = self.client.get(reverse("catalog:book_list"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "The Hobbit")

    def test_search_filters_results(self):
        Book.objects.create(title="Neuromancer", author="Gibson")
        resp = self.client.get(reverse("catalog:book_list"), {"q": "hobbit"})
        self.assertContains(resp, "The Hobbit")
        self.assertNotContains(resp, "Neuromancer")

    def test_genre_filter(self):
        Book.objects.create(title="Neuromancer", author="Gibson")  # no genre
        resp = self.client.get(reverse("catalog:book_list"), {"genre": "fantasy"})
        self.assertContains(resp, "The Hobbit")
        self.assertNotContains(resp, "Neuromancer")

    def test_pagination_present_with_many_books(self):
        for i in range(10):
            Book.objects.create(title=f"Filler {i}", author="A")
        resp = self.client.get(reverse("catalog:book_list"))
        self.assertEqual(len(resp.context["page_obj"]), 6)  # PAGE size

    def test_book_detail_loads(self):
        resp = self.client.get(self.book.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Tolkien")

    def test_create_requires_login(self):
        resp = self.client.get(reverse("catalog:book_create"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.url)

    def test_authenticated_user_can_create_book(self):
        self.client.login(username="owner", password="pw12345!")
        resp = self.client.post(
            reverse("catalog:book_create"),
            {"title": "Mistborn", "author": "Sanderson", "published_year": 2006},
        )
        self.assertEqual(resp.status_code, 302)
        book = Book.objects.get(title="Mistborn")
        self.assertEqual(book.added_by, self.owner)

    def test_non_owner_cannot_edit(self):
        self.client.login(username="other", password="pw12345!")
        self.client.post(
            reverse("catalog:book_edit", args=[self.book.slug]),
            {"title": "Hacked", "author": "x"},
        )
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, "The Hobbit")  # unchanged

    def test_owner_can_delete(self):
        self.client.login(username="owner", password="pw12345!")
        resp = self.client.post(reverse("catalog:book_delete", args=[self.book.slug]))
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_review_submission_and_update(self):
        self.client.login(username="other", password="pw12345!")
        url = reverse("catalog:review_submit", args=[self.book.slug])
        self.client.post(url, {"rating": 5, "headline": "Great", "body": "Loved it"})
        self.assertEqual(self.book.reviews.count(), 1)
        # Posting again updates rather than duplicates (unique constraint).
        self.client.post(url, {"rating": 2, "headline": "Changed", "body": "Meh"})
        self.assertEqual(self.book.reviews.count(), 1)
        self.assertEqual(self.book.reviews.first().rating, 2)

    def test_invalid_review_does_not_crash(self):
        self.client.login(username="other", password="pw12345!")
        url = reverse("catalog:review_submit", args=[self.book.slug])
        resp = self.client.post(url, {"rating": 99, "headline": "", "body": ""})
        self.assertEqual(resp.status_code, 302)  # redirects with error message
        self.assertEqual(self.book.reviews.count(), 0)

    def test_ajax_toggle_shelf(self):
        self.client.login(username="other", password="pw12345!")
        url = reverse("catalog:toggle_shelf", args=[self.book.slug])
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["shelved"])
        self.assertTrue(self.book.shelved_by.filter(pk=self.other.pk).exists())
        # Toggling again removes it.
        resp = self.client.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(resp.json()["shelved"])


class APITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("apiuser", password="pw12345!")
        self.book = Book.objects.create(title="Dune", author="Herbert")

    def test_list_books_public(self):
        resp = self.client.get("/api/books/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 1)

    def test_create_book_requires_auth(self):
        resp = self.client.post("/api/books/", {"title": "X", "author": "Y"})
        self.assertIn(resp.status_code, (401, 403))

    def test_authenticated_create_via_api(self):
        self.client.login(username="apiuser", password="pw12345!")
        resp = self.client.post("/api/books/", {"title": "New", "author": "Auth"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["added_by"], "apiuser")

    def test_api_search(self):
        Book.objects.create(title="Neuromancer", author="Gibson")
        resp = self.client.get("/api/books/", {"search": "dune"})
        self.assertEqual(resp.json()["count"], 1)


class OpenLibraryIntegrationTests(TestCase):
    """Third-party API integration, tested with the network mocked out."""

    FAKE_PAYLOAD = {
        "docs": [
            {"title": "Mistborn", "author_name": ["Brandon Sanderson"], "first_publish_year": 2006},
            {"title": "Elantris", "author_name": ["Brandon Sanderson"], "first_publish_year": 2005},
        ]
    }

    @patch("catalog.services.requests.get")
    def test_search_books_normalises_results(self, mock_get):
        mock_get.return_value.json.return_value = self.FAKE_PAYLOAD
        mock_get.return_value.raise_for_status.return_value = None
        results = search_books("sanderson")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["title"], "Mistborn")
        self.assertEqual(results[0]["author"], "Brandon Sanderson")
        self.assertEqual(results[0]["published_year"], 2006)

    @patch("catalog.services.requests.get", side_effect=requests.RequestException("boom"))
    def test_search_books_wraps_errors(self, mock_get):
        with self.assertRaises(OpenLibraryError):
            search_books("anything")

    @patch("catalog.services.requests.get")
    def test_import_command_creates_books(self, mock_get):
        mock_get.return_value.json.return_value = self.FAKE_PAYLOAD
        mock_get.return_value.raise_for_status.return_value = None
        call_command("import_openlibrary", "sanderson")
        self.assertTrue(Book.objects.filter(title="Mistborn").exists())
        self.assertTrue(Book.objects.filter(title="Elantris").exists())
