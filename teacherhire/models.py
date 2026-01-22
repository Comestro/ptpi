from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import os
import base64
from django.utils.timezone import now


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, username, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True, default='default_username')
    Fname = models.CharField(max_length=100, null=True, blank=True)
    Lname = models.CharField(max_length=100, null=True, blank=True)
    user_code = models.CharField(max_length=100, null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_recruiter = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_centeruser = models.BooleanField(default=False)
    is_questionuser = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=8, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)
    date = models.DateTimeField(default=now)
    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['Fname', 'Lname','username']

    def __str__(self):
        return self.email
    

    def save(self, *args, **kwargs):
        if not self.user_code:
            self.user_code = self.generate_user_code()
        super().save(*args, **kwargs)

    def generate_user_code(self):
        from datetime import datetime

        # Determine prefix based on role
        if self.is_teacher:
            prefix = "T"
        elif self.is_recruiter:
            prefix = "R"
        elif self.is_centeruser:
            prefix = "C"
        elif self.is_questionuser:
            prefix = "Q"
        elif self.is_staff:  # For admin
            prefix = "A"
        else:
            prefix = "U"  # Unknown/default

        date_part = datetime.now().strftime("%d%m%Y")  # e.g., 05042025
        code_prefix = f"{prefix}-{date_part}"

        # Find the latest user with matching code_prefix
        last_user = CustomUser.objects.filter(user_code__startswith=code_prefix).order_by('-id').first()

        if last_user and last_user.user_code:
            try:
                last_number = int(last_user.user_code[len(code_prefix):])
                new_number = str(last_number + 1).zfill(3)
            except ValueError:
                new_number = "001"
        else:
            new_number = "001"

        return f"{code_prefix}{new_number}"


class TeachersAddress(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('current', 'Current'),
        ('permanent', 'Permanent'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name='teachersaddress')
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, null=True, blank=True)
    state = models.CharField(max_length=100, default='Bihar', null=True, blank=True)
    division = models.CharField(max_length=100, null=True, blank=True)
    postoffice = models.CharField(max_length=100, null=True, blank=True)
    district = models.CharField(max_length=100, null=True, blank=True)
    block = models.CharField(max_length=100, null=True, blank=True)
    village = models.CharField(max_length=100, null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)    
    def __str__(self):
        return f'{self.address_type} address of {self.user.username}'
    
    def is_complete(self):
        required_fields = {
            "state": self.state,
            "division": self.division,
            "district": self.district,
            "block": self.block,
            "village": self.village,
            "area": self.area,
            "pincode": self.pincode,
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields
    
class ClassCategory(models.Model):
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.name)
    
class Subject(models.Model):
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE, related_name='subjects')
    subject_name = models.CharField(max_length=100)
    subject_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.subject_name)
    
class Reason(models.Model):
    issue_type = models.CharField(max_length=200,unique=True, null=True, blank=True)

    def __str__(self):
        return self.issue_type

class EducationalQualification(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class TeacherQualification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True,related_name='teacherqualifications')
    qualification = models.ForeignKey(EducationalQualification, on_delete=models.CASCADE, null=True, blank=True)
    institution = models.CharField(max_length=225, null=True, blank=True)
    board_or_university = models.CharField(max_length=255, null=True, blank=True)
    year_of_passing = models.PositiveIntegerField(null=True, blank=True)
    grade_or_percentage = models.CharField(max_length=50, null=True, blank=True)
    session = models.CharField(max_length=50, null=True, blank=True)
    subjects = models.JSONField(null=True, blank=True)
    stream_or_degree = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.qualification.name} ({self.year_of_passing}) - ({self.stream_or_degree})"
        return f"Unknown User - {self.qualification.name} ({self.year_of_passing}) - {self.stream_or_degree}"

class Role(models.Model):
    jobrole_name = models.CharField(max_length=400)

    def __str__(self):
        return self.jobrole_name

class TeacherExperiences(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name='teacherexperiences')
    institution = models.CharField(max_length=255, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True, default=1)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    achievements = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name
    
class Level(models.Model):
    name = models.CharField(max_length=100)
    level_code = models.FloatField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return str(self.name)

class TeacherSkill(models.Model):
    user = models.ForeignKey(CustomUser, related_name='teacherskill', on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)  

    def __str__(self):
        return f"{self.user.Fname} {self.user.Lname} - {self.skill.name}"
    
    class Meta:
        unique_together = ('user', 'skill')

    
class TeacherJobType(models.Model):
    teacher_job_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.teacher_job_name

class Preference(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='preferences')
    class_category = models.ManyToManyField(ClassCategory)
    prefered_subject = models.ManyToManyField(Subject)

    def __str__(self):
        return self.user.username
    
    def is_complete(self):
        required_fields = {
            "job_role": self.job_role,
            "class_category": self.class_category,
            "prefered_subject": self.prefered_subject,
            "teacher_job_type": self.teacher_job_type
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields

class TeacherSubject(models.Model):	
   user = models.ForeignKey(CustomUser, on_delete=models.CASCADE,related_name='teachersubjects')	
   subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

   def __str__(self): 
        return self.user.username	 
class BasicProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="profiles", null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True)
    religion = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    marital_status = models.CharField(
        max_length=20,
        choices=[
            ('single', 'Single'),
            ('married', 'Married'),
            ('unmarried', 'Unmarried')
        ],
        blank=True,
        null=True
    )
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Male'),
            ('female', 'Female'),
            ('other', 'Other')
        ],
        blank=True,
        null=True
    )
    language = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def _str_(self):
        return f"Basic Profile of {self.user.username}"
    
    def is_complete(self):
        required_fields = {
            "profile_picture": self.profile_picture,
            "phone_number": self.phone_number,
            "religion": self.religion,
            "date_of_birth": self.date_of_birth,
            "marital_status": self.marital_status,
            "gender": self.gender,
            "language": self.language
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields
   
    def save(self, *args, **kwargs):
        if self.pk:
            old_instance = BasicProfile.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.profile_picture != self.profile_picture:
                if old_instance.profile_picture and os.path.isfile(old_instance.profile_picture.path):
                    os.remove(old_instance.profile_picture.path)
        super().save(*args, **kwargs)

class TeacherClassCategory(models.Model):	
  user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)	
  class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)

  def __str__(self):
        return self.user.username	

class ExamCenter(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    center_name = models.CharField(max_length=200, null=True, blank=True)
    phone = models.CharField(max_length=15)
    alt_phone = models.CharField(max_length=15, null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return str(self.center_name)
    
class AssignedQuestionUser(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    class_category = models.ManyToManyField(ClassCategory)
    subject = models.ManyToManyField(Subject)
    status = models.BooleanField(default=True)

    def __str__(self):
        return str(self.id) if self.user else "Unassigned User"

class Exam(models.Model):
    assigneduser = models.ForeignKey(AssignedQuestionUser, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255)
    set_name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)
    total_marks = models.PositiveIntegerField()
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    type = models.CharField(
        max_length=20,
        choices=[
            ('offline', 'offline'),
            ('online','online')
        ],
        default='online')
    total_questions = models.PositiveIntegerField(default=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=False)

    @property
    def count_question(self):
        qs = self.questions.all()
        return {
            "original_questions": qs.filter(related_question__isnull=True).count(),
            "related_questions": qs.filter(related_question__isnull=False).count(),
        }

    def __str__(self):
        return str(self.name) 

class Question(models.Model):
    order = models.PositiveIntegerField(default=0)
    related_question = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    language = models.CharField(
        max_length=20,
        choices=[
            ('Hindi', 'Hindi'),
            ('English', 'English'),
        ],blank=True, null=True)
    text = models.CharField(max_length=2000)
    options = models.JSONField()
    solution = models.TextField(blank=True,null=True, default="")
    correct_option = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.correct_option < 1 or self.correct_option > len(self.options):
            raise models.ValidationError({
                'correct_option': f'Correct option must be between 1 and {len(self.options)}.'
            })

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order:
            last_q = Question.objects.filter(exam=self.exam, language=self.language).count()
            self.order = last_q + 1
        super().save(*args, **kwargs)

    def __str__(self):
       return self.text
    

class TeacherExamResult(models.Model):
    examresult_id = models.AutoField(primary_key=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    correct_answer = models.IntegerField(default=0, null=True, blank=True)
    is_unanswered = models.IntegerField(null=True, blank=True)
    incorrect_answer = models.IntegerField(default=0, null=True, blank=True)
    isqualified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    has_exam_attempt = models.BooleanField(default=False)
    attempt = models.IntegerField(default=1)
    language = models.CharField(
        max_length=20,
        choices=[
            ('Hindi', 'Hindi'),
            ('English', 'English'),
        ],blank=True
    )

    def __str__(self):
        return f"ExamResult-{self.examresult_id}"

    def calculate_percentage(self):
        total_questions = self.correct_answer + (self.is_unanswered or 0) + (self.incorrect_answer or 0)
        if total_questions == 0:
            return 0
        return round((self.correct_answer / total_questions) * 100, 2)

    def get_(self):
        percentage = self.calculate_percentage()
        return percentage >= 60

    def save(self, *args, **kwargs):
        self.isqualified = self.get_()
        
        if self.pk is None:
            existing_result = TeacherExamResult.objects.filter(
                user=self.user,
                exam__subject=self.exam.subject,
                exam__class_category=self.exam.class_category,
                exam__level=self.exam.level
            ).order_by('-created_at').first()  

            if existing_result:
                self.attempt = existing_result.attempt + 1
            else:
                self.attempt = 1

        super().save(*args, **kwargs)


class Report(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_reports", null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    issue_type = models.ManyToManyField(Reason)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Report by {self.user.username if self.user else 'Anonymous'} on {self.question.id}"

    class Meta:
        unique_together = ('user', 'question')

class Passkey(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE,null=True, related_name='passkeys')
    center = models.ForeignKey(ExamCenter, on_delete=models.CASCADE,null=True, related_name='passkeys')
    code = models.CharField(max_length=200,null=True,blank=True,unique=True)
    status = models.CharField(max_length=200,choices=[('requested','requested'),('isused', 'isused'),('fulfilled','fulfilled'),('rejected','rejected')], default='requested')
    reject_reason = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return str(self.user.username)
    
def get_default_level():
    return Level.objects.get_or_create(name='2nd Level Online')[0]   

class Interview(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, null=True,blank=True)
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)
    time = models.DateTimeField(null=True, blank=True)
    link = models.CharField(max_length=200,null= True, blank=True)
    status = models.CharField(max_length=200,choices=[('requested','requested'),('scheduled','scheduled'),('fulfilled','fulfilled'),('rejected','rejected')], default='requested', null=True, blank=True)
    reject_reason = models.CharField(max_length=500, null=True, blank=True)
    grade = models.FloatField(default=0,null=True, blank=True)
    attempt = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return str(self.user.username)
    
class HireRequest(models.Model):
    recruiter_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recruiter')
    teacher_id = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    subject = models.ManyToManyField(Subject)
    class_category = models.ManyToManyField(ClassCategory)
    teacher_job_type = models.ManyToManyField(TeacherJobType)
    status = models.CharField(max_length=200,choices=[('requested','requested'),('fulfilled','fulfilled'),('rejected','rejected')], default='requested')
    reject_reason = models.CharField(max_length=500, null=True, blank=True)

class RecruiterEnquiryForm(models.Model):
    teachertype = models.CharField(max_length=200, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    class_category = models.ManyToManyField(ClassCategory)
    subject = models.ManyToManyField(Subject)
    name = models.CharField(max_length=200, null=True, blank=True)
    email = models.EmailField()
    contact = models.PositiveIntegerField(null=True, blank=True)

class Apply(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='apply')
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)
    teacher_job_type = models.ForeignKey(TeacherJobType, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    salary_expectation = models.CharField(max_length=200, null=True, blank=True)
    salary_type = models.CharField(max_length=200, null=True, blank=True, choices=[('monthly','monthly'),('hourly','hourly'),('daily','daily')])
    status = models.BooleanField(default=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username
    
    class Meta:
        unique_together = ('user', 'class_category', 'teacher_job_type', 'subject')
    
class JobPreferenceLocation(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, default=1, related_name='jobpreferencelocation')
    apply = models.ForeignKey(Apply, on_delete=models.CASCADE, related_name='preferred_locations', null=True, blank=True)
    state = models.CharField(max_length=200, null=True, blank=True)
    district = models.CharField(max_length=200, null=True, blank=True)
    city = models.CharField(max_length=200, null=True, blank=True)
    sub_division = models.CharField(max_length=200, null=True, blank=True)
    block = models.CharField(max_length=200, null=True, blank=True)
    post_office = models.CharField(max_length=200, null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return str(self.user.username  )

    def is_complete(self):
        required_fields = {
            "state": self.state,
            "district": self.district,   
            "city": self.city,
            "sub_division": self.sub_division,
            "block": self.block,
            "post_office": self.post_office,
            "area": self.area,
            "pincode": self.pincode
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields

class MissingSubject(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    subject_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject_name} - {self.user.username if self.user else 'Anonymous'}"
