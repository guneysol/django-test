"""Data models for the BookNest catalog.

The schema is built around four entities:

* :class:`Genre`  – a category a book belongs to (one-to-many with Book).
* :class:`Book`   – the central entity reviewed by the community.
* :class:`Review` – a user's rating + write-up for a book (one per user/book).
* The reading list – a many-to-many link between users and books, exposing the
  "want to read" shelf without a dedicated through-model.
"""

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils.text import slugify


class Genre(models.Model):
    """A book category such as "Science Fiction" or "History"."""

    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('catalog:book_list')}?genre={self.slug}"


class Book(models.Model):
    """A book that community members can review and shelve."""

    title = models.CharField(max_length=200)
    author = models.CharField(max_length=120)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    genre = models.ForeignKey(
        Genre,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="books",
    )
    description = models.TextField(blank=True)
    cover = models.ImageField(upload_to="covers/", blank=True, null=True)
    # An external cover image (e.g. from the Open Library Covers API). Used as a
    # fallback when no file has been uploaded, so seeded/imported books still
    # show real artwork.
    cover_url = models.URLField(blank=True)
    published_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(2100)],
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="added_books",
    )
    # Users who have shelved this book on their reading list.
    shelved_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="reading_list",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["author"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.author}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.title}-{self.author}")[:200]
            slug = base
            counter = 2
            # Guarantee uniqueness even for identically-titled books.
            while Book.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:book_detail", args=[self.slug])

    @property
    def cover_image_url(self):
        """Best available cover: an uploaded file, else an external URL."""
        if self.cover:
            return self.cover.url
        return self.cover_url or ""

    @property
    def average_rating(self):
        """Mean rating across all reviews, rounded to one decimal, or ``None``."""
        result = self.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(result, 1) if result is not None else None

    @property
    def review_count(self):
        return self.reviews.count()


class Review(models.Model):
    """A single member's rating and write-up for a book."""

    RATING_CHOICES = [(i, f"{i} star{'s' if i > 1 else ''}") for i in range(1, 6)]

    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    headline = models.CharField(max_length=120)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # A member may review any given book at most once.
            models.UniqueConstraint(
                fields=["book", "author"], name="unique_review_per_user_book"
            )
        ]

    def __str__(self):
        return f"{self.headline} ({self.rating}★) by {self.author}"

    def get_absolute_url(self):
        return self.book.get_absolute_url()
