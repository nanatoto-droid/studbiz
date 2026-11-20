# accounts/tests.py
# Tests for registration, login, logout, deactivated accounts, staff redirect.

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from business.models import Business


class RegistrationTests(TestCase):
    def test_register_creates_user_and_unapproved_business(self):
        resp = self.client.post(reverse("accounts:register"), {
            "first_name": "Amina", "last_name": "Otieno",
            "username": "amina", "password": "supersecret1",
            "password_confirm": "supersecret1",
            "phone": "0700000001", "business_name": "Amina's Snacks",
            "category": "Food", "university": "Strathmore",
            "description": "Snacks",
        })
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="amina")
        # Password is hashed, not stored in plain.
        self.assertNotEqual(user.password, "supersecret1")
        self.assertTrue(user.check_password("supersecret1"))
        biz = Business.objects.get(owner=user)
        self.assertFalse(biz.is_approved)

    def test_repeated_username_shows_error_and_saves_nothing(self):
        User.objects.create_user(username="dup", password="x")
        before_users = User.objects.count()
        before_biz = Business.objects.count()
        resp = self.client.post(reverse("accounts:register"), {
            "first_name": "A", "last_name": "B",
            "username": "dup", "password": "pw123456",
            "password_confirm": "pw123456",
            "phone": "07", "business_name": "X",
            "category": "Food", "university": "U", "description": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(User.objects.count(), before_users)
        self.assertEqual(Business.objects.count(), before_biz)

    def test_mismatched_passwords_shows_error_and_saves_nothing(self):
        resp = self.client.post(reverse("accounts:register"), {
            "first_name": "A", "last_name": "B",
            "username": "new", "password": "pw123456",
            "password_confirm": "different1",
            "phone": "07", "business_name": "X",
            "category": "Food", "university": "U", "description": "",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(User.objects.filter(username="new").exists())


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass12345")
        Business.objects.create(
            owner=self.user, name="X", category="Food",
            university="U", phone="07", is_approved=True,
        )

    def test_normal_login_redirects_to_dashboard(self):
        resp = self.client.post(reverse("accounts:login"), {
            "username": "owner", "password": "pass12345",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(resp.url.startswith("/dashboard/"))

    def test_staff_login_redirects_to_admin(self):
        staff = User.objects.create_user(username="admin", password="pass12345", is_staff=True)
        resp = self.client.post(reverse("accounts:login"), {
            "username": "admin", "password": "pass12345",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/admin/")

    def test_deactivated_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(reverse("accounts:login"), {
            "username": "owner", "password": "pass12345",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)


class LogoutTests(TestCase):
    def test_logout_clears_session(self):
        user = User.objects.create_user(username="u", password="pass12345")
        Business.objects.create(owner=user, name="N", category="Food",
                                university="U", phone="07", is_approved=True)
        self.client.force_login(user)
        self.client.post(reverse("accounts:logout"))
        self.assertNotIn("_auth_user_id", self.client.session)


class StaffWithoutBusinessTests(TestCase):
    def test_staff_without_business_does_not_crash(self):
        staff = User.objects.create_user(username="s", password="pass12345", is_staff=True)
        self.client.force_login(staff)
        for name in ("accounts:profile", "business:dashboard",
                     "business:product_list", "network:directory"):
            resp = self.client.get(reverse(name))
            # Either a redirect or a 200 is fine — no 500.
            self.assertIn(resp.status_code, (200, 302))

