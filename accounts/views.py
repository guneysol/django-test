"""Authentication-adjacent views: signup, profile view/edit, reading list."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProfileForm, SignUpForm


def signup(request):
    """Register a new account and log the user straight in."""
    if request.user.is_authenticated:
        return redirect("catalog:book_list")

    form = SignUpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome to BookNest, {user.username}!")
        return redirect("catalog:book_list")
    return render(request, "registration/signup.html", {"form": form})


def profile_detail(request, username):
    """Public profile page showing a member's reviews and shelf."""
    profile_user = get_object_or_404(
        User.objects.select_related("profile"), username=username
    )
    context = {
        "profile_user": profile_user,
        "reviews": profile_user.reviews.select_related("book"),
        "reading_list": profile_user.reading_list.select_related("genre"),
    }
    return render(request, "accounts/profile_detail.html", context)


@login_required
def profile_edit(request):
    """Let the signed-in user edit their own profile."""
    form = ProfileForm(
        request.POST or None, request.FILES or None, instance=request.user.profile
    )
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile_detail", username=request.user.username)
    return render(request, "accounts/profile_edit.html", {"form": form})
