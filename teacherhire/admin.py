from django.contrib import admin
from .models import *
from django.utils.html import format_html
from ptpi import settings
# Register your models here.

@admin.register(EducationalQualification)
class EducationalQualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['email', 'username', 'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter', 'is_teacher','is_centeruser', 'is_verified', 'otp', 'user_code', 'otp_created_at','date']
    search_fields = ['email', 'username', 'Fname', 'Lname', 'user_code']
    list_filter = ['is_staff', 'is_active', 'is_recruiter', 'is_teacher', 'is_centeruser', 'is_verified', 'date']

@admin.register(TeacherQualification)
class TeacherQualificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'qualification','institution','year_of_passing','grade_or_percentage',"stream_or_degree",'session','subjects']
    search_fields = ['user__email', 'user__username', 'institution', 'stream_or_degree', 'subjects']
    list_filter = ['qualification', 'year_of_passing']

@admin.register(TeacherExperiences)
class TeacherExperiencesAdmin(admin.ModelAdmin):
    list_display = ['user', 'role','institution','description','achievements','end_date','start_date']
    search_fields = ['user__email', 'user__username', 'role', 'institution']
    list_filter = ['start_date', 'end_date']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_name','subject_description','class_category']
    search_fields = ['subject_name']
    list_filter = ['class_category']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.exam_set.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['jobrole_name']
    search_fields = ['jobrole_name']

@admin.register(Reason)
class ReasonAdmin(admin.ModelAdmin):
    list_display = ['issue_type']
    search_fields = ['issue_type']

@admin.register(ClassCategory)
class classCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

    def has_delete_permission(self, request, obj=None):
        if obj and (obj.subjects.exists() or obj.exam_set.exists()):
            return False
        return super().has_delete_permission(request, obj)

@admin.register(TeacherClassCategory)
class TeacherClassCategoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_category']
    search_fields = ['user__email', 'user__username', 'class_category__name']
    list_filter = ['class_category']

@admin.register(TeacherExamResult)
class TeacherExamResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'isqualified','has_exam_attempt','attempt']
    search_fields = ['user__email', 'user__username', 'exam__name']
    list_filter = ['isqualified', 'has_exam_attempt']

@admin.register(JobPreferenceLocation)
class JobPreferenceLocationAdmin(admin.ModelAdmin):
    list_display = ['user','state', 'city', 'sub_division', 'block', 'post_office', 'area', 'pincode']
    search_fields = ['user__email', 'user__username', 'city', 'state', 'pincode', 'area']
    list_filter = ['state', 'city']

@admin.register(BasicProfile)
class BasicProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'bio', 'profile_picture', 'phone_number', 'religion', 'date_of_birth', 'marital_status','gender', 'language']
    search_fields = ['user__email', 'user__username', 'phone_number']
    list_filter = ['gender', 'marital_status', 'religion']

@admin.register(TeachersAddress)
class TeachersAddressAdmin(admin.ModelAdmin):
    list_display = ['user','address_type', 'state', 'division', 'district', 'block', 'village', 'area', 'pincode']
    search_fields = ['user__email', 'user__username', 'pincode', 'district', 'state', 'village']
    list_filter = ['address_type', 'state', 'district']

@admin.register(TeacherSkill)
class TeacherSkillAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill']
    search_fields = ['user__email', 'user__username', 'skill__name']
    list_filter = ['skill']

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject']
    search_fields = ['user__email', 'user__username', 'subject__subject_name']
    list_filter = ['subject']

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.teacherskill_set.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_class_category', 'get_prefered_subject']
    search_fields = ['user__email', 'user__username']

    def get_prefered_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.prefered_subject.all()])
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id','user','get_issue_type','created_at', 'status']
    search_fields = ['user__email', 'user__username']
    list_filter = ['status', 'created_at']

    def get_issue_type(self, obj):
        return ", ".join([str(issue_type) for issue_type in obj.issue_type.all()])

class QuestionAdmin(admin.ModelAdmin):
    list_display = ['exam', 'display_text','display_image', 'related_question','options', 'correct_option','language', 'created_at']
    search_fields = ['exam__name', 'language']
    list_filter = ['language', 'created_at', 'exam']

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
    search_fields = ['name', 'level_code']

    def has_delete_permission(self, request, obj=None):
        if obj and obj.exam_set.exists():
            return False
        return super().has_delete_permission(request, obj)

@admin.register(TeacherJobType)
class TeacherJobTypeAdmin(admin.ModelAdmin):
    list_display = ['teacher_job_name']
    search_fields = ['teacher_job_name']

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ['assigneduser','subject', 'level', 'class_category', 'duration', 'name', 'description', 'total_marks','type', 'created_at','updated_at', 'status']
    search_fields = ['name', 'assigneduser__email', 'assigneduser__username']
    list_filter = ['status', 'type', 'level', 'class_category', 'subject', 'created_at']

@admin.register(Passkey)
class PasskeyAdmin(admin.ModelAdmin):
    list_display = ['user', 'exam', 'code','center','status','created_at']
    search_fields = ['user__email', 'user__username', 'code', 'center__center_name']
    list_filter = ['status', 'created_at']

@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'time','link','subject','class_category','grade','level' ,'status','attempt','created_at']
    search_fields = ['user__email', 'user__username', 'link']
    list_filter = ['status', 'level', 'class_category', 'subject', 'created_at']

@admin.register(ExamCenter)
class ExamCenter(admin.ModelAdmin):
    list_display = ['user', 'center_name', 'pincode', 'state', 'city', 'status','area']
    search_fields = ['user__email', 'user__username', 'center_name', 'pincode', 'city', 'state']
    list_filter = ['status', 'state', 'city']

@admin.register(RecruiterEnquiryForm)
class RecruiterEnquiryForm(admin.ModelAdmin):
    list_display = ['user','teachertype', 'class_category',  'pincode',  'state', 'subject', 'area',  'name', 'city', 'email']
    search_fields = ['user__email', 'user__username', 'name', 'email', 'pincode', 'city', 'state']
    list_filter = ['teachertype', 'state', 'city']

    def subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])

    def class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

@admin.register(AssignedQuestionUser)
class AssignedQuestionUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'get_subject', 'get_class_category']
    search_fields = ['user__email', 'user__username']

    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])
    
@admin.register(HireRequest)
class HireRequestAdmin(admin.ModelAdmin):
    list_display = ['recruiter_id','teacher_id','date', 'get_subject','get_class_category']
    search_fields = ['recruiter_id__email', 'recruiter_id__username', 'teacher_id__email', 'teacher_id__username']
    list_filter = ['date']

    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

@admin.register(Apply)
class ApplyAdmin(admin.ModelAdmin):
    list_display = ['user','subject','class_category','teacher_job_type','status','date']
    search_fields = ['user__email', 'user__username']
    list_filter = ['status', 'teacher_job_type', 'subject', 'class_category', 'date']

admin.site.register(PendingRegistration)

@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_at', 'updated_at']
    search_fields = ['name', 'subject']
    list_filter = ['created_at']

@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'template', 'subject', 'sent_at', 'status']
    list_filter = ['status', 'sent_at']
    search_fields = ['user__email', 'subject', 'template__name']

@admin.register(InterviewerProfile)
class InterviewerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_available', 'total_interviews', 'average_score', 'rank']
    list_filter = ['is_available']
    search_fields = ['user__username', 'user__email']

@admin.register(InterviewerAvailabilitySlot)
class InterviewerAvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = ['interviewer', 'day_of_week', 'start_time', 'end_time']
    list_filter = ['day_of_week']
    search_fields = ['interviewer__user__email', 'interviewer__user__username']

@admin.register(SystemErrorLog)
class SystemErrorLogAdmin(admin.ModelAdmin):
    list_display = ['source', 'exception_type', 'request_method', 'request_path', 'created_at']
    list_filter = ['source', 'created_at', 'request_method']
    search_fields = ['exception_type', 'exception_message', 'request_path', 'user__email']
    readonly_fields = ['created_at']
