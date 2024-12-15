from django.contrib import admin
from .models import *

# Register your models here.

@admin.register(EducationalQualification)
class EducationalQualificationAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

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

@admin.register(TeacherClassCategory)
class TeacherClassCategoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'class_category']

@admin.register(TeacherExamResult)
class TeacherExamResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'isqulified', 'level', 'attempt']

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
    list_display = ['user', 'skill', 'proficiency_level', 'years_of_experience']

@admin.register(TeacherSubject)
class TeacherSubjectAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject']

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ['user', 'fullname', 'gender', 'religion', 'nationality', 'image', 'aadhar_no', 'alternate_phone', 'verified', 'class_categories', 'rating', 'date_of_birth', 'availability_status']

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(Preference)
class PreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'job_role', 'class_category', 'get_prefered_subject', 'get_teacher_job_type']

    def get_prefered_subject(self, obj):
        return ", ".join([str(subject) for subject in obj.prefered_subject.all()])
    def get_teacher_job_type(self, obj):
        return ", ".join([str(job_type) for job_type in obj.teacher_job_type.all()])
    
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['user', 'question', 'created_at', 'reason']

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['subject', 'level', 'classCategory', 'time', 'text', 'options', 'correct_option', 'created_at']

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']

@admin.register(TeacherJobType)
class TeacherJobTypeAdmin(admin.ModelAdmin):
    list_display = ['teacher_job_name']
