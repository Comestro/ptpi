from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.timezone import timedelta
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
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_recruiter = models.BooleanField(default=False)
    is_teacher = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    otp = models.CharField(max_length=8, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True) 

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['Fname', 'Lname','username']

    def __str__(self):
        return self.email
    
    def is_complete(self):
        required_fields = {
            "email": self.email,
            "username": self.username,
            "Fname": self.Fname,
            "Lname": self.Lname,

        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields

class TeachersAddress(models.Model):
    ADDRESS_TYPE_CHOICES = [
        ('current', 'Current'),
        ('permanent', 'Permanent'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPE_CHOICES, null=True, blank=True)
    state = models.CharField(max_length=100, default='Bihar', null=True, blank=True)
    division = models.CharField(max_length=100, null=True, blank=True)
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

class Subject(models.Model):
    subject_name = models.CharField(max_length=100, null=True, blank=True)
    subject_description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.subject_name

class ClassCategory(models.Model):
    name = models.CharField(max_length=100,unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

class Teacher(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=255, null=True, blank=True)
    gender = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[
            ("Female", "Female"),
            ("Male", "Male"),
            ("other", "other"),
        ]
    )
    religion = models.CharField(max_length=100, null=True, blank=True)
    nationality = models.CharField(
        max_length=100, null=True, blank=True,
        choices=[
            ("Indian", "Indian"),
            ("other", "other"),
        ]
    )
    image = models.ImageField(upload_to='images/', null=True, blank=True)
    aadhar_no = models.CharField(max_length=12, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    alternate_phone = models.CharField(max_length=15, null=True, blank=True)
    verified = models.BooleanField(default=False)
    class_categories = models.ForeignKey(ClassCategory, on_delete=models.CASCADE, null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    availability_status = models.CharField(max_length=50, default='Available')

    def __str__(self):
        return self.user.username

class EducationalQualification(models.Model):
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class TeacherQualification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    qualification = models.ForeignKey(EducationalQualification, on_delete=models.CASCADE, null=True, blank=True)
    institution = models.CharField(max_length=225, null=True, blank=True)
    year_of_passing = models.PositiveIntegerField(null=True, blank=True)
    grade_or_percentage = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.qualification.name} ({self.year_of_passing})"
        return f"Unknown User - {self.qualification.name} ({self.year_of_passing})"
    
    def is_complete(self):
        required_fields = {
            "qualification": self.qualification,
            "institution": self.institution,
            "year_of_passing": self.year_of_passing,
            "grade_or_percentage": self.grade_or_percentage
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields

class Role(models.Model):
    jobrole_name = models.CharField(max_length=400, null=True, blank=True)

    def __str__(self):
        return self.jobrole_name

class TeacherExperiences(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    institution = models.CharField(max_length=255, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.CASCADE, null=True, blank=True, default=1)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    achievements = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.user.username

class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True, null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

class Level(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return self.name

class TeacherSkill(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username
    
class TeacherJobType(models.Model):
    teacher_job_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.teacher_job_name

class Preference(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    job_role = models.ManyToManyField(Role)
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE,default=1)
    prefered_subject = models.ManyToManyField(Subject)
    teacher_job_type = models.ManyToManyField(TeacherJobType)

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
   user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)	
   subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

   def __str__(self): 
        return self.user.username	
   
class BasicProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="user_profile", null=True)
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
    language = models.CharField(max_length=100, blank=True, null=True)
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
   
class TeacherClassCategory(models.Model):	
  user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)	
  class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)

  def __str__(self):
        return self.user.username	

class Exam(models.Model):
    name = models.CharField(max_length=255)
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    time = models.FloatField(default=2.5)
    language = models.CharField(
        max_length=20,
        choices=[
            ('Hindi', 'Hindi'),
            ('English', 'English'),
        ],blank=True, null=True)
    text = models.CharField(max_length=2000)
    options = models.JSONField()
    solution = models.TextField(null=True,blank=True)
    correct_option = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()
        if self.correct_option < 1 or self.correct_option > len(self.options):
            raise models.ValidationError({
                'correct_option': f'Correct option must be between 1 and {len(self.options)}.'
            })

    class Meta:
        ordering = ['created_at']

    def __str__(self):
       return self.text

class TeacherExamResult(models.Model):
    examresult_id = models.AutoField(primary_key=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    correct_answer = models.IntegerField(default=0, null=True, blank=True)
    is_unanswered = models.IntegerField(null=True, blank=True)
    incorrect_answer = models.IntegerField(default=0, null=True, blank=True)
    isqulified = models.BooleanField(default=False)
    attempt = models.IntegerField(default=10)
    created_at = models.DateTimeField(auto_now_add=True)

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

    # def get_level(self):
    #     percentage = self.calculate_percentage()
    #     if self.isqulified and percentage >= 60:
    #         return "2nd Level"
    #     # elif self.isqulified:
    #     return "1st Level"
    #     # return "not_qualified"

    def save(self, *args, **kwargs):
        self.isqulified = self.get_()
        if self.pk is None:  # Handle attempts only for new entries
            last_result = TeacherExamResult.objects.filter(
                user=self.user
            ).order_by('-created_at').first()
            self.attempt = max(0, (last_result.attempt if last_result else self.attempt) + 1)

        super().save(*args, **kwargs)

class JobPreferenceLocation(models.Model):
    preference = models.ForeignKey(Preference, on_delete=models.CASCADE)
    state = models.CharField(max_length=200,null=True, blank=True)
    city = models.CharField(max_length=200,null=True, blank=True)
    sub_division = models.CharField(max_length=200,null=True, blank=True)
    block = models.CharField(max_length=200,null=True, blank=True)
    post_office = models.CharField(max_length=200, null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return self.preference.user.username
    
    def is_complete(self):
        required_fields = {
            "preference": self.preference,
            "state": self.state,
            "city": self.city,
            "sub_division": self.sub_division,
            "block": self.block,
            "post_office": self.post_office,
            "area": self.area,
            "pincode": self.pincode
        }
        missing_fields = [field for field, value in required_fields.items() if not value]
        return not missing_fields, missing_fields

class Report(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_reports", null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return f"Report by {self.user.username if self.user else 'Anonymous'} on {self.question.id}"

    class Meta:
        unique_together = ('user', 'question')

class Passkey(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE,null=True, related_name='passkeys')
    code = models.CharField(max_length=200,null=True,blank=True,unique=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # Check if the passkey is still valid (e.g., 10 minutes expiration)
        expiration_time = self.created_at + timedelta(minutes=10)
        return self.status and now() < expiration_time

    def __str__(self):
        return f"{self.code} - {self.exam}"
