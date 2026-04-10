"""
Unit tests for custom permission classes.
Tests role-based access for admin, teacher, recruiter, question user, and center user.
"""
from django.test import TestCase, RequestFactory
from rest_framework.test import APIRequestFactory
from teacherhire.permissions import (
    IsAdminUser, IsTeacherUser, IsRecruiterUser,
    IsQuestionUser, IsAdminOrTeacher, IsAuthenticatedReadOnly,
)
from .factories import (
    create_admin, create_teacher, create_recruiter,
    create_questionuser, create_user,
)


class MockView:
    """Minimal view mockup for permission checks."""
    pass


class IsAdminUserTest(TestCase):
    def setUp(self):
        self.permission = IsAdminUser()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_admin_has_permission(self):
        admin = create_admin()
        request = self.factory.get("/")
        request.user = admin
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_teacher_denied(self):
        teacher = create_teacher()
        request = self.factory.get("/")
        request.user = teacher
        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_anonymous_denied(self):
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsTeacherUserTest(TestCase):
    def setUp(self):
        self.permission = IsTeacherUser()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_teacher_has_permission(self):
        teacher = create_teacher()
        request = self.factory.get("/")
        request.user = teacher
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_admin_denied(self):
        admin = create_admin()
        request = self.factory.get("/")
        request.user = admin
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsRecruiterUserTest(TestCase):
    def setUp(self):
        self.permission = IsRecruiterUser()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_recruiter_has_permission(self):
        recruiter = create_recruiter()
        request = self.factory.get("/")
        request.user = recruiter
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_teacher_denied(self):
        teacher = create_teacher()
        request = self.factory.get("/")
        request.user = teacher
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsQuestionUserTest(TestCase):
    def setUp(self):
        self.permission = IsQuestionUser()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_questionuser_has_permission(self):
        qu = create_questionuser()
        request = self.factory.get("/")
        request.user = qu
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_teacher_denied(self):
        teacher = create_teacher()
        request = self.factory.get("/")
        request.user = teacher
        self.assertFalse(self.permission.has_permission(request, self.view))


class IsAdminOrTeacherTest(TestCase):
    def setUp(self):
        self.permission = IsAdminOrTeacher()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_admin_has_permission(self):
        admin = create_admin()
        request = self.factory.get("/")
        request.user = admin
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_teacher_has_permission(self):
        teacher = create_teacher()
        request = self.factory.get("/")
        request.user = teacher
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_recruiter_has_permission(self):
        """IsAdminOrTeacher also allows recruiters per the implementation."""
        recruiter = create_recruiter()
        request = self.factory.get("/")
        request.user = recruiter
        self.assertTrue(self.permission.has_permission(request, self.view))


class IsAuthenticatedReadOnlyTest(TestCase):
    def setUp(self):
        self.permission = IsAuthenticatedReadOnly()
        self.factory = APIRequestFactory()
        self.view = MockView()

    def test_get_allowed(self):
        user = create_teacher()
        request = self.factory.get("/")
        request.user = user
        self.assertTrue(self.permission.has_permission(request, self.view))

    def test_post_denied(self):
        user = create_teacher()
        request = self.factory.post("/")
        request.user = user
        self.assertFalse(self.permission.has_permission(request, self.view))

    def test_put_denied(self):
        user = create_teacher()
        request = self.factory.put("/")
        request.user = user
        self.assertFalse(self.permission.has_permission(request, self.view))
