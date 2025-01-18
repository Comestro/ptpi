from django.contrib import admin
from django.urls import path, include
from teacherhire.views import *
from rest_framework import routers
from .views import ProfilecompletedView,CheckoutView

#access admin
router = routers.DefaultRouter()
router.register(r"admin/teacherqualification", TeacherQualificationViewSet)
router.register(r"admin/skill", SkillViewSet)
router.register(r"admin/teacherskill", TeacherSkillViewSet)
router.register(r"admin/subject", SubjectViewSet)
router.register(r"admin/classcategory", ClassCategoryViewSet)
router.register(r'admin/question', QuestionViewSet)
router.register(r'admin/educationalQulification', EducationalQulificationViewSet)
router.register(r'admin/teacherclasscategory', TeacherClassCategoryViewSet, basename='teacherclasscategory')
router.register(r'admin/teachersAddress', TeachersAddressViewSet)
router.register(r'admin/teachersubject', TeacherSubjectViewSet)
router.register(r'admin/level', LevelViewSet)
router.register(r'admin/teacherexperience', TeacherExperiencesViewSet, basename='teacher-experience')
router.register(r'admin/role', RoleViewSet, basename='role')
router.register(r'admin/teacherjobtype', TeacherJobTypeViewSet, basename='teacherjobtype')
router.register(r'admin/exam', ExamViewSet)
router.register(r'admin/report', ReportViewSet, basename='report')
router.register(r'admin/passkey', PasskeyViewSet, basename='passkey')
router.register(r'admin/teacher', TeacherViewSet, basename='admin-teacher')
router.register(r'admin/interview', InterviewViewSet)

#access OnlyTeacher

# router.register(r"self/", SelfViewSet, basename='self-teacher')
router.register(r'self/customuser', CustomUserViewSet, basename='self-customuser')
router.register(r"self/teacherexperience", SingleTeacherExperiencesViewSet, basename="self-teacherexperience")
router.register(r'self/teacherexamresult', TeacherExamResultViewSet, basename='self-teacherexamresult')
router.register(r'self/teacherclasscategory', SingleTeacherClassCategory, basename='self-teacherclasscategory')
router.register(r'self/teacherskill', SingleTeacherSkillViewSet, basename='self-teacherskill')
router.register(r'self/teacherAddress', SingleTeachersAddressViewSet, basename='self-teacherAddress')
router.register(r'self/teacherqualification', SingleTeacherQualificationViewSet, basename='self-teacherqualification')
router.register(r'self/teachersubject', SingleTeacherSubjectViewSet, basename='self-teachersubject')
router.register(r'self/teacherpreference', PreferenceViewSet, basename='teacher-preference')
router.register(r'self/teacherjobpreferencelocation', JobPreferenceLocationViewSet, basename='teacher-jobpreferencelocation')
router.register(r'self/basicProfile', BasicProfileViewSet, basename='teacher-basicProfile')
router.register(r'self/question', SelfQuestionViewSet, basename='teacher-question')
router.register(r'self/exam', SelfExamViewSet, basename='self-exam')
router.register(r'self/report', SelfReportViewSet, basename='self-report')
router.register(r'self/interview', SelfInterviewViewSet, basename='self-interview')


urlpatterns = [
    path('', include(router.urls)),
    path('profile/completed/', ProfilecompletedView.as_view(), name='profile-completed'),
    path('checklevel/', CheckoutView.as_view(), name='checkout-level'),

    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('recruiter/register/', RecruiterRegisterUser.as_view(), name='register'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('forget-password/', SendPasswordResetEmailViewSet.as_view(), name='forget-password'),
    path('verify-user/', UserVerify.as_view(), name='user-verify'),
    path('verify/', VarifyOTP.as_view()),
    path('resend-otp/', ResendOTP.as_view(), name='resend_otp'),
    path('reset-password/<str:uidb64>/<str:token>/', ResetPasswordViewSet.as_view(), name='reset_password'),
    path('register/', TeacherRegisterUser.as_view(), name='teacher-register'),
    path('login/', LoginUser.as_view()),
    path('logout/', LogoutUser.as_view()),
    path('insert/data/', insert_data, name='insert_data'),
    path('generate-passkey/', GeneratePasskeyView.as_view(), name='generate_passkey'),
    path('approve-passkey/', ApprovePasscodeView.as_view(), name='approve_passkey'),
    path('verify-passcode/', VerifyPasscodeView.as_view(), name='verify_passcode'),

    #path('levels/<int:pk>/<int:subject_id>/questions/', SubjectQuestionsView.as_view(), name='subject-questions'),
]