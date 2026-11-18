# network/helpers.py
# One helper decides phone visibility. Use it everywhere.

from .models import PartnershipRequest


def can_see_phone(viewer_business, target_business):
    """Return True if viewer_business may see target_business.phone.

    Phone is shown ONLY when a PartnershipRequest between the two businesses
    is Accepted (in either direction). Pending and Declined hide it.
    """
    if viewer_business is None or target_business is None:
        return False
    if viewer_business.id == target_business.id:
        return True  # you can always see your own phone
    return PartnershipRequest.objects.filter(
        status="Accepted",
    ).filter(
        sender=viewer_business, receiver=target_business,
    ).exists() or PartnershipRequest.objects.filter(
        status="Accepted",
    ).filter(
        sender=target_business, receiver=viewer_business,
    ).exists()