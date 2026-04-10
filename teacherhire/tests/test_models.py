"""
Unit tests for teacherhire models.
Tests model creation, custom methods, constraints, and relationships.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from teacherhire.models import (
    CustomUser, ClassCategory, Subject, Level, Skill,
    EducationalQualification, Exam, Question, TeacherExamResult,
    ExamCenter, AssignedQuestionUser, TeacherSkill, BasicProfile,
    TeachersAddress, Passkey, Report, Reason, Role, Apply,
    TeacherJobType, PendingRegistration,
)
from .factories import (
    create_user, create_admin, create_teacher, create_recruiter,
    create_class_category, create_subject, create_level, create_skill,
    create_exam, create_question, create_exam_center, create_centeruser,
    create_questionuser, create_role,
)


# ─────────────────────────────────────────────
#  CustomUser Model
# ─────────────────────────────────────────────
class CustomUserModelTest(TestCase):
    def test_create_user(self):
        user = create_user()
        self.assertEqual(user.email, "teacher@test.com")
        self.assertTrue(user.check_password("TestPass123!"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        user = CustomUser.objects.create_superuser(
            email="super@test.com", username="super", password="SuperPass123!"
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_user_code_generated_on_save(self):
        """user_code should be auto-generated based on role and date."""
        teacher = create_teacher()
        self.assertTrue(teacher.user_code.startswith("T-"))
        self.assertEqual(len(teacher.user_code), 13)  # T-DDMMYYYY001

    def test_user_code_prefix_per_role(self):
        """Different roles should get different user_code prefixes."""
        teacher = create_teacher(email="t1@test.com")
        recruiter = create_recruiter(email="r1@test.com")
        admin = create_admin(email="a1@test.com")
        questionuser = create_questionuser(email="q1@test.com")
        centeruser = create_centeruser(email="c1@test.com")

        self.assertTrue(teacher.user_code.startswith("T-"))
        self.assertTrue(recruiter.user_code.startswith("R-"))
        self.assertTrue(admin.user_code.startswith("A-"))
        self.assertTrue(questionuser.user_code.startswith("Q-"))
        self.assertTrue(centeruser.user_code.startswith("C-"))

    def test_user_code_increments(self):
        """Sequential users of the same role should get incrementing codes."""
        t1 = create_teacher(email="t1@test.com")
        t2 = create_teacher(email="t2@test.com")
        # Last 3 chars should be 001, 002
        self.assertEqual(t1.user_code[-3:], "001")
        self.assertEqual(t2.user_code[-3:], "002")

    def test_email_is_unique(self):
        create_user(email="dup@test.com")
        with self.assertRaises(IntegrityError):
            create_user(email="dup@test.com", username="different")

    def test_user_str(self):
        user = create_user()
        self.assertEqual(str(user), "teacher@test.com")

    def test_create_user_without_email_raises(self):
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(email="", username="nomail", password="pass")


# ─────────────────────────────────────────────
#  ClassCategory & Subject Models
# ─────────────────────────────────────────────
class ClassCategoryModelTest(TestCase):
    def test_create_class_category(self):
        cat = create_class_category("Class 12")
        self.assertEqual(str(cat), "Class 12")

    def test_unique_category_name(self):
        create_class_category("Unique")
        with self.assertRaises(IntegrityError):
            create_class_category("Unique")


class SubjectModelTest(TestCase):
    def test_create_subject(self):
        cat = create_class_category()
        sub = create_subject(cat, "Physics")
        self.assertEqual(str(sub), "Physics")
        self.assertEqual(sub.class_category, cat)

    def test_subject_category_relationship(self):
        cat = create_class_category()
        sub1 = create_subject(cat, "Math")
        sub2 = create_subject(cat, "Science")
        self.assertEqual(cat.subjects.count(), 2)


# ─────────────────────────────────────────────
#  Level & Skill Models
# ─────────────────────────────────────────────
class LevelModelTest(TestCase):
    def test_create_level(self):
        level = create_level()
        self.assertEqual(str(level), "1st Level Online")
        self.assertEqual(level.level_code, 1.0)


class SkillModelTest(TestCase):
    def test_create_skill(self):
        skill = create_skill("Django")
        self.assertEqual(str(skill), "Django")

    def test_unique_skill_name(self):
        create_skill("React")
        with self.assertRaises(IntegrityError):
            create_skill("React")


class TeacherSkillModelTest(TestCase):
    def test_unique_together_user_skill(self):
        user = create_teacher()
        skill = create_skill()
        TeacherSkill.objects.create(user=user, skill=skill)
        with self.assertRaises(IntegrityError):
            TeacherSkill.objects.create(user=user, skill=skill)


# ─────────────────────────────────────────────
#  Exam Model
# ─────────────────────────────────────────────
class ExamModelTest(TestCase):
    def test_create_exam(self):
        exam = create_exam()
        self.assertEqual(exam.total_marks, 20)
        self.assertEqual(exam.duration, 30)
        self.assertEqual(exam.type, "online")
        self.assertFalse(exam.status)  # default is False

    def test_exam_str(self):
        exam = create_exam()
        self.assertIn("Class 10", str(exam))

    def test_count_question_property(self):
        exam = create_exam()
        q1 = create_question(exam=exam, text="Q1")
        q2 = create_question(exam=exam, text="Q2", language="Hindi", related_question=q1)

        counts = exam.count_question
        self.assertEqual(counts["original_questions"], 1)
        self.assertEqual(counts["related_questions"], 1)


# ─────────────────────────────────────────────
#  Question Model
# ─────────────────────────────────────────────
class QuestionModelTest(TestCase):
    def test_create_question(self):
        q = create_question()
        self.assertEqual(q.correct_option, 4)
        self.assertEqual(len(q.options), 4)
        self.assertEqual(q.language, "English")

    def test_auto_order_assignment(self):
        """Questions should auto-assign order based on exam + language."""
        exam = create_exam()
        q1 = create_question(exam=exam, text="Q1")
        q2 = create_question(exam=exam, text="Q2")
        self.assertEqual(q1.order, 1)
        self.assertEqual(q2.order, 2)

    def test_auto_order_per_language(self):
        """Order should be independent per language within the same exam."""
        exam = create_exam()
        en1 = create_question(exam=exam, text="EN1", language="English")
        hi1 = create_question(exam=exam, text="HI1", language="Hindi")
        en2 = create_question(exam=exam, text="EN2", language="English")

        self.assertEqual(en1.order, 1)
        self.assertEqual(hi1.order, 1)
        self.assertEqual(en2.order, 2)

    def test_clean_correct_option_out_of_range(self):
        q = create_question()
        q.correct_option = 5  # Only 4 options exist
        with self.assertRaises(ValidationError):
            q.clean()

    def test_clean_correct_option_zero(self):
        q = create_question()
        q.correct_option = 0
        with self.assertRaises(ValidationError):
            q.clean()


# ─────────────────────────────────────────────
#  TeacherExamResult Model
# ─────────────────────────────────────────────
class TeacherExamResultModelTest(TestCase):
    def setUp(self):
        self.teacher = create_teacher()
        self.exam = create_exam()

    def test_calculate_percentage(self):
        result = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=12, incorrect_answer=5, is_unanswered=3,
        )
        # 12 / (12+5+3) = 60%
        self.assertEqual(result.calculate_percentage(), 60.0)

    def test_qualified_at_60_percent(self):
        result = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=12, incorrect_answer=5, is_unanswered=3,
        )
        self.assertTrue(result.isqualified)

    def test_not_qualified_below_60(self):
        result = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=5, incorrect_answer=10, is_unanswered=5,
        )
        self.assertFalse(result.isqualified)

    def test_attempt_auto_increment(self):
        """Sequential results for the same exam config should increment attempt."""
        r1 = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=5, incorrect_answer=15,
        )
        r2 = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=8, incorrect_answer=12,
        )
        self.assertEqual(r1.attempt, 1)
        self.assertEqual(r2.attempt, 2)

    def test_zero_total_percentage(self):
        result = TeacherExamResult.objects.create(
            exam=self.exam, user=self.teacher,
            correct_answer=0, incorrect_answer=0, is_unanswered=0,
        )
        self.assertEqual(result.calculate_percentage(), 0)


# ─────────────────────────────────────────────
#  ExamCenter Model
# ─────────────────────────────────────────────
class ExamCenterModelTest(TestCase):
    def test_create_exam_center(self):
        center = create_exam_center()
        self.assertEqual(str(center), "Test Center")
        self.assertTrue(center.status)

    def test_exam_center_default_status_active(self):
        center = create_exam_center()
        self.assertTrue(center.status)


# ─────────────────────────────────────────────
#  TeachersAddress Model
# ─────────────────────────────────────────────
class TeachersAddressModelTest(TestCase):
    def test_is_complete_all_filled(self):
        user = create_teacher()
        addr = TeachersAddress.objects.create(
            user=user, address_type="current",
            state="Bihar", division="Patna", district="Patna",
            block="Danapur", village="Test", area="Test Area", pincode="800001",
        )
        complete, missing = addr.is_complete()
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_is_complete_missing_fields(self):
        user = create_teacher()
        addr = TeachersAddress.objects.create(user=user, address_type="current", state="Bihar")
        complete, missing = addr.is_complete()
        self.assertFalse(complete)
        self.assertIn("district", missing)
        self.assertIn("pincode", missing)


# ─────────────────────────────────────────────
#  PendingRegistration Model
# ─────────────────────────────────────────────
class PendingRegistrationModelTest(TestCase):
    def test_create_pending_registration(self):
        pending = PendingRegistration.objects.create(
            email="pending@test.com",
            password_hash="hashed",
            Fname="Test",
            Lname="User",
            role="teacher",
            otp="123456",
        )
        self.assertEqual(str(pending), "Pending teacher: pending@test.com")

    def test_unique_email(self):
        PendingRegistration.objects.create(
            email="dup@test.com", password_hash="h", Fname="A", role="teacher", otp="111111",
        )
        with self.assertRaises(IntegrityError):
            PendingRegistration.objects.create(
                email="dup@test.com", password_hash="h", Fname="B", role="teacher", otp="222222",
            )
