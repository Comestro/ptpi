from django.contrib.auth.models import Group
from django.contrib import admin
from .models import *
from django.utils.html import format_html
from ptpi import settings
from unfold.admin import ModelAdmin
from unfold.paginator import InfinitePaginator
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
# Register your models here.

admin.site.unregister(Group)

@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

@admin.register(EducationalQualification)
class EducationalQualificationAdmin(ModelAdmin):
    list_display = ['name', 'description']
    list_filter = ['name']
    search_fields = ['name']

@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    list_display = ['email', 'username', 'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter', 'is_teacher','is_centeruser', 'is_verified', 'otp', 'user_code', 'otp_created_at','date']
    list_filter = ['is_staff', 'is_active', 'is_recruiter', 'is_teacher','is_centeruser', 'is_verified', 'is_questionuser', 'date']
    search_fields = ['email', 'username', 'Fname', 'Lname', 'user_code']

@admin.register(TeacherQualification)
class TeacherQualificationAdmin(ModelAdmin):
    list_display = ['user', 'qualification','institution','year_of_passing','grade_or_percentage',"stream_or_degree",'session','subjects']
    list_filter = ['qualification','institution','year_of_passing','grade_or_percentage',"stream_or_degree",'session','subjects']
    search_fields = ['user', 'qualification','institution','year_of_passing','grade_or_percentage',"stream_or_degree",'session','subjects']

@admin.register(TeacherExperiences)
class TeacherExperiencesAdmin(ModelAdmin):
    list_display = ['user', 'role','institution','description','achievements','end_date','start_date']
    list_filter = ['role','institution','end_date','start_date']
    search_fields = ['user', 'role','institution','achievements']

@admin.register(Subject)
class SubjectAdmin(ModelAdmin):
    list_display = ['subject_name','subject_description','class_category']
    list_filter = ['subject_name','class_category']
    search_fields = ['subject_name','class_category']

@admin.register(Role)
class RoleAdmin(ModelAdmin):
    list_display = ['jobrole_name']
    list_filter = ['jobrole_name']
    search_fields = ['jobrole_name']

@admin.register(Reason)
class ReasonAdmin(ModelAdmin):
    list_display = ['issue_type']
    list_filter = ['issue_type']
    search_fields = ['issue_type']

@admin.register(ClassCategory)
class classCategoryAdmin(ModelAdmin):
    list_display = ['name', 'description']
    list_filter = ['name']
    search_fields = ['name']

@admin.register(TeacherClassCategory)
class TeacherClassCategoryAdmin(ModelAdmin):
    list_display = ['user', 'class_category']
    list_filter = ['class_category']
    search_fields = ['user', 'class_category']

@admin.register(TeacherExamResult)
class TeacherExamResultAdmin(ModelAdmin):
    list_display = ['user', 'exam', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'isqualified','has_exam_attempt','attempt']
    list_filter = ['exam', 'isqualified', 'has_exam_attempt']
    search_fields = ['user', 'exam']

@admin.register(JobPreferenceLocation)
class JobPreferenceLocationAdmin(ModelAdmin):
    list_display = ['user','state', 'city', 'sub_division', 'block', 'area', 'pincode']
    search_fields = ['user','state', 'city', 'sub_division', 'block', 'area', 'pincode']

@admin.register(BasicProfile)
class BasicProfileAdmin(ModelAdmin):
    list_display = ['user', 'bio', 'profile_picture', 'phone_number', 'religion', 'date_of_birth', 'marital_status','gender', 'language']
    list_filter = [ 'religion', 'date_of_birth', 'marital_status','gender', 'language']
    search_fields = ['user', 'phone_number', 'bio']
    
@admin.register(TeachersAddress)
class TeachersAddressAdmin(ModelAdmin):
    list_display = ['user','address_type', 'state', 'division', 'district', 'block', 'village', 'area', 'pincode']
    list_filter = ['address_type']
    search_fields = ['user','address_type', 'state', 'division', 'district', 'block', 'village', 'area', 'pincode']

@admin.register(TeacherSkill)
class TeacherSkillAdmin(ModelAdmin):
    list_display = ['user', 'skill']
    list_filter = ['skill']
    search_fields = ['user', 'skill']

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(ModelAdmin):
    list_display = ['user', 'subject']
    list_filter = ['subject']
    search_fields = ['user', 'subject']


@admin.register(Skill)
class SkillAdmin(ModelAdmin):
    list_display = ['name', 'description']
    list_filter = ['name']
    search_fields = ['name']

    
@admin.register(Preference)
class PreferenceAdmin(ModelAdmin):
    list_display = ['user', 'get_job_role', 'get_class_category', 'get_prefered_subject', 'get_teacher_job_type']
    list_filter = ['prefered_subject', 'teacher_job_type', 'class_category', 'job_role']
    search_fields = ['user', 'prefered_subject', 'teacher_job_type', 'class_category', 'job_role'
                     ]
    def get_prefered_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.prefered_subject.all()])
    def get_teacher_job_type(self, obj):
        return ", ".join([str(job_type) for job_type in obj.teacher_job_type.all()])   
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])
    def get_job_role(self, obj):
        return ", ".join([str(job_role) for job_role in obj.job_role.all()])  # Changed teacher_job_role to teacher_job_type
    
@admin.register(Report)
class ReportAdmin(ModelAdmin):
    list_display = ['id','user','get_issue_type','created_at', 'status']
    list_filter = ['issue_type', 'status']
    search_fields = ['user', 'issue_type', 'status']

    def get_issue_type(self, obj):
        return ", ".join([str(issue_type) for issue_type in obj.issue_type.all()])


class QuestionAdmin(ModelAdmin):
    list_display = ['exam', 'display_text','display_image', 'related_question','options', 'correct_option','language', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['exam', 'text', 'related_question', 'options', 'correct_option']
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
class LevelAdmin(ModelAdmin):
    list_display = ['name','level_code', 'description']
    list_filter = ['level_code']
    search_fields = ['name']

@admin.register(TeacherJobType)
class TeacherJobTypeAdmin(ModelAdmin):
    list_display = ['teacher_job_name']
    list_filter = ['teacher_job_name']
    search_fields = ['teacher_job_name']

@admin.register(Exam)
class ExamAdmin(ModelAdmin):
    list_display = ['assigneduser','subject', 'level', 'class_category', 'duration', 'name', 'description', 'total_marks','type', 'created_at','updated_at', 'status']
    list_filter = ['subject', 'level', 'class_category', 'type', 'status']
    search_fields = ['name', 'description']
    paginator = InfinitePaginator
    show_full_result_count = True

@admin.register(Passkey)
class PasskeyAdmin(ModelAdmin):
    list_display = ['user', 'exam', 'code','center','status','created_at']
    list_filter = ['exam', 'center', 'status']
    search_fields = ['user', 'exam', 'code','center']

@admin.register(Interview)
class InterviewAdmin(ModelAdmin):
    list_display = ['user', 'time','link','subject','class_category','grade','level' ,'status','attempt','created_at']
    list_filter = ['subject','class_category','grade','level' ,'status','attempt']
    search_fields = ['user', 'link','subject','class_category','grade','level' ]

@admin.register(ExamCenter)
class ExamCenter(ModelAdmin):
    list_display = ['user', 'center_name', 'pincode', 'state', 'city', 'status','area']
    list_filter = ['status']
    search_fields = ['user', 'center_name', 'pincode', 'state', 'city', 'area']

@admin.register(RecruiterEnquiryForm)
class RecruiterEnquiryForm(ModelAdmin):
    list_display = ['user','teachertype', 'class_category',  'pincode',  'state', 'subject', 'area',  'name', 'city', 'email']
    list_filter = ['teachertype', 'class_category', 'subject']
    search_fields = ['user', 'teachertype', 'class_category',  'pincode',  'state', 'subject', 'area',  'name', 'city', 'email']

    def subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])

    def class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])


@admin.register(AssignedQuestionUser)
class AssignedQuestionUserAdmin(ModelAdmin):
    list_display = ['user', 'get_subject', 'get_class_category']
    list_filter = ['subject', 'class_category']
    search_fields = ['user', 'subject', 'class_category']
    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])
    
@admin.register(HireRequest)
class HireRequestAdmin(ModelAdmin):
    list_display = ['recruiter_id','teacher_id','date', 'get_subject','get_class_category']
    list_filter = ['date']
    search_fields = ['recruiter_id','teacher_id','date']

    def get_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.subject.all()])
    def get_class_category(self, obj):
        return ", ".join([str(class_category) for class_category in obj.class_category.all()])

@admin.register(Apply)
class ApplyAdmin(ModelAdmin):
    list_display = ['user','subject','class_category','get_teacher_job_type','status','date']
    list_filter = ['subject','class_category','teacher_job_type','status','date']
    search_fields = ['user','subject','class_category','teacher_job_type','status','date']

    def get_teacher_job_type(self, obj):
        return ", ".join([str(job_type) for job_type in obj.teacher_job_type.all()])   
