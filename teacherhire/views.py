from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from teacherhire.models import *
from rest_framework.exceptions import NotFound
from teacherhire.serializers import *
from teacherhire.utils import calculate_profile_completed, send_otp_via_email, verified_msg
from .authentication import ExpiringTokenAuthentication
from rest_framework.decorators import action
from .permissions import IsRecruiterPermission, IsAdminPermission
import uuid
import random
from django.core.mail import send_mail
import re
from django.utils import timezone
from datetime import date, timedelta
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import JsonResponse
from django.db.models import F
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
import random
from django.utils.html import format_html
from django.core.cache import cache
import requests
import logging
from django.contrib.auth.forms import SetPasswordForm
from django.conf import settings
from fuzzywuzzy import process, fuzz
from django.db.models import Q
import re
from datetime import date
from django.db.models import Count
from django.contrib.auth.hashers import make_password
class RecruiterView(APIView):
    permission_classes = [IsRecruiterPermission]

    def get(self, request):
        return Response({"message": "You are a recruiter!"}, status=status.HTTP_200_OK)
class AdminView(APIView):
    permission_classes = [IsAdminPermission]

    def get(self, request):
        return Response({"message": "You are an admin!"}, status=status.HTTP_200_OK)

def check_for_duplicate(model_class, **kwargs):
    return model_class.objects.filter(**kwargs).exists()

def create_object(serializer_class, request_data, model_class):
    serializer = serializer_class(data=request_data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# for authenticated teacher
def create_auth_data(serializer_class, request_data, model_class, user, *args, **kwargs):
    if not user or not user.is_authenticated:
        return Response(
            {'message': 'Authentication required to perform this action.'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    serializer = serializer_class(data=request_data)
    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def update_auth_data(serialiazer_class, instance, request_data, user):
    serializer = serialiazer_class(instance, data=request_data, partial=False)
    if serializer.is_valid():
        serializer.save(user=user)
        return Response({"detail": "Data updated successfully.", "data": serializer.data}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def get_single_object(viewset):
    queryset = viewset.get_queryset()
    profile = queryset.first()
    serializer = viewset.get_serializer(profile)
    return Response(serializer.data)

def get_count(model_class):
    return model_class.objects.count()

class RecruiterRegisterUser(APIView):
    def post(self, request):
        serializer = RecruiterRegisterSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({
                'error': serializer.errors,
                # Todo
                'message': 'Something went wrong'
            }, status=status.HTTP_409_CONFLICT)

        serializer.save()
        email = serializer.data['email']
        send_otp_via_email(email)
        # request.session['email'] = email
        user = CustomUser.objects.get(email=email)

        return Response({
            'payload': serializer.data,
            'message': 'Your data is saved. Please check your email and verify your account first.'
        }, status=status.HTTP_200_OK)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            # Set the new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Password updated successfully!"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class TeacherRegisterUser(APIView):
    def post(self, request):
        serializer = TeacherRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': serializer.errors,
                # Todo
                'message': 'Something went wrong'
            }, status=status.HTTP_409_CONFLICT)
        serializer.save()
        send_otp_via_email(serializer.data['email'])
        email = serializer.data['email']
        user = CustomUser.objects.get(email=email)

        return Response({
            'payload': serializer.data,
            'message': 'Your data is saved. Please check your email and verify your account first.'
        }, status=status.HTTP_200_OK)
    
def generate_refresh_token():
    return str(uuid.uuid4())
class LoginUser(APIView):
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_verified:
            return Response({'message': 'Account is not verified. Please verify your account before logging in.'}, status=status.HTTP_403_FORBIDDEN)
        # Check password validity
        if user.check_password(password):
            # Delete old token if it exists
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)

            refresh_token = generate_refresh_token()

            is_admin = user.is_staff
            roles = {
                'is_admin': user.is_staff,
                'is_recruiter': user.is_recruiter,
                'is_user': not (user.is_staff and user.is_recruiter)
            }
            if user.is_staff:
                role = 'admin'
            elif user.is_recruiter:
                role = 'recruiter'
            else:
                role = 'user'
            return Response({
                'access_token': token.key,
                'refresh_token': refresh_token,
                'Fname': user.Fname,
                'email': user.email,
                'role': role,                
                # 'refresh_expires_at': refresh_expires_at,  
                'message': 'Login successful'
            }, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

class LogoutUser(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({"success": "Logout succesJobsful"}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

# TeacerAddress GET ,CREATE ,DELETE
class TeachersAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeachersAddressSerializer
    queryset = TeachersAddress.objects.all().select_related('user')

    # def create(self, request, *args, **kwargs):
    #     print(f"User: {request.user}")
    #     return create_auth_data(self, TeachersAddressSerializer, request.data, TeachersAddress)

    @action(detail=False, methods=['get'])
    def count(self, request):
        print(f"User: {request.user}")
        count = get_count(TeachersAddress)
        return Response({"count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "TeacherAddress deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SingleTeachersAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeachersAddressSerializer
    queryset = TeachersAddress.objects.all().select_related('user')

    def create(self, request, *args, **kwargs):
        print("Request data:", request.data)
        data = request.data.copy()
        address_type = data.get('address_type')

        # Validate the `address_type`
        if not address_type or address_type not in ['current', 'permanent']:
            return Response(
                {"detail": "Invalid or missing 'address_type'. Expected 'current' or 'permanent'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the address already exists for the user
        if TeachersAddress.objects.filter(address_type=address_type, user=request.user).exists():
            return Response(
                {"detail": f"{address_type.capitalize()} address already exists for this user."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Associate the address with the authenticated user
        data['user'] = request.user.id

        # Serialize and validate data
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        address_type = data.get('address_type')  # Get the address type from the request data

        # Ensure address_type is provided and is valid
        if not address_type or address_type not in ['current', 'permanent']:
            return Response(
                {"detail": "Invalid or missing 'address_type'. Expected 'current' or 'permanent'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try to find the address of the given address type for the authenticated user
        address = TeachersAddress.objects.filter(user=request.user, address_type=address_type).first()

        if address:
            # If the address exists, proceed to update it
            return self.update_address_data(
                serializer_class=self.get_serializer_class(),
                instance=address,
                request_data=data,
                user=request.user
            )
        else:
            # If no address of the specified type exists, return a 404 response
            return Response(
                {"detail": f"{address_type.capitalize()} address not found for the user."},
                status=status.HTTP_404_NOT_FOUND
            )

    def update_address_data(self, serializer_class, instance, request_data, user):
        serializer = serializer_class(instance, data=request_data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return TeachersAddress.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        current_address = self.get_queryset().filter(address_type='current').first()
        permanent_address = self.get_queryset().filter(address_type='permanent').first()

        current_address_data = self.get_serializer(current_address).data if current_address else None
        permanent_address_data = self.get_serializer(permanent_address).data if permanent_address else None

        data = {
            "current_address": current_address_data,
            "permanent_address": permanent_address_data
        }
        return Response(data, status=status.HTTP_200_OK)

    # def get_object(self):
    #  try:
    #     return TeachersAddress.objects.get(user=self.request.user)
    #  except TeachersAddress.DoesNotExist:
    #     return Response({"detail": "This address not found."}, status=status.HTTP_404_NOT_FOUND)

class EducationalQulificationViewSet(viewsets.ModelViewSet):   
    permission_classes = [IsAuthenticated]    
    authentication_classes = [ExpiringTokenAuthentication] 
    serializer_class = EducationalQualificationSerializer 
    queryset = EducationalQualification.objects.all()

    def create(self, request):
        return create_object(EducationalQualificationSerializer, request.data, EducationalQualification)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(EducationalQualification)
        return Response({"count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Educationqulification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class LevelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Level.objects.all()
    serializer_class = LevelSerializer

    @action(detail=False, methods=['get'])
    def count(self):
        count = get_count(Level)
        return Response({"Count": count})

    @action(detail=True, methods=['get'],
            url_path=r'classes/(?P<class_category_id>[^/.]+)/?subject/(?P<subject_id>[^/.]+)/?questions')
    def level_questions(self, request, pk=None, subject_id=None, class_category_id=None):
        """
        Custom action to fetch questions by level, optional subject, optional class category, and optional language.
        """
        # Get the level by pk
        try:
            level = Level.objects.get(pk=pk)
        except Level.DoesNotExist:
            return Response({"error": "Level not found"}, status=status.HTTP_404_NOT_FOUND)
        # Start with filtering by level
        questions = Question.objects.filter(level=level)
        # Filter by subject if provided
        if subject_id:
            try:
                subject = Subject.objects.get(pk=subject_id)
            except Subject.DoesNotExist:
                return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
            questions = questions.filter(subject=subject)
        # Filter by class category if provided
        if class_category_id:
            try:
                class_category = ClassCategory.objects.get(pk=class_category_id)
            except ClassCategory.DoesNotExist:
                return Response({"error": "Class Category not found"}, status=status.HTTP_404_NOT_FOUND)
            questions = questions.filter(classCategory=class_category)

        language = request.query_params.get('language', None)
        if language:
            if language not in ['Hindi', 'English']:
                return Response({"error": "Invalid language, please choose 'Hindi' or 'English'."}, status=status.HTTP_400_BAD_REQUEST)
            questions = questions.filter(language=language)

        # Serialize the filtered questions
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Level deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset = Skill.objects.all()    
    serializer_class = SkillSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Skill)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Skill deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class TeacherSkillViewSet(viewsets.ModelViewSet):
    queryset = TeacherSkill.objects.all()
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSkillSerializer

    def create(self, request):
        return create_object(TeacherSkillSerializer, request.data, TeacherSkill)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(TeacherSkill)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "TeacherSkill deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SingleTeacherSkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSkillSerializer
    lookup_field = 'id'

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        return create_auth_data(
            serializer_class=self.get_serializer_class(),
            request_data=data,
            user=request.user,
            model_class=TeacherSkill)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        skill_id = kwargs.get('id')
        user = request.user.id

        try:
            skill = TeacherSkill.objects.get(id=skill_id, user=user)
        except TeacherSkill.DoesNotExist:
            return Response(
                {"error": "Skill not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if skill:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=skill,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeacherSkill
            )

    def get_queryset(self):
        return TeacherSkill.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacherqualification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    # def list(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)

    # def get_object(self):
    #     skill_id = self.kwargs.get('id')
    #     try:
    #         return TeacherSkill.objects.get(id=skill_id, user=self.request.user)
    #     except TeacherSkill.DoesNotExist:
    #         raise Response({"detail": "this user skill not found."}, status=status.HTTP_404_NOT_FOUND)

class SubjectViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated] 
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Subject)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "subject deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SelfViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        user = self.request.user
        queryset =  CustomUser.objects.filter(id=user.id,is_teacher=True)    
        return queryset

def get_pincodes_by_post_office(post_office_name):
    cache_key = f"post_office_{post_office_name.lower()}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data

    url = f"https://api.postalpincode.in/postoffice/{post_office_name}"

    try:
        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        if data and isinstance(data, list) and data[0].get('Status') == 'Success':
            post_offices = data[0].get('PostOffice', [])
            pincodes = [post_office['Pincode'] for post_office in post_offices]
            cache.set(cache_key, pincodes, timeout=60 * 60 * 24)
            return pincodes

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching pincode data for post office {post_office_name}: {e}")

    return []

class RecruiterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = CustomUser.objects.filter(is_recruiter=True)
    serializer_class = RecruiterSerializer

class TeacherViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer    
    
    def get_queryset(self):
        return_all = self.request.query_params.get('all', None)
        if return_all and return_all.lower() == 'true':
            queryset = CustomUser.objects.filter(is_teacher=True)
        else:
            queryset = CustomUser.objects.filter(is_teacher=True)
        
        teacher_name = self.request.query_params.getlist('name[]', [])
        if teacher_name:
            teacher_name = [name.strip().lower() for name in teacher_name]
            name_query = Q()
            for name in teacher_name:
                name_parts = name.split()
                if len(name_parts) >= 2:
                    fname = name_parts[0]
                    lname = name_parts[-1]
                    name_query |= Q(Fname__icontains=fname) & Q(Lname__icontains=lname)
                elif len(name_parts) == 1:
                    fname = name_parts[0]
                    name_query |= Q(Fname__icontains=fname) | Q(Lname__icontains=fname)
            queryset = queryset.filter(name_query)


        queryset = queryset.prefetch_related('preferences')        
      
        teacher_skills = self.request.query_params.getlist('skill[]', [])
        if teacher_skills:
            teacher_skills = [skill.strip().lower() for skill in teacher_skills]
            skill_query = Q()
            for skill in teacher_skills:
                skill_query |= Q(teacherskill__skill__name__iexact=skill)
            queryset = queryset.filter(skill_query)

        teacher_qualifications = self.request.query_params.getlist('qualification[]', [])
        if teacher_qualifications:
            teacher_qualifications = [qualification.strip().lower() for qualification in teacher_qualifications]
            qualification_query = Q()
            for qualification in teacher_qualifications:
                qualification_query |= Q(teacherqualifications__qualification__name__iexact=qualification)
            queryset = queryset.filter(qualification_query)


        filters = {
        'state': self.request.query_params.get('state[]', []),
        'district': self.request.query_params.getlist('district[]', []),
        'division': self.request.query_params.get('division', []),
        'pincode': self.request.query_params.getlist('pincode[]', []),
        'block': self.request.query_params.getlist('block[]', []),
        'village': self.request.query_params.getlist('village[]', []),
        'experience': self.request.query_params.get('experience', None),
        'class_category': self.request.query_params.getlist('class_category[]', []),
        'subject': self.request.query_params.getlist('subject[]', []),
        'job_role': self.request.query_params.getlist('job_role[]', []),
        'teacher_job_type': self.request.query_params.getlist('teacher_job_type[]', []),
        'postOffice': self.request.query_params.get('postOffice', None),

        }

        post_office_filter = filters.get('postOffice', None)
        if post_office_filter:
            pincodes = get_pincodes_by_post_office(post_office_filter)
            if pincodes:
                filters['pincode'] = pincodes
        print(post_office_filter)

        experience_filter = self.get_experience_filter(filters['experience'])
        if experience_filter:
            queryset = queryset.filter(experience_filter)       

        for field in ['state', 'district', 'division', 'block', 'village']:
            queryset = self.filter_by_address_field(queryset, field, filters.get(field))

        job_role_filter = filters['job_role']
        if job_role_filter:
            job_roles = [role.strip().lower() for role in job_role_filter]
            job_role_query = Q()
            for role in job_roles:
                job_role_query |= Q(preferences__job_role__jobrole_name__iexact=role)
            queryset = queryset.filter(job_role_query)
        
        class_category_filter = filters['class_category']
        if class_category_filter:
            class_categories = [class_category.strip().lower() for class_category in class_category_filter]
            class_category_query = Q()
            for class_category in class_categories:
                class_category_query |= Q(preferences__class_category__name__iexact=class_category)
            queryset = queryset.filter(class_category_query)

        subject_filter = filters['subject']
        if subject_filter:
            prefer_subjects = [subject.strip().lower() for subject in subject_filter]
            subject_query = Q()
            for subject in prefer_subjects:
                subject_query |= Q(preferences__prefered_subject__subject_name__iexact=subject)
            queryset = queryset.filter(subject_query)
        
        teacher_job_type = filters['teacher_job_type']
        if teacher_job_type:
            teacher_job_types = [teacher_job_type.strip().lower() for teacher_job_type in teacher_job_type]
            teacher_job_type_query = Q()
            for teacher_job_type in teacher_job_types:
                teacher_job_type_query |= Q(preferences__teacher_job_type__teacher_job_name__iexact=teacher_job_type)
            queryset = queryset.filter(teacher_job_type_query)
        

        if filters['pincode']:
            pincodes = filters['pincode']
            queryset = queryset.filter(teachersaddress__pincode__in=pincodes)
        queryset = queryset.distinct()
        return queryset
    
    def filter_by_address_field(self, queryset, field, filter_value):
        if filter_value:
            q_objects = Q()  
            for value in filter_value:
                value = value.strip()
                best_match = process.extractOne(value.lower(), queryset.values_list(f'teachersaddress__{field}', flat=True))
                
                if best_match and best_match[1] >= 70:
                    q_objects |= Q(**{f'teachersaddress__{field}__iexact': best_match[0]})
                else:
                    q_objects |= Q(**{f'teachersaddress__{field}__icontains': value})

            queryset = queryset.filter(q_objects)

        return queryset

    def fuzzy_filter(self, queryset, field_name, filter_value, threshold=80):
        """
        Perform fuzzy matching using fuzzywuzzy on the field and filter value.
        """
        if not filter_value:
            return queryset
        filter_value = filter_value.strip().lower()
        all_values = queryset.values_list(field_name, flat=True).distinct()
        
        best_match = process.extractOne(filter_value, all_values, scorer=fuzz.ratio)
        
        if best_match and best_match[1] >= threshold:
            return queryset.filter(**{f"{field_name}__iexact": best_match[0]})
        else:
            # If no sufficiently close match is found, return an empty queryset or raise an exception.
            raise NotFound(detail=f"No records found for '{filter_value}'. Please check your spelling.")
        
    def get_experience_filter(self, experience_str):
        if experience_str:
            match = re.match(r'(\d+)\s*(year|yr|y|years?)', experience_str.strip().lower())
            if match:
                years = int(match.group(1))
                start_date_threshold = date.today().replace(year=date.today().year - years)
                end_date_threshold = start_date_threshold.replace(year=start_date_threshold.year + 1)

                return Q(teacherexperiences__start_date__gte=start_date_threshold) & Q(
                    teacherexperiences__start_date__lt=end_date_threshold)
        return None   
    


class ClassCategoryViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset= ClassCategory.objects.all()
    serializer_class = ClassCategorySerializer

    def create(self, request):
        return create_object(ClassCategorySerializer, request.data, ClassCategory)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(ClassCategory)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "ClassCategory deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class ReasonViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset= Reason.objects.all()
    serializer_class = ReasonSerializer

    def create(self, request):
        return create_object(ReasonSerializer, request.data, Reason)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Reason)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Reason deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class TeacherQualificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherQualification.objects.all()
    serializer_class = TeacherQualificationSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(TeacherQualification)
        return Response({"count": count})

    def create(self, request, *args, **kwargs):
        return create_object(TeacherQualificationSerializer, request.data, TeacherQualification)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacherqualification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class SingleTeacherQualificationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherQualification.objects.all()
    serializer_class = TeacherQualificationSerializer
    lookup_field = 'id'

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        qualification_id = kwargs.get('id')
        user = request.user.id

        try:
            qualification = TeacherQualification.objects.get(id=qualification_id, user=user)
        except TeacherQualification.DoesNotExist:
            return Response(
                {"error": "Qualification not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        if qualification:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=qualification,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeacherQualification
            )
    def create(self, request):
        data = request.data.copy()
        qualification = data.get('qualification')  # Slug value of the qualification
        year_of_passing = int(data.get('year_of_passing')) if data.get('year_of_passing') else None

        if not qualification or not year_of_passing:
            return Response(
                {"error": "Qualification and year_of_passing are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not EducationalQualification.objects.filter(name=qualification).exists():
            return Response(
                {"error": f"Qualification '{qualification}' does not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if TeacherQualification.objects.filter(
                user=request.user,
                qualification__name=qualification,
                year_of_passing=year_of_passing
        ).exists():
            return Response(
                {
                    "error": f"A record with qualification '{qualification}' and year of passing '{year_of_passing}' already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_qua = TeacherQualification.objects.filter(user=request.user)

        if qualification == "inter":
            matric = user_qua.filter(qualification__name="matric").first()
            if matric and (year_of_passing - matric.year_of_passing < 2):
                return Response(
                    {"error": "There must be at least a 2-year gap between matric and inter."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        if qualification == "graduation":
            inter_record = user_qua.filter(qualification__name="inter").first()
            if inter_record and (year_of_passing - inter_record.year_of_passing < 3):
                return Response(
                    {"error": "There must be at least a 3-year gap between inter and graduation."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return create_auth_data(
            serializer_class=self.get_serializer_class(),
            request_data=data,
            user=request.user,
            model_class=TeacherQualification
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacherqualification deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def suggest_institutes(self, request):
        query = request.query_params.get('q','').strip()
        if not query:
            return Response({"error":"Please enter a search term."}, status=status.HTTP_400_BAD_REQUEST)
        suggestions = TeacherQualification.objects.filter(institution__icontains=query).values_list('institution',flat=True).distinct()
        return Response({"suggestions": list(suggestions)}, status=status.HTTP_200_OK)


    def get_queryset(self):
        return TeacherQualification.objects.filter(user=self.request.user)
class TeacherExperiencesViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherExperiences.objects.all()
    serializer_class = TeacherExperiencesSerializer

    def create(self, request, *args, **kwargs):
        return create_object(TeacherExperiencesSerializer, request.data, TeacherExperiences)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(TeacherExperiences)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacherexperience deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SingleTeacherExperiencesViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherExperiences.objects.all()
    serializer_class = TeacherExperiencesSerializer
    lookup_field = 'id'

    def create(self, request):
        data = request.data.copy()
        institution = data.get('institution')
        role = data.get('role')
        if TeacherExperiences.objects.filter(user=request.user, institution=institution, role=role).exists():
            return Response(
                {"error": "Experience with the same institution and role already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return create_auth_data(
            serializer_class=self.get_serializer_class(),
            request_data=data,
            user=request.user,
            model_class=TeacherExperiences
        )
           
    @action(detail=False, methods=['get'])
    def suggest_institutes(self, request):
        query = request.query_params.get('q','').strip()
        if not query:
            return Response({"error":"Please enter a search term."}, status=status.HTTP_400_BAD_REQUEST)
        suggestions = TeacherExperiences.objects.filter(institution__icontains=query).values_list('institution',flat=True).distinct()
        return Response({"suggestions": list(suggestions)}, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        experienced_id = kwargs.get('id')
        user = request.user.id
        try:
            teacher_experienced = TeacherExperiences.objects.get(id=experienced_id, user=user)
        except TeacherExperiences.DoesNotExist:
            return Response({"error": "Experience not found"}, status=status.HTTP_404_NOT_FOUND)

        if teacher_experienced:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=teacher_experienced,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeacherExperiences
            )
    def get_queryset(self):
        return TeacherExperiences.objects.filter(user=self.request.user)

class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def create(self, request):
        return create_object(QuestionSerializer, request.data, Question)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Question)
        return Response({"Count": count})

    @action(detail=False, methods=['get'])
    def questions(self, request):
        user = request.user
        exam_id = request.query_params.get('exam_id')
        language = request.query_params.get('language')

        questions = Question.objects.all()

        if exam_id:
            try:
                exam = Exam.objects.get(pk=exam_id)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

            questions = questions.filter(exam=exam)

        if language:
            questions = questions.filter(language=language)

        serialized_questions = QuestionSerializer(questions, many=True)
        return Response(serialized_questions.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Question deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SelfQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = Question.objects.filter(user=request.user).count()
        return Response({"count": count})

    @action(detail=False, methods=['get'])
    def questions(self, request):
        user = request.user
        exam_id = request.query_params.get('exam_id')
        language = request.query_params.get('language')

        questions = Question.objects.all()

        if not exam_id:
            return Response(
                {"error": "Exam ID is required."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        questions = Question.objects.filter(exam=exam)

        if language:
            if language not in ['Hindi', 'English']:
                return Response({"error": "Invalid language."}, status=status.HTTP_400_BAD_REQUEST)
            questions = questions.filter(language=language)

        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class RoleViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset= Role.objects.all()
    serializer_class = RoleSerializer

    def create(self, request):
        return create_object(RoleSerializer, request.data, Role)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Role)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Role deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
class PreferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        if Preference.objects.filter(user=request.user).exists():
            return Response({"detail": "Preference already exists."}, status=status.HTTP_400_BAD_REQUEST)

        if 'teacher_job_type' in data and isinstance(data['teacher_job_type'], str):
            data['teacher_job_type'] = [data['teacher_job_type']]

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():

            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        # Check if the user has an existing preference
        profile = Preference.objects.filter(user=request.user).first()

        change_in_str = ['teacher_job_type', 'prefered_subject', 'job_role', 'class_category']
        for key in change_in_str:
            if key in data and isinstance(data[key], str):
                data[key] = [data[key]]
                
        if profile:
            return self.update_auth_data(
                serializer_class=self.get_serializer_class(),
                instance=profile,
                request_data=data,
                user=request.user
            )
        else:
            return self.create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=Preference
            )
    def get_queryset(self):
        return Preference.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        # Retrieve the preference object for the current user
        try:
            return Preference.objects.get(user=self.request.user)
        except Preference.DoesNotExist:
            raise NotFound({"detail": "Preference not found."}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Prefrence deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def update_auth_data(self, serializer_class, instance, request_data, user):
        """Handle updating preference data."""
        serializer = serializer_class(instance, data=request_data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def create_auth_data(self, serializer_class, request_data, user, model_class):
        """Handle creating preference data."""
        serializer = serializer_class(data=request_data)
        if serializer.is_valid():
            serializer.save(user=user)  # Assign the user to the new preference object
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TeacherSubjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherSubject.objects.all()
    serializer_class = TeacherSubjectSerializer

    def create(self, request):
        return create_object(TeacherSubjectSerializer, request.data, TeacherSubject)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(TeacherSubject)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teachersubject deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
class SingleTeacherSubjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherSubject.objects.all()
    serializer_class = TeacherSubjectSerializer

    def get_queryset(self):
        return TeacherSubject.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get_object(self):
        try:
            return TeacherSubject.objects.get(user=self.request.user)
        except TeacherSubject.DoesNotExist:
            raise NotFound({"detail": "TeacherSubject not found."})

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        SingleTeacherSubject = TeacherSubject.objects.filter(user=request.user).first()

        if SingleTeacherSubject:
            return update_auth_data(
                serializer_class=self.get_serializer_class(),
                instance=SingleTeacherSubject,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeacherSubject
            )

    def delete(self, request, *args, **kwargs):
        try:
            profile = TeacherSubject.objects.get(user=request.user)
            profile.delete()
            return Response({"detail": "TeacherSubject deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except TeacherSubject.DoesNotExist:
            return Response({"detail": "TeacherSubject not found."}, status=status.HTTP_404_NOT_FOUND)
class TeacherClassCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherClassCategory.objects.all()
    serializer_class = TeacherClassCategorySerializer

    def create(self, request):
        return create_object(TeacherClassCategorySerializer, request.data, TeacherClassCategory)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(TeacherClassCategory)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacherclasscategory deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SingleTeacherClassCategory(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherClassCategory.objects.all()
    serializer_class = TeacherClassCategorySerializer

    def get_queryset(self):
        return TeacherClassCategory.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id
        if TeacherClassCategory.objects.filter(user=request.user).exists():
            return Response({"detail": "SingleTeacher class category already exists. "},
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_object(self):
        try:
            return TeacherClassCategory.objects.get(user=self.request.user)
        except TeacherClassCategory.DoesNotExist:
            raise NotFound({"detail": "TeacherClassCategory not found."})

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        SingleTeacherClassCategory = TeacherClassCategory.objects.filter(user=request.user).first()

        if SingleTeacherClassCategory:
            return update_auth_data(
                serializer_class=self.get_serializer_class(),
                instance=SingleTeacherClassCategory,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeacherClassCategory
            )

    def delete(self, request, *args, **kwargs):
        try:
            profile = TeacherClassCategory.objects.get(user=request.user)
            profile.delete()
            return Response({"detail": "TeacherClassCategory deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except TeacherClassCategory.DoesNotExist:
            return Response({"detail": "TeacherClassCategory not found."}, status=status.HTTP_404_NOT_FOUND)
class TeacherExamResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherExamResult.objects.all()
    serializer_class = TeacherExamResultSerializer

    def create(self, request, *args, **kwargs):
        # Add the authenticated user to the request data
        data = request.data.copy()
        data['user'] = request.user.id  # Set user to the currently authenticated user

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def count(self, request):
        user = request.user

        if not user.is_authenticated:
            return Response({"detail": "Authentication credentials were not provided."}, status=401)

        preferred_subjects = Subject.objects.filter(preference__user=user).distinct()
        preferred_class_categories = ClassCategory.objects.filter(preference__user=user).distinct()

        response_data = {}
        for class_category in preferred_class_categories:
            response_data[class_category.name] = {}
            for subject in preferred_subjects:
                level1_count = TeacherExamResult.objects.filter(
                    user=user,
                    exam__subject=subject,
                    exam__class_category=class_category,
                    exam__level_id=1
                ).count()

                level2_count = TeacherExamResult.objects.filter(
                    user=user,
                    exam__subject=subject,
                    exam__class_category=class_category,
                    exam__level_id=2

                ).count()

                response_data[class_category.name][subject.subject_name] = {
                    "level1": level1_count,
                    "level2": level2_count
                }
        for class_category in preferred_class_categories:
            if class_category.name not in response_data:
                response_data[class_category.name] = {}
        for subject in preferred_subjects:
            if subject.subject_name not in response_data[class_category.name]:
                response_data[class_category.name][subject.subject_name] = {
                    "level1": 0,
                    "level2": 0
                }

        return Response(response_data)

class JobPreferenceLocationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = JobPreferenceLocation.objects.all()
    serializer_class = JobPreferenceLocationSerializer
    lookup_field = 'id'

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        preference = user.preference_set.first()

        if not preference:
            return Response({"error": "No preference found for the user."}, status=status.HTTP_400_BAD_REQUEST)

        data["preference"] = preference.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        return JobPreferenceLocation.objects.filter(preference__user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Job preference location deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user

        user_preference = user.preference_set.first()

        if not user_preference:
            return Response({"error": "Create a preference first."}, status=status.HTTP_400_BAD_REQUEST)

        jobPreferenceLocation = self.get_object()

        if jobPreferenceLocation.preference.id != user_preference.id:
            return Response({"error": "You can only update locations linked to your preference."},
                            status=status.HTTP_403_FORBIDDEN)

        data['preference'] = user_preference.id

        serializer = self.get_serializer(instance=jobPreferenceLocation, data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_200_OK)

class BasicProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = BasicProfile.objects.all()
    serializer_class = BasicProfileSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        if BasicProfile.objects.filter(user=request.user).exists():
            return Response({"detail": "Profile already exists."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        profile = BasicProfile.objects.filter(user=request.user).first()

        if profile:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=profile,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=BasicProfile
            )

    def get_queryset(self):
        return BasicProfile.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        """
        Fetch the BasicProfile object for the logged-in user. 
        If it doesn't exist, create one or return an appropriate response.
        """
        profile = BasicProfile.objects.filter(user=self.request.user).first()
        if profile:
            return profile
        else:
            # Option 1: Automatically create a profile for the user
            data = {"user": self.request.user.id}
            serializer = self.get_serializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return serializer.instance  # Return the newly created profile
            # Option 2: Raise an error response if creation fails
            raise Response({"detail": "Profile not found and could not be created."},status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        try:
            profile = BasicProfile.objects.get(user=request.user)
            profile.delete()
            return Response({"detail": "Profile deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except BasicProfile.DoesNotExist:
            return Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

class CustomUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        if CustomUser.objects.filter(username=request.user.username).exists():
            return Response({"detail": "Customuser already exists."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        profile = CustomUser.objects.filter(username=request.user.username).first()

        if profile:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=profile,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=CustomUser
            )

    def get_queryset(self):
        return CustomUser.objects.filter(username=self.request.user.username)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        try:
            return CustomUser.objects.get(id=self.request.user.id)

        except CustomUser.DoesNotExist:
            raise Response({"detail": "Customuser not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request):
        try:
            profile = CustomUser.objects.get(user=request.user)
            profile.delete()
            return Response({"detail": "Customuser deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"detail": "Customuser not found."}, status=status.HTTP_404_NOT_FOUND)

class TeacherJobTypeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherJobType.objects.all()
    serializer_class = TeacherJobTypeSerializer

class SendPasswordResetEmailViewSet(APIView):
    def post(self, request, format=None):
        serializer = SendPasswordResetEmailSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            email = serializer.validated_data['email']
            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return Response({"msg": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            reset_password_link = f'https://ptpiui-gbdvdbbpe0hwh7gv.centralindia-01.azurewebsites.net/reset-password/{uidb64}/{token}'
            subject = 'Reset Your Password'
            message = f'Click the following link to reset your password: {reset_password_link}'

            try:
                # Send the email
                send_mail(subject, message, settings.EMAIL_HOST_USER, [email])
                return Response({'msg': 'Password reset link sent. Please check your email.'},
                                status=status.HTTP_200_OK)
            except Exception as e:
                return Response({'msg': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordViewSet(APIView):
    def post(self, request, uidb64, token, format=None):
        try:
            # Decode the uidb64 to get the user ID
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)

            # Validate the token
            if default_token_generator.check_token(user, token):
                # Reset the password
                new_password = request.data.get('new_password')
                user.set_password(new_password)
                user.save()
                return Response({"msg": "Password reset successful."}, status=status.HTTP_200_OK)

            return Response({"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class VarifyOTP(APIView):
    def post(self, request):
        try:
            data = request.data
            serializer = VerifyOTPSerializer(data=data)
            if not serializer.is_valid():
                return Response({
                    'error': serializer.errors,
                    'message': 'Invalid data provided'
                }, status=status.HTTP_400_BAD_REQUEST)

            email = serializer.data['email']
            otp = serializer.data['otp']

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                return Response({
                    'error': 'Invalid Email',
                    'message': 'User does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            if user.otp != otp:
                return Response({
                    'error': 'Invalid OTP',
                    'message': 'The provided OTP is incorrect'
                }, status=status.HTTP_400_BAD_REQUEST)

            expiration_time = timedelta(minutes=10)
            if user.otp_created_at is None or now() > user.otp_created_at + expiration_time:
                return Response({
                    'error': 'OTP expired',
                    'message': 'Please request a new OTP'
                }, status=status.HTTP_400_BAD_REQUEST)

            user.is_verified = True
            user.save()
            verified_msg(serializer.data['email'])

            return Response({
                'message': 'Account verified successfully'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"Error occurred: {e}")
            return Response({
                'error': 'Server Error',
                'message': 'An unexpected error occurred'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ResendOTP(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response({
                    'error': 'Email is required',
                    'message': 'Please provide a valid email address'
                }, status=status.HTTP_400_BAD_REQUEST)

            user = CustomUser.objects.filter(email=email).first()
            if not user:
                return Response({
                    'error': 'Invalid Email',
                    'message': 'Something went wrong'
                }, status=status.HTTP_403_FORBIDDEN)

            if user.is_verified:
                return Response({
                    'error': 'User already verified',
                    'message': 'Account already verified'
                }, status=status.HTTP_400_BAD_REQUEST)

            send_otp_via_email(user.email)

            return Response({
                'message': 'OTP resent successfully'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response({
                'error': 'Something went wrong',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class UserVerify(APIView):
    def post(self, request):
        try:
            email = request.data.get('email')
            if not email:
                return Response({
                    'error': 'Email is required',
                    'message': 'Please provide a valid email address'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = CustomUser.objects.get(email=email)
            except CustomUser.DoesNotExist:
                return Response({
                    'error': 'Invalid Email',
                    'message': 'User with this email does not exist'
                }, status=status.HTTP_404_NOT_FOUND)

            if not user.is_verified:
                return Response({
                    'error': 'User is not verified',
                    'message': 'Please verify your email first'
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "verified": True,
                "email": user.email,
                "username": user.username,
                "First name": user.Fname,
                "Last name": user.Lname,
                'message': 'User is verified'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({
                'error': 'An unexpected error occurred',
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ProfilecompletedView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    @action(detail=False, methods=["get"])
    def get(self, request, *args, **kwargs):
        user = request.user  # Get the logged-in user
        try:
            completed_percentage = calculate_profile_completed(user)  # Calculate completed
            return Response(
                {"profile_completed": completed_percentage},  # Return percentage
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": "An error occurred while calculating profile completed.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# Increase level based on qualified exam
class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def get(self, request, *args, **kwargs):
        user = request.user        
        try:
            user_basic_profile = BasicProfile.objects.get(user=user)
            user_qualification = TeacherQualification.objects.get(user=user)
            user_preference = Preference.objects.get(user=user)
        except BasicProfile.DoesNotExist:
            return Response(
                {"message": "Please complete your basic profile first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Preference.DoesNotExist:
            return Response(
                {"message": "Please complete your preference details first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TeacherQualification.DoesNotExist:
            return Response(
                {"message": "Please complete your qualification details first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        qualified_exams = TeacherExamResult.objects.filter(user=user, isqualified=True)

        levels = []
        for subject in user_preference.prefered_subject.all():
            for class_category in user_preference.class_category.all():
                unlocked_levels = ["Level 1"]

                has_level_1 = qualified_exams.filter(exam__level_id=1, exam__type="online",
                                                     exam__subject=subject, exam__class_category=class_category).exists()
                has_level_2_online = qualified_exams.filter(exam__level_id=2, exam__type="online",
                                                            exam__subject=subject, exam__class_category=class_category).exists()
                has_level_2_offline = qualified_exams.filter(exam__level_id=2, exam__type="offline",
                                                             exam__subject=subject, exam__class_category=class_category).exists()

                if has_level_1:
                    unlocked_levels.append("Level 2 Online")
                if has_level_2_online:
                    unlocked_levels.append("Level 2 Offline")
                if has_level_2_offline:
                    unlocked_levels.append("Interview")

                levels.append({
                    "subject_id": subject.id, 
                    "subject_name": subject.subject_name,
                    "classcategory_id": class_category.id,
                    "classcategory_name": class_category.name,
                    "levels": unlocked_levels
                })

        return Response(levels, status=status.HTTP_200_OK)

class ExamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def create(self, request):
        return create_object(ExamSerializer, request.data, Exam)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Exam)
        return Response({"Count": count})

    @action(detail=False, methods=['get'])
    def exams(self, request):
        level_id = request.query_params.get('level_id', None)
        class_category_id = request.query_params.get('class_category_id', None)
        subject_id = request.query_params.get('subject_id', None)

        exams = Exam.objects.all()

        if class_category_id:
            class_category = ClassCategory.objects.filter(pk=class_category_id).first()
            if not class_category:
                return Response(
                    {"message": "Please choose a valid class category."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            exams = exams.filter(class_category=class_category)

        if subject_id:
            subject = Subject.objects.filter(pk=subject_id).first()
            if not subject:
                return Response(
                    {"message": "Please choose a valid subject."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            exams = exams.filter(subject=subject)

        if level_id:
            try:
                level = Level.objects.get(pk=level_id)
                exams = exams.filter(level=level)
            except Level.DoesNotExist:
                return Response({"error": "Level not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        exam_id = request.data.get('id', None)

        if exam_id:
            try:
                exam_instance = Exam.objects.get(id=exam_id)
                serializer = ExamSerializer(exam_instance, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Exam.DoesNotExist:
                return create_object(ExamSerializer, request.data, Exam)
        else:
            return Response({"error": "ID field is required for PUT"}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Exam deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class SelfExamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve an Exam instance and filter its questions by language if specified.
        """
        exam = self.get_object()
        language = request.query_params.get('language', None)

        questions = list(exam.questions.all())

        if language:
            if language not in ['Hindi', 'English']:
                return Response({"error": "Invalid language."}, status=status.HTTP_400_BAD_REQUEST)
            questions = [q for q in questions if q.language == language]

        serializer = self.get_serializer(exam)
        exam_data = serializer.data
        exam_data['questions'] = QuestionSerializer(questions, many=True).data

        return Response(exam_data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def exams(self, request):
        user = request.user
        subject_id = request.query_params.get('subject_id', None)
        class_category_id = request.query_params.get('class_category_id', None)

        try:
            user_basic_profile = BasicProfile.objects.get(user=user)
            user_qualification = TeacherQualification.objects.filter(user=user).exists()
            user_preference = Preference.objects.get(user=user)
        except BasicProfile.DoesNotExist:
            return Response(
                {"message": "Please complete your basic profile first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Preference.DoesNotExist:
            return Response(
                {"message": "Please complete your preference details first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        except TeacherQualification.DoesNotExist:
            return Response(
                {"message": "Please complete your qualification details first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        exams = Exam.objects.all()

        # Ensure class category is selected
        if not class_category_id:
            return Response(
                {"message": "Please choose a class category first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        teacher_class_category = ClassCategory.objects.filter(preference__user=user, id=class_category_id).first()
        if teacher_class_category:
            exams = exams.filter(class_category=class_category_id)
        else:
            return Response(
                {"message": "Please choose a valid class category."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Ensure subject is selected
        if not subject_id:
            return Response({"message": "Please choose a subject."}, status=status.HTTP_400_BAD_REQUEST)

        teacher_subject = Subject.objects.filter(preference__user=user, id=subject_id).first()
        if teacher_subject:
            exams = exams.filter(subject=subject_id)
        else:
            return Response(
                {"message": "Please choose a valid subject."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check qualification for Level 1 and Level 2 exams
        qualified_level_1 = TeacherExamResult.objects.filter(
            user=user, isqualified=True, exam__subject_id=subject_id,
            exam__class_category_id=class_category_id, exam__level_id=1
        ).exists()

        online_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='online', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level_id=2
        ).exists()
        # Filter exams based on qualifications
        if not qualified_level_1:
            exams = exams.filter(level_id=1)  # If not qualified for Level 1, return only Level 1 exams
        elif qualified_level_1 and not online_qualified_level_2:
            exams = exams.filter(level_id__in=[1, 2], type='online')  # If qualified for Level 1, show Level 1 and Level 2 exams
        elif online_qualified_level_2:
            exams = exams.filter(level_id__in=[1, 2])  # If qualified for Level 2 online, show Level 2 offline exams
        # Exclude exams the user has already qualified for
        unqualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=False).values_list('exam_id', flat=True)
        exams = exams.exclude(id__in=unqualified_exam_ids)

        qualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=True).values_list('exam_id', flat=True)
        exams = exams.exclude(id__in=qualified_exam_ids)
        exam_set = exams.order_by('created_at')  # Get the first exam based on the creation date

        level_1_exam = exam_set.filter(level_id=1).first()
        level_2_online_exam = exam_set.filter(level_id=2, type='online').first()
        level_2_offline_exam = exam_set.filter(level_id=2, type='offline').first()

        final_exam_set = []
        if level_1_exam:
            final_exam_set.append(level_1_exam)
        if level_2_online_exam:
            final_exam_set.append(level_2_online_exam)
        if level_2_offline_exam:
            final_exam_set.append(level_2_offline_exam)

        if not final_exam_set:
            return Response({"message": "No exams available for the given criteria."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExamSerializer(final_exam_set, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

def insert_data(request):
    data_to_insert = {
        "class_categories": {
            "model": ClassCategory,
            "field": "name",
            "data": ["1 to 5", "6 to 10", "11 to 12", "BCA", "MCA"]
        },
        "reason": {
            "model": Reason,
            "field": "issue_type",
            "data": ["answer worng", "question worng", "spelling mistake", "question and answer worng ", "number mistake"]
        },
        "levels": {
            "model": Level,
            "field": "name",
            "data": ["1st Level", "2nd Level", "3rd Level", "4th Level", "5th Level"]
        },
        "skills": {
            "model": Skill,
            "field": "name",
            "data": ["Maths", "Physics", "Writing", "Mapping", "Research"]
        },
        "roles": {
            "model": Role,
            "field": "jobrole_name",
            "data": ["Teacher", "Professor", "Principal", "PtTeacher", "Sports Teacher"]
        },
        "subjects": {
            "model": Subject,
            "field": "subject_name",
            "data": ["Maths", "Physics", "php", "DBMS", "Hindi"]
        },
        "Teacherjobtype": {
            "model": TeacherJobType,
            "field": "teacher_job_name",
            "data": ["Coaching Teacher", "School Teacher", "Tutor"]
        },
        "Educationqualification": {
            "model": EducationalQualification,
            "field": "name",
            "data": ["matric", "Intermediate", "Under Graduate", "Post Graduate"]
        },
        "exam_centers": {
            "model": ExamCenter,
            "field": "center_name",
            "data": [
                {"center_name": "Alpha Exam Center", "pincode": "111111", "state": "State A", "city": "City A", "area": "Area A"},
                {"center_name": "Beta Exam Center", "pincode": "222222", "state": "State B", "city": "City B", "area": "Area B"},
                {"center_name": "Gamma Exam Center", "pincode": "333333", "state": "State C", "city": "City C", "area": "Area C"},
                {"center_name": "Delta Exam Center", "pincode": "444444", "state": "State D", "city": "City D", "area": "Area D"},
                {"center_name": "Epsilon Exam Center", "pincode": "555555", "state": "State E", "city": "City E", "area": "Area E"},
            ]
        },
        "Exams": {
            "model": Exam,
            "field": "name",
            "data": [
                {"name": "Set A", "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B", "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "1st Level", "subject": "Maths",
                 "total_marks": 200, "duration": 240, "type": "online"},
                {"name": "Set A", "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B", "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set A", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set B", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 200, "duration": 240, "type": "online"},
                {"name": "Set A", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 100, "duration": 180, "type": "online"},
                {"name": "Set B", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Set C", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                {"name": "Offline Set A", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                {"name": "Offline Set B", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                {"name": "Offline Set C", "class_category": "1 to 5", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set A", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set B", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Offline Set C", "class_category": "1 to 5", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "offline"},
                 {"name": "Set A", "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B", "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "1st Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A", "class_category": "6 to 10", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B", "class_category": "6 to 10", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "2nd Level", "subject": "Maths",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A", "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B", "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "1st Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set A", "class_category": "6 to 10", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set B", "class_category": "6 to 10", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
                 {"name": "Set C", "class_category": "6 to 10", "level": "2nd Level", "subject": "Physics",
                 "total_marks": 50, "duration": 90, "type": "online"},
            ]
        },
    }

    response_data = {}

    for key, config in data_to_insert.items():
        model = config["model"]
        field = config["field"]
        entries = config["data"]
        added_count = 0

        for entry in entries:
            if key == "exam_centers":  # Handle ExamCenter data
                if not model.objects.filter(center_name=entry["center_name"]).exists():
                    model.objects.create(
                        center_name=entry["center_name"],
                        pincode=entry["pincode"],
                        state=entry["state"],
                        city=entry["city"],
                        area=entry["area"]
                    )
                    added_count += 1
            elif key == "Exams":  # Handle Exam data
                name = entry.get("name")
                total_marks = entry.get("total_marks")
                duration = entry.get("duration")
                type = entry.get("type")
                class_category_name = entry.get("class_category")
                level_name = entry.get("level")
                subject_name = entry.get("subject")

                # Fetch related objects
                class_category, _ = ClassCategory.objects.get_or_create(name=class_category_name)
                level, _ = Level.objects.get_or_create(name=level_name)
                subject, _ = Subject.objects.get_or_create(subject_name=subject_name)

                if not model.objects.filter(
                        name=name,
                        class_category=class_category,
                        level=level,
                        subject=subject,
                        type=type
                ).exists():
                    model.objects.create(
                        name=name,
                        total_marks=total_marks,
                        duration=duration,
                        class_category=class_category,
                        level=level,
                        subject=subject,
                        type=type
                    )
                    added_count += 1
            else:  # Handle other data
                if not model.objects.filter(**{field: entry}).exists():
                    model.objects.create(**{field: entry})
                    added_count += 1

        response_data[key] = {
            "message": f'{added_count} {key.replace("_", " ")} added successfully.' if added_count > 0 else f'All {key.replace("_", " ")} already exist.',
            "added_count": added_count
        }

    exams = Exam.objects.all()
    if exams.exists():
        questions_data = [
    {
                "exam": exams[0],
                "time": 1.5,
                "language": "English",
                "text": "What is the capital of India?",
                "options": ["New Delhi", "Mumbaiinsert_", "Kolkata", "Chennai"],
                "solution": "New Delhi is the capital of India.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "What is the full form of DBMS?",
                "options": ["Database Management System", "Data Management System", "Database Maintenance System",
                            "Data Backup Management System"],
                "solution": "DBMS stands for Database Management System.",
                "correct_option": 1
            },
            {
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "Which of the following is a type of database model?",
                "options": ["Hierarchical Model", "Relational Model", "Object-Oriented Model", "All of the above"],
                "solution": "The correct answer is 'All of the above'. Each of these is a type of database model.",
                "correct_option": 3
            },
            {
                "exam": exams[4],
                "language": "English",
                "time": 1.5,
                "text": "Which SQL command is used to retrieve data from a database?",
                "options": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "solution": "The correct SQL command to retrieve data from a database is 'SELECT'.",
                "correct_option": 1
            },
            {
                "exam": exams[5],
                "language": "English",
                "time": 1.5,
                "text": "What is normalization in DBMS?",
                "options": ["The process of organizing data to reduce redundancy",
                            "The process of copying data for backup", "The process of making data available online",
                            "The process of encrypting data"],
                "solution": "Normalization is the process of organizing data in a database to reduce redundancy and improve data integrity.",
                "correct_option": 1
            },
            {
                "exam": exams[6],
                "time": 1.5,
                "language": "English",
                "text": "Which of the following is a type of join in SQL?",
                "options": ["INNER JOIN", "OUTER JOIN", "CROSS JOIN", "All of the above"],
                "solution": "The correct answer is 'All of the above'. INNER JOIN, OUTER JOIN, and CROSS JOIN are all types of SQL joins.",
                "correct_option": 3
            },
            {
                "exam": exams[7],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत की राजधानी क्या है?",
                "options": ["नई दिल्ली", "मुंबई", "कोलकाता", "चेन्नई"],
                "solution": "नई दिल्ली भारत की राजधानी है।",
                "correct_option": 1
            },
            {
                "exam": exams[8],
                "time": 1.5,
                "language": "English",
                "text": "What is 5 + 5?",
                "options": ["8", "9", "10", "11"],
                "solution": "The correct answer is 10.",
                "correct_option": 3
            },
            {
                "exam": exams[9],
                "time": 1.5,
                "language": "English",
                "text": "What is the boiling point of water?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The correct answer is 100°C.",
                "correct_option": 2
            },
            {
                "exam": exams[9],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत का सबसे बड़ा राज्य कौन सा है?",
                "options": ["राजस्थान", "उत्तर प्रदेश", "मध्य प्रदेश", "महाराष्ट्र"],
                "solution": "भारत का सबसे बड़ा राज्य राजस्थान है।",
                "correct_option": 1
            },
            {
                "exam": exams[10],
                "time": 1.5,
                "language": "Hindi",
                "text": "भारत का पहला प्रधानमंत्री कौन थे?",
                "options": ["लाल बहादुर शास्त्री", "पंडित नेहरू", "इंदिरा गांधी", "राजीव गांधी"],
                "solution": "भारत के पहले प्रधानमंत्री पंडित नेहरू थे।",
                "correct_option": 2
            },
            {
                "exam": exams[11],
                "time": 1.5,
                "language": "Hindi",
                "text": "एक ट्रेन 60 किमी/घंटे की गति से 2 घंटे में कितनी दूरी तय करेगी?",
                "options": ["60 किमी", "120 किमी", "180 किमी", "240 किमी"],
                "solution": "ट्रेन 120 किमी की दूरी तय करेगी।",
                "correct_option": 2
            },
            {
                "exam": exams[5],
                "time": 1.5,
                "language": "English",
                "text": "If a train travels at 60 km/hr for 2 hours, what distance does it cover?",
                "options": ["60 km", "120 km", "180 km", "240 km"],
                "solution": "The train covers 120 km.",
                "correct_option": 2
            },
            {
                "exam": exams[0],
                "time": 1.5,
                "language": "Hindi",
                "text": "5 का घनफल क्या है?",
                "options": ["25", "125", "15", "225"],
                "solution": "5 का घनफल 125 है।",
                "correct_option": 2
            },
            {
                "exam": exams[1],
                "time": 1.5,
                "language": "English",
                "text": "What is the cube of 5?",
                "options": ["25", "125", "15", "225"],
                "solution": "The cube of 5 is 125.",
                "correct_option": 2
            },
            {
                "exam": exams[2],
                "time": 1.5,
                "language": "Hindi",
                "text": "100 और 250 का औसत क्या है?",
                "options": ["175", "150", "200", "225"],
                "solution": "100 और 250 का औसत 175 है।",
                "correct_option": 1
            },
            {
                "exam": exams[3],
                "time": 1.5,
                "language": "English",
                "text": "What is the average of 100 and 250?",
                "options": ["175", "150", "200", "225"],
                "solution": "The average of 100 and 250 is 175.",
                "correct_option": 1
            },
            {
                "exam": exams[4],
                "time": 1.5,
                "language": "Hindi",
                "text": "प्रकाश की गति क्या है?",
                "options": ["3 × 10^6 मीटर/सेकेंड", "3 × 10^8 मीटर/सेकेंड", "3 × 10^9 मीटर/सेकेंड",
                            "3 × 10^7 मीटर/सेकेंड"],
                "solution": "प्रकाश की गति 3 × 10^8 मीटर/सेकेंड है।",
                "correct_option": 2
            },
            {
                "exam": exams[5],
                "time": 1.5,
                "language": "English",
                "text": "What is the speed of light?",
                "options": ["3 × 10^6 m/s", "3 × 10^8 m/s", "3 × 10^9 m/s", "3 × 10^7 m/s"],
                "solution": "The speed of light is 3 × 10^8 m/s.",
                "correct_option": 2
            },
            {
                "exam": exams[6],
                "time": 1.5,
                "language": "Hindi",
                "text": "न्यूटन के गति का दूसरा नियम क्या है?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "न्यूटन के गति का दूसरा नियम F = ma है।",
                "correct_option": 1
            },
            {
                "exam": exams[7],
                "time": 1.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                "exam": exams[8],
                "time": 1.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                "exam": exams[9],
                "time": 1.5,
                "language": "English",
                "text": "Which of the following is the largest planet in our solar system?",
                "options": ["Earth", "Mars", "Jupiter", "Saturn"],
                "solution": "Jupiter is the largest planet in our solar system.",
                "correct_option": 3
            },
            {
                "exam": exams[10],
                "time": 1.5,
                "language": "English",
                "text": "Who is the author of the play 'Romeo and Juliet'?",
                "options": ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"],
                "solution": "The author of 'Romeo and Juliet' is William Shakespeare.",
                "correct_option": 1
            },
            {
                "exam": exams[1],
                "time": 1.5,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 1.5,
                "language": "English",
                "text": "Who proposed the theory of relativity?",
                "options": ["Isaac Newton", "Albert Einstein", "Galileo Galilei", "Marie Curie"],
                "solution": "The theory of relativity was proposed by Albert Einstein.",
                "correct_option": 2
            },
            {
                "exam": exams[3],
                "time": 1.5,
                "language": "English",
                "text": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria", "Ribosome", "Golgi apparatus"],
                "solution": "The mitochondria are known as the powerhouse of the cell.",
                "correct_option": 2
            },
            {
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 64?",
                "options": ["6", "7", "8", "9"],
                "solution": "The square root of 64 is 8.",
                "correct_option": 3
            },
            {
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
                "solution": "'Romeo and Juliet'",
                "correct_option": 1
            },
            {
                "exam": exams[1],
                "time": 2.5,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "Who proposed the theory of relativity?",
                "options": ["Isaac Newton", "Albert Einstein", "Galileo Galilei", "Marie Curie"],
                "solution": "The theory of relativity was proposed by Albert Einstein.",
                "correct_option": 2
            },
            {
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "What is the powerhouse of the cell?",
                "options": ["Nucleus", "Mitochondria", "Ribosome", "Golgi apparatus"],
                "solution": "The mitochondria are known as the powerhouse of the cell.",
                "correct_option": 2
            },
            {
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 64?",
                "options": ["6", "7", "8", "9"],
                "solution": "The square root of 64 is 8.",
                "correct_option": 3
            },
            {
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "Who wrote 'Romeo and Juliet'?",
                "options": ["Charles Dickens", "William Shakespeare", "Jane Austen", "Mark Twain"],
                "solution": "'Romeo and Juliet' was written by William Shakespeare.",
                "correct_option": 2
            },
            {
                "exam": exams[7],
                "time": 2.5,
                "language": "English",
                "text": "What is the boiling point of water at sea level?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The boiling point of water at sea level is 100°C.",
                "correct_option": 2
            },
            {
                "exam": exams[8],
                "time": 2.5,
                "language": "English",
                "text": "Which planet is known as the Red Planet?",
                "options": ["Venus", "Mars", "Jupiter", "Saturn"],
                "solution": "Mars is known as the Red Planet.",
                "correct_option": 2
            },
            {
                "exam": exams[9],
                "time": 2.5,
                "language": "English",
                "text": "What is the largest organ in the human body?",
                "options": ["Liver", "Heart", "Skin", "Lungs"],
                "solution": "The skin is the largest organ in the human body.",
                "correct_option": 3
            },
            {
                "exam": exams[10],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of π (pi) up to two decimal places?",
                "options": ["3.12", "3.13", "3.14", "3.15"],
                "solution": "The value of π (pi) up to two decimal places is 3.14.",
                "correct_option": 3
            },
            {
                "exam": exams[0],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of π (pi) up to two decimal places?",
                "options": ["3.12", "3.14", "3.16", "3.18"],
                "solution": "The value of π up to two decimal places is 3.14.",
                "correct_option": 2
            },
            {
                "exam": exams[1],
                "time": 2.5,
                "language": "English",
                "text": "What is the square root of 144?",
                "options": ["10", "11", "12", "13"],
                "solution": "The square root of 144 is 12.",
                "correct_option": 3
            },
            {
                "exam": exams[2],
                "time": 2.5,
                "language": "English",
                "text": "Solve: 5 + 3 × 2.",
                "options": ["11", "16", "21", "13"],
                "solution": "According to the order of operations (BODMAS), 5 + 3 × 2 = 11.",
                "correct_option": 1
            },
            {
                "exam": exams[3],
                "time": 2.5,
                "language": "English",
                "text": "What is 15% of 200?",
                "options": ["25", "30", "35", "40"],
                "solution": "15% of 200 is 30.",
                "correct_option": 2
            },
            {
                "exam": exams[4],
                "time": 2.5,
                "language": "English",
                "text": "If x + 5 = 12, what is the value of x?",
                "options": ["5", "6", "7", "8"],
                "solution": "Subtracting 5 from both sides gives x = 7.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "Solve: 9 × (3 + 2).",
                "options": ["36", "40", "45", "50"],
                "solution": "Using BODMAS, 9 × (3 + 2) = 45.",
                "correct_option": 3
            },
            {
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "What is the perimeter of a rectangle with length 10 and width 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The perimeter of a rectangle is 2 × (length + width). So, 2 × (10 + 5) = 30.",
                "correct_option": 3
            },
            {
                "exam": exams[7],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of 2³?",
                "options": ["6", "8", "9", "12"],
                "solution": "2³ means 2 × 2 × 2 = 8.",
                "correct_option": 2
            },
            {
                "exam": exams[8],
                "time": 2.5,
                "language": "English",
                "text": "What is the area of a triangle with base 8 and height 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The area of a triangle is ½ × base × height. So, ½ × 8 × 5 = 20.",
                "correct_option": 1
            },
            {
                "exam": exams[9],
                "time": 2.5,
                "language": "English",
                "text": "What is the value of 100 ÷ 4?",
                "options": ["20", "25", "30", "40"],
                "solution": "100 ÷ 4 = 25.",
                "correct_option": 2
            },
            {
                "exam": exams[12],
                "time": 2.5,
                "language": "English",
                "text": "What is the unit of force?",
                "options": ["Newton", "Pascal", "Joule", "Watt"],
                "solution": "The SI unit of force is the Newton (N), named after Isaac Newton.",
                "correct_option": 1
            },
            {
                "exam": exams[12],
                "time": 2.5,
                "language": "English",
                "text": "What is the acceleration due to gravity on Earth?",
                "options": ["9.8 m/s²", "8.9 m/s²", "10.2 m/s²", "7.6 m/s²"],
                "solution": "The acceleration due to gravity on Earth is approximately 9.8 m/s².",
                "correct_option": 1
            },
            {
                "exam": exams[13],
                "time": 2.5,
                "language": "English",
                "text": "Which law explains why a rocket moves upward when gases are expelled downward?",
                "options": [
                    "Newton's First Law",
                    "Newton's Second Law",
                    "Newton's Third Law",
                    "Law of Gravitation"
                ],
                "solution": "Newton's Third Law states that for every action, there is an equal and opposite reaction.",
                "correct_option": 2
            },
            {
                "exam": exams[13],
                "time": 2.5,
                "language": "English",
                "text": "Which of the following is a scalar quantity?",
                "options": ["Velocity", "Force", "Speed", "Momentum"],
                "solution": "Speed is a scalar quantity because it has only magnitude, not direction.",
                "correct_option": 2
            },
            {
                "exam": exams[14],
                "time": 2.5,
                "language": "English",
                "text": "What is the formula for kinetic energy?",
                "options": [
                    "KE = mv",
                    "KE = 1/2 mv²",
                    "KE = 2mv",
                    "KE = m²v"
                ],
                "solution": "The formula for kinetic energy is KE = 1/2 mv².",
                "correct_option": 1
            },
            {
                "exam": exams[14],
                "time": 2.5,
                "language": "English",
                "text": "What is the speed of light in a vacuum?",
                "options": [
                    "3 × 10⁸ m/s",
                    "2 × 10⁸ m/s",
                    "1.5 × 10⁸ m/s",
                    "4 × 10⁸ m/s"
                ],
                "solution": "The speed of light in a vacuum is approximately 3 × 10⁸ meters per second.",
                "correct_option": 1
            },
            {
        "exam": exams[15],
        "time": 2.5,
        "language": "English",
        "text": "Solve: 5 + 3 × 2.",
        "options": ["11", "16", "21", "13"],
        "solution": "According to the order of operations (BODMAS), 5 + 3 × 2 = 11.",
        "correct_option": 2
    },
    {
        "exam": exams[15],
        "time": 2.5,
        "language": "English",
        "text": "What is the square root of 81?",
        "options": ["7", "8", "9", "10"],
        "solution": "The square root of 81 is 9.",
        "correct_option": 3
    },
    { 
        "exam": exams[16],
        "time": 1.5,
        "language": "English",
        "text": "Find the value of 12 ÷ 4 × 3.",
        "options": ["9", "3", "12", "15"],
        "solution": "Using BODMAS, 12 ÷ 4 × 3 = 3 × 3 = 9.",
        "correct_option": 1
    },
    {
        "exam": exams[16],
        "time": 1.5,
        "language": "English",
        "text": "Solve: 7 × (8 - 3).",
        "options": ["35", "56", "40", "21"],
        "solution": "First solve inside the brackets: 8 - 3 = 5. Then multiply: 7 × 5 = 35.",
        "correct_option": 1
    },
    {
        "exam": exams[17],
        "time": 1.5,
        "language": "English",
        "text": "What is 50% of 200?",
        "options": ["50", "100", "150", "200"],
        "solution": "50% of 200 is 100.",
        "correct_option": 1
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 + 3?",
        "options": ["4", "5", "6", "7"],
        "solution": "2 + 3 equals 5.",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What comes after 7?",
        "options": ["6", "8", "9", "10"],
        "solution": "8 comes after 7.",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 - 4?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 - 4 equals 6.",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "English",
        "text": "What is the smallest two-digit number?",
        "options": ["9", "10", "11", "12"],
        "solution": "The smallest two-digit number is 10.",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 + 3 कितना है?",
        "options": ["4", "5", "6", "7"],
        "solution": "2 + 3 का उत्तर 5 है।",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "7 के बाद कौन सा नंबर आता है?",
        "options": ["6", "8", "9", "10"],
        "solution": "7 के बाद 8 आता है।",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 - 4 कितना है?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 - 4 का उत्तर 6 है।",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज के कितने भुजाएँ होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज की 3 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[0],
        "time": 1.5,
        "language": "Hindi",
        "text": "सबसे छोटा दो-अंकीय नंबर कौन सा है?",
        "options": ["9", "10", "11", "12"],
        "solution": "सबसे छोटा दो-अंकीय नंबर 10 है।",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 + 2?",
        "options": ["1", "2", "4", "5"],
        "solution": "The sum of 2 and 2 is 4.",
        "correct_option": 3
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is the next number after 5?",
        "options": ["4", "6", "7", "8"],
        "solution": "The next number after 5 is 6.",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 minus 4?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 minus 4 equals 6.",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "English",
        "text": "How many hours are there in a day?",
        "options": ["12", "24", "36", "48"],
        "solution": "There are 24 hours in a day.",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 + 2 कितना होता है?",
        "options": ["1", "2", "4", "5"],
        "solution": "2 और 2 का योग 4 होता है।",
        "correct_option": 3
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 के बाद कौन सा संख्या आती है?",
        "options": ["4", "6", "7", "8"],
        "solution": "5 के बाद 6 आता है।",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज में कितने भुजाएं होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज में 3 भुजाएं होती हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 में से 4 घटाएं तो कितना होगा?",
        "options": ["5", "6", "7", "8"],
        "solution": "10 में से 4 घटाने पर 6 होता है।",
        "correct_option": 2
    },
    {
        "exam": exams[1],
        "time": 1.5,
        "language": "Hindi",
        "text": "एक दिन में कितने घंटे होते हैं?",
        "options": ["12", "24", "36", "48"],
        "solution": "एक दिन में 24 घंटे होते हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 5 + 3?",
        "options": ["7", "8", "9", "6"],
        "solution": "5 + 3 equals 8.",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a square have?",
        "options": ["3", "4", "5", "6"],
        "solution": "A square has 4 sides.",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 divided by 2?",
        "options": ["3", "5", "7", "10"],
        "solution": "10 divided by 2 equals 5.",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is 2 times 4?",
        "options": ["6", "8", "9", "10"],
        "solution": "2 times 4 equals 8.",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "English",
        "text": "What is the smallest two-digit number?",
        "options": ["9", "10", "11", "12"],
        "solution": "The smallest two-digit number is 10.",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 और 3 का योगफल क्या है?",
        "options": ["7", "8", "9", "6"],
        "solution": "5 और 3 का योगफल 8 है।",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "एक वर्ग में कितने भुजाएँ होती हैं?",
        "options": ["3", "4", "5", "6"],
        "solution": "एक वर्ग में 4 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 को 2 से विभाजित करें।",
        "options": ["3", "5", "7", "10"],
        "solution": "10 को 2 से विभाजित करने पर 5 प्राप्त होता है।",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "2 और 4 का गुणा क्या है?",
        "options": ["6", "8", "9", "10"],
        "solution": "2 और 4 का गुणा 8 है।",
        "correct_option": 2
    },
    {
        "exam": exams[2],
        "time": 1.5,
        "language": "Hindi",
        "text": "सबसे छोटा दो अंकों का अंक कौन सा है?",
        "options": ["9", "10", "11", "12"],
        "solution": "सबसे छोटा दो अंकों का अंक 10 है।",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that pulls objects towards the Earth?",
        "options": ["Magnetic force", "Gravitational force", "Electric force", "Frictional force"],
        "solution": "Gravitational force pulls objects towards the Earth.",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "वह कौन सी ताकत है जो वस्तुओं को पृथ्वी की ओर खींचती है?",
        "options": ["चुम्बकीय बल", "गुरुत्वाकर्षण बल", "वैद्युतिक बल", "घर्षण बल"],
        "solution": "गुरुत्वाकर्षण बल वस्तुओं को पृथ्वी की ओर खींचता है।",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a source of light?",
        "options": ["Moon", "Sun", "Earth", "Clouds"],
        "solution": "The Sun is a source of light.",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा प्रकाश का स्रोत है?",
        "options": ["चाँद", "सूरज", "पृथ्वी", "बादल"],
        "solution": "सूरज प्रकाश का स्रोत है।",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What is the change in position of an object called?",
        "options": ["Motion", "Speed", "Force", "Energy"],
        "solution": "The change in position of an object is called motion.",
        "correct_option": 1
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "वस्तु की स्थिति में परिवर्तन को क्या कहा जाता है?",
        "options": ["गति", "गति", "बल", "ऊर्जा"],
        "solution": "वस्तु की स्थिति में परिवर्तन को गति कहा जाता है।",
        "correct_option": 1
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "What do we use to measure temperature?",
        "options": ["Thermometer", "Barometer", "Speedometer", "Odometer"],
        "solution": "We use a thermometer to measure temperature.",
        "correct_option": 1
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "हम तापमान मापने के लिए किसका उपयोग करते हैं?",
        "options": ["थर्मामीटर", "बारोमीटर", "स्पीडोमीटर", "ओडोमीटर"],
        "solution": "हम तापमान मापने के लिए थर्मामीटर का उपयोग करते हैं।",
        "correct_option": 1
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a form of energy?",
        "options": ["Water", "Electricity", "Wood", "Stone"],
        "solution": "Electricity is a form of energy.",
        "correct_option": 2
    },
    {
        "exam": exams[3],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा ऊर्जा का रूप है?",
        "options": ["पानी", "बिजली", "लकड़ी", "पत्थर"],
        "solution": "बिजली ऊर्जा का रूप है।",
        "correct_option": 2
    },
     {
    "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the unit of force?",
    "options": ["Meter", "Newton", "Kilogram", "Second"],
    "solution": "The unit of force is Newton.",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "बल की इकाई क्या है?",
    "options": ["मीटर", "न्यूटन", "किलोग्राम", "सेकंड"],
    "solution": "बल की इकाई न्यूटन है।",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the boiling point of water?",
    "options": ["90°C", "100°C", "110°C", "120°C"],
    "solution": "The boiling point of water is 100°C.",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "पानी का उबालने का बिंदु क्या है?",
    "options": ["90°C", "100°C", "110°C", "120°C"],
    "solution": "पानी का उबालने का बिंदु 100°C है।",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the force that attracts objects towards the Earth?",
    "options": ["Gravity", "Magnetism", "Friction", "Electricity"],
    "solution": "Gravity is the force that attracts objects towards the Earth.",
    "correct_option": 1
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "वह बल जो वस्तुओं को पृथ्वी की ओर आकर्षित करता है, क्या कहलाता है?",
    "options": ["गुरुत्वाकर्षण", "चुम्बकत्व", "घर्षण", "बिजली"],
    "solution": "वह बल जो वस्तुओं को पृथ्वी की ओर आकर्षित करता है, गुरुत्वाकर्षण कहलाता है।",
    "correct_option": 1
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the shape of the Earth?",
    "options": ["Flat", "Round", "Oval", "Square"],
    "solution": "The Earth is round in shape.",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "पृथ्वी का आकार क्या है?",
    "options": ["समतल", "गोल", "अंडाकार", "वर्गाकार"],
    "solution": "पृथ्वी का आकार गोल है।",
    "correct_option": 2
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "English",
    "text": "What is the source of light in the daytime?",
    "options": ["Moon", "Lamp", "Sun", "Star"],
    "solution": "The source of light in the daytime is the Sun.",
    "correct_option": 3
  },
  {
    "exam": exams[4],
    "time": 1.5,
    "language": "Hindi",
    "text": "दिन के समय प्रकाश का स्रोत क्या है?",
    "options": ["चाँद", "दीपक", "सूर्य", "तारा"],
    "solution": "दिन के समय प्रकाश का स्रोत सूर्य है।",
    "correct_option": 3
  },
  {
        "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is the main source of light on Earth?",
        "options": ["Sun", "Moon", "Stars", "Lamp"],
        "solution": "The Sun is the main source of light on Earth.",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is water in its solid form?",
        "options": ["Ice", "Liquid", "Steam", "Rain"],
        "solution": "Water in its solid form is ice.",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a gas?",
        "options": ["Oxygen", "Water", "Iron", "Gold"],
        "solution": "Oxygen is a gas.",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that slows down a moving object?",
        "options": ["Push", "Friction", "Gravity", "Lift"],
        "solution": "Friction is the force that slows down a moving object.",
        "correct_option": 2
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "English",
        "text": "Which of these is an example of an insulator?",
        "options": ["Wood", "Metal", "Glass", "Copper"],
        "solution": "Wood is an example of an insulator.",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी पर मुख्य प्रकाश स्रोत क्या है?",
        "options": ["सूर्य", "चाँद", "तारे", "दीपक"],
        "solution": "पृथ्वी पर मुख्य प्रकाश स्रोत सूर्य है।",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "पानी अपनी ठोस अवस्था में क्या होता है?",
        "options": ["बर्फ", "द्रव", "वाष्प", "बारिश"],
        "solution": "पानी अपनी ठोस अवस्था में बर्फ होता है।",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन गैस है?",
        "options": ["ऑक्सीजन", "पानी", "लोहा", "सोना"],
        "solution": "ऑक्सीजन गैस है।",
        "correct_option": 1
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "वह कौन सा बल है जो चलती हुई वस्तु को धीमा कर देता है?",
        "options": ["धक्का", "घर्षण", "गुरुत्वाकर्षण", "उठाव"],
        "solution": "घर्षण वह बल है जो चलती हुई वस्तु को धीमा कर देता है।",
        "correct_option": 2
    },
    {
        "exam": exams[5],
        "time": 1.5,
        "language": "Hindi",
        "text": "इनमें से कौन सा उदाहरण इंसुलेटर का है?",
        "options": ["लकड़ी", "धातु", "कांच", "तांबा"],
        "solution": "लकड़ी इंसुलेटर का उदाहरण है।",
        "correct_option": 1
    },
     {
        "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 5 + 3?",
        "options": ["6", "7", "8", "9"],
        "solution": "5 + 3 equals 8.",
        "correct_option": 3
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 10 - 4?",
        "options": ["5", "6", "7", "4"],
        "solution": "10 - 4 equals 6.",
        "correct_option": 2
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is the shape of a ball?",
        "options": ["Square", "Rectangle", "Circle", "Triangle"],
        "solution": "The shape of a ball is a circle.",
        "correct_option": 3
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "How many sides does a triangle have?",
        "options": ["2", "3", "4", "5"],
        "solution": "A triangle has 3 sides.",
        "correct_option": 2
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "English",
        "text": "What is 7 × 2?",
        "options": ["12", "13", "14", "15"],
        "solution": "7 × 2 equals 14.",
        "correct_option": 3
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "5 + 3 क्या है?",
        "options": ["6", "7", "8", "9"],
        "solution": "5 + 3 का उत्तर 8 है।",
        "correct_option": 3
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "10 - 4 क्या है?",
        "options": ["5", "6", "7", "4"],
        "solution": "10 - 4 का उत्तर 6 है।",
        "correct_option": 2
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "गेंद का आकार क्या है?",
        "options": ["वर्ग", "आयत", "वृत्त", "त्रिभुज"],
        "solution": "गेंद का आकार वृत्त होता है।",
        "correct_option": 3
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज के कितने भुजाएँ होती हैं?",
        "options": ["2", "3", "4", "5"],
        "solution": "त्रिभुज की 3 भुजाएँ होती हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[6],
        "time": 1.5,
        "language": "Hindi",
        "text": "7 × 2 क्या है?",
        "options": ["12", "13", "14", "15"],
        "solution": "7 × 2 का उत्तर 14 है।",
        "correct_option": 3
    },
    {
        "exam": exams[7],
        "language": "English",
        "text": "What is 15 - 7?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "15 - 7 = 8."
    },
    {
        "exam": exams[7],
        "language": "English",
        "text": "What is the smallest 2-digit number?",
        "options": ["9", "10", "11", "12"],
        "correct_option": 2,
        "solution": "The smallest two-digit number is 10."
    },
    {
        "exam": exams[7],
        "language": "English",
        "text": "How many sides does a pentagon have?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "A pentagon has 5 sides."
    },
    {
        "exam": exams[7],
        "language": "English",
        "text": "What is 25 ÷ 5?",
        "options": ["4", "5", "6", "7"],
        "correct_option": 2,
        "solution": "25 ÷ 5 = 5."
    },
    {
        "exam": exams[7],
        "language": "English",
        "text": "What comes after 499?",
        "options": ["498", "500", "501", "502"],
        "correct_option": 2,
        "solution": "The number after 499 is 500."
    },
    {
        "exam": exams[7],
        "language": "Hindi",
        "text": "15 - 7 क्या है?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "15 - 7 = 8।"
    },
    {
        "exam": exams[7],
        "language": "Hindi",
        "text": "सबसे छोटी दो-अंकीय संख्या क्या है?",
        "options": ["9", "10", "11", "12"],
        "correct_option": 2,
        "solution": "सबसे छोटी दो-अंकीय संख्या 10 है।"
    },
    {
        "exam": exams[7],
        "language": "Hindi",
        "text": "पंचभुज में कितने भुजाएँ होती हैं?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "पंचभुज में 5 भुजाएँ होती हैं।"
    },
    {
        "exam": exams[7],
        "language": "Hindi",
        "text": "25 ÷ 5 कितना है?",
        "options": ["4", "5", "6", "7"],
        "correct_option": 2,
        "solution": "25 ÷ 5 = 5।"
    },
    {
        "exam": exams[7],
        "language": "Hindi",
        "text": "499 के बाद कौन सी संख्या आती है?",
        "options": ["498", "500", "501", "502"],
        "correct_option": 2,
        "solution": "499 के बाद 500 आती है।"
    },
    {
        "exam": exams[8],
        "language": "English",
        "text": "What is 12 + 8?",
        "options": ["18", "19", "20", "21"],
        "correct_option": 3,
        "solution": "12 + 8 = 20."
    },
    {
        "exam": exams[8],
        "language": "English",
        "text": "How many hours are there in 2 days?",
        "options": ["24", "36", "48", "60"],
        "correct_option": 3,
        "solution": "2 days × 24 hours/day = 48 hours."
    },
    {
        "exam": exams[8],
        "language": "English",
        "text": "Which shape has 4 equal sides?",
        "options": ["Triangle", "Square", "Rectangle", "Circle"],
        "correct_option": 2,
        "solution": "A square has 4 equal sides."
    },
    {
        "exam": exams[8],
        "language": "English",
        "text": "What is 5 × 6?",
        "options": ["25", "30", "35", "40"],
        "correct_option": 2,
        "solution": "5 × 6 = 30."
    },
    {
        "exam": exams[8],
        "language": "English",
        "text": "What is 100 minus 45?",
        "options": ["55", "50", "60", "45"],
        "correct_option": 1,
        "solution": "100 - 45 = 55."
    },
    {
        "exam": exams[8],
        "language": "Hindi",
        "text": "12 + 8 क्या है?",
        "options": ["18", "19", "20", "21"],
        "correct_option": 3,
        "solution": "12 + 8 = 20।"
    },
    {
        "exam": exams[8],
        "language": "Hindi",
        "text": "2 दिनों में कितने घंटे होते हैं?",
        "options": ["24", "36", "48", "60"],
        "correct_option": 3,
        "solution": "2 दिनों में 48 घंटे होते हैं।"
    },
    {
        "exam": exams[8],
        "language": "Hindi",
        "text": "कौन सा आकार चार बराबर भुजाएँ रखता है?",
        "options": ["त्रिभुज", "वर्ग", "आयत", "वृत्त"],
        "correct_option": 2,
        "solution": "वर्ग चार बराबर भुजाएँ रखता है।"
    },
    {
        "exam": exams[8],
        "language": "Hindi",
        "text": "5 × 6 कितना है?",
        "options": ["25", "30", "35", "40"],
        "correct_option": 2,
        "solution": "5 × 6 = 30।"
    },
    {
        "exam": exams[8],
        "language": "Hindi",
        "text": "100 में से 45 घटाने पर क्या प्राप्त होगा?",
        "options": ["55", "50", "60", "45"],
        "correct_option": 1,
        "solution": "100 - 45 = 55।"
    },
    {
        "exam": exams[9],
        "language": "English",
        "text": "What is the source of energy for the sun?",
        "options": ["Nuclear fusion", "Electric energy", "Chemical reaction", "Magnetic field"],
        "correct_option": 1,
        "solution": "The sun's energy comes from nuclear fusion, where hydrogen atoms combine to form helium, releasing a vast amount of energy."
    },
    {
        "exam": exams[9],
        "language": "English",
        "text": "What force pulls objects towards the Earth?",
        "options": ["Friction", "Magnetism", "Gravity", "Air resistance"],
        "correct_option": 3,
        "solution": "Gravity is the force that pulls objects towards the Earth's center due to its mass."
    },
    {
        "exam": exams[9],
        "language": "English",
        "text": "Which is the lightest planet in the solar system?",
        "options": ["Earth", "Mars", "Jupiter", "Mercury"],
        "correct_option": 4,
        "solution": "Mercury is the lightest planet in the solar system due to its small size and low mass."
    },
    {
        "exam": exams[9],
        "language": "English",
        "text": "What do we use to see very small objects?",
        "options": ["Telescope", "Binoculars", "Microscope", "Magnifying glass"],
        "correct_option": 3,
        "solution": "A microscope is used to observe very small objects by magnifying them to make them visible."
    },
    {
        "exam": exams[9],
        "language": "English",
        "text": "What is formed when light passes through a prism?",
        "options": ["Shadow", "Spectrum", "Reflection", "Absorption"],
        "correct_option": 2,
        "solution": "When light passes through a prism, it splits into its constituent colors, forming a spectrum."
    },
    {
        "exam": exams[9],
        "language": "Hindi",
        "text": "सूरज का ऊर्जा स्रोत क्या है?",
        "options": ["नाभिकीय संलयन", "विद्युत ऊर्जा", "रासायनिक प्रतिक्रिया", "चुंबकीय क्षेत्र"],
        "correct_option": 1,
        "solution": "सूरज की ऊर्जा का स्रोत नाभिकीय संलयन है, जिसमें हाइड्रोजन परमाणु मिलकर हीलियम बनाते हैं और ऊर्जा उत्पन्न करते हैं।"
    },
    {
        "exam": exams[9],
        "language": "Hindi",
        "text": "पृथ्वी की ओर वस्तुओं को खींचने वाला बल कौन सा है?",
        "options": ["घर्षण", "चुंबकत्व", "गुरुत्वाकर्षण", "वायुरोध"],
        "correct_option": 3,
        "solution": "गुरुत्वाकर्षण बल पृथ्वी की ओर वस्तुओं को खींचता है क्योंकि यह पृथ्वी के द्रव्यमान के कारण उत्पन्न होता है।"
    },
    {
        "exam": exams[9],
        "language": "Hindi",
        "text": "सौरमंडल में सबसे हल्का ग्रह कौन सा है?",
        "options": ["पृथ्वी", "मंगल", "बृहस्पति", "बुध"],
        "correct_option": 4,
        "solution": "बुध सौरमंडल का सबसे हल्का ग्रह है क्योंकि इसका आकार और द्रव्यमान बहुत छोटा है।"
    },
    {
        "exam": exams[9],
        "language": "Hindi",
        "text": "बहुत छोटे वस्तुओं को देखने के लिए हम क्या उपयोग करते हैं?",
        "options": ["दूरबीन", "दूरदर्शी", "सूक्ष्मदर्शी", "आवर्धक काँच"],
        "correct_option": 3,
        "solution": "बहुत छोटे वस्तुओं को देखने के लिए सूक्ष्मदर्शी का उपयोग किया जाता है, जो वस्तुओं को बड़ा दिखाने में मदद करता है।"
    },
    {
        "exam": exams[9],
        "language": "Hindi",
        "text": "प्रिज्म से प्रकाश गुजरने पर क्या बनता है?",
        "options": ["छाया", "वर्णक्रम", "परावर्तन", "अवशोषण"],
        "correct_option": 2,
        "solution": "प्रिज्म से प्रकाश गुजरने पर यह विभाजित होकर विभिन्न रंगों का वर्णक्रम बनाता है।"
    },

    {
        "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What happens when you place an object in water, and it floats?",
        "options": ["The object is heavy", "The object is light", "The water is hot", "The water is cold"],
        "solution": "The object is light, which is why it floats.",
        "correct_option": 2
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What is the natural satellite of Earth?",
        "options": ["Mars", "Sun", "Moon", "Venus"],
        "solution": "The Moon is the natural satellite of Earth.",
        "correct_option": 3
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "Which force slows down a moving ball on the ground?",
        "options": ["Friction", "Gravity", "Electricity", "Magnetism"],
        "solution": "Friction slows down a moving ball on the ground.",
        "correct_option": 1
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "Which of these can change the shape of an object?",
        "options": ["Push", "Pull", "Both", "None"],
        "solution": "Both pushing and pulling can change the shape of an object.",
        "correct_option": 3
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "English",
        "text": "What do plants use from sunlight to make food?",
        "options": ["Heat", "Energy", "Water", "Air"],
        "solution": "Plants use energy from sunlight to make food.",
        "correct_option": 2
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "जब आप किसी वस्तु को पानी में रखते हैं और वह तैरती है, तो क्या होता है?",
        "options": ["वस्तु भारी होती है", "वस्तु हल्की होती है", "पानी गर्म होता है", "पानी ठंडा होता है"],
        "solution": "वस्तु हल्की होती है, इसलिए वह तैरती है।",
        "correct_option": 2
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी का प्राकृतिक उपग्रह क्या है?",
        "options": ["मंगल", "सूर्य", "चंद्रमा", "शुक्र"],
        "solution": "चंद्रमा पृथ्वी का प्राकृतिक उपग्रह है।",
        "correct_option": 3
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "कौन सा बल जमीन पर चल रही गेंद को धीमा कर देता है?",
        "options": ["घर्षण", "गुरुत्वाकर्षण", "बिजली", "चुंबकत्व"],
        "solution": "घर्षण जमीन पर चल रही गेंद को धीमा कर देता है।",
        "correct_option": 1
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "इनमें से कौन सी चीज किसी वस्तु का आकार बदल सकती है?",
        "options": ["धक्का", "खींचना", "दोनों", "कोई नहीं"],
        "solution": "धक्का और खींचना दोनों वस्तु का आकार बदल सकते हैं।",
        "correct_option": 3
    },
    {
        "exam": exams[10],
        "time": 1.5,
        "language": "Hindi",
        "text": "पौधे भोजन बनाने के लिए सूर्य के प्रकाश से क्या उपयोग करते हैं?",
        "options": ["गर्मी", "ऊर्जा", "पानी", "हवा"],
        "solution": "पौधे भोजन बनाने के लिए सूर्य के प्रकाश से ऊर्जा का उपयोग करते हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[11],
        "language": "English",
        "text": "What is the force that pulls objects towards the Earth?",
        "options": ["Magnetism", "Friction", "Gravity", "Electricity"],
        "correct_option": 3,
        "solution": "Gravity is the force that pulls objects towards the Earth."
    },
    {
        "exam": exams[11],
        "language": "English",
        "text": "Which of the following is the source of light during the day?",
        "options": ["Moon", "Stars", "Sun", "Streetlight"],
        "correct_option": 3,
        "solution": "The Sun is the source of light during the day."
    },
    {
        "exam": exams[11],
        "language": "English",
        "text": "What is the state of water when it freezes?",
        "options": ["Liquid", "Gas", "Solid", "Plasma"],
        "correct_option": 3,
        "solution": "Water turns into a solid state when it freezes."
    },
    {
        "exam": exams[11],
        "language": "English",
        "text": "What tool do we use to measure the weight of an object?",
        "options": ["Thermometer", "Barometer", "Spring scale", "Compass"],
        "correct_option": 3,
        "solution": "A spring scale is used to measure the weight of an object."
    },
    {
        "exam": exams[11],
        "language": "English",
        "text": "What happens when you heat a solid?",
        "options": ["It becomes liquid", "It becomes gas", "It stays the same", "It becomes smaller"],
        "correct_option": 1,
        "solution": "When you heat a solid, it can melt and turn into a liquid."
    },
    {
        "exam": exams[11],
        "language": "Hindi",
        "text": "वह कौन सा बल है जो वस्तुओं को पृथ्वी की ओर खींचता है?",
        "options": ["चुंबकत्व", "घर्षण", "गुरुत्वाकर्षण", "विद्युत ऊर्जा"],
        "correct_option": 3,
        "solution": "गुरुत्वाकर्षण वह बल है जो वस्तुओं को पृथ्वी की ओर खींचता है।"
    },
    {
        "exam": exams[11],
        "language": "Hindi",
        "text": "दिन के समय प्रकाश का स्रोत क्या है?",
        "options": ["चाँद", "तारे", "सूरज", "सड़क की बत्तियाँ"],
        "correct_option": 3,
        "solution": "सूरज दिन के समय प्रकाश का मुख्य स्रोत है।"
    },
    {
        "exam": exams[11],
        "language": "Hindi",
        "text": "जब पानी जमता है, तो उसकी अवस्था क्या होती है?",
        "options": ["तरल", "गैस", "ठोस", "प्लाज्मा"],
        "correct_option": 3,
        "solution": "जब पानी जमता है, तो वह ठोस अवस्था में बदल जाता है।"
    },
    {
        "exam": exams[11],
        "language": "Hindi",
        "text": "हम किसी वस्तु का वजन मापने के लिए कौन सा यंत्र उपयोग करते हैं?",
        "options": ["थर्मामीटर", "वायुदाबमापी", "स्प्रिंग स्केल", "कंपास"],
        "correct_option": 3,
        "solution": "वजन मापने के लिए हम स्प्रिंग स्केल का उपयोग करते हैं।"
    },
    {
        "exam": exams[11],
        "language": "Hindi",
        "text": "जब आप किसी ठोस को गरम करते हैं, तो क्या होता है?",
        "options": ["यह तरल बन जाता है", "यह गैस बन जाता है", "यह वैसा का वैसा रहता है", "यह छोटा हो जाता है"],
        "correct_option": 1,
        "solution": "जब आप किसी ठोस को गरम करते हैं, तो वह पिघलकर तरल में बदल सकता है।"
    },
    {
        "exam": exams[18],
        "language": "English",
        "text": "What is the sum of 56 and 78?",
        "options": ["134", "136", "148", "138"],
        "correct_option": 1,
        "solution": "The sum of 56 and 78 is 134."
    },
    {
        "exam": exams[18],
        "language": "English",
        "text": "What is the product of 12 and 9?",
        "options": ["108", "96", "72", "110"],
        "correct_option": 1,
        "solution": "The product of 12 and 9 is 108."
    },
    {
        "exam": exams[18],
        "language": "English",
        "text": "What is 36 divided by 4?",
        "options": ["9", "8", "7", "10"],
        "correct_option": 1,
        "solution": "36 divided by 4 equals 9."
    },
    {
        "exam": exams[18],
        "language": "English",
        "text": "What is the square of 7?",
        "options": ["49", "56", "72", "64"],
        "correct_option": 1,
        "solution": "The square of 7 is 49."
    },
    {
        "exam": exams[18],
        "language": "English",
        "text": "What is the perimeter of a rectangle with length 8 cm and width 5 cm?",
        "options": ["26 cm", "32 cm", "16 cm", "18 cm"],
        "correct_option": 1,
        "solution": "The perimeter of the rectangle is 26 cm (2 × (8 + 5))."
    },
    {
        "exam": exams[18],
        "language": "Hindi",
        "text": "56 और 78 का योगफल क्या है?",
        "options": ["134", "136", "148", "138"],
        "correct_option": 1,
        "solution": "56 और 78 का योगफल 134 है।"
    },
    {
        "exam": exams[18],
        "language": "Hindi",
        "text": "12 और 9 का गुणनफल क्या है?",
        "options": ["108", "96", "72", "110"],
        "correct_option": 1,
        "solution": "12 और 9 का गुणनफल 108 है।"
    },
    {
        "exam": exams[18],
        "language": "Hindi",
        "text": "36 को 4 से भाग देने पर क्या प्राप्त होता है?",
        "options": ["9", "8", "7", "10"],
        "correct_option": 1,
        "solution": "36 को 4 से भाग देने पर 9 प्राप्त होता है।"
    },
    {
        "exam": exams[18],
        "language": "Hindi",
        "text": "7 का वर्गफल क्या है?",
        "options": ["49", "56", "72", "64"],
        "correct_option": 1,
        "solution": "7 का वर्गफल 49 है।"
    },
    {
        "exam": exams[18],
        "language": "Hindi",
        "text": "8 सेंटीमीटर लंबाई और 5 सेंटीमीटर चौड़ाई वाले आयत का परिमाप क्या होगा?",
        "options": ["26 सेंटीमीटर", "32 सेंटीमीटर", "16 सेंटीमीटर", "18 सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का परिमाप 26 सेंटीमीटर होगा (2 × (8 + 5))."
    },
    {
        "exam": exams[19],
        "language": "English",
        "text": "What is the sum of 45 and 63?",
        "options": ["108", "110", "112", "114"],
        "correct_option": 1,
        "solution": "The sum of 45 and 63 is 108."
    },
    {
        "exam": exams[19],
        "language": "English",
        "text": "What is the difference between 95 and 47?",
        "options": ["48", "50", "52", "58"],
        "correct_option": 1,
        "solution": "The difference between 95 and 47 is 48."
    },
    {
        "exam": exams[19],
        "language": "English",
        "text": "What is 15 multiplied by 6?",
        "options": ["90", "96", "84", "72"],
        "correct_option": 1,
        "solution": "15 multiplied by 6 is 90."
    },
    {
        "exam": exams[19],
        "language": "English",
        "text": "What is the area of a rectangle with length 10 cm and width 5 cm?",
        "options": ["50 cm²", "55 cm²", "60 cm²", "45 cm²"],
        "correct_option": 1,
        "solution": "The area of the rectangle is 50 cm² (length × width)."
    },
    {
        "exam": exams[19],
        "language": "English",
        "text": "What is the square root of 49?",
        "options": ["7", "6", "8", "9"],
        "correct_option": 1,
        "solution": "The square root of 49 is 7."
    },
     {
        "exam": exams[19],
        "language": "Hindi",
        "text": "45 और 63 का योगफल क्या है?",
        "options": ["108", "110", "112", "114"],
        "correct_option": 1,
        "solution": "45 और 63 का योगफल 108 है।"
    },
    {
        "exam": exams[19],
        "language": "Hindi",
        "text": "95 और 47 के बीच का अंतर क्या है?",
        "options": ["48", "50", "52", "58"],
        "correct_option": 1,
        "solution": "95 और 47 के बीच का अंतर 48 है।"
    },
    {
        "exam": exams[19],
        "language": "Hindi",
        "text": "15 को 6 से गुणा करने पर क्या मिलता है?",
        "options": ["90", "96", "84", "72"],
        "correct_option": 1,
        "solution": "15 को 6 से गुणा करने पर 90 मिलता है।"
    },
    {
        "exam": exams[19],
        "language": "Hindi",
        "text": "10 सेंटीमीटर लंबाई और 5 सेंटीमीटर चौड़ाई वाले आयत का क्षेत्रफल क्या है?",
        "options": ["50 सेमी²", "55 सेमी²", "60 सेमी²", "45 सेमी²"],
        "correct_option": 1,
        "solution": "आयत का क्षेत्रफल 50 सेमी² है (लंबाई × चौड़ाई)।"
    },
    {
        "exam": exams[19],
        "language": "Hindi",
        "text": "49 का वर्गमूल क्या है?",
        "options": ["7", "6", "8", "9"],
        "correct_option": 1,
        "solution": "49 का वर्गमूल 7 है।"
    },
     {
        "exam": exams[20],
        "language": "English",
        "text": "What is the sum of 125 and 75?",
        "options": ["200", "210", "190", "180"],
        "correct_option": 1,
        "solution": "The sum of 125 and 75 is 200."
    },
    {
        "exam": exams[20],
        "language": "English",
        "text": "What is the product of 12 and 8?",
        "options": ["96", "98", "100", "104"],
        "correct_option": 1,
        "solution": "The product of 12 and 8 is 96."
    },
    {
        "exam": exams[20],
        "language": "English",
        "text": "What is the perimeter of a square with side length 6 cm?",
        "options": ["24 cm", "18 cm", "20 cm", "22 cm"],
        "correct_option": 1,
        "solution": "The perimeter of the square is 24 cm (4 × side length)."
    },
    {
        "exam": exams[20],
        "language": "English",
        "text": "What is 72 divided by 9?",
        "options": ["8", "7", "9", "6"],
        "correct_option": 1,
        "solution": "72 divided by 9 equals 8."
    },
    {
        "exam": exams[20],
        "language": "English",
        "text": "What is the value of 15 raised to the power of 2?",
        "options": ["225", "250", "200", "300"],
        "correct_option": 1,
        "solution": "15 raised to the power of 2 equals 225."
    },
    {
        "exam": exams[20],
        "language": "Hindi",
        "text": "125 और 75 का योगफल क्या है?",
        "options": ["200", "210", "190", "180"],
        "correct_option": 1,
        "solution": "125 और 75 का योगफल 200 है।"
    },
    {
        "exam": exams[20],
        "language": "Hindi",
        "text": "12 और 8 का गुणनफल क्या है?",
        "options": ["96", "98", "100", "104"],
        "correct_option": 1,
        "solution": "12 और 8 का गुणनफल 96 है।"
    },
    {
        "exam": exams[20],
        "language": "Hindi",
        "text": "6 सेंटीमीटर लंबाई वाले वर्ग का परिमाप क्या है?",
        "options": ["24 सेमी", "18 सेमी", "20 सेमी", "22 सेमी"],
        "correct_option": 1,
        "solution": "वर्ग का परिमाप 24 सेमी है (4 × लंबाई)।"
    },
    {
        "exam": exams[20],
        "language": "Hindi",
        "text": "72 को 9 से भाग करने पर क्या मिलता है?",
        "options": ["8", "7", "9", "6"],
        "correct_option": 1,
        "solution": "72 को 9 से भाग करने पर 8 मिलता है।"
    },
    {
        "exam": exams[20],
        "language": "Hindi",
        "text": "15 का वर्गमूल क्या है?",
        "options": ["225", "250", "200", "300"],
        "correct_option": 1,
        "solution": "15 का वर्गमूल 225 है।"
    },
    {
        "exam": exams[21],
        "language": "English",
        "text": "What is the square root of 81?",
        "options": ["8", "9", "7", "6"],
        "correct_option": 2,
        "solution": "The square root of 81 is 9."
    },
    {
        "exam": exams[21],
        "language": "English",
        "text": "What is the result of 15 × 4?",
        "options": ["60", "55", "65", "70"],
        "correct_option": 1,
        "solution": "15 multiplied by 4 is 60."
    },
    {
        "exam": exams[21],
        "language": "English",
        "text": "If a rectangle has a length of 8 cm and a width of 5 cm, what is its area?",
        "options": ["40 cm²", "50 cm²", "60 cm²", "45 cm²"],
        "correct_option": 1,
        "solution": "The area of the rectangle is 40 cm² (length × width)."
    },
    {
        "exam": exams[21],
        "language": "English",
        "text": "What is the sum of 56 and 44?",
        "options": ["90", "100", "110", "120"],
        "correct_option": 2,
        "solution": "The sum of 56 and 44 is 100."
    },
    {
        "exam": exams[21],
        "language": "English",
        "text": "What is the value of 100 ÷ 5?",
        "options": ["25", "20", "30", "15"],
        "correct_option": 1,
        "solution": "100 divided by 5 is 20."
    },
    {
        "exam": exams[21],
        "language": "Hindi",
        "text": "81 का वर्गमूल क्या है?",
        "options": ["8", "9", "7", "6"],
        "correct_option": 2,
        "solution": "81 का वर्गमूल 9 है।"
    },
    {
        "exam": exams[21],
        "language": "Hindi",
        "text": "15 × 4 का परिणाम क्या है?",
        "options": ["60", "55", "65", "70"],
        "correct_option": 1,
        "solution": "15 गुणा 4 का परिणाम 60 है।"
    },
    {
        "exam": exams[21],
        "language": "Hindi",
        "text": "यदि आयत की लंबाई 8 सेंटीमीटर और चौड़ाई 5 सेंटीमीटर है, तो उसका क्षेत्रफल क्या होगा?",
        "options": ["40 वर्ग सेंटीमीटर", "50 वर्ग सेंटीमीटर", "60 वर्ग सेंटीमीटर", "45 वर्ग सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का क्षेत्रफल 40 वर्ग सेंटीमीटर है (लंबाई × चौड़ाई)।"
    },
    {
        "exam": exams[21],
        "language": "Hindi",
        "text": "56 और 44 का योगफल क्या है?",
        "options": ["90", "100", "110", "120"],
        "correct_option": 2,
        "solution": "56 और 44 का योगफल 100 है।"
    },
    {
        "exam": exams[21],
        "language": "Hindi",
        "text": "100 ÷ 5 का मान क्या है?",
        "options": ["25", "20", "30", "15"],
        "correct_option": 1,
        "solution": "100 को 5 से विभाजित करने पर 20 मिलता है।"
    },
    {
        "exam": exams[22],
        "language": "English",
        "text": "What is 18 ÷ 3?",
        "options": ["5", "6", "7", "8"],
        "correct_option": 2,
        "solution": "18 divided by 3 is 6."
    },
    {
        "exam": exams[22],
        "language": "English",
        "text": "What is the perimeter of a square with each side measuring 4 cm?",
        "options": ["12 cm", "14 cm", "16 cm", "20 cm"],
        "correct_option": 3,
        "solution": "The perimeter of a square is 4 times the length of one side. 4 × 4 = 16 cm."
    },
    {
        "exam": exams[22],
        "language": "English",
        "text": "What is 25 × 3?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 2,
        "solution": "25 multiplied by 3 is 75."
    },
    {
        "exam": exams[22],
        "language": "English",
        "text": "What is the area of a rectangle with a length of 6 cm and width of 3 cm?",
        "options": ["15 cm²", "18 cm²", "20 cm²", "24 cm²"],
        "correct_option": 2,
        "solution": "The area of the rectangle is 18 cm² (length × width)."
    },
    {
        "exam": exams[22],
        "language": "English",
        "text": "What is the sum of 45 and 35?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 1,
        "solution": "The sum of 45 and 35 is 80."
    },
    {
        "exam": exams[22],
        "language": "Hindi",
        "text": "18 ÷ 3 क्या है?",
        "options": ["5", "6", "7", "8"],
        "correct_option": 2,
        "solution": "18 को 3 से विभाजित करने पर 6 मिलता है।"
    },
    {
        "exam": exams[22],
        "language": "Hindi",
        "text": "एक वर्ग का परिधि क्या है जिसका प्रत्येक किनारा 4 सेंटीमीटर है?",
        "options": ["12 सेंटीमीटर", "14 सेंटीमीटर", "16 सेंटीमीटर", "20 सेंटीमीटर"],
        "correct_option": 3,
        "solution": "वर्ग का परिधि 4 गुना एक किनारे की लंबाई होती है। 4 × 4 = 16 सेंटीमीटर।"
    },
    {
        "exam": exams[22],
        "language": "Hindi",
        "text": "25 × 3 क्या है?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 2,
        "solution": "25 को 3 से गुणा करने पर 75 मिलता है।"
    },
    {
        "exam": exams[22],
        "language": "Hindi",
        "text": "एक आयत का क्षेत्रफल क्या होगा जिसकी लंबाई 6 सेंटीमीटर और चौड़ाई 3 सेंटीमीटर है?",
        "options": ["15 वर्ग सेंटीमीटर", "18 वर्ग सेंटीमीटर", "20 वर्ग सेंटीमीटर", "24 वर्ग सेंटीमीटर"],
        "correct_option": 2,
        "solution": "आयत का क्षेत्रफल 18 वर्ग सेंटीमीटर होगा (लंबाई × चौड़ाई)।"
    },
    {
        "exam": exams[22],
        "language": "Hindi",
        "text": "45 और 35 का योगफल क्या है?",
        "options": ["70", "75", "80", "85"],
        "correct_option": 1,
        "solution": "45 और 35 का योगफल 80 है।"
    },
     {
        "exam": exams[23],
        "language": "English",
        "text": "What is the square root of 64?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "The square root of 64 is 8."
    },
    {
        "exam": exams[23],
        "language": "English",
        "text": "What is 9 × 7?",
        "options": ["56", "63", "72", "81"],
        "correct_option": 2,
        "solution": "9 multiplied by 7 is 63."
    },
    {
        "exam": exams[23],
        "language": "English",
        "text": "What is the area of a triangle with base 10 cm and height 6 cm?",
        "options": ["30 cm²", "40 cm²", "50 cm²", "60 cm²"],
        "correct_option": 1,
        "solution": "The area of the triangle is 30 cm² (base × height ÷ 2)."
    },
    {
        "exam": exams[23],
        "language": "English",
        "text": "What is the sum of 150 and 275?",
        "options": ["425", "450", "475", "500"],
        "correct_option": 1,
        "solution": "The sum of 150 and 275 is 425."
    },
    {
        "exam": exams[23],
        "language": "English",
        "text": "What is 12 ÷ 4?",
        "options": ["2", "3", "4", "5"],
        "correct_option": 2,
        "solution": "12 divided by 4 is 3."
    },
    {
        "exam": exams[23],
        "language": "Hindi",
        "text": "64 का वर्गमूल क्या है?",
        "options": ["6", "7", "8", "9"],
        "correct_option": 3,
        "solution": "64 का वर्गमूल 8 है।"
    },
    {
        "exam": exams[23],
        "language": "Hindi",
        "text": "9 × 7 क्या है?",
        "options": ["56", "63", "72", "81"],
        "correct_option": 2,
        "solution": "9 को 7 से गुणा करने पर 63 मिलता है।"
    },
    {
        "exam": exams[23],
        "language": "Hindi",
        "text": "एक त्रिकोण का क्षेत्रफल क्या होगा जिसकी आधार 10 सेंटीमीटर और ऊंचाई 6 सेंटीमीटर है?",
        "options": ["30 वर्ग सेंटीमीटर", "40 वर्ग सेंटीमीटर", "50 वर्ग सेंटीमीटर", "60 वर्ग सेंटीमीटर"],
        "correct_option": 1,
        "solution": "त्रिकोण का क्षेत्रफल 30 वर्ग सेंटीमीटर होगा (आधार × ऊंचाई ÷ 2)।"
    },
    {
        "exam": exams[23],
        "language": "Hindi",
        "text": "150 और 275 का योगफल क्या है?",
        "options": ["425", "450", "475", "500"],
        "correct_option": 1,
        "solution": "150 और 275 का योगफल 425 है।"
    },
    {
        "exam": exams[23],
        "language": "Hindi",
        "text": "12 ÷ 4 क्या है?",
        "options": ["2", "3", "4", "5"],
        "correct_option": 2,
        "solution": "12 को 4 से विभाजित करने पर 3 मिलता है।"
    },
     {
        "exam": exams[24],
        "language": "English",
        "text": "What is 15 × 8?",
        "options": ["120", "130", "140", "150"],
        "correct_option": 1,
        "solution": "15 multiplied by 8 is 120."
    },
    {
        "exam": exams[24],
        "language": "English",
        "text": "What is the perimeter of a rectangle with length 12 cm and width 8 cm?",
        "options": ["40 cm", "50 cm", "60 cm", "70 cm"],
        "correct_option": 1,
        "solution": "The perimeter of a rectangle is 2 × (length + width), so 2 × (12 + 8) = 40 cm."
    },
    {
        "exam": exams[24],
        "language": "English",
        "text": "What is 45 ÷ 9?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 1,
        "solution": "45 divided by 9 is 5."
    },
    {
        "exam": exams[24],
        "language": "English",
        "text": "What is the product of 12 and 7?",
        "options": ["72", "75", "78", "84"],
        "correct_option": 4,
        "solution": "The product of 12 and 7 is 84."
    },
    {
        "exam": exams[24],
        "language": "English",
        "text": "What is the area of a square with side length 6 cm?",
        "options": ["30 cm²", "36 cm²", "42 cm²", "48 cm²"],
        "correct_option": 2,
        "solution": "The area of a square is side × side, so 6 × 6 = 36 cm²."
    },
    {
        "exam": exams[24],
        "language": "Hindi",
        "text": "15 × 8 क्या है?",
        "options": ["120", "130", "140", "150"],
        "correct_option": 1,
        "solution": "15 को 8 से गुणा करने पर 120 मिलता है।"
    },
    {
        "exam": exams[24],
        "language": "Hindi",
        "text": "एक आयत का परिधि क्या होगा, जिसकी लंबाई 12 सेंटीमीटर और चौड़ाई 8 सेंटीमीटर है?",
        "options": ["40 सेंटीमीटर", "50 सेंटीमीटर", "60 सेंटीमीटर", "70 सेंटीमीटर"],
        "correct_option": 1,
        "solution": "आयत का परिधि 2 × (लंबाई + चौड़ाई) होता है, तो 2 × (12 + 8) = 40 सेंटीमीटर।"
    },
    {
        "exam": exams[24],
        "language": "Hindi",
        "text": "45 ÷ 9 क्या है?",
        "options": ["3", "4", "5", "6"],
        "correct_option": 3,
        "solution": "45 को 9 से विभाजित करने पर 5 मिलता है।"
    },
    {
        "exam": exams[24],
        "language": "Hindi",
        "text": "12 और 7 का गुणनफल क्या है?",
        "options": ["72", "75", "78", "84"],
        "correct_option": 4,
        "solution": "12 और 7 का गुणनफल 84 है।"
    },
    {
        "exam": exams[24],
        "language": "Hindi",
        "text": "एक वर्ग का क्षेत्रफल क्या होगा, जिसका एक भुजा 6 सेंटीमीटर है?",
        "options": ["30 वर्ग सेंटीमीटर", "36 वर्ग सेंटीमीटर", "42 वर्ग सेंटीमीटर", "48 वर्ग सेंटीमीटर"],
        "correct_option": 2,
        "solution": "वर्ग का क्षेत्रफल भुजा × भुजा होता है, तो 6 × 6 = 36 वर्ग सेंटीमीटर।"
    },
     {
        "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the dimensional formula of force?",
        "options": ["MLT^-2", "ML^-1T^-2", "ML^2T^-2", "MLT^-1"],
        "solution": "The dimensional formula of force is MLT^-2.",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "Which physical quantity is measured in Hertz?",
        "options": ["Frequency", "Force", "Energy", "Power"],
        "solution": "Frequency is measured in Hertz.",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of acceleration due to gravity on Earth?",
        "options": ["9.8 m/s^2", "10.8 m/s^2", "8.8 m/s^2", "7.8 m/s^2"],
        "solution": "The acceleration due to gravity on Earth is 9.8 m/s^2.",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is a scalar quantity?",
        "options": ["Speed", "Velocity", "Force", "Momentum"],
        "solution": "Speed is a scalar quantity.",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "English",
        "text": "What is the SI unit of work?",
        "options": ["Joule", "Newton", "Watt", "Pascal"],
        "solution": "The SI unit of work is Joule.",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "बल का विमीय सूत्र क्या है?",
        "options": ["MLT^-2", "ML^-1T^-2", "ML^2T^-2", "MLT^-1"],
        "solution": "बल का विमीय सूत्र MLT^-2 है।",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "कौन सा भौतिक मात्रा हर्ट्ज़ में मापा जाता है?",
        "options": ["आवृत्ति", "बल", "ऊर्जा", "शक्ति"],
        "solution": "आवृत्ति हर्ट्ज़ में मापा जाता है।",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "पृथ्वी पर गुरुत्वाकर्षण के कारण त्वरण का मान क्या है?",
        "options": ["9.8 मी/से^2", "10.8 मी/से^2", "8.8 मी/से^2", "7.8 मी/से^2"],
        "solution": "पृथ्वी पर गुरुत्वाकर्षण के कारण त्वरण का मान 9.8 मी/से^2 है।",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन एक अदिश मात्रा है?",
        "options": ["गति", "वेग", "बल", "संचलन"],
        "solution": "गति एक अदिश मात्रा है।",
        "correct_option": 1
    },
    {
        "exam": exams[25],
        "time": 1.5,
        "language": "Hindi",
        "text": "कार्य की एसआई इकाई क्या है?",
        "options": ["जूल", "न्यूटन", "वाट", "पास्कल"],
        "solution": "कार्य की एसआई इकाई जूल है।",
        "correct_option": 1
    },
     {
        "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the derivative of (x^2)?",
        "options": ["1", "2x", "x", "2"],
        "solution": "The derivative of (x^2) is 2x.",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "If the matrix A is of order 2x2, how many elements does it have?",
        "options": ["2", "4", "6", "8"],
        "solution": "A matrix of order 2x2 has 4 elements.",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the integral of (1/x)?",
        "options": ["ln(x)", "x", "x^2/2", "1/(2x)"],
        "solution": "The integral of (1/x) is ln(x).",
        "correct_option": 1
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "What is the sum of the angles in a triangle?",
        "options": ["90 degrees", "180 degrees", "270 degrees", "360 degrees"],
        "solution": "The sum of the angles in a triangle is 180 degrees.",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "English",
        "text": "Solve for x: (2x + 3 = 7)",
        "options": ["1", "2", "3", "4"],
        "solution": "The solution for (2x + 3 = 7) is x = 2.",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "क्या है (x^2) का अवकलन?",
        "options": ["1", "2x", "x", "2"],
        "solution": "(x^2) का अवकलन 2x है।",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "यदि मैट्रिक्स A का क्रम 2x2 है, तो इसमें कितने तत्व होते हैं?",
        "options": ["2", "4", "6", "8"],
        "solution": "क्रम 2x2 का एक मैट्रिक्स में 4 तत्व होते हैं।",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "(1/x) का समाकलन क्या है?",
        "options": ["ln(x)", "x", "x^2/2", "1/(2x)"],
        "solution": "(1/x) का समाकलन ln(x) है।",
        "correct_option": 1
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "त्रिभुज में कोणों का योग कितना होता है?",
        "options": ["90 डिग्री", "180 डिग्री", "270 डिग्री", "360 डिग्री"],
        "solution": "त्रिभुज में कोणों का योग 180 डिग्री होता है।",
        "correct_option": 2
    },
    {
        "exam": exams[26],
        "time": 1.5,
        "language": "Hindi",
        "text": "x के लिए हल करें: (2x + 3 = 7)",
        "options": ["1", "2", "3", "4"],
        "solution": "(2x + 3 = 7) के लिए हल x = 2 है।",
        "correct_option": 2
    },
    {
        "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the derivative of (e^x)?",
        "options": ["1", "e^x", "x", "e"],
        "solution": "The derivative of (e^x) is (e^x).",
        "correct_option": 2
    },
    {
        "exam": exams[27],
        "time": 1.5,
        "language": "Hindi",
        "text": "समीकरण (2x - 5 = 9) का हल क्या है?",
        "options": ["2", "4", "7", "5"],
        "solution": "समीकरण (2x - 5 = 9) का हल (x = 7) है।",
        "correct_option": 3
    },
     {
        "exam": exams[27],
        "time": 1.5,
        "language": "Hindi",
        "text": "यदि A = {1, 2, 3}, तो A का पावर सेट क्या है?",
        "options": ["{{1}, {2}, {3}}", "{{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}", "{{1}, {2}, {3}, {1,2,3}}", "{{1,2}, {2,3}, {1,3}}"],
        "solution": "A का पावर सेट {{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}} है।",
        "correct_option": 2
    },
    {
        "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the solution to the equation (2x - 5 = 9)?",
        "options": ["2", "4", "7", "5"],
        "solution": "The solution to the equation (2x - 5 = 9) is (x = 7).",
        "correct_option": 3
    },
    {
        "exam": exams[27],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of (log(1))?",
        "options": ["0", "1", "10", "Infinity"],
        "solution": "The value of (log(1)) is 0.",
        "correct_option": 1
    },
    {
        "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(e^x) का अवकलन क्या है?",
        "options": ["1", "e^x", "x", "e"],
        "solution": "(e^x) का अवकलन (e^x) है।",
        "correct_option": 2
    },
    {
        "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(sin(90^circ)) का मान क्या है?",
        "options": ["0", "1", "-1", "0.5"],
        "solution": "(sin(90^circ)) का मान 1 है।",
        "correct_option": 2
    },
    {
        "exam": exams[28],
        "time": 1.5,
        "language": "English",
        "text": "What is the value of (sin(90^circ))?",
        "options": ["0", "1", "-1", "0.5"],
        "solution": "The value of (sin(90^circ)) is 1.",
        "correct_option": 2
    },
    
    {
        "exam": exams[28],
        "time": 1.5,
        "language": "Hindi",
        "text": "(log(1)) का मान क्या है?",
        "options": ["0", "1", "10", "अनंत"],
        "solution": "(log(1)) का मान 0 है।",
        "correct_option": 1
    },
    {
        "exam": exams[28],
        "time": 1.5,
        "language": "English",
        "text": "If A = {1, 2, 3}, what is the power set of A?",
        "options": ["{{1}, {2}, {3}}", "{{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}", "{{1}, {2}, {3}, {1,2,3}}", "{{1,2}, {2,3}, {1,3}}"],
        "solution": "The power set of A is {{}, {1}, {2}, {3}, {1,2}, {1,3}, {2,3}, {1,2,3}}.",
        "correct_option": 2
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the unit of length?",
        "options": ["Meter", "Kilogram", "Newton", "Second"],
        "solution": "The unit of length is Meter.",
        "correct_option": 1
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the state of water at 0°C?",
        "options": ["Solid", "Liquid", "Gas", "Plasma"],
        "solution": "Water is in solid state at 0°C (Ice).",
        "correct_option": 1
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "Which of the following is not a natural source of light?",
        "options": ["Sun", "Moon", "Star", "Lamp"],
        "solution": "Lamp is not a natural source of light.",
        "correct_option": 4
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What is the force that opposes motion between two surfaces?",
        "options": ["Magnetism", "Gravity", "Friction", "Electricity"],
        "solution": "The force that opposes motion between two surfaces is Friction.",
        "correct_option": 3
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "English",
        "text": "What do you call the process of water changing from liquid to gas?",
        "options": ["Freezing", "Evaporation", "Condensation", "Melting"],
        "solution": "The process of water changing from liquid to gas is Evaporation.",
        "correct_option": 2
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "लंबाई की इकाई क्या है?",
        "options": ["मीटर", "किलोग्राम", "न्यूटन", "सेकंड"],
        "solution": "लंबाई की इकाई मीटर है।",
        "correct_option": 1
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "0°C पर पानी की अवस्था क्या होती है?",
        "options": ["ठोस", "तरल", "गैस", "प्लाज्मा"],
        "solution": "0°C पर पानी ठोस अवस्था में होता है (बर्फ)।",
        "correct_option": 1
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "निम्नलिखित में से कौन सा प्राकृतिक प्रकाश का स्रोत नहीं है?",
        "options": ["सूरज", "चाँद", "तारा", "दीपक"],
        "solution": "दीपक प्राकृतिक प्रकाश का स्रोत नहीं है।",
        "correct_option": 4
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "दो सतहों के बीच गति का विरोध करने वाली शक्ति क्या है?",
        "options": ["चुम्बकत्व", "गुरुत्वाकर्षण", "घर्षण", "विद्युत"],
        "solution": "दो सतहों के बीच गति का विरोध करने वाली शक्ति घर्षण है।",
        "correct_option": 3
    },
    {
        "exam": exams[29],
        "time": 1.5,
        "language": "Hindi",
        "text": "पानी का तरल से गैस में बदलने की प्रक्रिया को क्या कहते हैं?",
        "options": ["जमना", "वाष्पीकरण", "संघनन", "पिघलना"],
        "solution": "पानी का तरल से गैस में बदलने की प्रक्रिया वाष्पीकरण कहलाती है।",
        "correct_option": 2
    }
    

        ]

        question_added_count = 0
        for question in questions_data:
            existing_question = Question.objects.filter(
                exam=question["exam"],
                text=question["text"]
            ).first()

            if not existing_question:
                Question.objects.create(
                    exam=question["exam"],
                    language=question["language"],
                    text=question["text"],
                    options=question["options"],
                    solution=question["solution"],
                    correct_option=question["correct_option"]
                )
                question_added_count += 1

        response_data["questions"] = {
            "message": f'{question_added_count} questions added successfully.',
            "added_count": question_added_count
        }

    return JsonResponse(response_data)

class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Report.objects.all()
    serializer_class = ReportSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Report)
        return Response({"Count": count})

    def create(self, request, *args, **kwargs):
        return Response({"error": "POST method is not allow."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Report deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class SelfReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    lookup_field = 'id'

    def list(self, request, *args, **kwargs):
        return Response({"error": "GET method is not allowed on this endpoint."},status=status.HTTP_405_METHOD_NOT_ALLOWED)


    def create(self, request):
        user = request.user
        question_id = request.data.get('question')
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"error": "Question not found."}, status=status.HTTP_400_BAD_REQUEST)
        if Report.objects.filter(user=user, question=question).exists():
            return Response({"error": "You have already submitted a report for this question."}, status=status.HTTP_400_BAD_REQUEST)
        data = request.data.copy()

        if 'issue_type' in data and isinstance(data['issue_type'], str):
            data['issue_type'] = [data['issue_type']]  

        data['user'] = user.id
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            serializer.save(user=user, question=question)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasskeyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Passkey.objects.all()
    serializer_class = PasskeySerializer
 
 
class GeneratePasskeyView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        exam_id = request.data.get('exam_id')
        center_id = request.data.get('center_id')

        try:
            center = ExamCenter.objects.get(id=center_id)
        except ExamCenter.DoesNotExist:
            return Response({"error": "Please choose a exam center first."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User with this Id does not exist."}, status=status.HTTP_400_BAD_REQUEST)
 
        try:
            exam = Exam.objects.get(id=exam_id)
            if exam.level.id == 1 or exam.level.id == 2 and exam.type == 'online':
                return Response({"error": "The provided exam is not valid exam"}, status=status.HTTP_400_BAD_REQUEST)
        except Exam.DoesNotExist:
            return Response({"error": "Exam with this ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
        
        existing_passkey = Passkey.objects.filter(user=user, exam=exam).first()
        if existing_passkey:
            return Response({"error": "A passkey has already been generated for this exam."},
                status=status.HTTP_400_BAD_REQUEST)

        level_1_qualified = TeacherExamResult.objects.filter(user=user, exam__level_id=1, exam__type="online", isqualified=True).exists()
        level_2_online_qualified = TeacherExamResult.objects.filter(user=user, exam__level_id=2, exam__type="online", isqualified=True).exists()

        if not (level_1_qualified and level_2_online_qualified):
            return Response({"error": "User must qualify both Level 1 and Level 2 online exams to access Level 2 offline exams."}, status=status.HTTP_400_BAD_REQUEST)
        
        passkey = random.randint(1000, 9999)

        passkey_obj = Passkey.objects.create(
            user=user,
            exam=exam,
            code=str(passkey),
            center=center,
            status=False,
        )
        exam_serializer = ExamSerializer(exam)
        center_serializer = ExamCenterSerializer(center)
        return Response({"message": "Passkey generated successfully.",
            "center":center_serializer.data,
            "exam": exam_serializer.data
            },
        status=status.HTTP_200_OK)    
 
class ApprovePasscodeView(APIView):
    #permission_classes = [IsAdminPermission]  # Only accessible by admin users
 
    def post(self, request):
        user_id = request.data.get('user_id')
        exam_id = request.data.get('exam_id')
 
        try:
            passkey_obj = Passkey.objects.get(user_id=user_id, exam_id=exam_id)
        except Passkey.DoesNotExist:
            return Response({"error": "Passkey not found."}, status=status.HTTP_404_NOT_FOUND)
 
        # Approve the passkey
        passkey_obj.status = True
        passkey_obj.save()
 
        return Response({"message": "Passcode approved successfully."}, status=status.HTTP_200_OK)
 
class VerifyPasscodeView(APIView):
    def post(self, request):
        user_id = request.data.get('user_id')
        exam_id = request.data.get('exam_id')
        entered_passcode = request.data.get('passcode')
        if not user_id or not exam_id or not entered_passcode:
            return Response(
                {"error": "Missing required fields: user_id, exam_id, or passcode."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        passkey_status = Passkey.objects.filter(user=user_id,exam=exam_id,code=entered_passcode, status=False)
        if passkey_status.exists():
            return Response({"error":"Passcode verification is allowed only if the passcode is approved by the exam center."})
        try:
            passkey_obj = Passkey.objects.get(user_id=user_id, exam_id=exam_id, code=entered_passcode)
        except Passkey.DoesNotExist:
            return Response({"error": "Invalid passcode or exam."}, status=status.HTTP_400_BAD_REQUEST)

        passkey_obj.status = False
        passkey_obj.save()
        exam = passkey_obj.exam
        exam_serializer = ExamSerializer(exam)
        if passkey_obj.status==False:
            passkey_obj.delete()
        # result = TeacherExamResult.objects.filter(user=user_id, exam=exam_id).first()
        # if result:
        #     passkey_obj.delete()
        return Response(
            {
                "message": "Passcode verified successfully.",
                "offline_exam" : exam_serializer.data
            },
            status=status.HTTP_200_OK,
        )
class InterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Interview)
        return Response({"Count": count})

    def create(self, request, *args, **kwargs):
        return Response({"error": "POST method is not allow."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    def send_interview_link(self, interview, recipient_email):
        subject = f"Your Interview for {interview.subject} {interview.class_category} has been scheduled!"
        
        message = format_html("""
            <html>
                <body>
                    <p>Dear {user},</p>
                    <p>Your interview for <strong>{subject} {class_category}</strong> has been scheduled.</p>
                    <p><strong>Interview Time:</strong> {time}</p>
                    <p><strong>Interview Link:</strong> <a href="{link}">Join your interview here</a></p>
                    <p>Please make sure to join at the scheduled time.</p>
                    <p>Best regards,<br>The Interview Team</p>
                </body>
            </html>
        """, user=interview.user.username, subject=interview.subject, class_category=interview.class_category, time=interview.time, link=interview.link)

        # Send the email using HTML format
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            html_message=message  
        )

    def update(self, request, *args, **kwargs):
        interview = self.get_object()
        serializer = self.get_serializer(interview, data=request.data, partial=True)

        if serializer.is_valid():
            updated_interview = serializer.save()
            self.send_interview_link(updated_interview, updated_interview.user.email)
            return Response({
                "message": "Interview updated successfully and email with the link has been sent.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class SelfInterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Interview.objects.all()
    serializer_class = InterviewSerializer
    lookup_field = 'id'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            time = serializer.validated_data.get('time')
            subject = serializer.validated_data.get('subject') 
            class_category = serializer.validated_data.get('class_category')
            if isinstance(subject, Subject):  
                subject = subject.id  
            if isinstance(class_category, ClassCategory):
                class_category = class_category.id
            if Interview.objects.filter(user=user, status=False).exists():
                return Response({"error": "You already have a pending interview. Please complete it before scheduling another."}, status=status.HTTP_400_BAD_REQUEST)
            if Interview.objects.filter(user=user, time=time, subject=subject, class_category=class_category).exists():
                return Response({"error": "Interview with the same details already exists."}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Validation errors:", serializer.errors) 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class ExamCenterViewSets(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ExamCenter.objects.all()
    serializer_class = ExamCenterSerializer
    
    # Override the default create method for ExamCenter creation
    def create(self, request, *args, **kwargs):
        # Handle user creation first
        user_serializer = CenterUserSerializer(data=request.data.get("user"))
        if not user_serializer.is_valid():
            return Response({
                "error": user_serializer.errors,
                "message": "User creation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save the user
        user_serializer.save()
        user_email = user_serializer.data["email"]
        user = CustomUser.objects.get(email=user_email)

        # Handle ExamCenter creation
        exam_center_data = request.data.get("exam_center")
        if not exam_center_data:
            return Response({
                "error": "Exam center data not provided",
                "message": "Please include exam center details"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Assign the user to the exam center data
        exam_center_data["user"] = user.id
        exam_center_serializer = ExamCenterSerializer(data=exam_center_data)

        if not exam_center_serializer.is_valid():
            return Response({
                "error": exam_center_serializer.errors,
                "message": "Exam center creation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save the exam center
        exam_center_serializer.save()

        return Response({
            "user": user_serializer.data,
            "exam_center": exam_center_serializer.data,
            "message": "User and Exam Center created successfully"
        }, status=status.HTTP_201_CREATED)

    def put(self, request, *args, **kwargs):
        examcenter_id = request.data.get('id', None)
        if examcenter_id:
            try:
                examcenter_instance = ExamCenter.objects.get(id=examcenter_id)
                serializer = ExamSerializer(examcenter_instance, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Exam.DoesNotExist:
                return create_object(ExamSerializer, request.data, Exam)
        else:
            return Response({"error": "ID field is required for PUT"}, status=status.HTTP_400_BAD_REQUEST)
        
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
class SelfExamCenterViewSets(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ExamCenter.objects.all()
    serializer_class = ExamCenterSerializer
    
    @action(detail=False, methods=['get'])
    def teachers(self, request):
        user = request.user
        try:
            exam_center = ExamCenter.objects.get(user=user)
        except ExamCenter.DoesNotExist:
            return Response({"error": "ExamCenter not found for the user."}, status=404)
        # Extract query parameters
        user_id = request.query_params.get('user_id', None)
        status = request.query_params.get('status', None)
        date = request.query_params.get('date', None)
        # Build filters
        filters = Q(center=exam_center)
        if user_id:
            filters &= Q(user_id=user_id)
        if status is not None:
            status = status.lower()
            if status in ['true', '1', 'yes']:
                filters &= Q(status=True)
        if date:
            try:
                date_obj = datetime.strptime(date, '%Y-%m-%d').date()
                filters &= Q(created_at__date=date_obj)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)
        # Filter Passkey objects
        teachers = Passkey.objects.filter(filters).select_related('user')

        serializer = PasskeySerializer(teachers, many=True) 
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        passkey_id = kwargs.get('pk')
        if passkey_id:
            try:
                passkey_instance = Passkey.objects.get(id=passkey_id)
                allowed_fields = {'status'}
                updating_field = set(request.data.keys())
                if not updating_field.issubset(allowed_fields):
                    return Response({"error": "You can only update the 'status' field."}, status=status.HTTP_400_BAD_REQUEST)
                serializer = PasskeySerializer(passkey_instance, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Passkey.DoesNotExist:
                return create_object(PasskeySerializer, request.data, Passkey)
        else:
            return Response({"error": "ID field is required for PUT"}, status=status.HTTP_400_BAD_REQUEST)

def insert_data_examcenter(request):
    users_data = [
        {"username": "komal", "email": "ks@gmail.com", "password": "12345",  "Fname": "Komal", "Lname": "Raj"},
        {"username": "rahul", "email": "rahul@gmail.com", "password": "12345","Fname": "Rahul", "Lname": "Sharma"},
        {"username": "priya", "email": "priya@gmail.com", "password": "12345", "Fname": "Priya", "Lname": "Verma"},
        {"username": "aman", "email": "aman@gmail.com", "password": "12345", "Fname": "Aman", "Lname": "Kumar"},
        {"username": "neha", "email": "neha@gmail.com", "password": "12345",  "Fname": "Neha", "Lname": "Singh"},
    ]

    centers_data = [
        {"center_name": "Alpha Exam Center", "pincode": "111111", "state": "State A", "city": "City A", "area": "Area A"},
        {"center_name": "Beta Exam Center", "pincode": "222222", "state": "State B", "city": "City B", "area": "Area B"},
        {"center_name": "Gamma Exam Center", "pincode": "333333", "state": "State C", "city": "City C", "area": "Area C"},
        {"center_name": "Delta Exam Center", "pincode": "444444", "state": "State D", "city": "City D", "area": "Area D"},
        {"center_name": "Epsilon Exam Center", "pincode": "555555", "state": "State E", "city": "City E", "area": "Area E"},
    ]

    response_data = {"users_added": 0, "centers_added": 0}

    for user in users_data:
        if not CustomUser.objects.filter(username=user["username"]).exists():
            CustomUser.objects.create(
                username=user["username"],
                email=user["email"],
                password=make_password(user["password"]), 
                is_centeruser = True,
                Fname=user["Fname"],
                Lname=user["Lname"]
            )
            response_data["users_added"] += 1

    users = list(CustomUser.objects.all())

    for center in centers_data:
        if not ExamCenter.objects.filter(center_name=center["center_name"]).exists():
            assigned_user = random.choice(users) if users else None  
            ExamCenter.objects.create(
                user=assigned_user,
                center_name=center["center_name"],
                pincode=center["pincode"],
                state=center["state"],
                city=center["city"],
                area=center["area"],
                status = True,
            )
            response_data["centers_added"] += 1

    return JsonResponse({
        "message": "Seeding completed",
        "users_added": response_data["users_added"],
        "centers_added": response_data["centers_added"]
    })

class TeacherReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherReportSerializer
    queryset = CustomUser.objects.all()
    def get(self, request):
        user = self.request.user
        try:
            user_data = CustomUser.objects.get(id=user.id)

            qualifications = user_data.teacherqualification.all()
            experiences = user_data.teacherexperience.all()
            skills = user_data.teacherskills.all()
            exam_results = user_data.teacherexamresult.filter(is_qualified=True)
            preferences = user_data.teacherpreference.all()

            rate = 0

            qualification_weight = 0.3
            experience_weight = 0.4
            result_weight = 0.2
            preference_weight = 0.1

            high_qualification = max(q.qualification for q in qualifications) if qualifications else 0
            rate += high_qualification * qualification_weight

            total_experience = sum(exp.end_date.year - exp.start_date.year for exp in experiences) if experiences else 0
            rate += total_experience * experience_weight

            qualified_results_count = exam_results.count()
            rate += qualified_results_count * result_weight

            preferred_categories = preferences.aggregate(total_categories=Count('classcategory'))
            rate += preferred_categories['total_categories'] * preference_weight

            report = {
                "teacher_id": user.id,
                "name": f"{user_data.Fname} {user_data.Lname}",
                "email": user_data.email,
                "rate": rate,
                "details": {
                    "qualifications": [q.name for q in qualifications],
                    "experiences": [f"{exp.institution} ({exp.start_date} - {exp.end_date})" for exp in experiences],
                    "qualified_exam_results": qualified_results_count,
                    "preferences": [pref.classcategory.name for pref in preferences],
                }
            }

            return Response(report)

        except CustomUser.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

def insert_data_teachers(request):
    users_data = [
        {"username": "john", "email": "john@gmail.com", "password": "12345", "Fname": "John", "Lname": "Doe"},
        {"username": "alice", "email": "alice@gmail.com", "password": "12345", "Fname": "Alice", "Lname": "Brown"},
        {"username": "mark", "email": "mark@gmail.com", "password": "12345", "Fname": "Mark", "Lname": "Smith"},
    ]

    skills_data = ["Python", "Java", "Mathematics", "Physics", "History"]    
    addresses_data = [
        {"city": "New York", "state": "NY", "pincode": "10001", "area": "Downtown"},
        {"city": "Los Angeles", "state": "CA", "pincode": "90001", "area": "Uptown"},
    ]
    experiences_data = [
        {"institution": "XYZ School", "role": "Teacher", "start_date": "2015-06-01", "end_date": "2018-05-31", "description": "Taught various subjects", "achievements": "Awarded Best Teacher 2017"},
        {"institution": "ABC College", "role": "Lecturer", "start_date": "2019-08-01", "end_date": "Present", "description": "Lecturing Mathematics", "achievements": "Published research paper"}
    ]
    qualifications_data = ["B.Ed", "M.Ed", "PhD"]
    exam_results_data = [
        {"exam_name": "NET", "score": 85},
        {"exam_name": "TET", "score": 90},
    ]
    
    response_data = {"users_added": 0, "skills_added": 0, "subjects_added": 0, "classes_added": 0, 
                     "addresses_added": 0, "results_added": 0, "job_types_added": 0, 
                     "experiences_added": 0, "qualifications_added": 0, "preferences_added": 0}
    
    for user in users_data:
        if not CustomUser.objects.filter(username=user["username"]).exists():
            CustomUser.objects.create(
                username=user["username"],
                email=user["email"],
                password=make_password(user["password"]), 
                is_teacher=True,
                Fname=user["Fname"],
                Lname=user["Lname"]
            )
            response_data["users_added"] += 1
    users = list(CustomUser.objects.all())
    
    for skill_name in skills_data:
        skill_obj, created = Skill.objects.get_or_create(name=skill_name)
        for user in users:
            TeacherSkill.objects.create(user=user, skill=skill_obj)
            response_data["skills_added"] += 1
    
    for qualification_name in qualifications_data:
        qualification_obj, created = EducationalQualification.objects.get_or_create(name=qualification_name)
        for user in users:
            institution = f"{qualification_name} Institution"
            year_of_passing = random.randint(2000, 2024)
            grade_or_percentage = f"{random.randint(60, 100)}%"
            TeacherQualification.objects.create(
                user=user,
                qualification=qualification_obj,
                institution=institution,
                year_of_passing=year_of_passing,
                grade_or_percentage=grade_or_percentage
            )
            response_data["qualifications_added"] += 1
    
    for address in addresses_data:
        assigned_user = random.choice(users) if users else None
        if not assigned_user:
            continue  
        city = address.get("city", "")
        state = address.get("state", "")
        pincode = address.get("pincode", "")
        area = address.get("area", "")
        TeachersAddress.objects.create(
            user=assigned_user,
            address_type="current",  
            state="Bihar",
            division="Some Division",
            district="Some District",
            block="Some Block",
            village="Some Village",
            area="Some Area",
            pincode="123456" 
        )
        response_data["addresses_added"] += 1
        
    
    for experience_data in experiences_data:
        for user in users:
            role_obj, created = Role.objects.get_or_create(jobrole_name=experience_data["role"])  # Create or get the role
            start_date = timezone.datetime.strptime(experience_data["start_date"], "%Y-%m-%d").date()
            end_date = timezone.datetime.strptime(experience_data["end_date"], "%Y-%m-%d").date() if experience_data["end_date"] != "Present" else None
            
            TeacherExperiences.objects.create(
                user=user,
                institution=experience_data["institution"],
                role=role_obj,
                start_date=start_date,
                end_date=end_date,
                description=experience_data["description"],
                achievements=experience_data["achievements"]
            )
            response_data["experiences_added"] += 1
    
    for qualification_name in qualifications_data:
        assigned_user = random.choice(users) if users else None
        if assigned_user:
            qualification_obj, created = EducationalQualification.objects.get_or_create(name=qualification_name)
            TeacherQualification.objects.create(user=assigned_user, qualification=qualification_obj)
            response_data["qualifications_added"] += 1
    
    # Seed Preferences
    for user in users:
        job_roles = Role.objects.all()  # Fetch all roles
        class_categories = ClassCategory.objects.all()  # Fetch all class categories
        subjects = Subject.objects.all()  # Fetch all subjects
        job_types = TeacherJobType.objects.all()  # Fetch all job types
        
        preference = Preference.objects.create(user=user)
        
        preference.job_role.set(random.sample(list(job_roles), min(3, len(job_roles))))
        preference.class_category.set(random.sample(list(class_categories), min(2, len(class_categories)))) 
        preference.prefered_subject.set(random.sample(list(subjects), min(2, len(subjects))))
        preference.teacher_job_type.set(random.sample(list(job_types), min(2, len(job_types))))
        
        preference.save()
        response_data["preferences_added"] += 1
    
    return JsonResponse({
        "message": "Seeding completed",
        **response_data
    })
