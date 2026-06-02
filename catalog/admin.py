"""Admin registrations for catalog models."""

from django.contrib import admin

from .models import Book, Genre, Review


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["author", "created_at"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "genre", "published_year", "review_count"]
    list_filter = ["genre", "published_year"]
    search_fields = ["title", "author"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["genre"]
    inlines = [ReviewInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["headline", "book", "author", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["headline", "body", "book__title"]
