"""Forms for creating/editing books and reviews."""

from django import forms

from .models import Book, Review


class BookForm(forms.ModelForm):
    """Create or edit a book entry."""

    class Meta:
        model = Book
        fields = ["title", "author", "genre", "description", "cover", "published_year"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "published_year": forms.NumberInput(attrs={"min": 0, "max": 2100}),
        }


class ReviewForm(forms.ModelForm):
    """Submit or edit a review for a book."""

    class Meta:
        model = Review
        fields = ["rating", "headline", "body"]
        widgets = {
            "rating": forms.Select(),
            "body": forms.Textarea(attrs={"rows": 5}),
        }
