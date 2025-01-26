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

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'password' ,'Fname', 'Lname', 'email','is_verified']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = CustomUser.objects.create(
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
    
    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_recruiter = True
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
                is_recruiter=is_recruiter
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

    def create(self, validated_data):
        email = validated_data['email']
        base_username = email.split('@')[0]
        username = base_username
        Fname = validated_data['Fname']
        Lname = validated_data['Lname']
        is_teacher = True
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
                is_teacher=is_teacher
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
        fields = ['id', 'user', 'institution', 'role', 'start_date', 'end_date', 'achievements']

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
            representation['user'] = UserSerializer(instance.user).data
            representation['role'] = RoleSerializer(instance.role).data
        return representation

#subject serializer 
class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = ['id', 'subject_name']

    def validate_subject_name(self, value):
        if Subject.objects.filter(subject_name=value).exists():
            raise serializers.ValidationError("A subject with this name already exists.")
        return value

class ClassCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassCategory
        fields = ['id', 'name']

    def validate_name(self, value):
        if ClassCategory.objects.filter(name=value).exists():
            raise serializers.ValidationError("A classcategory with this name already exists.")
        return value

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
        fields = ['id', 'user', 'address_type', 'state', 'division', 'district', 'block', 'village', 'area', 'pincode']
    
    def validate_pincode(self, value):
        # Only validate if the pincode is not empty or null
        if value and (len(value) != 6 or not value.isdigit()):
            raise serializers.ValidationError("Pincode must be exactly 6 digits.")
        return value

# serializers.py
    # aadhar_no = serializers.CharField(max_length=12, required=False, allow_null=True)
    # fullname = serializers.CharField(max_length=20, required=False, allow_null=True)
    # phone = serializers.CharField(max_length=10, required=False, allow_null=True)
    # alternate_phone = serializers.CharField(max_length=10, required=False, allow_null=True)
    # date_of_birth = serializers.DateField(required=False, allow_null=True)

    # address = serializers.SerializerMethodField()
    # teacher_experience = serializers.SerializerMethodField()
    # teacherQualification = serializers.SerializerMethodField()
    # teacherSkill = serializers.SerializerMethodField()

    # class Meta:
    #     model = Teacher
    #     fields = [
    #         'id', 'user', 'fullname', 'gender', 'religion', 'nationality',
    #         'aadhar_no', 'phone', 'alternate_phone', 'verified',
    #         'class_categories', 'rating', 'date_of_birth',
    #         'availability_status', 'address', 'teacher_experience', 'teacherQualification', 'teacherSkill'
    #     ]

    # def validate_fullname(self, value):
    #     if value is not None:
    #         value = value.strip()
    #         if len(value) < 3:
    #             raise serializers.ValidationError("Full name must be at least 3 characters.")
    #     return value

    # def validate_phone(self, value):
    #     return self.validate_phone_number(value)

    # def validate_alternate_phone(self, value):
    #     return self.validate_phone_number(value)

    # def validate_phone_number(self, value):
    #     if value:
    #         cleaned_value = re.sub(r'[^0-9]', '', value)
    #         if len(cleaned_value) != 10:
    #             raise serializers.ValidationError("Phone number must be exactly 10 digits.")
    #         # if Teacher.objects.filter(phone=value).exists():
    #         #     raise serializers.ValidationError("This Phone no. is alreary exist.")
    #         if not cleaned_value.startswith(('6', '7', '8', '9')):
    #             raise serializers.ValidationError("Phone number must start with 6, 7, 8, or 9.")
    #         return cleaned_value
    #     return value

    # def validate_aadhar_no(self, value):
    #     if value:
    #         if not re.match(r'^\d{12}$', value):
    #             raise serializers.ValidationError("Aadhar number must be exactly 12 digits.")
    #         # if Teacher.objects.filter(aadhar_no=value).exists():
    #         #     raise serializers.ValidationError("This Aadhar no. is alreary exist.")
    #     return value
    
    # # def validate(self, data):
    # #     user = data.get('user')
    # #     if user and Teacher.objects.filter(user=user).exists():
    # #         raise serializers.ValidationError({"user": "A teacher entry for this user already exists."})
    # #     return data 

    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['user'] = UserSerializer(instance.user).data
    #     return representation

    # def get_address(self, obj):
    #     addresses = TeachersAddress.objects.filter(user=obj.user)
    #     return TeachersAddressSerializer(addresses, many=True).data

    # def get_teacher_experience(self, obj):
    #     teacher_experiences = TeacherExperiences.objects.filter(user=obj.user)
    #     return TeacherExperiencesSerializer(teacher_experiences, many=True).data

    # def get_teacherQualification(self, obj):
    #     teacherQualifications = TeacherQualification.objects.filter(user=obj.user)
    #     return TeacherQualificationSerializer(teacherQualifications, many=True).data

    # def get_teacherSkill(self, obj):
    #     teacherSkills = TeacherSkill.objects.filter(user=obj.user)
    #     return TeacherSkillSerializer(teacherSkills, many=True).data

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
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), required=True)
    level = serializers.PrimaryKeyRelatedField(queryset=Level.objects.all(), required=True)
    class_category = serializers.PrimaryKeyRelatedField(queryset=ClassCategory.objects.all(), required=False)

    class Meta:
        model = Exam
        fields = ['id', 'name', 'description', 'subject', 'level', 'class_category', 'total_marks', 'duration', 'questions','type']
        depth = 1 
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['subject'] = SubjectSerializer(instance.subject).data
        representation['level'] = LevelSerializer(instance.level).data
        representation['class_category'] = ClassCategorySerializer(instance.class_category).data
        representation['questions'] = QuestionSerializer(instance.questions.all(), many=True).data

        return representation
class TeacherSkillSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    skill = serializers.PrimaryKeyRelatedField(queryset=Skill.objects.all(), required=False)
    class Meta:
        model = TeacherSkill
        fields = ['id', 'user', 'skill']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['skill'] = SkillSerializer(instance.skill).data
        return representation
 
    def validate(self, attrs):
        user = attrs.get('user')
        skill = attrs.get('skill')
        # This user have skill already exists
        if TeacherSkill.objects.filter(user=user, skill=skill).exists():
            raise serializers.ValidationError('This user already has this skill.')
        return attrs

class EducationalQualificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalQualification
        fields = ['id', 'name']

class TeacherQualificationSerializer(serializers.ModelSerializer):
    # This will allow you to include the user and qualification in the serialized data
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    qualification = serializers.SlugRelatedField(queryset=EducationalQualification.objects.all(), slug_field="name", required=False)
    
    class Meta:
        model = TeacherQualification
        fields = ['id', 'user', 'qualification', 'institution', 'year_of_passing', 'grade_or_percentage']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        
        representation['user'] = UserSerializer(instance.user).data
        representation['qualification'] = EducationalQualificationSerializer(instance.qualification).data
        
        return representation

    def validate_year_of_passing(self, value):
        current_year = datetime.now().year
        if value > current_year:
            raise serializers.ValidationError("Year of passing cannot be in the future.")
        return value

    def validate(self, data):
        user = data.get('user')
        if user:
            previous_qualification = TeacherQualification.objects.filter(user=user).order_by('-year_of_passing').first()
            if previous_qualification:
                if data.get('year_of_passing') <= previous_qualification.year_of_passing:
                    raise serializers.ValidationError(
                        "Year of passing should be greater than the previous qualification's year."
                    )
        return data
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id','jobrole_name']

    def validate_jobrole_name(self, value):
        # Validate if the name has at least 3 characters
        if len(value) < 3:
            raise serializers.ValidationError("Role name must be at least 3 characters.")
        
        if Role.objects.filter(jobrole_name=value).exists():
            raise serializers.ValidationError("A Role with this name already exists.")
        return value

class PreferenceSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    job_role = serializers.PrimaryKeyRelatedField(queryset=Role.objects.all(), many=True)
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
        fields = '__all__'
     
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

    class Meta:
        model = TeacherExamResult
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        representation['exam'] = ExamSerializer(instance.exam).data
        return representation

class JobPreferenceLocationSerializer(serializers.ModelSerializer):
    preference = serializers.PrimaryKeyRelatedField(queryset=Preference.objects.all(), required=False)
    class Meta:
        model = JobPreferenceLocation
        fields = '__all__'
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['preference'] = PreferenceSerializer(instance.preference).data
        return representation
    
    def validate_area(self, value):
        if JobPreferenceLocation.objects.filter(area=value, preference=self.initial_data.get('preference')).exists():
            raise serializers.ValidationError(" this area name already exists")
        
        preference_id = self.initial_data.get('preference')
        if preference_id:
            area_count = JobPreferenceLocation.objects.filter(preference=preference_id).count()
            if area_count >= 5:
                raise serializers.ValidationError("You can only add up to 5 areas for a single preference.")
        return value

class BasicProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    bio = models.CharField(max_length=100, blank=True, null=True)    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    religion = models.CharField(max_length=15, blank=True, null=True)
    class Meta:
        model = BasicProfile
        fields = ['id', 'user', 'bio', 'phone_number', 'religion','profile_picture','date_of_birth','marital_status','gender','language']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['user'] = UserSerializer(instance.user).data
        return representation

    def validate_mobile(self, value):
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
    class Meta:
        model = CustomUser
        fields = ['id', 'last_login', 'is_superuser', 'email', 'username',
            'Fname', 'Lname', 'is_staff', 'is_active', 'is_recruiter',
            'is_teacher', 'groups', 'user_permissions']
        read_only_fields = ['email', 'username'] 

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
    teachersaddress = TeachersAddressSerializer(many=True,required=False)
    teacherexperiences = TeacherExperiencesSerializer(many=True,required=False)
    teacherqualifications = TeacherQualificationSerializer(many=True,required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'Fname', 'Lname', 'email', 'profiles', 'teacherskill', 'teachersaddress', 'teacherexperiences','teacherqualifications']
    
class ExamCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamCenter
        fields = "__all__"


class TeacherReportSerializer(serializers.ModelSerializer):
    teacherskill = TeacherSkillSerializer(many=True, required=False)
    teacherqualifications = TeacherQualificationSerializer(many=True, required=False)
    teacherexperiences = TeacherExperiencesSerializer(many=True, required=False)
    teacherexamresult = TeacherExamResultSerializer(many=True, required=False)
    preference = PreferenceSerializer(many=True, required=False)  

    class Meta:
        model = CustomUser
        fields = ['id', 'Fname', 'Lname', 'email', 'teacherskill', 'teacherqualifications', 'teacherexperiences', 'teacherexamresult', 'preference']


        