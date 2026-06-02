"""DRF serializers exposing the catalog over a REST API."""

from rest_framework import serializers

from .models import Book, Genre, Review


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")

    class Meta:
        model = Review
        fields = ["id", "book", "author", "rating", "headline", "body", "created_at"]
        read_only_fields = ["author", "created_at"]


class BookSerializer(serializers.ModelSerializer):
    genre = serializers.SlugRelatedField(
        slug_field="name", queryset=Genre.objects.all(), required=False, allow_null=True
    )
    average_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    added_by = serializers.ReadOnlyField(source="added_by.username")

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "author",
            "slug",
            "genre",
            "description",
            "published_year",
            "average_rating",
            "review_count",
            "added_by",
        ]
        read_only_fields = ["slug", "added_by"]
