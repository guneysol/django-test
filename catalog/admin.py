"""Admin registrations for catalog models, with a richer, branded UI."""

from django.contrib import admin
from django.db.models import Avg, Count
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from .models import Book, Genre, Review


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ["author", "created_at"]


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "book_count"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_books=Count("books"))

    @admin.display(description="Books", ordering="_books")
    def book_count(self, obj):
        return obj._books


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["cover_thumb", "title", "author", "genre", "rating_badge", "reviews_count"]
    list_display_links = ["cover_thumb", "title"]
    list_filter = ["genre", "published_year"]
    search_fields = ["title", "author"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["genre"]
    list_per_page = 20
    inlines = [ReviewInline]

    def get_queryset(self, request):
        # Annotate once so the rating/review columns are efficient and sortable.
        return (
            super()
            .get_queryset(request)
            .select_related("genre")
            .annotate(_avg=Avg("reviews__rating"), _count=Count("reviews"))
        )

    @admin.display(description="Cover")
    def cover_thumb(self, obj):
        url = obj.cover_image_url
        if url:
            return format_html(
                '<img src="{}" style="height:54px;width:36px;object-fit:cover;'
                'border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.3);">',
                url,
            )
        return mark_safe('<span style="font-size:1.6rem;">📖</span>')

    @admin.display(description="Rating", ordering="_avg")
    def rating_badge(self, obj):
        if obj._avg is None:
            return mark_safe('<span style="color:#999;">— no reviews</span>')
        return format_html(
            '<span style="color:#d8a33a;font-weight:700;">★ {}</span>',
            round(obj._avg, 1),
        )

    @admin.display(description="Reviews", ordering="_count")
    def reviews_count(self, obj):
        return obj._count


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["headline", "stars", "book", "author", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["headline", "body", "book__title"]
    autocomplete_fields = ["book"]
    date_hierarchy = "created_at"

    @admin.display(description="Rating", ordering="rating")
    def stars(self, obj):
        filled = "★" * obj.rating
        empty = "☆" * (5 - obj.rating)
        return format_html('<span style="color:#d8a33a;">{}{}</span>', filled, empty)
