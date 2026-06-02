"""Populate the database with realistic demo data.

Usage::

    python manage.py seed_data          # add demo data (idempotent)
    python manage.py seed_data --flush   # wipe catalog data first

Creates genres, books, a handful of users and a spread of reviews so the UI,
search, filtering, pagination and ratings can be explored immediately.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Book, Genre, Review

GENRES = ["Science Fiction", "Fantasy", "Mystery", "Non-Fiction", "Romance", "History"]

# Cover artwork is pulled live from the Open Library Covers API by ISBN:
#   https://covers.openlibrary.org/b/isbn/<isbn>-L.jpg
# (title, author, genre, year, description, isbn)
BOOKS = [
    ("Dune", "Frank Herbert", "Science Fiction", 1965,
     "A desert planet, a precious spice, and a young heir caught in a galactic power struggle.",
     "9780441013593"),
    ("Neuromancer", "William Gibson", "Science Fiction", 1984,
     "A washed-up hacker is hired for one last job in cyberspace.",
     "9780441569595"),
    ("The Hobbit", "J.R.R. Tolkien", "Fantasy", 1937,
     "Bilbo Baggins is swept into a quest to reclaim a treasure guarded by a dragon.",
     "9780547928227"),
    ("The Name of the Wind", "Patrick Rothfuss", "Fantasy", 2007,
     "The story of Kvothe, a legendary figure recounting his rise from gifted child to notorious wizard.",
     "9780756404741"),
    ("Gone Girl", "Gillian Flynn", "Mystery", 2012,
     "On their fifth anniversary, Amy disappears and Nick becomes the prime suspect.",
     "9780307588371"),
    ("The Girl with the Dragon Tattoo", "Stieg Larsson", "Mystery", 2005,
     "A journalist and a brilliant hacker investigate a decades-old disappearance.",
     "9780307454546"),
    ("Sapiens", "Yuval Noah Harari", "Non-Fiction", 2011,
     "A sweeping look at how Homo sapiens came to dominate the planet.",
     "9780062316097"),
    ("Educated", "Tara Westover", "Non-Fiction", 2018,
     "A memoir of growing up off-grid and the transformative power of education.",
     "9780399590504"),
    ("Pride and Prejudice", "Jane Austen", "Romance", 1813,
     "Elizabeth Bennet navigates manners, morality and marriage in Georgian England.",
     "9780141439518"),
    ("The Notebook", "Nicholas Sparks", "Romance", 1996,
     "An enduring love story told across decades.",
     "9780553816716"),
    ("Guns, Germs, and Steel", "Jared Diamond", "History", 1997,
     "Why some societies advanced while others did not — geography as destiny.",
     "9780393317558"),
    ("A People's History of the United States", "Howard Zinn", "History", 1980,
     "American history told from the perspective of ordinary people.",
     "9780062397348"),
    ("Project Hail Mary", "Andy Weir", "Science Fiction", 2021,
     "A lone astronaut wakes with no memory and the fate of humanity on his shoulders.",
     "9780593135204"),
    ("Mistborn", "Brandon Sanderson", "Fantasy", 2006,
     "In a world of ash and oppression, a street thief discovers she can wield metals as magic.",
     "9780765311788"),
]

REVIEWS = [
    (5, "A masterpiece", "Dense but rewarding. The world-building is unmatched."),
    (4, "Really enjoyed it", "Pacing drags in the middle but the payoff is worth it."),
    (3, "Decent read", "Solid, though it didn't quite live up to the hype for me."),
    (5, "Couldn't put it down", "Read it in two sittings. Highly recommended."),
    (4, "Smart and engaging", "Thought-provoking with memorable characters."),
]


class Command(BaseCommand):
    help = "Seed the database with demo genres, books, users and reviews."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing catalog data before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            Review.objects.all().delete()
            Book.objects.all().delete()
            Genre.objects.all().delete()
            self.stdout.write(self.style.WARNING("Flushed existing catalog data."))

        genres = {name: Genre.objects.get_or_create(name=name)[0] for name in GENRES}

        # Demo users (password is the same for all to ease grading/testing).
        users = []
        for name in ["ada", "grace", "linus", "margaret"]:
            user, created = User.objects.get_or_create(
                username=name, defaults={"email": f"{name}@example.com"}
            )
            if created:
                user.set_password("booknest123")
                user.save()
            users.append(user)

        created_books = 0
        for i, (title, author, genre_name, year, desc, isbn) in enumerate(BOOKS):
            cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
            book, created = Book.objects.get_or_create(
                title=title,
                author=author,
                defaults={
                    "genre": genres[genre_name],
                    "published_year": year,
                    "description": desc,
                    "cover_url": cover_url,
                    "added_by": users[i % len(users)],
                },
            )
            if not created and not book.cover_url:
                # Backfill artwork for books seeded before covers were added.
                book.cover_url = cover_url
                book.save(update_fields=["cover_url"])
            if created:
                created_books += 1
            # Attach a couple of reviews from different users per book.
            for j in range(2):
                reviewer = users[(i + j + 1) % len(users)]
                rating, headline, body = REVIEWS[(i + j) % len(REVIEWS)]
                Review.objects.get_or_create(
                    book=book,
                    author=reviewer,
                    defaults={"rating": rating, "headline": headline, "body": body},
                )

        # Spread review dates across the last ~6 months so the Insights timeline
        # chart shows a realistic trend. (`update` bypasses auto_now_add.)
        now = timezone.now()
        for idx, review in enumerate(Review.objects.order_by("id")):
            days_ago = (idx * 6) % 175
            Review.objects.filter(pk=review.pk).update(
                created_at=now - timedelta(days=days_ago)
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed complete: {len(genres)} genres, {Book.objects.count()} books "
                f"({created_books} new), {User.objects.count()} users, "
                f"{Review.objects.count()} reviews."
            )
        )
        self.stdout.write("Demo login → username: ada / password: booknest123")
