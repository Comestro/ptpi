from django.contrib import admin
from django.urls import path, include
from teacherhire.views import *
from rest_framework import routers

#access admin
router = routers.DefaultRouter()
router.register(r"admin/teacherqualification", TeacherQualificationViewSet)
router.register(r"admin/skill", SkillViewSet)
router.register(r"admin/teacherskill", TeacherSkillViewSet)
router.register(r"admin/subject", SubjectViewSet)
router.register(r"admin/classcategory", ClassCategoryViewSet)
router.register(r"admin/teacher", TeacherViewSet)
router.register(r'admin/question', QuestionViewSet)
router.register(r'admin/educationalQulification', EducationalQulificationViewSet)
router.register(r'admin/teachersAddress', TeachersAddressViewSet)
router.register(r'admin/teachersubject', TeacherSubjectViewSet)
router.register(r'admin/level', LevelViewSet)
router.register(r'admin/role', RoleViewSet, basename='role')
router.register(r'admin/teacherjobtype', TeacherJobTypeViewSet, basename='teacherjobtype')

#access OnlyTeacher
router.register(r'self/teacher', SingleTeacherViewSet, basename='self-teacher')
router.register(r'self/customuser', CustomUserViewSet, basename='self-customuser')
router.register(r"self/teacherexperience", TeacherExperiencesViewSet, basename="self-teacherexperience")
router.register(r'self/teacherexamresult', TeacherExamResultViewSet, basename='self-teacherexamresult')
router.register(r'self/teacherclasscategory', TeacherClassCategoryViewSet, basename='self-teacherclasscategory')
router.register(r'self/teacherskill', SingleTeacherSkillViewSet, basename='self-teacherskill')
router.register(r'self/teacherAddress', SingleTeachersAddressViewSet, basename='self-teacherAddress')
router.register(r'self/teacherqualification', SingleTeacherQualificationViewSet, basename='self-teacherqualification')
router.register(r'self/teachersubject', SingleTeacherSubjectViewSet, basename='self-teachersubject')
router.register(r'self/teacherpreference', PreferenceViewSet, basename='teacher-preference')
router.register(r'self/teacherexperience', TeacherExperiencesViewSet, basename='teacher-experience')
router.register(r'self/teacherjobpreferencelocation', JobPreferenceLocationViewSet, basename='teacher-jobpreferencelocation')
router.register(r'self/basicProfile', BasicProfileViewSet, basename='teacher-basicProfile')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('register/', RegisterUser.as_view(), name='register'),
    path('login/', LoginUser.as_view()),
    path('logout/', LogoutUser.as_view()),
    #path('levels/<int:pk>/<int:subject_id>/questions/', SubjectQuestionsView.as_view(), name='subject-questions'),
]