"""
Shared test helpers and factory functions.
Centralizes object creation so individual test files stay DRY.
"""
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from teacherhire.models import (
    CustomUser, ClassCategory, Subject, Level, Skill,
    EducationalQualification, Role, Exam, Question, ExamCenter,
    AssignedQuestionUser, TeacherExamResult, Reason, Passkey,
)


def create_user(email="teacher@test.com", password="TestPass123!", **kwargs):
    """Create a CustomUser with sensible defaults."""
    defaults = {
        "username": email.split("@")[0],
        "Fname": "Test",
        "Lname": "User",
        "is_verified": True,
        "is_active": True,
    }
    defaults.update(kwargs)
    user = CustomUser.objects.create_user(email=email, password=password, **defaults)
    return user


def create_admin(email="admin@test.com", password="AdminPass123!"):
    return create_user(email=email, password=password, is_staff=True, is_superuser=True)


def create_teacher(email="teacher@test.com", password="TestPass123!"):
    return create_user(email=email, password=password, is_teacher=True)


def create_recruiter(email="recruiter@test.com", password="TestPass123!", **kwargs):
    return create_user(email=email, password=password, is_recruiter=True, **kwargs)


def create_questionuser(email="setter@test.com", password="TestPass123!"):
    return create_user(email=email, password=password, is_questionuser=True)


def create_centeruser(email="center@test.com", password="TestPass123!"):
    return create_user(email=email, password=password, is_centeruser=True)


def create_class_category(name="Class 10"):
    return ClassCategory.objects.create(name=name)


def create_subject(class_category=None, name="Mathematics"):
    if class_category is None:
        class_category = create_class_category()
    return Subject.objects.create(class_category=class_category, subject_name=name)


def create_level(name="1st Level Online", level_code=1.0):
    return Level.objects.create(name=name, level_code=level_code)


def create_skill(name="Python"):
    return Skill.objects.create(name=name)


def create_qualification(name="Bachelor of Education"):
    return EducationalQualification.objects.create(name=name)


def create_role(name="Teacher"):
    return Role.objects.create(jobrole_name=name)


def create_exam(subject=None, level=None, class_category=None, **kwargs):
    """Create an Exam with auto-generated dependencies if not provided."""
    if class_category is None:
        class_category = create_class_category()
    if subject is None:
        subject = create_subject(class_category=class_category)
    if level is None:
        level = create_level()

    defaults = {
        "name": f"{class_category.name} | {subject.subject_name} | {level.name}",
        "subject": subject,
        "level": level,
        "class_category": class_category,
        "total_marks": 20,
        "duration": 30,
        "total_questions": 20,
        "type": "online",
    }
    defaults.update(kwargs)
    return Exam.objects.create(**defaults)


def create_question(exam=None, **kwargs):
    """Create a Question with sensible defaults."""
    if exam is None:
        exam = create_exam()

    defaults = {
        "exam": exam,
        "text": "What is 2 + 2?",
        "options": ["1", "2", "3", "4"],
        "correct_option": 4,
        "language": "English",
    }
    defaults.update(kwargs)
    return Question.objects.create(**defaults)


def create_exam_center(user=None, **kwargs):
    if user is None:
        user = create_centeruser()
    defaults = {
        "user": user,
        "center_name": "Test Center",
        "phone": "9876543210",
        "pincode": "800001",
        "state": "Bihar",
        "city": "Patna",
        "status": True,
    }
    defaults.update(kwargs)
    return ExamCenter.objects.create(**defaults)


def create_reason(issue_type="Wrong answer"):
    return Reason.objects.create(issue_type=issue_type)


def get_auth_client(user):
    """Return an APIClient with Token authentication for the given user."""
    token, _ = Token.objects.get_or_create(user=user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client
