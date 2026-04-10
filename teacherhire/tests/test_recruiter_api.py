"""
API tests for recruiter management endpoints.
Tests the recruiter basic profile list and serializer corrections.
"""
from django.test import TestCase
from rest_framework import status
from teacherhire.models import CustomUser, BasicProfile
from .factories import create_admin, create_recruiter, get_auth_client


class RecruiterAdminAPITest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.client = get_auth_client(self.admin)
        self.url = "/api/all/recruiter/basicProfile/"

    def test_list_recruiters_includes_pending(self):
        """Verify that the list includes both verified and unverified recruiters."""
        create_recruiter(email="verified@test.com", is_verified=True)
        create_recruiter(email="pending@test.com", is_verified=False)
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should have 2 recruiters
        self.assertEqual(len(response.data), 2)

    def test_recruiter_basic_profile_serialization(self):
        """Verify that basic profile data (bio, phone) is correctly serialized."""
        recruiter = create_recruiter(email="profile@test.com")
        BasicProfile.objects.create(
            user=recruiter,
            bio="Test Bio",
            phone_number="1234567890",
            gender="male"
        )
        
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Find our recruiter in the results
        rec_data = next(r for r in response.data if r['email'] == "profile@test.com")
        self.assertEqual(rec_data['profiles']['bio'], "Test Bio")
        self.assertEqual(rec_data['profiles']['phone_number'], "1234567890")
        self.assertEqual(rec_data['profiles']['gender'], "male")

    def test_non_admin_cannot_access_recruiter_list(self):
        """Verify only admins can access this endpoint."""
        recruiter = create_recruiter(email="other_rec@test.com")
        client = get_auth_client(recruiter)
        
        response = client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
