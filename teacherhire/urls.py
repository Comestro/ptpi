from django.urls import path, include
from rest_framework import routers
from teacherhire.views import *
from teacherhire.auth_view import *
from teacherhire.seeder_view import *
from teacherhire.views_permissions import *
from .views import ProfilecompletedView, CheckoutView

# Initialize router
router = routers.DefaultRouter()

# === Admin Routes ===
router.register(r"admin/teacherqualification", TeacherQualificationViewSet)
router.register(r"admin/skill", SkillViewSet)
router.register(r"admin/teacherskill", TeacherSkillViewSet)
router.register(r"admin/subject", SubjectViewSet)
router.register(r"admin/classcategory", ClassCategoryViewSet)
router.register(r"admin/question", QuestionViewSet)
router.register(r"admin/educationalQulification", EducationalQulificationViewSet)
router.register(r"admin/teacherclasscategory", TeacherClassCategoryViewSet, basename="teacherclasscategory")
router.register(r"admin/teachersAddress", TeachersAddressViewSet)
router.register(r"admin/teachersubject", TeacherSubjectViewSet)
router.register(r"admin/level", LevelViewSet)
router.register(r"admin/teacherexperience", TeacherExperiencesViewSet, basename="teacher-experience")
router.register(r"admin/role", RoleViewSet, basename="role")
router.register(r"admin/teacherjobtype", TeacherJobTypeViewSet, basename="teacherjobtype")
router.register(r"admin/exam", ExamViewSet)
router.register(r"admin/report", ReportViewSet, basename="report")
router.register(r"admin/passkey", PasskeyViewSet, basename="passkey")
router.register(r"admin/interview", InterviewViewSet, basename="interview")
router.register(r"admin/reason", ReasonViewSet, basename="reason")
router.register(r"admin/examcenter", ExamCenterViewSets)
router.register(r"admin/allTeacher", AllTeacherViewSet, basename="allTeacher")
router.register(r"admin/allRecruiter", AllRecruiterViewSet, basename="allRecruiter")
router.register(r"admin/assigneduser", AssignedQuestionUserViewSet)
router.register(r"examsetter/question", ExamSetterQuestionViewSet, basename="examsetter-question")
router.register(r"admin/hirerequest", HireRequestViewSet, basename='hire-request')
router.register(r"admin/recruiterenquiryform", RecruiterEnquiryFormViewSet,basename='recruiter-enquiryform')
router.register(r"all/teacher/basicProfile", AllTeacherBasicProfileViewSet, basename="teachers-basicProfile")
router.register(r"all/recruiter/basicProfile", AllRecruiterBasicProfileViewSet, basename="recruiters-basicProfile")


# === Teacher Routes ===
router.register(r"admin/teacher", TeacherViewSet, basename="admin-teacher")
router.register(r"self/customuser", CustomUserViewSet, basename="self-customuser")
router.register(r"self/teacherexperience", SingleTeacherExperiencesViewSet, basename="self-teacherexperience")
router.register(r"self/teacherexamresult", TeacherExamResultViewSet, basename="self-teacherexamresult")
router.register(r"self/teacherclasscategory", SingleTeacherClassCategory, basename="self-teacherclasscategory")
router.register(r"self/teacherskill", SingleTeacherSkillViewSet, basename="self-teacherskill")
router.register(r"self/teacherAddress", SingleTeachersAddressViewSet, basename="self-teacherAddress")
router.register(r"self/teacherqualification", SingleTeacherQualificationViewSet, basename="self-teacherqualification")
router.register(r"self/teachersubject", SingleTeacherSubjectViewSet, basename="self-teachersubject")
router.register(r"self/teacherpreference", PreferenceViewSet, basename="teacher-preference")
router.register(r"self/teacherjobpreferencelocation", JobPreferenceLocationViewSet,
                basename="teacher-jobpreferencelocation")
router.register(r"self/basicProfile", BasicProfileViewSet, basename="teacher-basicProfile")
router.register(r"self/question", SelfQuestionViewSet, basename="teacher-question")
router.register(r"self/exam", SelfExamViewSet, basename="self-exam")
router.register(r"self/report", SelfReportViewSet, basename="self-report")
router.register(r"self/interview", SelfInterviewViewSet, basename="self-interview")
router.register(r"examcenters", SelfExamCenterViewSets, basename="self-examcenter")
router.register(r"self/teacherReport", TeacherReportViewSet, basename="self-teacherReport")
router.register(r"examsetter", ExamSetterViewSet, basename="examsetter")
router.register(r"self/recruiterenquiryform", SelfRecruiterEnquiryFormViewSet, basename="recruiterenquiryform")

# recruiter
router.register(r"self/hirerequest", RecHireRequestViewSet, basename='self-hire-request')
router.register(r"self/teacher", SelfViewSet, basename="self-teacher")

# === Permission-Based Routes ===
urlpatterns = [
    path("", include(router.urls)),

    # Profile & Checkout
    path("profile/completed/", ProfilecompletedView.as_view(), name="profile-completed"),
    path("checklevel/", CheckoutView.as_view(), name="checkout-level"),

    # Authentication Routes
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('verify-account/<str:token>/', VerifyLinkView.as_view(), name='verify-account'),
    path("register/<str:role>/", RegisterUser.as_view(), name="register"),
    path("change_password/", ChangePasswordView.as_view(), name="change_password"),
    path("login/", LoginUser.as_view(), name="login"),
    path("logout/", LogoutUser.as_view(), name="logout"),
    path("password_reset_request/", PasswordResetRequest.as_view(), name="password_reset_request"),
    path("reset_password/<str:token>/", ResetPasswordView.as_view(), name="reset_password"),
    path("verify_otp/", VerifyOTP.as_view(), name="verify_otp"),
    path("resend_otp/", ResendOTP.as_view(), name="resend_otp"),
    path("verify_user/", UserVerify.as_view(), name="verify_user"),

    # Passkey Routes
    path("generate-passkey/", GeneratePasskeyView.as_view(), name="generate_passkey"),
    path("approve-passkey/", ApprovePasscodeView.as_view(), name="approve_passkey"),
    path("verify-passcode/", VerifyPasscodeView.as_view(), name="verify_passcode"),

    # Seeder Data Routes
    path("insert/data/teacher/", insert_data_teachers, name="insert_data_teachers"),
    path("translate/", TranslatorView.as_view(), name="translate"),
    path("admin/insert/data/", insert_all_data, name="insert_all_data"),

    # === View Permissions API ===
    path("admin-only/", AdminOnlyView.as_view(), name="admin-only"),
    path("recruiter-only/", RecruiterOnlyView.as_view(), name="recruiter-only"),
    path("teacher-only/", TeacherOnlyView.as_view(), name="teacher-only"),
    path("center-user-only/", CenterUserOnlyView.as_view(), name="center-user-only"),
    path("question-user-only/", QuestionUserOnlyView.as_view(), name="question-user-only"),
    path("default-user-only/", DefaultUserOnlyView.as_view(), name="default-user-only"),
    path("admin-or-teacher/", AdminOrTeacherView.as_view(), name="admin-or-teacher"),
    path("read-only-authenticated/", ReadOnlyForAuthenticatedUsers.as_view(), name="read-only-authenticated"),
    path("public/", PublicView.as_view(), name="public"),
]
