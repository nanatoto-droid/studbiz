# accounts/views.py
# Register, login, logout, and profile view/edit.

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction

from .forms import RegisterForm, LoginForm, ProfileForm
from business.models import Business


def register(request):
    """Create a User + Business atomically. Business starts unapproved."""
    if request.user.is_authenticated:
        return redirect("business:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                with transaction.atomic():
                    user = User.objects.create_user(
                        username=data["username"],
                        password=data["password"],
                        first_name=data["first_name"],
                        last_name=data["last_name"],
                    )
                    Business.objects.create(
                        owner=user,
                        name=data["business_name"],
                        category=data["category"],
                        university=data["university"],
                        phone=data["phone"],
                        description=data["description"] or "",
                        is_approved=False,
                    )
            except Exception:
                messages.error(request, "Registration failed. Please try again.")
                return render(request, "accounts/register.html", {"form": form})

            messages.success(
                request,
                "Registration successful. Your business is pending approval.",
            )
            return redirect("accounts:login")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Authenticate. Refuse deactivated accounts. Staff go to /admin/."""
    if request.user.is_authenticated:
        return redirect("business:dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            # Deactivated accounts are refused by ModelBackend already, but
            # double-check to give a friendly message.
            if not user.is_active:
                messages.error(request, "This account has been deactivated.")
                return render(request, "accounts/login.html", {"form": form})
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}.")
            if user.is_staff:
                return redirect("/admin/")
            return redirect("business:dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Log the user out (POST preferred; GET also allowed for convenience)."""
    if request.method == "POST" or request.user.is_authenticated:
        logout(request)
        messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def profile_view(request):
    """View or edit the owner's business profile. Staff without a Business
    are redirected to admin with a friendly message."""
    business = getattr(request.user, "business", None)
    if business is None:
        if request.user.is_staff:
            messages.info(request, "Staff accounts use the admin site for management.")
            return redirect("/admin/")
        messages.error(request, "No business profile found for this account.")
        return redirect("accounts:login")

    if request.method == "POST":
        form = ProfileForm(request.POST, instance=business)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=business)

    return render(
        request,
        "accounts/profile.html",
        {"form": form, "business": business},
    )
def home(request):
    """Root URL: send logged-in users to the dashboard, others to login."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("/admin/")
        return redirect("business:dashboard")
    return redirect("accounts:login")