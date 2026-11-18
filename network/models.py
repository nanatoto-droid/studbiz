# network/models.py
# PartnershipRequest links two businesses.

from django.db import models
from business.models import Business


class PartnershipRequest(models.Model):
    """A request from one business to partner with another."""

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Accepted", "Accepted"),
        ("Declined", "Declined"),
    ]

    sender = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="sent_requests",
    )
    receiver = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name="received_requests",
    )
    message = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender.name} -> {self.receiver.name} [{self.status}]"


