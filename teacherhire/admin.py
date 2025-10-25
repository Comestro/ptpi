from django.contrib import admin
from .models import *
from django.utils.html import format_html
from ptpi import settings
# Register your models here.

@admin.register(EducationalQualification)
class EducationalQualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter', 'is_teacher','is_centeruser', 'is_verified', 'otp', 'user_code', 'otp_created_at','date']

@admin.register(TeacherQualification)
class TeacherQualificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'qualification','institution','year_of_passing','grade_or_percentage',"stream_or_degree"]

@admin.register(TeacherExperiences)
class TeacherExperiencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'role','institution','description','achievements','end_date','start_date']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_name','subject_description','class_category']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['jobrole_name']

@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ['issue_type']

@admin.register(ClassCategory)
class classCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(TeacherClassCategory)
class TeacherClassCategoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_category']

@admin.register(TeacherExamResult)
class TeacherExamResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'isqualified','has_exam_attempt','attempt']

@admin.register(JobPreferenceLocation)
class JobPreferenceLocationAdmin(admin.ModelAdmin):
    list_display = ['user','state', 'city', 'sub_division', 'block', 'area', 'pincode']

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
    list_display = ['id','user','get_issue_type','created_at', 'status']

    def get_issue_type(self, obj):
        return ", ".join([str(issue_type) for issue_type in obj.issue_type.all()])


class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'display_text','display_image', 'related_question','options', 'correct_option','language', 'created_at']
    def display_text(self, obj):
        if isinstance(obj.text, dict):
            return obj.text.get("text", "No Text")
        return str(obj.text)
    
    def display_image(self, obj):
        if isinstance(obj.text, dict) and "image" in obj.text and obj.text["image"]:
            image_url = obj.text["image"]  # This can be a relative URL or external URL
            return format_html('<a href="{}" target="_blank">View Image</a>', image_url)
        return "No Image"

    display_text.short_description = "Question Text"
    display_image.short_description = "Image"

admin.site.register(Question, QuestionAdmin)

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['name','level_code', 'description']

@admin.register(TeacherJobType)
class TeacherJobTypeAdmin(admin.ModelAdmin):
    list_display = ['teacher_job_name']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['assigneduser','subject', 'level', 'class_category', 'duration', 'name', 'description', 'total_marks','type', 'created_at','updated_at', 'status']

@admin.register(Passkey)
class PasskeyAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'code','center','status','created_at']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'time','link','subject','class_category','grade','level' ,'status','attempt','created_at']
@admin.register(ExamCenter)
class ExamCenter(admin.ModelAdmin):
    list_display = ['user', 'center_name', 'pincode', 'state', 'city', 'status','area']

@admin.register(RecruiterEnquiryForm)
class RecruiterEnquiryForm(admin.ModelAdmin):
    list_display = ['user','teachertype', 'class_category',  'pincode',  'state', 'subject', 'area',  'name', 'city', 'email']

    def subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])

    def class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])


@admin.register(AssignedQuestionUser)
class AssignedQuestionUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_subject', 'get_class_category']
    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])
    
@admin.register(HireRequest)
class HireRequestAdmin(admin.ModelAdmin):
    list_display = ['recruiter_id','teacher_id','date', 'get_subject','get_class_category']

    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

@admin.register(Apply)
class ApplyAdmin(admin.ModelAdmin):
    list_display = ['user','get_subject','get_class_category','get_teacher_job_type','status','date']

    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])
    def get_teacher_job_type(self, obj):
        return ", ".join([str(job_type) for job_type in obj.teacher_job_type.all()])   
