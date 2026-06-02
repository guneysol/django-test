"""Forms for registration and profile editing."""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profile


class SignUpForm(UserCreationForm):
    """Registration form that also captures an email address."""

    email = forms.EmailField(required=True, help_text="Required.")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    """Lets a member edit their public profile."""

    class Meta:
        model = Profile
        fields = ["bio", "location", "favorite_genre", "avatar"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
        }
