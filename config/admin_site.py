# config/admin_site.py
# Custom AdminSite that adds summary counts to the admin index.

from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model


class PlatformAdminSite(AdminSite):
    site_header = "Student Business Platform Administration"
    site_title = "Platform Admin"
    index_title = "Administration"

    def index(self, request, extra_context=None):
        from business.models import Business
        from network.models import PartnershipRequest

        User = get_user_model()
        extra_context = extra_context or {}
        extra_context["summary_owners"] = User.objects.filter(is_staff=False).count()
        extra_context["summary_approved"] = Business.objects.filter(is_approved=True).count()
        extra_context["summary_pending"] = Business.objects.filter(is_approved=False).count()
        extra_context["summary_total_requests"] = PartnershipRequest.objects.count()
        extra_context["summary_accepted_requests"] = PartnershipRequest.objects.filter(status="Accepted").count()
        return super().index(request, extra_context=extra_context)


# A single shared admin site instance.
admin_site = PlatformAdminSite(name="admin")