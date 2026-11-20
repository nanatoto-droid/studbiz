# network/tests.py
# Tests for directory, phone visibility, and partnership requests.

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from business.models import Business
from network.helpers import can_see_phone
from network.models import PartnershipRequest


class NetworkBase(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username="u1", password="pass12345")
        self.u2 = User.objects.create_user(username="u2", password="pass12345")
        self.u3 = User.objects.create_user(username="u3", password="pass12345")
        self.b1 = Business.objects.create(owner=self.u1, name="B1", category="Food",
                                          university="U", phone="111", is_approved=True)
        self.b2 = Business.objects.create(owner=self.u2, name="B2", category="Fashion",
                                          university="U", phone="222", is_approved=True)
        self.b3 = Business.objects.create(owner=self.u3, name="B3", category="Food",
                                          university="U", phone="333", is_approved=False)


class DirectoryTests(NetworkBase):
    def test_only_approved_excluding_self(self):
        self.client.force_login(self.u1)
        resp = self.client.get(reverse("network:directory"))
        ids = [b.id for b in resp.context["businesses"]]
        self.assertIn(self.b2.id, ids)
        self.assertNotIn(self.b1.id, ids)   # self excluded
        self.assertNotIn(self.b3.id, ids)   # unapproved excluded

    def test_unapproved_public_profile_404(self):
        self.client.force_login(self.u1)
        resp = self.client.get(reverse("network:directory_detail", args=[self.b3.id]))
        self.assertEqual(resp.status_code, 404)


class RequestRulesTests(NetworkBase):
    def test_self_request_refused(self):
        self.client.force_login(self.u1)
        resp = self.client.post(reverse("network:send_request", args=[self.b1.id]),
                                {"message": "hi"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(PartnershipRequest.objects.count(), 0)

    def test_duplicate_pending_request_refused(self):
        self.client.force_login(self.u1)
        self.client.post(reverse("network:send_request", args=[self.b2.id]),
                        {"message": "hi"})
        self.assertEqual(PartnershipRequest.objects.count(), 1)
        # Second attempt refused.
        self.client.post(reverse("network:send_request", args=[self.b2.id]),
                        {"message": "hi again"})
        self.assertEqual(PartnershipRequest.objects.count(), 1)

    def test_only_receiver_can_accept(self):
        req = PartnershipRequest.objects.create(
            sender=self.b1, receiver=self.b2, status="Pending", message="x",
        )
        # Owner of b1 (sender) cannot accept.
        self.client.force_login(self.u1)
        self.client.post(reverse("network:accept_request", args=[req.id]))
        req.refresh_from_db()
        self.assertEqual(req.status, "Pending")

        # Owner of b2 (receiver) can accept.
        self.client.force_login(self.u2)
        self.client.post(reverse("network:accept_request", args=[req.id]))
        req.refresh_from_db()
        self.assertEqual(req.status, "Accepted")


class PhoneVisibilityTests(NetworkBase):
    def test_phone_hidden_until_accepted(self):
        self.assertFalse(can_see_phone(self.b1, self.b2))

        req = PartnershipRequest.objects.create(
            sender=self.b1, receiver=self.b2, status="Pending",
        )
        self.assertFalse(can_see_phone(self.b1, self.b2))
        self.assertFalse(can_see_phone(self.b2, self.b1))

        req.status = "Accepted"
        req.save()
        self.assertTrue(can_see_phone(self.b1, self.b2))
        self.assertTrue(can_see_phone(self.b2, self.b1))

        req.status = "Declined"
        req.save()
        self.assertFalse(can_see_phone(self.b1, self.b2))

    def test_phone_visible_in_received_template_only_when_accepted(self):
        self.client.force_login(self.u2)
        # Pending: phone hidden
        r = PartnershipRequest.objects.create(sender=self.b1, receiver=self.b2,
                                              status="Pending", message="x")
        resp = self.client.get(reverse("network:request_list"))
        self.assertNotContains(resp, "111")
        # Accepted: phone visible
        r.status = "Accepted"
        r.save()
        resp = self.client.get(reverse("network:request_list"))
        self.assertContains(resp, "111")
