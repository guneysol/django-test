"""Views for the catalog: book browsing, detail, CRUD, reviews and AJAX."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BookForm, ReviewForm
from .models import Book, Genre, Review
from .services import generate_ai_summary

# Whitelist of sort options to keep the ordering ORM-safe.
SORT_OPTIONS = {
    "title": "title",
    "newest": "-created_at",
    "rating": "-avg_rating",
    "popular": "-num_reviews",
}


def book_list(request):
    """Browse books with full-text-ish search, genre filter, sort and paging."""
    query = request.GET.get("q", "").strip()
    genre_slug = request.GET.get("genre", "").strip()
    sort = request.GET.get("sort", "title")

    # Annotate once so search, sort and display all share the same queryset.
    books = (
        Book.objects.select_related("genre")
        .annotate(avg_rating=Avg("reviews__rating"), num_reviews=Count("reviews"))
    )

    if query:
        books = books.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(description__icontains=query)
        )

    active_genre = None
    if genre_slug:
        active_genre = Genre.objects.filter(slug=genre_slug).first()
        if active_genre:
            books = books.filter(genre=active_genre)

    books = books.order_by(SORT_OPTIONS.get(sort, "title"))

    paginator = Paginator(books, 6)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "genres": Genre.objects.annotate(num_books=Count("books")),
        "query": query,
        "active_genre": active_genre,
        "sort": sort,
        "sort_options": SORT_OPTIONS,
        # Headline stats for the hero banner.
        "total_books": Book.objects.count(),
        "total_reviews": Review.objects.count(),
        "total_genres": Genre.objects.count(),
    }
    # Instant search: an AJAX request only needs the results fragment, which the
    # front-end swaps into the page without a full reload.
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return render(request, "catalog/_results.html", context)
    return render(request, "catalog/book_list.html", context)


def ai_summary(request, slug):
    """Return an AI-generated summary of a book's reviews as JSON (AJAX)."""
    book = get_object_or_404(Book, slug=slug)
    return JsonResponse({"summary": generate_ai_summary(book)})


def stats(request):
    """Insights dashboard: community statistics rendered as charts.

    Every dataset is produced by a single aggregation query (no Python-side
    counting loops), then handed to Chart.js in the template as JSON.
    """
    review_qs = Review.objects.all()

    # 1. Rating distribution (how many 1★…5★ reviews).
    rating_counts = {
        row["rating"]: row["c"]
        for row in review_qs.values("rating").annotate(c=Count("id"))
    }
    ratings = {
        "labels": ["1★", "2★", "3★", "4★", "5★"],
        "data": [rating_counts.get(i, 0) for i in range(1, 6)],
    }

    # 2. Books per genre (doughnut).
    by_genre = Genre.objects.annotate(n=Count("books")).order_by("-n")
    genre_books = {"labels": [g.name for g in by_genre], "data": [g.n for g in by_genre]}

    # 3. Average rating per genre (only genres that have any reviews).
    avg_genre = (
        Genre.objects.annotate(avg=Avg("books__reviews__rating"))
        .filter(avg__isnull=False)
        .order_by("-avg")
    )
    genre_avg = {
        "labels": [g.name for g in avg_genre],
        "data": [round(g.avg, 2) for g in avg_genre],
    }

    # 4. Reviews over time, grouped by month.
    timeline_rows = (
        review_qs.annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(c=Count("id"))
        .order_by("month")
    )
    timeline = {
        "labels": [r["month"].strftime("%b %Y") for r in timeline_rows],
        "data": [r["c"] for r in timeline_rows],
    }

    # 5. Top-rated books (need at least one review).
    top_books = (
        Book.objects.annotate(avg=Avg("reviews__rating"), n=Count("reviews"))
        .filter(n__gt=0)
        .order_by("-avg", "-n")[:5]
    )
    top = {
        "labels": [b.title for b in top_books],
        "data": [round(b.avg, 2) for b in top_books],
    }

    context = {
        "charts": {
            "ratings": ratings,
            "genre_books": genre_books,
            "genre_avg": genre_avg,
            "timeline": timeline,
            "top": top,
        },
        "totals": {
            "books": Book.objects.count(),
            "reviews": review_qs.count(),
            "genres": Genre.objects.count(),
            "avg_rating": round(review_qs.aggregate(a=Avg("rating"))["a"] or 0, 2),
        },
        "top_books": top_books,
    }
    return render(request, "catalog/stats.html", context)


def book_detail(request, slug):
    """Show one book, its reviews, and a review form for signed-in members."""
    book = get_object_or_404(
        Book.objects.select_related("genre", "added_by"), slug=slug
    )
    reviews = book.reviews.select_related("author")

    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(author=request.user).first()

    context = {
        "book": book,
        "reviews": reviews,
        "user_review": user_review,
        "review_form": ReviewForm(),
        "is_shelved": (
            request.user.is_authenticated
            and book.shelved_by.filter(pk=request.user.pk).exists()
        ),
    }
    return render(request, "catalog/book_detail.html", context)


@login_required
def book_create(request):
    """Add a new book to the catalog. Restricted to staff/administrators."""
    if not request.user.is_staff:
        messages.error(request, "Only administrators can add books to the catalog.")
        return redirect("catalog:book_list")
    form = BookForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        book = form.save(commit=False)
        book.added_by = request.user
        book.save()
        messages.success(request, f"“{book.title}” was added to the catalog.")
        return redirect(book)
    return render(request, "catalog/book_form.html", {"form": form, "creating": True})


@login_required
def book_edit(request, slug):
    """Edit a book. Only the contributor or staff may do so."""
    book = get_object_or_404(Book, slug=slug)
    if book.added_by != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to edit this book.")
        return redirect(book)

    form = BookForm(request.POST or None, request.FILES or None, instance=book)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Book updated.")
        return redirect(book)
    return render(request, "catalog/book_form.html", {"form": form, "creating": False})


@login_required
@require_POST
def book_delete(request, slug):
    """Delete a book. Only the contributor or staff may do so."""
    book = get_object_or_404(Book, slug=slug)
    if book.added_by != request.user and not request.user.is_staff:
        messages.error(request, "You don't have permission to delete this book.")
        return redirect(book)
    title = book.title
    book.delete()
    messages.success(request, f"“{title}” was deleted.")
    return redirect("catalog:book_list")


@login_required
@require_POST
def review_submit(request, slug):
    """Create or update the current user's review for a book."""
    book = get_object_or_404(Book, slug=slug)
    instance = Review.objects.filter(book=book, author=request.user).first()
    form = ReviewForm(request.POST, instance=instance)
    if form.is_valid():
        review = form.save(commit=False)
        review.book = book
        review.author = request.user
        review.save()
        messages.success(
            request, "Review updated." if instance else "Thanks for your review!"
        )
    else:
        # Surface the first validation error so the user isn't left guessing.
        first_error = next(iter(form.errors.values()))[0]
        messages.error(request, f"Could not save review: {first_error}")
    return redirect(book)


@login_required
@require_POST
def review_delete(request, pk):
    """Delete a review you authored."""
    review = get_object_or_404(Review, pk=pk)
    if review.author != request.user and not request.user.is_staff:
        messages.error(request, "You can only delete your own reviews.")
        return redirect(review.book)
    book = review.book
    review.delete()
    messages.success(request, "Your review was deleted.")
    return redirect(book)


@login_required
@require_POST
def toggle_shelf(request, slug):
    """AJAX endpoint: add/remove a book from the user's reading list.

    Returns JSON so the front-end can update the button without a reload.
    Degrades gracefully to a redirect for non-AJAX (no-JS) requests.
    """
    book = get_object_or_404(Book, slug=slug)
    if book.shelved_by.filter(pk=request.user.pk).exists():
        book.shelved_by.remove(request.user)
        shelved = False
    else:
        book.shelved_by.add(request.user)
        shelved = True

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if is_ajax:
        return JsonResponse(
            {
                "shelved": shelved,
                "count": book.shelved_by.count(),
                "label": "On your shelf" if shelved else "Add to reading list",
            }
        )
    messages.success(
        request, "Added to your reading list." if shelved else "Removed from your list."
    )
    return redirect(book)
