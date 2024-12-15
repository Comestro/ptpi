from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

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

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


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
        return self.user.username

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

class Question(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    classCategory = models.ForeignKey(ClassCategory, on_delete=models.CASCADE, default=1)
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
        subject_name = getattr(self.subject, 'subject_name', 'Unknown Subject')
        level_name = getattr(self.level, 'name', 'Unknown Level')
        text_preview = self.text[:50] if self.text else "No text"
        return f"{subject_name} - {level_name} - {text_preview}"


class TeacherSkill(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficiency_level = models.CharField(max_length=100, null=True, blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.username
    
class TeacherJobType(models.Model):
    teacher_job_name = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.teacher_job_name

class Preference(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    job_role = models.ForeignKey(Role, on_delete=models.CASCADE,default=1)
    class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE,default=1)
    prefered_subject = models.ManyToManyField(Subject)
    teacher_job_type = models.ManyToManyField(TeacherJobType)

    def __str__(self):
        return self.user.username
class TeacherSubject(models.Model):	
   user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)	
   subject = models.ForeignKey(Subject, on_delete=models.CASCADE)

   def __str__(self): 
        return self.user.username	
   
class BasicProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name="user_profile", null=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
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
   
class TeacherClassCategory(models.Model):	
  user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)	
  class_category = models.ForeignKey(ClassCategory, on_delete=models.CASCADE)

  def __str__(self):
        return self.user.username	
  
class TeacherExamResult(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    correct_answer = models.IntegerField(default=0, null=True, blank=True)
    is_unanswered = models.IntegerField(null=True, blank=True)
    incorrect_answer = models.IntegerField(default=0, null=True, blank=True)
    isqulified = models.BooleanField(default=False)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    attempt = models.IntegerField(default=3)

    def __str__(self):
        return self.correct_answer
    
class JobPreferenceLocation(models.Model):
    preference = models.ForeignKey(Preference, on_delete=models.CASCADE)
    state = models.CharField(max_length=200,null=True, blank=True)
    city = models.CharField(max_length=200,null=True, blank=True)
    sub_division = models.CharField(max_length=200,null=True, blank=True)
    block = models.CharField(max_length=200,null=True, blank=True)
    area = models.TextField(null=True, blank=True)
    pincode = models.CharField(max_length=6, null=True, blank=True)
    def __str__(self):
        return self.preference.user.username
class Report(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="user_reports", null=True)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Report by {self.user.username if self.user else 'Anonymous'} on {self.question.id}"

    class Meta:
        unique_together = ('user', 'question')