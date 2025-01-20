from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(EducationalQualification)
class EducationalQualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter', 'is_teacher', 'is_verified', 'otp', 'otp_created_at']
@admin.register(TeacherQualification)
class TeacherQualificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'qualification','institution','year_of_passing','grade_or_percentage']

@admin.register(TeacherExperiences)
class TeacherExperiencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'role','institution','description','achievements','end_date','start_date']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_name','subject_description']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['jobrole_name']

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['issue_type']

@admin.register(ClassCategory)
class classCategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(TeacherClassCategory)
class TeacherClassCategoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_category']

@admin.register(TeacherExamResult)
class TeacherExamResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'isqualified']

@admin.register(JobPreferenceLocation)
class JobPreferenceLocationAdmin(admin.ModelAdmin):
    list_display = ['preference', 'state', 'city', 'sub_division', 'block', 'area', 'pincode']

@admin.register(BasicProfile)
class BasicProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio', 'profile_picture', 'phone_number', 'religion', 'date_of_birth', 'marital_status','gender', 'language']
    
@admin.register(TeachersAddress)
class TeachersAddressAdmin(admin.ModelAdmin):
    list_display = ['user','address_type', 'state', 'division', 'district', 'block', 'village', 'area', 'pincode']

@admin.register(TeacherSkill)
class TeacherSkillAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill']

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject']


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

    
@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_job_role', 'get_class_category', 'get_prefered_subject', 'get_teacher_job_type']

    def get_prefered_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.prefered_subject.all()])

    def get_teacher_job_type(self, obj):
        return ", ".join([str(job_type) for job_type in obj.teacher_job_type.all()])
    
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

    def get_job_role(self, obj):
        return ", ".join([str(job_role) for job_role in obj.job_role.all()])  # Changed teacher_job_role to teacher_job_type

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'created_at', 'status']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'text', 'options', 'correct_option','language', 'created_at']

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(TeacherJobType)
class TeacherJobTypeAdmin(admin.ModelAdmin):
    list_display = ['teacher_job_name']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['subject', 'level', 'class_category', 'duration', 'name', 'description', 'total_marks','type', 'created_at', 'updated_at']

@admin.register(Passkey)
class PasskeyAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'code','status','created_at']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'time','link','grade','status','created_at']
