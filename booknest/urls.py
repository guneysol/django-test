"""Root URL configuration for the BookNest project."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from catalog.api import BookViewSet, GenreViewSet, ReviewViewSet

# --- REST API router ---------------------------------------------------------
router = DefaultRouter()
router.register("books", BookViewSet, basename="book")
router.register("reviews", ReviewViewSet, basename="review")
router.register("genres", GenreViewSet, basename="genre")

# --- Admin branding ----------------------------------------------------------
admin.site.site_header = "📚 BookNest Admin"
admin.site.site_title = "BookNest Admin"
admin.site.index_title = "Catalogue management"

urlpatterns = [
    path("admin/", admin.site.urls),
    # Built-in auth views (login, logout, password management).
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("accounts.urls")),
    # Browsable REST API under /api/ with session-auth login support.
    path("api/", include((router.urls, "api"))),
    path("api-auth/", include("rest_framework.urls")),
    # The catalog owns the site root.
    path("", include("catalog.urls")),
]

# Serve user-uploaded media during development.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
