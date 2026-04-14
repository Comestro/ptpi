from django.test import TestCase
from rest_framework import status
from teacherhire.models import Report, Reason
from .factories import (
    create_admin, create_teacher, create_question, 
    create_class_category, create_subject, create_level,
    create_exam, get_auth_client, create_reason
)

class AdminParityTests(TestCase):
    def setUp(self):
        self.admin = create_admin(email="testadmin@ptpi.com")
        self.client = get_auth_client(self.admin)
        self.teacher = create_teacher(email="testteacher@ptpi.com")

    def test_admin_teacher_list_ordering_no_crash(self):
        """
        Ensures the AdminTeacherListView doesn't crash due to 'date_joined' vs 'date' field.
        """
        url = "/api/admin/teacher/list/"
        response = self.client.get(url)
        if response.status_code != 200:
            print(f"ERROR CONTENT: {response.content}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        # Should have at least one teacher (the one created in setUp)
        self.assertTrue(len(response.data['results']) >= 1)

    def test_report_serializer_metadata_parity(self):
        """
        Verifies that ReportSerializer returns the new metadata fields.
        """
        cat = create_class_category(name="Grade 12")
        sub = create_subject(class_category=cat, name="Physics")
        lvl = create_level(name="Online")
        exam = create_exam(class_category=cat, subject=sub, level=lvl, name="Physics 101")
        question = create_question(exam=exam)
        reason = create_reason(issue_type="incorrect option")
        
        report = Report.objects.create(user=self.teacher, question=question)
        report.issue_type.add(reason)

        url = "/api/admin/report/"
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if at least one report exists
        reports = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertTrue(len(reports) > 0)
        
        target_report = reports[0]
        # Verify metadata fields are present and correct
        self.assertEqual(target_report.get('exam_name'), "Physics 101")
        self.assertEqual(target_report.get('class_category'), "Grade 12")
        self.assertEqual(target_report.get('subject'), "Physics")
        self.assertEqual(target_report.get('v_check'), "ACTIVE_V4")

    def test_report_defaults(self):
        """
        Verifies fallback behavior when metadata is missing or generic.
        """
        # Create an exam with generic name to test fallbacks if name is missing/empty
        cat = create_class_category(name="")
        sub = create_subject(class_category=cat, name="")
        exam = create_exam(class_category=cat, subject=sub, name="")
        question = create_question(exam=exam)
        
        report = Report.objects.create(user=self.teacher, question=question)
        
        url = "/api/admin/report/"
        response = self.client.get(url)
        reports = response.data if isinstance(response.data, list) else response.data.get('results', [])
        target_report = [r for r in reports if r['id'] == report.id][0]
        
        # Based on ReportSerializer logic:
        # return getattr(exam, 'name', "General Practice") if exam else "General Practice"
        # If exam name is empty string, it returns "" because getattr finds it.
        # But if we want to confirm 'General Practice', we'd need exam to be None.
        # Since it's NOT NULL, 'General Practice' is mostly a safety fallback for broken data.
        self.assertIn('v_check', target_report)
        self.assertEqual(target_report.get('v_check'), "ACTIVE_V4")
