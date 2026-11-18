# accounts/forms.py
# Forms for registration, login, and profile editing.

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from business.models import Business


class RegisterForm(forms.Form):
    """Collects everything needed to create a User and their Business."""

    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=True)
    phone = forms.CharField(max_length=20, required=True)
    business_name = forms.CharField(max_length=150, required=True)
    category = forms.ChoiceField(choices=Business.CATEGORY_CHOICES, required=True)
    university = forms.CharField(max_length=150, required=True)
    description = forms.CharField(widget=forms.Textarea, required=False)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("That username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password")
        p2 = cleaned.get("password_confirm")
        if p1 and p2 and p1 != p2:
            self.add_error("password_confirm", "Passwords do not match.")
        return cleaned


class LoginForm(AuthenticationForm):
    """Small override so the label reads 'Username' and 'Password'."""

    username = forms.CharField(label="Username", max_length=150)
    password = forms.CharField(label="Password", widget=forms.PasswordInput)


class ProfileForm(forms.ModelForm):
    """Edit the owner's Business profile fields."""

    class Meta:
        model = Business
        fields = ["name", "category", "university", "phone", "description"]