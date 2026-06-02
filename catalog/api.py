"""REST API viewsets for the catalog (Django REST Framework)."""

from rest_framework import permissions, viewsets

from .models import Book, Genre, Review
from .serializers import BookSerializer, GenreSerializer, ReviewSerializer


class IsAuthorOrReadOnly(permissions.BasePermission):
    """Object-level permission: only the creator may modify an object."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        owner = getattr(obj, "author", None) or getattr(obj, "added_by", None)
        return owner == request.user or request.user.is_staff


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of genres."""

    queryset = Genre.objects.all()
    serializer_class = GenreSerializer


class BookViewSet(viewsets.ModelViewSet):
    """Full CRUD over books with search (?search=) and ordering (?ordering=)."""

    queryset = Book.objects.select_related("genre").all()
    serializer_class = BookSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    lookup_field = "slug"
    search_fields = ["title", "author", "description"]
    ordering_fields = ["title", "published_year", "created_at"]

    def perform_create(self, serializer):
        serializer.save(added_by=self.request.user)


class ReviewViewSet(viewsets.ModelViewSet):
    """Full CRUD over reviews; users may only edit their own."""

    queryset = Review.objects.select_related("author", "book").all()
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
