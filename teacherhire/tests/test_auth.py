"""
API tests for authentication endpoints.
Tests login, logout, registration, OTP, and access control.
"""
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from teacherhire.models import CustomUser, PendingRegistration
from .factories import create_user, create_teacher, create_admin, get_auth_client


# ─────────────────────────────────────────────
#  Login API
# ─────────────────────────────────────────────
class LoginAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/login/"

    def test_successful_login(self):
        user = create_teacher(email="login@test.com")
        response = self.client.post(self.url, {
            "email": "login@test.com",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "success")
        self.assertIn("access_token", response.data["data"])
        self.assertEqual(response.data["data"]["role"], "teacher")
        self.assertEqual(response.data["data"]["email"], "login@test.com")

    def test_login_returns_correct_role_admin(self):
        create_admin(email="adminlogin@test.com")
        response = self.client.post(self.url, {
            "email": "adminlogin@test.com",
            "password": "AdminPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["role"], "admin")

    def test_login_wrong_password(self):
        create_teacher(email="wrongpw@test.com")
        response = self.client.post(self.url, {
            "email": "wrongpw@test.com",
            "password": "WrongPassword!",
        })
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED
        ])

    def test_login_nonexistent_email(self):
        response = self.client.post(self.url, {
            "email": "nobody@test.com",
            "password": "Password123!",
        })
        self.assertIn(response.status_code, [
            status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED
        ])

    def test_login_inactive_user_blocked(self):
        """Deactivated users should get 403 Forbidden."""
        user = create_teacher(email="inactive@test.com")
        user.is_active = False
        user.save()
        response = self.client.post(self.url, {
            "email": "inactive@test.com",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(response.data.get("is_active", True))

    def test_login_unverified_user_gets_otp_prompt(self):
        """Unverified users should be told to verify, not logged in."""
        user = create_teacher(email="unverified@test.com")
        user.is_verified = False
        user.save()
        response = self.client.post(self.url, {
            "email": "unverified@test.com",
            "password": "TestPass123!",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("verify", response.data.get("message", "").lower())

    def test_login_creates_new_token(self):
        """Each login should create a fresh token (old one deleted)."""
        user = create_teacher(email="tokentest@test.com")
        # First login
        self.client.post(self.url, {
            "email": "tokentest@test.com",
            "password": "TestPass123!",
        })
        first_token = Token.objects.get(user=user).key

        # Second login
        self.client.post(self.url, {
            "email": "tokentest@test.com",
            "password": "TestPass123!",
        })
        second_token = Token.objects.get(user=user).key

        self.assertNotEqual(first_token, second_token)
        self.assertEqual(Token.objects.filter(user=user).count(), 1)

    def test_login_pending_registration_gets_otp(self):
        """If email exists only in PendingRegistration, user should get an OTP prompt."""
        PendingRegistration.objects.create(
            email="pending@test.com",
            password_hash="hashed",
            Fname="Pending",
            role="teacher",
            otp="123456",
        )
        response = self.client.post(self.url, {
            "email": "pending@test.com",
            "password": "anything",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(response.data.get("is_pending", False))


# ─────────────────────────────────────────────
#  Logout API
# ─────────────────────────────────────────────
class LogoutAPITest(TestCase):
    def test_logout_deletes_token(self):
        user = create_teacher(email="logout@test.com")
        client = get_auth_client(user)
        response = client.post("/api/logout/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_logout_unauthenticated(self):
        client = APIClient()
        response = client.post("/api/logout/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────
#  Registration API
# ─────────────────────────────────────────────
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RegistrationAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_teacher(self):
        response = self.client.post("/api/register/teacher/", {
            "email": "newteacher@test.com",
            "password": "StrongPass123!",
            "Fname": "New",
            "Lname": "Teacher",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PendingRegistration.objects.filter(email="newteacher@test.com").exists())

    def test_register_recruiter(self):
        response = self.client.post("/api/register/recruiter/", {
            "email": "newrecruiter@test.com",
            "password": "StrongPass123!",
            "Fname": "New",
            "Lname": "Recruiter",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_register_duplicate_email(self):
        """Registering with an email that already has a full account should fail."""
        create_teacher(email="existing@test.com")
        response = self.client.post("/api/register/teacher/", {
            "email": "existing@test.com",
            "password": "StrongPass123!",
            "Fname": "Dup",
            "Lname": "User",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_weak_password(self):
        """Weak passwords should be rejected by Django validators."""
        response = self.client.post("/api/register/teacher/", {
            "email": "weakpw@test.com",
            "password": "123",
            "Fname": "Weak",
            "Lname": "Pass",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# ─────────────────────────────────────────────
#  Protected Endpoints - Auth Guard
# ─────────────────────────────────────────────
class AuthGuardTest(TestCase):
    """Ensure protected endpoints reject unauthenticated requests."""

    def test_protected_endpoint_requires_auth(self):
        """Unauthenticated access to self/ endpoints should be rejected."""
        client = APIClient()
        response = client.get("/api/self/customuser/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_only_endpoint_requires_admin(self):
        """A teacher token should not access admin-only endpoints like allTeacher."""
        teacher = create_teacher(email="teacher_guard@test.com")
        client = get_auth_client(teacher)
        response = client.get("/api/admin/allTeacher/")
        self.assertIn(response.status_code, [
            status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED
        ])

    def test_admin_can_access_admin_endpoint(self):
        admin = create_admin(email="admin_guard@test.com")
        client = get_auth_client(admin)
        response = client.get("/api/admin/subject/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
