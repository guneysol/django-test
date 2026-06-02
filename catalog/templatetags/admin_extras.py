"""Template tags powering the custom admin dashboard."""

from django.contrib.auth import get_user_model
from django.db.models import Avg
from django.template import Library

from catalog.models import Book, Genre, Review

register = Library()


@register.simple_tag
def get_admin_stats():
    """Headline numbers + recent activity for the admin dashboard."""
    avg = Review.objects.aggregate(a=Avg("rating"))["a"]
    return {
        "books": Book.objects.count(),
        "reviews": Review.objects.count(),
        "members": get_user_model().objects.count(),
        "genres": Genre.objects.count(),
        "avg_rating": round(avg, 1) if avg else "—",
        "recent": (
            Review.objects.select_related("book", "author").order_by("-created_at")[:6]
        ),
    }
