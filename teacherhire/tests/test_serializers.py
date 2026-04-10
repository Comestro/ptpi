"""
Unit tests for teacherhire serializers.
Tests validation logic, data transformation, and create/update behavior.
"""
from django.test import TestCase
from rest_framework.test import APIRequestFactory
from teacherhire.serializers import (
    QuestionSerializer, NewQuestionSerializer, ExamSerializer,
    SubjectSerializer, ClassCategorySerializer, LevelSerializer,
    SkillSerializer, TeachersAddressSerializer,
    TeacherExamResultSerializer,
)
from teacherhire.models import Question
from .factories import (
    create_user, create_admin, create_teacher, create_class_category,
    create_subject, create_level, create_skill, create_exam, create_question,
)


# ─────────────────────────────────────────────
#  QuestionSerializer
# ─────────────────────────────────────────────
class QuestionSerializerTest(TestCase):
    def test_valid_question_data(self):
        exam = create_exam()
        data = {
            "text": "What is the capital of India?",
            "options": ["Delhi", "Mumbai", "Kolkata", "Chennai"],
            "correct_option": 1,
            "exam": exam.id,
            "language": "English",
        }
        serializer = QuestionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_text_too_short(self):
        exam = create_exam()
        data = {
            "text": "Hi",  # Less than 5 chars
            "options": ["A", "B", "C", "D"],
            "correct_option": 1,
            "exam": exam.id,
            "language": "English",
        }
        serializer = QuestionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("text", serializer.errors)

    def test_duplicate_options_rejected(self):
        exam = create_exam()
        data = {
            "text": "A valid question text",
            "options": ["Same", "Same", "C", "D"],
            "correct_option": 1,
            "exam": exam.id,
            "language": "English",
        }
        serializer = QuestionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("options", serializer.errors)

    def test_empty_options_skipped_in_uniqueness_check(self):
        """Empty options should not trigger the uniqueness validation."""
        exam = create_exam()
        data = {
            "text": "Question with partial options",
            "options": ["", "", "", ""],
            "correct_option": 1,
            "exam": exam.id,
            "language": "Hindi",
        }
        serializer = QuestionSerializer(data=data)
        # Empty options should pass uniqueness but may fail other validation
        is_valid = serializer.is_valid()
        if not is_valid:
            # Should NOT have an "options must be unique" error
            options_errors = serializer.errors.get("options", [])
            for err in options_errors:
                self.assertNotIn("unique", str(err).lower())

    def test_correct_option_min_value(self):
        exam = create_exam()
        data = {
            "text": "A valid question text here",
            "options": ["A", "B", "C", "D"],
            "correct_option": 0,  # min_value=1 in serializer
            "exam": exam.id,
            "language": "English",
        }
        serializer = QuestionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("correct_option", serializer.errors)


# ─────────────────────────────────────────────
#  NewQuestionSerializer
# ─────────────────────────────────────────────
class NewQuestionSerializerTest(TestCase):
    def test_valid_question(self):
        exam = create_exam()
        data = {
            "text": "What is Newton's first law?",
            "options": ["Inertia", "F=ma", "Action-Reaction", "Gravity"],
            "correct_option": 1,
            "exam": exam.id,
            "language": "English",
        }
        serializer = NewQuestionSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_options_rejected(self):
        exam = create_exam()
        data = {
            "text": "Choose the correct answer",
            "options": ["Same", "Same", "Diff1", "Diff2"],
            "correct_option": 1,
            "exam": exam.id,
            "language": "English",
        }
        serializer = NewQuestionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("options", serializer.errors)

    def test_empty_options_not_flagged_as_duplicates(self):
        """Empty strings in options should pass uniqueness validation."""
        exam = create_exam()
        data = {
            "text": "Question with empty options",
            "options": ["", "", "", ""],
            "correct_option": 1,
            "exam": exam.id,
            "language": "Hindi",
        }
        serializer = NewQuestionSerializer(data=data)
        is_valid = serializer.is_valid()
        if not is_valid:
            options_errors = serializer.errors.get("options", [])
            for err in options_errors:
                self.assertNotIn("unique", str(err).lower())


# ─────────────────────────────────────────────
#  SubjectSerializer
# ─────────────────────────────────────────────
class SubjectSerializerTest(TestCase):
    def test_valid_subject(self):
        cat = create_class_category()
        data = {"subject_name": "Chemistry", "class_category": cat.id}
        serializer = SubjectSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_subject_in_same_category(self):
        cat = create_class_category()
        create_subject(cat, "Physics")
        data = {"subject_name": "Physics", "class_category": cat.id}
        serializer = SubjectSerializer(data=data)
        self.assertFalse(serializer.is_valid())

    def test_same_subject_name_different_categories(self):
        cat1 = create_class_category("Class 10")
        cat2 = create_class_category("Class 12")
        create_subject(cat1, "Physics")
        data = {"subject_name": "Physics", "class_category": cat2.id}
        serializer = SubjectSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


# ─────────────────────────────────────────────
#  LevelSerializer
# ─────────────────────────────────────────────
class LevelSerializerTest(TestCase):
    def test_valid_level(self):
        data = {"name": "3rd Level Interview", "level_code": 3.0}
        serializer = LevelSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicate_level_name_rejected(self):
        create_level(name="1st Level Online")
        data = {"name": "1st Level Online", "level_code": 1.0}
        serializer = LevelSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


# ─────────────────────────────────────────────
#  SkillSerializer
# ─────────────────────────────────────────────
class SkillSerializerTest(TestCase):
    def test_valid_skill(self):
        data = {"name": "JavaScript"}
        serializer = SkillSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_skill_name_too_short(self):
        data = {"name": "JS"}  # Less than 3 chars
        serializer = SkillSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_duplicate_skill_rejected(self):
        create_skill("Python")
        data = {"name": "Python"}
        serializer = SkillSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)


# ─────────────────────────────────────────────
#  TeachersAddressSerializer
# ─────────────────────────────────────────────
class TeachersAddressSerializerTest(TestCase):
    def test_valid_pincode(self):
        teacher = create_teacher()
        data = {
            "user": teacher.id,
            "address_type": "current",
            "pincode": "800001",
        }
        serializer = TeachersAddressSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_invalid_pincode_length(self):
        teacher = create_teacher()
        data = {
            "user": teacher.id,
            "address_type": "current",
            "pincode": "12345",  # 5 digits, not 6
        }
        serializer = TeachersAddressSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("pincode", serializer.errors)

    def test_non_numeric_pincode(self):
        teacher = create_teacher()
        data = {
            "user": teacher.id,
            "address_type": "current",
            "pincode": "abcdef",
        }
        serializer = TeachersAddressSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("pincode", serializer.errors)
