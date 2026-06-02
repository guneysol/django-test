# BookNest — Technical Documentation

This document explains the data model, application architecture and the design
decisions behind BookNest.

---

## 1. Architecture overview

BookNest is a classic server-rendered Django application with a REST API layer
bolted on for programmatic access. It follows Django's MVT
(Model–View–Template) pattern and is split into two focused apps plus the
project package.

```
Request
  │
  ▼
booknest/urls.py ──┬─► accounts.urls ─► accounts.views ─► templates/
                   ├─► catalog.urls  ─► catalog.views  ─► templates/
                   └─► DRF router    ─► catalog.api    ─► serializers ─► JSON
                                          │
                            models (ORM) ◄┘
```

| Package | Responsibility |
|---------|----------------|
| `booknest/` | Settings (environment-aware), root URL config, WSGI entry point. |
| `accounts/` | User `Profile` model, signup, profile pages, and a signal that keeps a profile in sync with every user. |
| `catalog/` | The domain: `Genre`, `Book`, `Review`; the web views, the DRF API, and the Open Library service. |

**Why two apps?** Authentication/identity concerns (`accounts`) are kept
separate from the book domain (`catalog`) so each app stays cohesive and could
be reused or replaced independently.

---

## 2. Data model

```
            ┌───────────┐         ┌──────────────┐
            │   User    │1───────1│   Profile    │
            │ (Django)  │         │ bio,location │
            └─────┬─────┘         └──────────────┘
                  │
     added_by (1..*)│        ┌─ shelved_by (M:N "reading list")
                  │         │
            ┌─────▼─────────▼─┐        ┌──────────┐
            │      Book       │*──────1│  Genre   │
            │ title, author,  │ genre  │ name,slug│
            │ slug, year, …   │        └──────────┘
            └────────┬────────┘
                     │ 1
                     │
                     │ * (reviews)
            ┌────────▼────────┐
            │     Review      │   UNIQUE(book, author)
            │ rating, body, … │
            └─────────────────┘
```

### Entities and relationships

- **`Profile` — `User` (One-to-One).** Extends the built-in auth user with
  public fields (bio, location, favourite genre, avatar) without swapping out
  Django's `User`. A `post_save` signal (`accounts/signals.py`) creates the
  profile automatically, so a profile always exists.

- **`Book` — `Genre` (Many-to-One / ForeignKey).** Each book optionally belongs
  to one genre; `on_delete=SET_NULL` means deleting a genre doesn't delete its
  books. The reverse relation (`genre.books`) powers genre counts.

- **`Book` — `User` via `added_by` (ForeignKey).** Tracks the contributor for
  authorization (only the contributor or staff may edit/delete).

- **`Book` — `User` via `shelved_by` (Many-to-Many).** The "reading list".
  M:N is the natural fit: a user shelves many books and a book is shelved by
  many users. Exposed on the user side as `user.reading_list`.

- **`Review` — `Book` and `Review` — `User` (ForeignKey each).** A review links
  one book to one author. A **`UniqueConstraint(book, author)`** enforces "one
  review per member per book" at the database level (not just in app code), so
  re-submitting updates the existing review instead of duplicating it.

### Data integrity & constraints

- **Unique slugs.** `Genre` and `Book` generate URL slugs in `save()`. `Book`
  loops with a numeric suffix to guarantee uniqueness even for two books with
  the same title and author.
- **Validators.** `rating` is bounded 1–5 (`MinValueValidator`/`MaxValueValidator`
  + `choices`); `published_year` is range-checked.
- **Database-level uniqueness.** The one-review-per-user rule is a real DB
  constraint, verified by a test that expects an `IntegrityError`.
- **Indexes.** `Book.title` and `Book.author` are indexed to keep search fast.

---

## 3. Query efficiency

The catalog is read-heavy, so queries are tuned to avoid the N+1 problem:

- **`select_related`** on `genre`/`added_by`/`author` wherever those FKs are
  rendered (list, detail, profile, API), collapsing per-row lookups into joins.
- **Annotations** (`book_list`): `Avg("reviews__rating")` and
  `Count("reviews")` are computed in a single SQL query and reused for display
  **and** sorting (`?sort=rating|popular`), rather than calling the
  `average_rating` property per object in a loop.
- **Whitelisted ordering.** Sort keys map through a `SORT_OPTIONS` dict so user
  input never reaches `.order_by()` directly.

---

## 4. Views & request flow

All web views live in `catalog/views.py` and `accounts/views.py` as function
based views (chosen for readability in a teaching context).

- **Permission pattern.** Mutating views use `@login_required` and
  `@require_POST`; ownership is checked explicitly (`obj.added_by == request.user
  or request.user.is_staff`) before any write, with a friendly message + redirect
  on failure rather than a bare 403.
- **Review submission** (`review_submit`) uses `get_or_create`-style logic via
  `ModelForm(instance=…)` so the same endpoint creates or updates, honouring the
  unique constraint.
- **AJAX shelf toggle** (`toggle_shelf`) detects `X-Requested-With:
  XMLHttpRequest` and returns JSON for the dynamic path, or falls back to a
  redirect + flash message for clients without JavaScript (progressive
  enhancement).

---

## 5. REST API design (DRF)

- **ViewSets + `DefaultRouter`** give consistent, RESTful URLs and a browsable
  API for free.
- **Permissions are layered:** `IsAuthenticatedOrReadOnly` (global) gates writes,
  and a custom **`IsAuthorOrReadOnly`** object-level permission ensures users can
  only modify their own books/reviews — mirroring the web UI's rules so the two
  interfaces can't diverge.
- **`perform_create`** stamps `added_by`/`author` from `request.user`, so the
  client can't spoof ownership.
- **Built-in `SearchFilter` + `OrderingFilter`** and `PageNumberPagination`
  (page size 10) provide search, sort and paging declaratively.
- **`SlugRelatedField`** lets the API accept/emit a genre by name rather than a
  raw PK, keeping payloads human-readable.

---

## 6. Frontend & UX

- **One responsive stylesheet** (`static/css/styles.css`) using CSS custom
  properties, Flexbox and Grid. Mobile-first with a single breakpoint at 720px;
  the book grid uses `auto-fill` + `minmax` so it reflows naturally.
- **Vanilla JS, no build step** (`static/js/app.js`): mobile nav toggle,
  AJAX shelving, and debounced live search. Everything degrades gracefully — the
  site is fully usable with JavaScript disabled.
- **Accessibility:** semantic landmarks (`header`/`main`/`footer`/`nav`), labelled
  form fields, `aria-pressed` on the toggle button, and `role="status"` on flash
  messages.

---

## 7. Configuration & deployment

- **Environment-aware settings.** `settings.py` reads from environment variables
  with safe local defaults, so the same code runs in dev (SQLite, `DEBUG=1`) and
  prod (Postgres via `DATABASE_URL`, `DEBUG=0`).
- **Security hardening** activates automatically when `DEBUG=0`: SSL redirect,
  HSTS, secure/HTTP-only cookies, `nosniff`, and proxy SSL header handling for
  platforms like Render.
- **Static files** are served by WhiteNoise. In production the
  `CompressedManifestStaticFilesStorage` backend produces hashed, compressed
  assets; in dev the plain backend avoids needing `collectstatic`.

---

## 8. Testing strategy

The 29-test suite (`catalog/tests.py`, `accounts/tests.py`) is organised by
concern:

- **Model tests** — slug generation, average-rating math, the unique-review DB
  constraint.
- **View tests** — page loads, search, genre filter, pagination size,
  login-required redirects, and **authorization** (a non-owner's edit is
  rejected; an owner's delete succeeds).
- **AJAX test** — asserts the JSON response and the M:N side effect of toggling.
- **API tests** — public reads, auth-gated writes, ownership stamping, search.
- **Account tests** — signup creates + logs in a user, duplicate emails are
  rejected, login/logout, profile auto-creation.
- **Integration test** — Open Library import with the network mocked so tests
  stay fast and offline-safe.

Run with `python manage.py test`.
