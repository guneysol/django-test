"""URL routes for the catalog app."""

from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.book_list, name="book_list"),
    path("insights/", views.stats, name="stats"),
    path("books/new/", views.book_create, name="book_create"),
    path("books/<slug:slug>/", views.book_detail, name="book_detail"),
    path("books/<slug:slug>/ai-summary/", views.ai_summary, name="ai_summary"),
    path("books/<slug:slug>/edit/", views.book_edit, name="book_edit"),
    path("books/<slug:slug>/delete/", views.book_delete, name="book_delete"),
    path("books/<slug:slug>/review/", views.review_submit, name="review_submit"),
    path("books/<slug:slug>/shelf/", views.toggle_shelf, name="toggle_shelf"),
    path("reviews/<int:pk>/delete/", views.review_delete, name="review_delete"),
]
