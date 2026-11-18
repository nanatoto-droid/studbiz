# network/context_processors.py
# Supplies the navbar pending-request count and admin summary counts.

from .models import PartnershipRequest


def pending_requests_count(request):
    """Add pending_requests_count to every template context.

    Also adds admin summary numbers when rendering the admin index page.
    """
    from django.contrib.auth import get_user_model
    from business.models import Business

    context = {"pending_requests_count": 0}

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated and not user.is_staff:
        business = getattr(user, "business", None)
        if business is not None:
            context["pending_requests_count"] = PartnershipRequest.objects.filter(
                receiver=business, status="Pending"
            ).count()

    # Admin summary counts (safe defaults; only used by admin/index.html).
    if request.path.startswith("/admin"):
        User = get_user_model()
        context["summary_owners"] = User.objects.filter(is_staff=False).count()
        context["summary_approved"] = Business.objects.filter(is_approved=True).count()
        context["summary_pending"] = Business.objects.filter(is_approved=False).count()
        context["summary_total_requests"] = PartnershipRequest.objects.count()
        context["summary_accepted_requests"] = PartnershipRequest.objects.filter(
            status="Accepted"
        ).count()

    return context