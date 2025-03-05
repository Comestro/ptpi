from rest_framework import serializers
import re
from teacherhire.models import *
import random
from rest_framework.exceptions import ValidationError
from django.utils.encoding import smart_str, force_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .utils import Util
from datetime import datetime
from datetime import date
import string
from translate import Translator
from rest_framework.validators import UniqueValidator
from django.contrib.auth.password_validation import validate_password

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'password' ,'Fname', 'Lname', 'email','is_verified']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data['email'].split('@')[0],
            Fname=validated_data['Fname'],
            Lname=validated_data['Lname'],
            email=validated_data['email'],

        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class RecruiterRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    Fname = serializers.CharField(required=True)
    Lname = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'Fname', 'Lname', 'is_recruiter', 'is_verified']

    def validate_password(self, value):
        if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value) or not re.search(r"@", value):
            raise serializers.ValidationError("Password must be at least 8 characters long, contain a letter, a number, and '@'.")
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_recruiter = True
        is_verified = True
        
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email is already in use.'})
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{random.randint(1000, 9999)}"
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=validated_data['password'],
                Fname=Fname,
                Lname=Lname,
                is_recruiter=is_recruiter,   
                is_verified = is_verified
            )            
        except Exception as e:
            raise ValidationError({'error': str(e)})
        return user
    
class CenterUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    Fname = serializers.CharField(required=True)
    Lname = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'Fname', 'Lname', 'is_centeruser', 'is_verified']

    def validate_password(self, value):
        if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value) or not re.search(r"@", value):
            raise serializers.ValidationError("Password must be at least 8 characters long, contain a letter, a number, and '@'.")
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_centeruser = True
        is_verified = True
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email is already in use.'})
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{random.randint(1000, 9999)}"
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=validated_data['password'],
                Fname=Fname,
                Lname=Lname,
                is_centeruser=is_centeruser,
                is_verified=is_verified
            )
        except Exception as e:
            raise ValidationError({'error': str(e)})
        return user
    
class QuestionUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    Fname = serializers.CharField(required=True)
    Lname = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'Fname', 'Lname', 'is_questionuser', 'is_verified']

    def validate_password(self, value):
        if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value) or not re.search(r"@", value):
            raise serializers.ValidationError("Password must be at least 8 characters long, contain a letter, a number, and '@'.")
        return value
    
    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_questionuser = True
        is_verified = True
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email is already in use.'})
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{random.randint(1000, 9999)}"
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=validated_data['password'],
                Fname=Fname,
                Lname=Lname,
                is_questionuser=is_questionuser,
                is_verified=is_verified 
            )
        except Exception as e:
            raise ValidationError({'error': str(e)})
        return user
    
class ChangePasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, min_length=8)

    def validate_new_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value
       
class TeacherRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    Fname = serializers.CharField(required=True)
    Lname = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'Fname', 'Lname', 'is_verified']

    def validate_password(self, value):
        if len(value) < 8 or not re.search(r"[A-Za-z]", value) or not re.search(r"\d", value) or not re.search(r"@", value):
            raise serializers.ValidationError("Password must be at least 8 characters long, contain a letter, a number, and '@'.")
        return value

    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_teacher = True
        is_verified = True
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError({'email': 'Email is already in use.'})
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}{random.randint(1000, 9999)}"
        try:
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=validated_data['password'],
                Fname=Fname,
                Lname=Lname,
                is_teacher=is_teacher,
                is_verified = is_verified,
            )            
        except Exception as e:
            raise ValidationError({'error': str(e)})
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=100)
    password = serializers.CharField(max_length=100)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise ValidationError({'email': 'Email not found.'})

        if not user.check_password(password):
            raise ValidationError({'password': 'Incorrect password.'})
        
        is_admin = user.is_staff
        is_recruiter = user.is_recruiter
        if is_admin and is_recruiter:
            is_admin = True
            
        data["is_admin"] = True if user.is_staff else False
        data["is_recruiter"] = True if user.is_recruiter else False
        data["user"] = user
        return data

class TeacherExperiencesSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    institution = serializers.CharField(max_length=255, required=False, allow_null=True)
    role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    achievements = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = TeacherExperiences
        fields = ['id','user','institution', 'role', 'start_date', 'end_date', 'achievements']

    def validate_institution(self, value):
        if value and len(value) < 3:
            raise serializers.ValidationError("Institution name must be at least 3 characters long.")
        return value

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError("End date cannot be earlier than start date.")
        return data

    def validate_achievements(self, value):
        if value:
            value = value.strip()
            if len(value) < 10:
                raise serializers.ValidationError("Achievements must be at least 10 characters long.")
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.user:
            # representation['user'] = UserSerializer(instance.user).data
            representation['role'] = RoleSerializer(instance.role).data
        return representation
class SubjectSerializer(serializers.ModelSerializer):
    class_category_name = serializers.SerializerMethodField()  # Add new field

    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'class_category', 'class_category_name']

    def get_class_category_name(self, obj):
        """Returns the name of the class category"""
        return obj.class_category.name if obj.class_category else None 

    def validate(self, data):
        subject_name = data.get('subject_name')
        class_category = data.get('class_category')

        if not subject_name or not class_category:
            raise serializers.ValidationError("Both subject name and class category are required.")

        # Case-insensitive check if subject already exists in the same class_category
        if Subject.objects.filter(subject_name__iexact=subject_name, class_category=class_category).exists():
            raise serializers.ValidationError(
                f"The subject '{subject_name}' already exists for class category '{class_category.name}'."
            )

        return data



class ClassCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassCategory
        fields = ['id', 'name', 'subjects']
        depth = 1 

    def validate_name(self, value):
        if ClassCategory.objects.filter(name=value).exists():
            raise serializers.ValidationError("A classcategory with this name already exists.")
        return value
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subjects'] = SubjectSerializer(instance.subjects.all(), many=True).data
        return representation

class ReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reason
        fields = ['id', 'issue_type']

    def validate_issue_type(self, value):
        if Reason.objects.filter(issue_type=value).exists():
            raise serializers.ValidationError("A Reason with this issue_type already exists.")
        return value

class LevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Level
        fields = ['id','name','description']
    
    def validate_name(self, value):
        if Level.objects.filter(name=value).exists():
            raise serializers.ValidationError("A level with this name already exists.")
        return value

class SkillSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=20, required=False, allow_null=True)

    class Meta:
        model = Skill
        fields = ['id', 'name','description']

    def validate_name(self, value):
        if value is not None:
            if len(value) < 3:
                raise serializers.ValidationError("Skill name must be at least 3 characters.")
        return value
    
    def validate_name(self, value):
        if Skill.objects.filter(name=value).exists():
            raise serializers.ValidationError("A skill with this name already exists.")
        return value
class TeachersAddressSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    pincode = serializers.CharField(max_length=6, required=False, allow_null=True)
    
    class Meta:
        model = TeachersAddress
        fields = ['id', 'user', 'address_type', 'state', 'division', 'district','postoffice', 'block', 'village', 'area', 'pincode']
    
    def validate_pincode(self, value):
        # Only validate if the pincode is not empty or null
        if value and (len(str(value)) != 6):
            raise serializers.ValidationError("Pincode must be 6-digit integer.")
        if (not str(value).isdigit() or int(value) <= 0):
            raise serializers.ValidationError("Pincode must be positive integer.")
        return value
    
class QuestionSerializer(serializers.ModelSerializer):
    text = serializers.CharField(max_length=2000, allow_null=True, required=False)
    options = serializers.JSONField(required=False, allow_null=True)
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all(),required=False, allow_null=True)
    class Meta:
        model = Question
        fields = ['id', 'text', 'options','exam', 'solution', 'correct_option', 'language', 'time']
    def validate_text(self, value):
        if value is not None and len(value)< 5:
            raise serializers.ValidationError("Text must be at least 5 characters.")
        if Question.objects.filter(text=value).exists():
            raise serializers.ValidationError("This question is already exists.")
        return value
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # representation['exam'] = ExamSerializer(instance.exam).data
        return representation

class ExamSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=2000, required=False)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=True)
    level = serializers.PrimaryKeyRelatedField(queryset=Level.objects.all(), required=True)
    class_category = serializers.PrimaryKeyRelatedField(queryset=ClassCategory.objects.all(), required=False)
    assigneduser = serializers.PrimaryKeyRelatedField(queryset=AssignedQuestionUser.objects.all(), required=False, allow_null=True)

    class Meta:
        model = Exam
        fields = ['id', 'name', 'description', 'assigneduser', 'subject', 'level', 'class_category', 'total_marks', 'duration', 'questions','type']
        depth = 1 

    def create(self, validated_data):
        subject = validated_data.get('subject')
        level = validated_data.get('level')
        class_category = validated_data.get('class_category')
        assigneduser = validated_data.get('assigneduser', None)
        try:
            subject = Subject.objects.get(id=subject.id, class_category_id=class_category.id)
        except Subject.DoesNotExist:
            serializers.ValidationError("Invalid subject")
        # auto generate exam name
        exam_name = f"{class_category.name}, {subject.subject_name}, {level.name}".strip()

        existing_count = Exam.objects.filter(name__startswith=exam_name).count()
        auto_name = f"{exam_name} - Set {existing_count + 1}"

        if not assigneduser:
            admin_user = CustomUser.objects.filter(is_staff=True).first()
            print(admin_user)
            if admin_user:
                assigneduser, created = AssignedQuestionUser.objects.get_or_create(user=admin_user)
            validated_data['assigneduser'] = assigneduser
        validated_data['name'] = auto_name
        return super().create(validated_data) 
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subject'] = SubjectSerializer(instance.subject).data
        representation['level'] = LevelSerializer(instance.level).data
        representation['class_category'] = ClassCategorySerializer(instance.class_category).data
        representation['questions'] = QuestionSerializer(instance.questions.all(), many=True).data
        representation['assigneduser'] = AssignedQuestionUserSerializer(instance.assigneduser).data if instance.assigneduser else None
        return representation
    
class TeacherSkillSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    skill = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), required=False)
    class Meta:
        model = TeacherSkill
        fields = ['id', 'user' ,'skill']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # representation['user'] = UserSerializer(instance.user).data
        representation['skill'] = SkillSerializer(instance.skill).data
        return representation
 
    def validate(self, attrs):
        # user = attrs.get('user')
        skill = attrs.get('skill')
        # This user have skill already exists
        if TeacherSkill.objects.filter( skill=skill).exists():
            raise serializers.ValidationError('This user already has this skill.')
        return attrs

class EducationalQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalQualification
        fields = ['id', 'name']

class TeacherQualificationSerializer(serializers.ModelSerializer):
    # This will allow you to include the user and qualification in the serialized data
    # user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    qualification = serializers.SlugRelatedField(queryset=EducationalQualification.objects.all(), slug_field="name", required=False)
    
    class Meta:
        model = TeacherQualification
        fields = ['id', 'qualification', 'institution', 'year_of_passing', 'grade_or_percentage']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        # representation['user'] = UserSerializer(instance.user).data
        representation['qualification'] = EducationalQualificationSerializer(instance.qualification).data
        
        return representation
    
    def validate_year_of_passing(self, value):
        current_year = datetime.now().year
        if not (1000 <= value <= current_year):  
            raise serializers.ValidationError("Year of passing must be a valid four-digit year and cannot be in the future.")
        return value

    def validate_grade_or_percentage(self, value):
        value_str = str(value).strip()  # Convert to string for regex checking

        # Check if input is a valid letter grade (A, B+, C-, etc.)
        if re.fullmatch(r"^[A-D][+-]?$", value_str, re.IGNORECASE):  
            return value_str.upper()  # Standardize to uppercase (e.g., "a" → "A")

        try:
            value_float = float(value_str)  # Convert to float
        except ValueError:
            raise serializers.ValidationError("Grade or percentage must be a valid letter grade (A, B+, etc.) or a number (0-100).")

        # Ensure number is in range
        if value_float < 0 or value_float > 100:
            raise serializers.ValidationError("Grade or percentage must be between 0 and 100.")
        return value_float  

    def validate(self, data):
        user = data.get('user')
        if user:
            previous_qualification = TeacherQualification.objects.filter(user=user).order_by('-year_of_passing').first()
            if previous_qualification:
                if data.get('year_of_passing')<= previous_qualification.year_of_passing:
                    raise serializers.ValidationError(
                        "Year of passing should be greater than the previous qualification's year."
                    )
        return data
    
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id','jobrole_name']

    def validate_jobrole_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Role name must be at least 3 characters.")
        
        if Role.objects.filter(jobrole_name=value).exists():
            raise serializers.ValidationError("A Role with this name already exists.")
        return value

class PreferenceSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    job_role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), many=True,required=False,)
    class_category = serializers.PrimaryKeyRelatedField(queryset=ClassCategory.objects.all(), required=False, many=True)
    prefered_subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    teacher_job_type = serializers.PrimaryKeyRelatedField(queryset=TeacherJobType.objects.all(), many=True, required=False)

    class Meta:
        model = Preference
        fields = [
            'id', 
            'user', 
            'job_role', 
            'class_category', 
            'prefered_subject', 
            'teacher_job_type', 
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['job_role'] = RoleSerializer(instance.job_role.all(), many=True).data
        representation['class_category'] = ClassCategorySerializer(instance.class_category.all(), many=True).data if instance.class_category else None
        representation['prefered_subject'] = SubjectSerializer(instance.prefered_subject.all(), many=True).data
        representation['teacher_job_type'] = TeacherJobTypeSerializer(instance.teacher_job_type.all(), many=True).data
        return representation

class TeacherSubjectSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=True)
    class Meta:
        model = TeacherSubject
        fields = ['id','user','subject']
     
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['subject'] = SubjectSerializer(instance.subject).data
        return representation
    
class TeacherClassCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherClassCategory
        fields = '__all__'
class TeacherExamResultSerializer(serializers.ModelSerializer):
    exam = serializers.PrimaryKeyRelatedField(queryset=Exam.objects.all(), required=False)
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    total_question = serializers.SerializerMethodField()

    class Meta:
        model = TeacherExamResult
        fields = ['examresult_id', 'exam', 'user', 'correct_answer', 'is_unanswered', 'incorrect_answer', 'total_question','isqualified','calculate_percentage','created_at','has_exam_attempt']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = {"id":instance.user.id, "name":instance.user.username}
        representation['exam'] = {"id":instance.exam.id, "name":instance.exam.name, "level_id": instance.exam.level.id, "level_name": instance.exam.level.name, "subject_id": instance.exam.subject.id, "subjet_name": instance.exam.subject.subject_name, "class_category_id": instance.exam.class_category.id, "class_category_name": instance.exam.class_category.name}
        return representation
    
    def get_total_question(self, obj):
        correct = obj.correct_answer if obj.correct_answer is not None else 0
        unanswered = obj.is_unanswered if obj.is_unanswered is not None else 0
        incorrect = obj.incorrect_answer if obj.incorrect_answer is not None else 0
        return correct + unanswered + incorrect

class JobPreferenceLocationSerializer(serializers.ModelSerializer):
    teacher_apply = serializers.PrimaryKeyRelatedField(queryset=Apply.objects.all(), required=False)
    class Meta:
        model = JobPreferenceLocation
        fields = '__all__'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['teacher_apply'] = ApplySerializer(instance.teacher_apply).data
        return representation
    
    def validate_area(self, value):
        if JobPreferenceLocation.objects.filter(area=value, teacher_apply=self.initial_data.get('teacher_apply')).exists():
            raise serializers.ValidationError(" this area name already exists")
        
        teacher_apply_id = self.initial_data.get('teacher_apply')
        if teacher_apply_id:
            area_count = JobPreferenceLocation.objects.filter(teacher_apply=teacher_apply_id).count()
            if area_count >= 5:
                raise serializers.ValidationError("You can only add up to 5 areas for a single preference.")
        return value

class BasicProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    bio = models.CharField(max_length=100, blank=True, null=True)    
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True, validators=[UniqueValidator(queryset=BasicProfile.objects.all())])
    religion = models.CharField(max_length=15, blank=True, null=True)
    class Meta:
        model = BasicProfile
        fields = ['id', 'user', 'bio', 'phone_number', 'religion','profile_picture','date_of_birth','marital_status','gender','language']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        return representation

    def validate_phone_number(self, value):
        if value:
            cleaned_value = re.sub(r'[^0-9]', '', value)
            if len(cleaned_value) != 10:
                raise serializers.ValidationError("Phone number must be exactly 10 digits.")
            if not cleaned_value.startswith(('6', '7', '8', '9')):
                raise serializers.ValidationError("Phone number must start with 6, 7, 8, or 9.")
            return cleaned_value
        return value
    
    def validate_date_of_birth(self, value):
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future.")
        age = (date.today() - value).days // 365  
        if age < 18:
            raise serializers.ValidationError("You must be at least 18 years old.")
        return value
class CustomUserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'last_login', 'is_superuser', 'email', 'username',
            'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter',
            'is_teacher', 'is_centeruser', 'is_questionuser', 'role'
        ]
        read_only_fields = ['email', 'username']

    def get_role(self, obj):
        if obj.is_staff:
            return "admin"
        elif obj.is_recruiter:
            return "recruiter"
        elif obj.is_teacher:
            return "teacher"
        elif obj.is_centeruser:
            return "centeruser"
        elif obj.is_questionuser:
            return "questionuser"
        else:
            return "user"

class TeacherJobTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherJobType
        fields = ['id', 'teacher_job_name']
class SendPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=200)
    class Meta:
        fields = ['email']
    def validate(self, attrs):
        email = attrs.get('email')
        if CustomUser.objects.filter(email=email).exists():
            user = CustomUser.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.id))
            print('Encoded UID', uid)
            token = PasswordResetTokenGenerator().make_token(user)
            print('Password reset token: ', token)
            reset_link = 'http://localhost:8000/api/reset-password/'+uid+'/'+token
            print('Password reset link ', reset_link)
            body = 'Click Following Link to Reset Your Password '+reset_link
            data = {
                'subject':'Reset your Password',
                'body':body,
                'to_email':user.email
            }
            Util.send_email(data)
            return attrs
        else:
            raise ValidationError('Not a valid Email. Please provide a valid Email.')
class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    class Meta:
        fields = ['password', 'confirm_password']
        
    def validate(self, attrs):
        try:
            password = attrs.get('password')
            confirm_password = attrs.get('confirm_password')
            uid = self.context.get('uid')
            token = self.context.get('token')
            if password != confirm_password:
                raise serializers.ValidationError("Password and Confirm password doesn't match")
            id = smart_str(urlsafe_base64_decode(uid))
            user = CustomUser.objects.get(id=id)
            if not PasswordResetTokenGenerator().check_token(user, token):
                raise ValidationError('Token is not valid or Expired')
            user.set_password(password)
            user.save()
            return attrs
        except DjangoUnicodeDecodeError as identifier:
            PasswordResetTokenGenerator().check_token(user, token)
            raise ValidationError('Token is not valid or Expired')
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField()

class ReportSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    issue_type = serializers.PrimaryKeyRelatedField(queryset=Reason.objects.all(), many=True)

    class Meta:
        model = Report
        fields = ['id', 'user', 'question','issue_type','status', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['issue_type'] = ReasonSerializer(instance.issue_type.all(), many=True).data      
        return representation

class PasskeySerializer(serializers.ModelSerializer):
    class Meta:
        model = Passkey
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = {"id":instance.user.id, "email":instance.user.email}
        representation['exam'] = {"id":instance.exam.id, "name":instance.exam.name}
        representation['center'] = {"id":instance.center.id, "name":instance.center.center_name}
        return representation
class InterviewSerializer(serializers.ModelSerializer):
    class Meta:                    
        model = Interview
        fields = ['id','time', 'link', 'status','class_category', 'subject', 'grade']  # Exclude 'user' from here
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        return representation
    

class TeacherSerializer(serializers.ModelSerializer):
    teacherskill = TeacherSkillSerializer(many=True, required=False)
    profiles = BasicProfileSerializer(required=False)
    teachersaddress = TeachersAddressSerializer(many=True, required=False)
    teacherexperiences = TeacherExperiencesSerializer(many=True, required=False)
    teacherqualifications = TeacherQualificationSerializer(many=True, required=False)
    preferences = PreferenceSerializer(many=True, required=False)
    total_marks = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'Fname', 'Lname', 'email', 'profiles',
            'teacherskill', 'teachersaddress', 
            'teacherexperiences', 'teacherqualifications', 
            'preferences', 'total_marks'
        ]

    def get_total_marks(self, instance):
        last_result = TeacherExamResult.objects.filter(user=instance).order_by('created_at').last()
        return last_result.correct_answer if last_result else 0

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        if 'total_marks' not in representation:
            representation['total_marks'] = self.get_total_marks(instance)
        
        if 'teacherskill' in representation:
            representation['teacherskill'] = [
                {'skill': skill.get('skill')} for skill in representation['teacherskill']
            ]
        if 'teacherqualifications' in representation:
            representation['teacherqualifications'] = [
                {'qualification': qualification.get('qualification')} for qualification in representation['teacherqualifications']
            ]
        if 'teacherexperiences' in representation:
            representation['teacherexperiences'] = [
                {'start_date': experience.get('start_date'), 'end_date': experience.get('end_date'), 'achievements': experience.get('achievements')}
                for experience in representation['teacherexperiences']
            ]
        if 'profiles' in representation and representation['profiles'] is not None:
            profile_data = representation['profiles']
            profile_filtered = {
                'bio': profile_data.get('bio', ''),
                'phone_number': profile_data.get('phone_number', None),
                'religion': profile_data.get('religion', None),
                'profile_picture': profile_data.get('profile_picture', None),
                'date_of_birth': profile_data.get('date_of_birth', None),
                'marital_status': profile_data.get('marital_status', None),
                'gender': profile_data.get('gender', None),
                'language': profile_data.get('language', None),
            }
            if any(value is not None for value in profile_filtered.values()):
                representation['profiles'] = profile_filtered
            else:
                del representation['profiles']

        if 'preferences' in representation:
            representation['preferences'] = [
                {
                    'job_role': preference.get('job_role'),
                    'class_category': preference.get('class_category'),
                    'prefered_subject': preference.get('prefered_subject'),
                    'teacher_job_type': preference.get('teacher_job_type'),
                } for preference in representation['preferences']
            ]
        
        return representation


class ExamCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamCenter
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        return representation
        
class TeacherReportSerializer(serializers.ModelSerializer):
    teacherskill = TeacherSkillSerializer(many=True, required=False)
    teacherqualifications = TeacherQualificationSerializer(many=True, required=False)
    teacherexperiences = TeacherExperiencesSerializer(many=True, required=False)
    teacherexamresult = TeacherExamResultSerializer(many=True, required=False)
    preference = PreferenceSerializer(many=True, required=False)  
    rate = serializers.CharField(max_length=10, required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'Fname', 'Lname', 'email','rate', 'teacherskill', 'teacherqualifications', 'teacherexperiences', 'teacherexamresult', 'preference']

class AssignedQuestionUserSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    
    class Meta:
        model = AssignedQuestionUser
        fields = ['user', 'subject']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['subject'] = SubjectSerializer(instance.subject.all(), many=True).data
        return representation
class AllRecruiterSerializer(serializers.ModelSerializer):
    profiles = BasicProfileSerializer(required=False)
    class Meta:
        model = CustomUser
        fields = ['id', 'Fname', 'Lname', 'email','profiles']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if 'profiles' in representation and representation['profiles'] is not None:
            profile_data = representation['profiles']
            profile_filtered = {
                'bio': profile_data.get('bio', ''),
                'phone_number': profile_data.get('phone_number', None),
                'religion': profile_data.get('religion', None),
                'profile_picture': profile_data.get('profile_picture', None),
                'date_of_birth': profile_data.get('date_of_birth', None),
                'marital_status': profile_data.get('marital_status', None),
                'gender': profile_data.get('gender', None),
            }
            if any(value is not None for value in profile_filtered.values()):
                representation['profiles'] = profile_filtered
            else:
                del representation['profiles']
        return representation
    
class AllTeacherSerializer(serializers.ModelSerializer):
    teachersaddress = TeachersAddressSerializer(many=True, required=False)
    teachersubjects = TeacherSubjectSerializer(many=True, required=False)
    teacherqualifications = TeacherQualificationSerializer(many=True, required=False)
    total_marks = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'Fname', 'Lname', 'email', 'teachersubjects',
            'teachersaddress', 'teacherqualifications', 'total_marks'
        ]

    def get_total_marks(self, instance):
        last_result = TeacherExamResult.objects.filter(user=instance).order_by('created_at').last()
        return last_result.correct_answer if last_result else 0

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        if 'total_marks' not in representation:
            representation['total_marks'] = self.get_total_marks(instance)

        if 'teacherqualifications' in representation and representation['teacherqualifications']:
            representation['teacherqualifications'] = [
                {'qualification': qualification.get('qualification')} 
                for qualification in representation['teacherqualifications']
            ]

        if 'teachersubjects' in representation and representation['teachersubjects']:
            representation['teachersubjects'] = [
                {'subject': subject.get('subject')} 
                for subject in representation['teachersubjects']
            ]

        if 'teachersaddress' in representation and representation['teachersaddress']:
            representation['teachersaddress'] = [
                {'state': address.get('state')} 
                for address in representation['teachersaddress']
            ]

        return representation

class HireRequestSerializer(serializers.ModelSerializer):
    teacher_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    recruiter_id = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = HireRequest
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['teacher_id'] = UserSerializer(instance.teacher_id).data
        representation['recruiter_id'] = UserSerializer(instance.recruiter_id).data
        representation['subject'] = SubjectSerializer(instance.subject.all(), many=True).data
        representation['teacher_job_type'] = TeacherJobTypeSerializer(instance.teacher_job_type.all(), many=True).data
        return representation

class RecruiterEnquiryFormSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    contact = serializers.CharField(max_length=15, required=False, allow_blank=True, validators=[UniqueValidator(queryset=RecruiterEnquiryForm.objects.all())])

    class Meta:
        model = RecruiterEnquiryForm
        fields = "__all__"
    
    def validate_contact(self, value):
        if value:
            cleaned_value = re.sub(r'[^0-9]', '', value)
            if len(cleaned_value) != 10:
                raise serializers.ValidationError("Phone number must be exactly 10 digits.")
            if not cleaned_value.startswith(('6', '7', '8', '9')):
                raise serializers.ValidationError("Phone number must start with 6, 7, 8, or 9.")
            return cleaned_value
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subject'] = SubjectSerializer(instance.subject.all(), many=True).data
        return representation
    
class AllBasicProfileSerializer(serializers.ModelSerializer):
    profiles =  BasicProfileSerializer(required=False)
    class Meta:
        model = CustomUser
        fields = ['id','Fname','Lname','email','is_verified','profiles']
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if 'profiles' in representation and representation['profiles'] is not None:
            profile_data = representation['profiles']
            profile_filtered = {
                'bio': profile_data.get('bio', ''),
                'phone_number': profile_data.get('phone_number', None),
                'religion': profile_data.get('religion', None),
                'profile_picture': profile_data.get('profile_picture', None),
                'date_of_birth': profile_data.get('date_of_birth', None),
                'marital_status': profile_data.get('marital_status', None),
                'gender': profile_data.get('gender', None),
            }
            if any(value is not None for value in profile_filtered.values()):
                representation['profiles'] = profile_filtered
            else:
                del representation['profiles']
        return representation
    
class ApplySerializer(serializers.ModelSerializer):
    class_category = serializers.PrimaryKeyRelatedField(queryset=ClassCategory.objects.all(), required=False, many=True)
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), many=True, required=False)
    teacher_job_type = serializers.PrimaryKeyRelatedField(queryset=TeacherJobType.objects.all(), many=True, required=False)

    class Meta:
        model = Apply
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['class_category'] = ClassCategorySerializer(instance.class_category.all(), many=True).data if instance.class_category else None
        representation['subject'] = SubjectSerializer(instance.subject.all(), many=True).data
        representation['teacher_job_type'] = TeacherJobTypeSerializer(instance.teacher_job_type.all(), many=True).data
        return representation
