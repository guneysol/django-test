# 📚 BookNest

A community book-review platform built with Django. Members can catalogue
books, rate and review them, curate a personal reading list, and explore what
the community is reading. BookNest ships with a REST API, AJAX interactions,
search, filtering, pagination, authentication and a responsive UI.

> Django term project. Built on **Django 6.0** + **Django REST Framework**.

---

## ✨ Features

| Area | What it does |
|------|--------------|
| **Books (CRUD)** | Create, read, update and delete books. Auto-generated unique slugs, optional cover image, genre, publication year. |
| **Reviews (CRUD)** | One rating (1–5★) + write-up per member per book; create/update/delete with ownership checks. |
| **Genres** | Books are categorised; browse and filter by genre with live counts. |
| **Reading list** | Shelve/unshelve any book (many-to-many) — updated instantly via **AJAX**, with a no-JS fallback. |
| **Authentication** | Sign up, log in, log out using Django's auth system; a `Profile` is auto-created per user. |
| **Authorization** | Only a book's contributor (or staff) can edit/delete it; members can only edit their own reviews. Enforced in views *and* the API. |
| **Search & filter** | Search by title/author/description, filter by genre, and sort by title / newest / rating / popularity. |
| **Pagination** | Paginated book grid that preserves the active search, filter and sort. |
| **REST API** | Full DRF API for books, reviews and genres with a browsable UI, search and ordering. |
| **Third-party API** | Import real book metadata from the [Open Library](https://openlibrary.org) API. |
| **Profiles** | Public profile pages showing a member's reviews and reading list. |
| **Admin** | Rich Django admin with inlines, filters, search and slug prepopulation. |

That comfortably exceeds the "3+ advanced features" bar (authentication,
authorization, search/filter, pagination, REST API, AJAX, and third-party API
integration — **7 in total**).

---

## 🛠 Tech stack

- **Backend:** Django 6.0, Django REST Framework 3.17
- **Database:** SQLite (dev) / PostgreSQL (prod, via `DATABASE_URL`)
- **Frontend:** Server-rendered Django templates + vanilla JS (no build step)
- **Static files:** WhiteNoise (compressed, hashed in production)
- **Server:** Gunicorn
- **Deployment:** Render.com blueprint included

---

## 🚀 Quick start (local)

```bash
# 1. Clone and enter the project
cd django-proj

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Apply migrations
python manage.py migrate

# 5. Seed demo data (genres, books, users, reviews)
python manage.py seed_data

# 6. (Optional) create an admin account
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

Visit **http://127.0.0.1:8000/**.

### Demo accounts (after `seed_data`)

| Username | Password |
|----------|----------|
| `ada` / `grace` / `linus` / `margaret` | `booknest123` |

---

## 🔌 REST API

Browsable at **`/api/`**. Reads are public; writes require login
(`/api-auth/login/`).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/books/` | List books (`?search=`, `?ordering=`, `?page=`) |
| `POST` | `/api/books/` | Create a book (auth required) |
| `GET/PUT/PATCH/DELETE` | `/api/books/{slug}/` | Retrieve/update/delete a book (owner only) |
| `GET/POST` | `/api/reviews/` | List/create reviews |
| `GET/PUT/PATCH/DELETE` | `/api/reviews/{id}/` | Manage a review (author only) |
| `GET` | `/api/genres/` | List genres (read-only) |

Example:

```bash
curl "http://127.0.0.1:8000/api/books/?search=dune&ordering=-published_year"
```

---

## 🌐 Third-party API: importing from Open Library

```bash
# Preview without writing
python manage.py import_openlibrary "ursula k le guin" --limit 3 --dry-run

# Import for real (de-duplicated, safe to re-run)
python manage.py import_openlibrary "brandon sanderson" --limit 5
```

---

## ✅ Testing

```bash
python manage.py test
```

29 tests cover models, slug generation, the unique-review constraint, every
view, permission boundaries, search/filter/pagination, the AJAX endpoint, the
REST API, signup/login/logout, and the Open Library integration (network
mocked).

---

## ☁️ Deployment (Render.com)

The repo includes a `render.yaml` blueprint, `build.sh`, and a `Procfile`.

1. Push to GitHub.
2. On Render, choose **New → Blueprint** and point it at the repo.
3. Render provisions a web service + free Postgres, generates a secret key, and
   runs `build.sh` (install → collectstatic → migrate).
4. Set `DJANGO_ALLOWED_HOSTS` to your `*.onrender.com` hostname.
5. After deploy, seed data from the Render shell: `python manage.py seed_data`.

### Configuration (environment variables)

See [`.env.example`](.env.example). Key variables:

| Variable | Default | Purpose |
|----------|---------|---------|
| `DJANGO_DEBUG` | `1` | Set `0` in production to enable security hardening |
| `DJANGO_SECRET_KEY` | dev key | **Required** in production |
| `DJANGO_ALLOWED_HOSTS` | localhost | Comma-separated allowed hosts |
| `DATABASE_URL` | (SQLite) | Postgres connection string |

With `DEBUG=0`, BookNest automatically enables SSL redirect, HSTS, secure
cookies and `nosniff`. Verify with `python manage.py check --deploy`.

---

## 📁 Project layout

```
booknest/        Project settings, root URLs, WSGI
accounts/        User profiles, signup, profile pages, auth signals
catalog/         Books, genres, reviews; web views + DRF API + services
templates/       Base layout + per-app templates
static/          CSS and JS (no build step)
```

See [`DOCUMENTATION.md`](DOCUMENTATION.md) for the data model, architecture and
design decisions.

---

## 📄 License

Educational project — free to use and adapt.
