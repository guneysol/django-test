"""Import books from the Open Library public API.

Example::

    python manage.py import_openlibrary "brandon sanderson" --limit 3

Demonstrates third-party API integration. Imports are de-duplicated against
existing (title, author) pairs so the command is safe to re-run.
"""

from django.core.management.base import BaseCommand, CommandError

from catalog.models import Book
from catalog.services import OpenLibraryError, search_books


class Command(BaseCommand):
    help = "Import books matching a query from the Open Library API."

    def add_arguments(self, parser):
        parser.add_argument("query", help="Search term, e.g. an author or title.")
        parser.add_argument("--limit", type=int, default=5, help="Max results to import.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without writing to the database.",
        )

    def handle(self, *args, **options):
        query = options["query"]
        try:
            results = search_books(query, limit=options["limit"])
        except OpenLibraryError as exc:
            raise CommandError(str(exc))

        if not results:
            self.stdout.write(self.style.WARNING(f"No results for “{query}”."))
            return

        created = 0
        for data in results:
            label = f"{data['title']} — {data['author']}"
            if options["dry_run"]:
                self.stdout.write(f"[dry-run] would import: {label}")
                continue
            _, was_created = Book.objects.get_or_create(
                title=data["title"],
                author=data["author"],
                defaults={
                    "published_year": data["published_year"],
                    "description": data["description"],
                    "cover_url": data.get("cover_url", ""),
                },
            )
            status = "imported" if was_created else "already present"
            created += int(was_created)
            self.stdout.write(f"{status}: {label}")

        if not options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(f"Done. {created} new book(s) imported.")
            )
