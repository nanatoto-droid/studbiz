# network/views.py
# Directory, public profile, and partnership requests.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q

from business.models import Business
from .models import PartnershipRequest
from .forms import PartnershipRequestForm
from .helpers import can_see_phone


def _viewer_business(request):
    """Return the logged-in user's Business or None."""
    return getattr(request.user, "business", None)


@login_required
def directory(request):
    """List APPROVED businesses only, excluding the viewer's own business."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    qs = Business.objects.filter(is_approved=True).exclude(id=viewer.id)

    q = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    university = request.GET.get("university", "").strip()

    if q:
        qs = qs.filter(
            Q(name__icontains=q)
            | Q(category__icontains=q)
            | Q(university__icontains=q)
        )
    if category:
        qs = qs.filter(category=category)
    if university:
        qs = qs.filter(university__icontains=university)

    qs = qs.order_by("name")

    # Suggestions: approved businesses with same category OR university, not self.
    suggestions = (
        Business.objects.filter(is_approved=True)
        .exclude(id=viewer.id)
        .filter(Q(category=viewer.category) | Q(university=viewer.university))
        .order_by("name")[:10]
    )

    # Which of these already have an Accepted request with the viewer?
    accepted_ids = set()
    for r in PartnershipRequest.objects.filter(
        Q(sender=viewer) | Q(receiver=viewer), status="Accepted"
    ):
        other = r.receiver_id if r.sender_id == viewer.id else r.sender_id
        accepted_ids.add(other)

    return render(request, "network/directory.html", {
        "businesses": qs,
        "suggestions": suggestions,
        "category_choices": Business.CATEGORY_CHOICES,
        "q": q,
        "category": category,
        "university": university,
        "viewer": viewer,
        "accepted_ids": accepted_ids,
    })


@login_required
def directory_detail(request, pk):
    """Public profile of an approved business. 404 if not approved."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    target = get_object_or_404(Business, pk=pk)
    if not target.is_approved:
        # Non-approved businesses must not be viewable publicly.
        from django.http import Http404
        raise Http404("Business not available.")

    show_phone = can_see_phone(viewer, target)

    # Report whether a Pending request already exists (to disable the button).
    already_pending = False
    if viewer.id != target.id:
        already_pending = PartnershipRequest.objects.filter(
            sender=viewer, receiver=target, status="Pending"
        ).exists()

    return render(request, "network/directory_detail.html", {
        "target": target,
        "show_phone": show_phone,
        "already_pending": already_pending,
        "is_self": viewer.id == target.id,
    })


@login_required
def send_request(request, pk):
    """Send a partnership request to an approved business."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    target = get_object_or_404(Business, pk=pk, is_approved=True)

    if target.id == viewer.id:
        messages.error(request, "You cannot send a partnership request to yourself.")
        return redirect("network:directory_detail", pk=target.id)

    if PartnershipRequest.objects.filter(sender=viewer, receiver=target, status="Pending").exists():
        messages.error(request, "You already have a pending request to this business.")
        return redirect("network:directory_detail", pk=target.id)

    if request.method == "POST":
        form = PartnershipRequestForm(request.POST)
        if form.is_valid():
            PartnershipRequest.objects.create(
                sender=viewer,
                receiver=target,
                message=form.cleaned_data["message"],
                status="Pending",
            )
            messages.success(request, f"Partnership request sent to {target.name}.")
            return redirect("network:request_list")
    else:
        form = PartnershipRequestForm()

    return render(request, "network/send_request.html", {
        "target": target, "form": form,
    })


@login_required
def request_list(request):
    """Show received and sent requests."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    received = PartnershipRequest.objects.filter(receiver=viewer).select_related(
        "sender", "receiver"
    ).order_by("-created_at")
    sent = PartnershipRequest.objects.filter(sender=viewer).select_related(
        "sender", "receiver"
    ).order_by("-created_at")

    return render(request, "network/request_list.html", {
        "received": received,
        "sent": sent,
    })


@login_required
def accept_request(request, pk):
    """Accept a Pending request. Only the receiver may do this."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    req = get_object_or_404(PartnershipRequest, pk=pk)
    if req.receiver_id != viewer.id:
        messages.error(request, "Only the receiver can accept this request.")
        return redirect("network:request_list")
    if req.status != "Pending":
        messages.error(request, "This request is no longer pending.")
        return redirect("network:request_list")

    if request.method == "POST":
        with transaction.atomic():
            req.status = "Accepted"
            req.save(update_fields=["status"])
        messages.success(request, f"You are now partners with {req.sender.name}.")
        return redirect("network:request_list")

    return render(request, "network/request_action.html", {"req": req, "action": "Accept"})


@login_required
def decline_request(request, pk):
    """Decline a Pending request. Only the receiver may do this."""
    viewer = _viewer_business(request)
    if viewer is None:
        return _no_business(request)

    req = get_object_or_404(PartnershipRequest, pk=pk)
    if req.receiver_id != viewer.id:
        messages.error(request, "Only the receiver can decline this request.")
        return redirect("network:request_list")
    if req.status != "Pending":
        messages.error(request, "This request is no longer pending.")
        return redirect("network:request_list")

    if request.method == "POST":
        with transaction.atomic():
            req.status = "Declined"
            req.save(update_fields=["status"])
        messages.info(request, f"You declined the request from {req.sender.name}.")
        return redirect("network:request_list")

    return render(request, "network/request_action.html", {"req": req, "action": "Decline"})


def _no_business(request):
    """Staff or owner without a Business — do not crash."""
    if request.user.is_staff:
        messages.info(request, "Staff accounts use the admin site.")
        return redirect("/admin/")
    messages.error(request, "No business profile found for this account.")
    return redirect("accounts:login")