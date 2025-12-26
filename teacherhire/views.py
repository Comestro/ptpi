from rest_framework import viewsets, permissions
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from teacherhire.models import *
from rest_framework.exceptions import NotFound
from teacherhire.serializers import *
from teacherhire.utils import calculate_profile_completed
from .authentication import ExpiringTokenAuthentication
from rest_framework.decorators import action
from .permissions import *
import random
import re
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings
import random
from django.utils.html import format_html
from django.core.cache import cache
import requests
import logging
from django.conf import settings
from fuzzywuzzy import process, fuzz
from django.db.models import Q
from datetime import date
from django.db.models import Count
from django.core.mail import send_mail
import string
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from googletrans import Translator
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError


class RecruiterView(APIView):
    permission_classes = [IsRecruiterUser]

    def get(self, request):
        return Response({"message": "You are a recruiter!"}, status=status.HTTP_200_OK)

class AdminView(APIView):
    permission_classes = [IsAdminUser]

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
    if serializer.is_valid(raise_exception=True):
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


# TeacerAddress GET ,CREATE ,DELETE
class TeachersAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeachersAddressSerializer
    queryset = TeachersAddress.objects.all().select_related('user')

    @action(detail=False, methods=['get'])
    def count(self, request):
        print(f"User: {request.user}")
        count = get_count(TeachersAddress)
        return Response({"count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "TeacherAddress deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return TeachersAddress.objects.filter(user_id=teacher_id)
        return TeachersAddress.objects.all()


class SingleTeachersAddressViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeachersAddressSerializer
    queryset = TeachersAddress.objects.all().select_related('user')
    
    def create(self, request, *args, **kwargs):
        print("Request data:", request.data)
        data = request.data.copy()

        if "data" in data and isinstance(data["data"], (dict, str)):
            import json
            try:
                nested = data["data"]
                if isinstance(nested, str):
                    nested = json.loads(nested)
                data.update(nested)
            except Exception:
                pass

        address_type = data.get('address_type')

        if not address_type or address_type not in ['current', 'permanent']:
            raise ValidationError({
                "address_type": ["Invalid or missing 'address_type'. Expected 'current' or 'permanent'."]
            })

        if TeachersAddress.objects.filter(address_type=address_type, user=request.user).exists():
            raise ValidationError({
                "address_type": [f"{address_type.capitalize()} address already exists for this user."]
            })

        data['user'] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

        

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        address_type = data.get('address_type')  

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
                return Response({"error": "Invalid language, please choose 'Hindi' or 'English'."},
                                status=status.HTTP_400_BAD_REQUEST)
            questions = questions.filter(language=language)

        # Serialize the filtered questions
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Level deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
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

    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return TeacherSkill.objects.filter(user_id=teacher_id)
        else:
            return TeacherSkill.objects.all()


class SingleTeacherSkillViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSkillSerializer
    lookup_field = 'id'

    def create_object(serializer_class, request_data, model_class):
        serializer = serializer_class(data=request_data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

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


class SubjectViewSet(viewsets.ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        return [IsAuthenticated(), IsAdminOrTeacher()]

    def get_authenticators(self):
        if self.request.method == 'GET':
            return []
        return [ExpiringTokenAuthentication()]

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Subject)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.exam_set.exists():
             return Response({"error": "Cannot delete subject because it has associated exams."}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "subject deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SelfViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.filter(id=user.id, is_teacher=True)
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


class TeacherViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherSerializer

    def get_queryset(self):
        return_all = self.request.query_params.get('all', None)
        queryset = CustomUser.objects.filter(is_teacher=True, is_staff=False)

        # Handle 'all' query parameter
        if return_all and return_all.lower() == 'true':
            return queryset.distinct()  
        # Filter by teacher name
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
            
            valid_qualifications = [
                'Matric', 'Intermediate', 'Bachelor', 'Master', 'phd',
                'post-doctorate', 'professional diploma', 'honorary doctorate'
            ]
            
            qualification_hierarchy = {
                'Matric': 1,
                'Intermediate': 2,
                'Bachelor': 3,
                'Master': 4,
                'phd': 5,
                'post-doctorate': 6,
                'professional diploma': 7,
                'honorary doctorate': 8
            }
            
            qualification_query = Q()
            matched_qualifications = []
            
            # Fuzzy match qualifications
            for qualification in teacher_qualifications:
                best_match = process.extractOne(qualification, valid_qualifications)
                if best_match and best_match[1] >= 80:  # Threshold for match confidence
                    matched_qualifications.append(best_match[0])
                else:
                    matched_qualifications.append(qualification)
            
            if len(matched_qualifications) == 1:
                # Single qualification
                qualification = matched_qualifications[0]
                if qualification == 'Matric':
                    # Exact match for Matric
                    qualification_query = Q(teacherqualifications__qualification__name__iexact='Matric')
                elif qualification in qualification_hierarchy:
                    # Include lower levels for other qualifications
                    max_level = qualification_hierarchy[qualification]
                    valid_quals = [
                        q for q, level in qualification_hierarchy.items() if level <= max_level
                    ]
                    for valid_q in valid_quals:
                        qualification_query |= Q(teacherqualifications__qualification__name__iexact=valid_q)
            else:
                # Multiple qualifications: Exact matches only
                for qualification in matched_qualifications:
                    qualification_query |= Q(teacherqualifications__qualification__name__iexact=qualification)
            
            queryset = queryset.filter(qualification_query)
        filters = {
            'state': self.request.query_params.get('state', []),
            'district': self.request.query_params.getlist('district', []),
            'division': self.request.query_params.get('division', []),
            'pincode': self.request.query_params.getlist('pincode', []),
            'block': self.request.query_params.getlist('block', []),
            'village': self.request.query_params.getlist('village', []),
            'experience': self.request.query_params.get('experience', None),
            'class_category': self.request.query_params.getlist('class_category', []),
            'subject': self.request.query_params.getlist('subject', []),
            'job_role': self.request.query_params.getlist('job_role', []),
            'teacher_job_type': self.request.query_params.getlist('teacher_job_type', []),
            'postOffice': self.request.query_params.get('postOffice', None),
        }

        # Handle post office filtering
        post_office_filter = filters.get('postOffice', None)
        if post_office_filter:
            pincodes = get_pincodes_by_post_office(post_office_filter)
            if pincodes:
                filters['pincode'] = pincodes

        # Experience filtering
        experience_filter = self.get_experience_filter(filters['experience'])
        if experience_filter:
            queryset = queryset.filter(experience_filter)

        # Dynamic filters for address fields
        for field in ['state', 'district', 'division', 'block', 'village']:
            queryset = self.filter_by_address_field(queryset, field, filters.get(field))

        # Apply other dynamic filters
        FILTERS_CONFIG = [
            ('job_role', 'preferences__job_role__jobrole_name'),
            ('class_category', 'preferences__class_category__name'),
            ('subject', 'preferences__prefered_subject__subject_name'),
            ('teacher_job_type', 'preferences__teacher_job_type__teacher_job_name'),
        ]

        for filter_key, field_path in FILTERS_CONFIG:
            filter_values = filters.get(filter_key, [])
            if filter_values:
                cleaned_values = [v.strip().lower() for v in filter_values]
                queryset = queryset.filter(self.build_or_query(cleaned_values, field_path))

        if filters['pincode']:
            pincodes = filters['pincode']
            queryset = queryset.filter(teachersaddress__pincode__in=pincodes)

        # Ensure distinct results
        queryset = queryset.distinct()
        return queryset

    def build_or_query(self, values, field_path):
        query = Q()
        for value in values:
            query |= Q(**{f"{field_path}__iexact": value})
        return query

    def filter_by_address_field(self, queryset, field, filter_value):
        if filter_value:
            q_objects = Q()
            for value in filter_value:
                value = value.strip()
                best_match = process.extractOne(value.lower(),
                                                queryset.values_list(f'teachersaddress__{field}', flat=True))
                if best_match and best_match[1] >= 70:
                    q_objects |= Q(**{f'teachersaddress__{field}__iexact': best_match[0]})
                else:
                    q_objects |= Q(**{f'teachersaddress__{field}__icontains': value})
            queryset = queryset.filter(q_objects)
        return queryset

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
    
    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        
        if not response.data:
            filter_messages = []
            filter_params = {
                'class_category': 'Class',
                'subject': 'Subject',
                'skill[]': 'Skill',
                'pincode': 'Pincode',
                'qualification[]': 'Qualification',
                'state': 'State',
                'district': 'District',
                'teacher_job_type[]': 'Job Type'
            }

            for param, label in filter_params.items():
                values = request.query_params.getlist(param) or request.query_params.get(param)
                if values:
                    if isinstance(values, list):
                        values_str = ", ".join([v.title() for v in values])
                    else:
                        values_str = values.title()
                    filter_messages.append(f"{label} - {values_str}")

            if filter_messages:
                message = "आपके चुने हुए विकल्पों के अनुसार यहां पर कोई शिक्षक उपलब्ध नहीं है कृपया दूसरी विकल्पों का चयन करें | According to the options you have selected, no teacher is available here. Please choose other options."
            else:
                message = "No teachers available"
            
            return Response(
                {"detail": message},
                status=status.HTTP_404_NOT_FOUND
            )

        return response
    

class RecruiterTeacherSearch(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRecruiterUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        queryset = CustomUser.objects.all()
        search_query = self.request.query_params.get('search', None)

        if search_query:
            search_query = search_query.strip()  
            name_parts = search_query.split()

            name_query = Q()
            if len(name_parts) >= 2:
                fname = name_parts[0]
                lname = name_parts[-1]
                name_query = Q(Fname__icontains=fname) & Q(Lname__icontains=lname)
            else:
                fname = name_parts[0]
                name_query = Q(Fname__icontains=fname) | Q(Lname__icontains=fname)

            search_conditions = (
                name_query |                
                Q(teacherqualifications__qualification__name__icontains=search_query) |
                Q(preferences__prefered_subject__subject_name__icontains=search_query) |
                Q(preferences__class_category__name__icontains=search_query) |
                Q(preferences__teacher_job_type__teacher_job_name__icontains=search_query)
            )

            queryset = queryset.filter(search_conditions).distinct()

        return queryset
class ClassCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ClassCategory.objects.all()
    serializer_class = ClassCategorySerializer

    

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(ClassCategory)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.subjects.exists():
            return Response({"error": "Cannot delete class category because it has associated subjects."}, status=status.HTTP_400_BAD_REQUEST)
        if instance.exam_set.exists():
             return Response({"error": "Cannot delete class category because it has associated exams."}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "ClassCategory deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class PublicClassCategoryViewSet(viewsets.ModelViewSet):
    queryset = ClassCategory.objects.all()
    serializer_class = ClassCategorySerializer

    def create(self, request):
        return create_object(ClassCategorySerializer, request.data, ClassCategory)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(ClassCategory)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.subjects.exists():
            return Response({"error": "Cannot delete class category because it has associated subjects."}, status=status.HTTP_400_BAD_REQUEST)
        if instance.exam_set.exists():
             return Response({"error": "Cannot delete class category because it has associated exams."}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "ClassCategory deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class ReasonViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Reason.objects.all()
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
   
    
    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return TeacherQualification.objects.filter(user_id=teacher_id)
        return TeacherQualification.objects.all()

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
        try:
            year_of_passing = int(data.get('year_of_passing'))
        except (ValueError, TypeError):
                raise DRFValidationError({"year_of_passing": ["Please enter a valid year."]})
        
        if not qualification or not data.get('year_of_passing'):
            errors = {}
            if not qualification:
                errors["qualification"] = ["This field is required."]
            if not data.get('year_of_passing'):
                errors["year_of_passing"] = ["This field is required."]
            raise DRFValidationError(errors)
        
        if not EducationalQualification.objects.filter(name=qualification).exists():
          raise DRFValidationError({"qualification": [f"Qualification '{qualification}' does not exist."]})
        

        if TeacherQualification.objects.filter(
              user=request.user,
               qualification__name=qualification,
               year_of_passing=year_of_passing
        ).exists():
           raise DRFValidationError({
               "non_field_errors": [f"A record with qualification '{qualification}' and year of passing '{year_of_passing}' already exists."]
          })

        user_qua = TeacherQualification.objects.filter(user=request.user)

        if qualification == "inter":
            matric = user_qua.filter(qualification__name="matric").first()
            if matric and (year_of_passing - matric.year_of_passing < 2):
               raise DRFValidationError({"non_field_errors": ["There must be at least a 2-year gap between matric and inter."]})  

        if qualification == "graduation":
            inter_record = user_qua.filter(qualification__name="inter").first()
            if inter_record and (year_of_passing - inter_record.year_of_passing < 3):
                raise DRFValidationError({"non_field_errors": ["There must be at least a 3-year gap between inter and graduation."]})
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
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({"error": "Please enter a search term."}, status=status.HTTP_400_BAD_REQUEST)
        suggestions = TeacherQualification.objects.filter(institution__icontains=query).values_list('institution',
                                                                                                    flat=True).distinct()
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

    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return TeacherExperiences.objects.filter(user_id=teacher_id)
        return TeacherExperiences.objects.all()

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
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response({"error": "Please enter a search term."}, status=status.HTTP_400_BAD_REQUEST)
        suggestions = TeacherExperiences.objects.filter(institution__icontains=query).values_list('institution',
                                                                                                  flat=True).distinct()
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

class ExamSetterQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_permissions(self):
        """Dynamically assign permissions based on user type"""
        if self.request.user.is_staff:
            return [IsAdminUser()]
        return [IsQuestionUser()]

    def create(self, request, *args, **kwargs):
        data = request.data
        exam_id = data.get("exam")

        if not exam_id:
            return Response({"error": "Exam ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_staff:  # Admin can create questions for any exam
            try:
                exam = Exam.objects.get(id=exam_id)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        else:  # Question setter can only create questions for their assigned exam
            assigned_user = AssignedQuestionUser.objects.filter(user=request.user).first()
            if not assigned_user:
                return Response({"error": "You are not assigned as a question user."}, status=status.HTTP_403_FORBIDDEN)

            try:
                exam = Exam.objects.get(pk=exam_id, assigneduser=assigned_user)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found or you do not have permission."}, 
                                status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            question_data = serializer.save()
            return Response({
                "message": "Question stored in English and Hindi",
                "english_data": question_data.get("english_data"),
                "hindi_data": question_data.get("hindi_data")
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            updated_instance = serializer.save()
            if updated_instance.exam:
                updated_instance.exam.status = False
                updated_instance.exam.save()
            english_data = QuestionSerializer(updated_instance).data
            if updated_instance.language == "Hindi":
                return Response({
                    "message": "Question updated successfully",
                    "hindi_data": QuestionSerializer(updated_instance).data  
                }, status=status.HTTP_200_OK)
            if updated_instance.exam.subject.subject_name == "English":
                return Response({
                    "message": "Question updated successfully",
                    "english_data": english_data
                }, status=status.HTTP_200_OK)
            hindi_data = None
            try:
                hindi_related_question = Question.objects.get(related_question=updated_instance)
                hindi_data = QuestionSerializer(hindi_related_question).data
            except Question.DoesNotExist:
                pass

            return Response({
                "message": "Question updated successfully",
                "english_data": english_data,
                "hindi_data": hindi_data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        exam = instance.exam
        if exam.status == True:
            return Response({"error": "Cannot delete question from an active exam."}, status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "Question deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = Question.objects.count()
        return Response({"Count": count})

    @action(detail=False, methods=['get'])
    def questions(self, request):
        exam_id = request.query_params.get('exam_id')
        language = request.query_params.get('language')
        questions = Question.objects.all()

        if exam_id:
            try:
                exam = Exam.objects.get(pk=exam_id)
                questions = questions.filter(exam=exam)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

        if language:
            questions = questions.filter(language=language)

        serialized_questions = QuestionSerializer(questions, many=True)
        return Response(serialized_questions.data, status=status.HTTP_200_OK)


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
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Role)
        return Response({"Count": count})

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Role deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class TeachersPreferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer


class PreferenceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Preference.objects.all()
    serializer_class = PreferenceSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        if Preference.objects.filter(user=request.user).exists():
            raise DRFValidationError({"preference": "Preference already exists."})

        if 'teacher_job_type' in data and isinstance(data['teacher_job_type'], str):
            data['teacher_job_type'] = [data['teacher_job_type']]

        serializer = self.get_serializer(data=data)
        if serializer.is_valid(raise_exception=True):
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user.id
        data['user'] = user

        profile = Preference.objects.filter(user=request.user).first()

        current_subjects = list(profile.prefered_subject.values_list('id', flat=True)) if profile else []
        current_class_categories = list(profile.class_category.values_list('id', flat=True)) if profile else []

        new_subjects = list(map(int, data.get("prefered_subject", [])))
        new_class_categories = list(map(int, data.get("class_category", [])))

        removed_subjects = set(current_subjects) - set(new_subjects)
        removed_class_categories = set(current_class_categories) - set(new_class_categories)

        # Check if any removed subject OR class category has attempted exams
        if TeacherExamResult.objects.filter(
                user=user,
                has_exam_attempt=True
        ).filter(Q(exam__subject_id__in=removed_subjects) | Q(
            exam__class_category_id__in=removed_class_categories)).exists():

            raise DRFValidationError({
                "teacherexamresult": "You cannot remove an attempted subject or class category, only add new ones."
            })

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
        try:
            return Preference.objects.filter(user=self.request.user).first()
        except Preference.DoesNotExist:
            raise NotFound({"detail": "Preference not found."})

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
        if serializer.is_valid(raise_exception=True):
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
        if serializer.is_valid(raise_exception=True):
            self.save(serializer)
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
        if serializer.is_valid(raise_exception=True):
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


class AllTeacherExamResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherExamResult.objects.all()
    serializer_class = TeacherExamResultSerializer

    def get_queryset(self):
        teacher_id = self.request.query_params.get('teacher_id')
        if teacher_id:
            return TeacherExamResult.objects.filter(user=teacher_id)
        return TeacherExamResult.objects.all()


class TeacherExamResultViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherExamResult.objects.all()
    serializer_class = TeacherExamResultSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        user = request.user.id
        data['user'] = user
        data['has_exam_attempt'] = True
        try:
            exam = Exam.objects.get(id=data['exam'])
        except Exam.DoesNotExist:
            return Response(
                {"error": "Invalid exam ID."},
                status=status.HTTP_400_BAD_REQUEST
        )

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get_queryset(self):
        isqualified = self.request.query_params.get('isqualified', None)
        level_code = self.request.query_params.get('level_code', None)
        if isqualified:
            return TeacherExamResult.objects.filter(user=self.request.user, isqualified=isqualified, exam__level__level_code=level_code)
        else:
            return TeacherExamResult.objects.filter(user=self.request.user)
    

class JobPreferenceLocationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = JobPreferenceLocation.objects.all()
    serializer_class = JobPreferenceLocationSerializer
    lookup_field = 'id'

    def create(self, request, *args, **kwargs):
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        user = self.request.user
        if user.is_teacher:
            return JobPreferenceLocation.objects.filter(user=user)
        return JobPreferenceLocation.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Job preference location deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)



class AllTeacherBasicProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllBasicProfileSerializer
    queryset = CustomUser.objects.filter(is_teacher=True, is_verified=True)


class AllRecruiterBasicProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllBasicProfileSerializer
    queryset = CustomUser.objects.filter(is_recruiter=True, is_verified=True)


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
        user = request.user
        data = request.data.copy()

        # Update first name & last name
        Fname = data.get("Fname")
        Lname = data.get("Lname")

        if Fname:
            user.Fname = Fname
        if Lname:
            user.Lname = Lname
        user.save()

        # Update profile fields
        profile = BasicProfile.objects.filter(user=user).first()
        if profile:
            serializer = self.get_serializer(profile, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                
                # Fetch updated user data
                user_data = {
                    "id": user.id,
                    "Fname": user.Fname,
                    "Lname": user.Lname,
                    "email": user.email,
                    "is_verified": user.is_verified
                }

                profile_data = serializer.data
                profile_data["user"] = user_data  # Embed user details properly

                return Response(
                    {
                        "detail": "User and profile updated successfully.",
                        "profile": profile_data
                    },
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

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
                return serializer.instance  
            # Option 2: Raise an error response if creation fails
            raise Response({"detail": "Profile not found and could not be created."},
                           status=status.HTTP_400_BAD_REQUEST)

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

        # if CustomUser.objects.filter(username=request.user.username).exists():
        #     return Response({"detail": "Customuser already exists."}, status=status.HTTP_400_BAD_REQUEST)

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
    # permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherJobType.objects.all()
    serializer_class = TeacherJobTypeSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAdminOrTeacher()]
        return []

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
        except BasicProfile.DoesNotExist:
            return Response(
                {"message": "Please complete your basic profile first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_preference = Preference.objects.filter(user=user).first()
        if user_preference is None:
            return Response(
                {"message": "Please complete your preference details first."},
                status=status.HTTP_400_BAD_REQUEST
            )

        qualified_exams = TeacherExamResult.objects.filter(user=user, isqualified=True)

        levels = []
        for subject in user_preference.prefered_subject.all():
            # for class_category in user_preference.class_category.all():
            unlocked_levels = ["Level 1"]

            has_level_1 = qualified_exams.filter(exam__level_id=1, exam__type="online",
                                                 exam__subject=subject,
                                                 exam__class_category=subject.class_category).exists()
            has_level_2_online = qualified_exams.filter(exam__level_id=2, exam__type="online",
                                                        exam__subject=subject,
                                                        exam__class_category=subject.class_category).exists()
            has_level_2_offline = qualified_exams.filter(exam__level_id=2, exam__type="offline",
                                                         exam__subject=subject,
                                                         exam__class_category=subject.class_category).exists()

            if has_level_1:
                unlocked_levels.append("Level 2 Online")
            if has_level_2_online:
                unlocked_levels.append("Level 2 Offline")
            if has_level_2_offline:
                unlocked_levels.append("Interview")

            levels.append({
                "subject_id": subject.id,
                "subject_name": subject.subject_name,
                "classcategory_id": subject.class_category.id,
                "classcategory_name": subject.class_category.name,
                "levels": unlocked_levels
            })

        return Response(levels, status=status.HTTP_200_OK)

    # def get(self, request, *args, **kwargs):
    #     user = request.user
    #     try:
    #         user_basic_profile = BasicProfile.objects.get(user=user)
    #     except BasicProfile.DoesNotExist:
    #         return Response(
    #             {"message": "Please complete your basic profile first."},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     user_qualification = TeacherQualification.objects.filter(user=user)
    #     if not user_qualification:
    #         return Response(
    #             {"message": "Please complete at least one qualification detail."},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )
    #     user_preference = Preference.objects.filter(user=user)

    #     if not user_preference.exists():
    #         return Response(
    #             {"message": "Please complete your preference details first."},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     # Get the first preference object
    #     user_preference = user_preference.first()

    #     if not user_preference.prefered_subject.exists() or not user_preference.class_category.exists():
    #         return Response(
    #             {"message": "Please select at least one subject and class category in your preferences."},
    #             status=status.HTTP_400_BAD_REQUEST
    #         )

    #     qualified_exams = TeacherExamResult.objects.filter(user=user, isqualified=True)

    #     levels = []
    #     for subject in user_preference.prefered_subject.all():
    #         for class_category in user_preference.class_category.all():
    #             unlocked_levels = ["Level 1"]

    #             has_level_1 = qualified_exams.filter(
    #                 exam__level_id=1, exam__type="online",
    #                 exam__subject=subject, exam__class_category=class_category
    #             ).exists()
    #             has_level_2_online = qualified_exams.filter(
    #                 exam__level_id=2, exam__type="online",
    #                 exam__subject=subject, exam__class_category=class_category
    #             ).exists()
    #             has_level_2_offline = qualified_exams.filter(
    #                 exam__level_id=2, exam__type="offline",
    #                 exam__subject=subject, exam__class_category=class_category
    #             ).exists()

    #             if has_level_1:
    #                 unlocked_levels.append("Level 2 Online")
    #             if has_level_2_online:
    #                 unlocked_levels.append("Level 2 Offline")
    #             if has_level_2_offline:
    #                 unlocked_levels.append("Interview")

    #             levels.append({
    #                 "subject_id": subject.id,
    #                 "subject_name": subject.subject_name,
    #                 "classcategory_id": class_category.id,
    #                 "classcategory_name": class_category.name,
    #                 "levels": unlocked_levels
    #             })

    #     return Response(levels, status=status.HTTP_200_OK)
from rest_framework.pagination import PageNumberPagination

class ExamPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

class ExamSetterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer
    pagination_class = ExamPagination

    def paginate_queryset(self, queryset):
        user = self.request.user
        # If searching, disable pagination to show all results
        if self.request.query_params.get('search', None):
            return None
            
        if user.is_staff:
            return super().paginate_queryset(queryset)
        return None

    def get_permissions(self):
        """Apply different permissions based on user type."""
        if self.request.user.is_staff:
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        else:
            self.permission_classes = [IsAuthenticated, IsQuestionUser]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action in ['list']:
            return ExamSetterSerializer
        return ExamSerializer

    def get_queryset(self):
        """Admins see all exams; assigned users see only their own."""
        user = self.request.user
        search_query = self.request.query_params.get('search', None)
        
        if user.is_staff:
            exams = Exam.objects.all()
        else:
            assigned_user = AssignedQuestionUser.objects.get(user=user)
            exams = Exam.objects.filter(assigneduser=assigned_user)
            
        if search_query:
            # When searching, we want to search across all relevant fields
            exams = exams.filter(
                Q(name__icontains=search_query) |
                Q(subject__subject_name__icontains=search_query) |
                Q(class_category__name__icontains=search_query) |
                Q(level__name__icontains=search_query)
            )
            
        return exams.order_by('level__level_code', 'created_at')

    def create(self, request):
        """Admins can create any exam; assigned users are restricted."""
        user = request.user
        print(user)
        subject = request.data.get('subject')
        if not user.is_staff:
            assigned_user = AssignedQuestionUser.objects.filter(user=user, subject=subject).first()
            print(assigned_user)
            if not assigned_user:
                return Response({"error": "You are not assigned to this subject."}, status=status.HTTP_403_FORBIDDEN)
            request.data["assigneduser"] = assigned_user.id
            request.data["status"] = False
        else:
            request.data["status"] = True

        serializer = ExamSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        user = request.user
        exam = get_object_or_404(Exam, id=kwargs.get('pk'))

        if not user.is_staff and exam.assigneduser.user != user:
            return Response({"error": "You do not have permission to update this exam."}, status=status.HTTP_403_FORBIDDEN)

        new_status = request.data.get('status')
        if new_status == True:
            total_questions = exam.total_questions
            actual_count = exam.questions.count()  
            if actual_count < total_questions:
                return Response({
                    "error": f"Cannot activate this exam. Total questions required: {total_questions}, current: {actual_count}"
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = ExamSerializer(exam, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Admins can delete any exam; assigned users can delete only their own."""
        user = request.user
        instance = get_object_or_404(Exam, id=kwargs.get('pk'))
        exam =  Exam.objects.get(id=instance.id)
        if not user.is_staff and exam.assigneduser.user != user:
            return Response({"error": "You do not have permission to delete this exam."}, status=status.HTTP_403_FORBIDDEN)
        questions = exam.questions.all().count()
        if questions == 0:
            instance.delete()
        else:
            return Response({"error": "Please delete the associated questions first."}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "Exam deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get total exam count."""
        count = Exam.objects.count()
        return Response({"Count": count})

    @action(detail=False, methods=['get'])
    def exams(self, request):
        """Filter exams based on class category, subject, or level."""
        level_id = request.query_params.get('level_id')
        class_category_id = request.query_params.get('class_category_id')
        subject_id = request.query_params.get('subject_id')

        exams = Exam.objects.all()

        if class_category_id:
            class_category = ClassCategory.objects.filter(pk=class_category_id).first()
            if not class_category:
                return Response({"message": "Invalid class category."}, status=status.HTTP_400_BAD_REQUEST)
            exams = exams.filter(class_category=class_category)

        if subject_id:
            subject = Subject.objects.filter(pk=subject_id).first()
            if not subject:
                return Response({"message": "Invalid subject."}, status=status.HTTP_400_BAD_REQUEST)
            exams = exams.filter(subject=subject)

        if level_id:
            try:
                level = Level.objects.get(pk=level_id)
                exams = exams.filter(level=level)
            except Level.DoesNotExist:
                return Response({"error": "Level not found."}, status=status.HTTP_404_NOT_FOUND)
            
        page = self.paginate_queryset(exams)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SelfExamViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.filter(status=True)
    serializer_class = ExamSerializer

    
    def retrieve(self, request, *args, **kwargs):
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
            user_preference = Preference.objects.filter(user=user).first()
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
        exams = Exam.objects.filter(status=True)

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

        teacher_subject = Subject.objects.filter(preference__user=user, id=subject_id, class_category_id=class_category_id).first()
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
            exam__class_category_id=class_category_id, exam__level__name="1st Level"
        ).exists()

        online_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='online', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level__name="2nd Level Online"
        ).exists()

        offline_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='offline', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level__name="2nd Level Offline"
        ).exists()
        
        # Filter exams based on qualifications
        if not qualified_level_1:
            exams = exams.filter(level__name="1st Level") 
        elif qualified_level_1 and not online_qualified_level_2:
            exams = exams.filter(level__name__in=["1st Level", "2nd Level Online"], type='online')  
        elif online_qualified_level_2 and not offline_qualified_level_2:
            exams = exams.filter(level__name__in=["1st Level", "2nd Level Online", "2nd Level Offline"])  

        unqualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=False).values_list('exam_id', flat=True)
        exams = exams.exclude(id__in=unqualified_exam_ids)

        qualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=True).values_list('exam_id', flat=True)
        exams = exams.exclude(id__in=qualified_exam_ids)

        exam_set = exams.order_by('created_at')  

        level_1_exam = exam_set.filter(level__name="1st Level").first()
        level_2_online_exam = exam_set.filter(level__name="2nd Level Online", type='online').first()
        level_2_offline_exam = exam_set.filter(level__name="2nd Level Offline", type='offline').first()
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
        response_data = {
            "exams": serializer.data
        }

        if online_qualified_level_2:
            qualified_exam = TeacherExamResult.objects.filter(user=user, isqualified=True, exam__level__level_code=2.0,exam__subject_id=subject_id,
                exam__class_category_id=class_category_id, exam__type='online').first()
            if not qualified_exam:
                return Response({"error": "No valid exam found for the 2nd Level Online."}, status=status.HTTP_400_BAD_REQUEST)

            pending_interview = Interview.objects.filter(user=user,subject=qualified_exam.exam.subject,class_category=qualified_exam.exam.class_category_id).exclude(status__in=['fulfilled', 'rejected']).first()

            if pending_interview:
                response_data["interview_details"] = {
                    "message": "You already have an interview in progress. Please complete it before scheduling another.",
                    "interview": InterviewSerializer(pending_interview).data
                }
            else:
                # Safe to create new interview
                interview = Interview.objects.create(
                    user=user,
                    subject=qualified_exam.exam.subject,
                    level=qualified_exam.exam.level,
                                       class_category=qualified_exam.exam.class_category
                )

                if interview:
                    interview_serializer = InterviewSerializer(interview)
                    response_data["interview_details"] = interview_serializer.data
                else:
                    response_data["interview_details"] = f"Congratulations! You are eligible for an interview for {qualified_exam.subject.name} - {qualified_exam.class_category.name}. No interview scheduled yet."

        return Response(response_data, status=status.HTTP_200_OK)
    
class ExamCard(viewsets.ModelViewSet):
    permissions_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.all()
    serializer_class = ExamDetailSerializer

    def retrieve(self, request, *args, **kwargs):
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
    def exam(self, request):
        user = request.user
        subject_id = request.query_params.get('subject_id')
        class_category_id = request.query_params.get('class_category_id')
        level_id = request.query_params.get('level_id')
        try:
            user_preference = Preference.objects.filter(user=user).first()
        except Preference.DoesNotExist:
            return Response(
                {"message": "Please complete your preference details first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not subject_id or not class_category_id or not level_id:
            return Response({"error": "Subject, Class Category, and Level are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            class_category_id = ClassCategory.objects.filter(preference__user=user, pk=class_category_id).first()
        except ClassCategory.DoesNotExist:
            return Response({"error": "Class Category is not valid choose your preference class category."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            subject_id = Subject.objects.filter(preference__user=user, pk=subject_id).first()
        except Subject.DoesNotExist:
            return Response({"error": "Subject is not valid choose your preference subject."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            level = Level.objects.get(pk=level_id)
        except Level.DoesNotExist:
            return Response({"error": "Level not found."}, status=status.HTTP_404_NOT_FOUND)
        
        last_attempt = TeacherExamResult.objects.filter(
            user=user, exam__subject_id=subject_id,
            exam__class_category_id=class_category_id, exam__level=level_id
        ).last()
        # print("last_attempt", last_attempt.attempt, last_attempt.exam.level.level_code, last_attempt.exam)
        if last_attempt and last_attempt.attempt>=5:
            return Response({"error": f"You have reached the maximum number of attempts for this exam level {last_attempt.exam.level.level_code}",}, status=status.HTTP_400_BAD_REQUEST)
        
        qualified_level_1 = TeacherExamResult.objects.filter(
            user=user, isqualified=True, exam__subject_id=subject_id,
            exam__class_category_id=class_category_id, exam__level__level_code=1.0
        ).exists()

        online_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='online', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level__level_code=2.0
        ).exists()

        offline_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='offline', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level__level_code=2.5
        ).exists()

        if level.level_code == 1.0:
            exam = Exam.objects.filter(subject_id=subject_id, class_category_id=class_category_id, level__level_code=level.level_code, status=True)
        elif level.level_code == 2.0:
            if not qualified_level_1:
                return Response({"error": "You must qualify Level 1 exam to access Level 2."}, status=status.HTTP_400_BAD_REQUEST)
            exam = Exam.objects.filter(subject_id=subject_id, class_category_id=class_category_id, level__level_code=level.level_code, status=True)
        elif level.level_code == 2.5:
            if not qualified_level_1 or not online_qualified_level_2:
                return Response({"error": "You must qualify Level 1 and Level 2 online exam to access Level 2 offline."}, status=status.HTTP_400_BAD_REQUEST)
            exam = Exam.objects.filter(subject_id=subject_id, class_category_id=class_category_id, level__level_code=level.level_code, status=True)
        else:
            return Response({"error": "Invalid level."}, status=status.HTTP_400_BAD_REQUEST)

        exam = Exam.objects.filter(subject_id=subject_id, class_category_id=class_category_id, level__level_code=level.level_code, status=True)
        user_exams_ids = TeacherExamResult.objects.filter(user=user, isqualified__in=['True','False']).values_list('exam_id', flat=True)
        unattempted_exams = exam.exclude(id__in=user_exams_ids).order_by('?')
    
        exam_set = unattempted_exams.first()

        if exam_set:
            exam_serializer = ExamDetailSerializer(exam_set).data
            return Response(exam_serializer, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "error": "No exams available for the selected subject and class category.",
                    "message": "Please choose your preferred subject and class category to proceed with the exam."
                },
                status=status.HTTP_404_NOT_FOUND
            )


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Report.objects.all().order_by('-id')
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
        raise MethodNotAllowed("GET", detail="GET method not allowed on this endpoint.")

    def create(self, request, *args, **kwargs):
        user = request.user
        question_id = request.data.get('question')

        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            raise ValidationError({"question": ["Question not found."]})

        if Report.objects.filter(user=user, question=question).exists():
            raise ValidationError({
                "question": ["You have already submitted a report for this question."]
            })

        data = request.data.copy()
        if 'issue_type' in data and isinstance(data['issue_type'], str):
            data['issue_type'] = [data['issue_type']]
        data['user'] = user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user, question=question)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PasskeyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Passkey.objects.all().order_by('-id')
    serializer_class = PasskeySerializer

    @action(detail=True, methods=['put'])
    def update_status(self, request, pk=None):
        passkey = self.get_object()
        serializer = self.get_serializer(passkey, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "status updated successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GeneratePasskeyView(APIView):
    def post(self, request):
        user_id = self.request.user.id
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

        existing_passkey = Passkey.objects.filter(user=user, status='requested').first()
        if existing_passkey:
            return Response({"error": "A passkey has already been generated for this exam."},
                            status=status.HTTP_400_BAD_REQUEST)

        level_1_qualified = TeacherExamResult.objects.filter(user=user, exam__subject_id=exam.subject.id,exam__class_category_id=exam.class_category.id,exam__level__level_code=1.0, exam__type="online",
                                                             isqualified=True).exists()
        level_2_online_qualified = TeacherExamResult.objects.filter(user=user, exam__subject_id=exam.subject.id,exam__class_category_id=exam.class_category.id,exam__level__level_code=2.0, exam__type="online",
                                                                    isqualified=True).exists()

        if not (level_1_qualified and level_2_online_qualified):
            return Response(
                {"error": "User must qualify both Level 1 and Level 2 online exams to access Level 2 offline exams."},
                status=status.HTTP_400_BAD_REQUEST)

        passkey = random.randint(1000, 9999)

        passkey_obj = Passkey.objects.create(
            user=user,
            exam=exam,
            code=str(passkey),
            center=center,
            status='requested',
        )
        user_serializer = UserSerializer(user)
        exam_serializer = ExamDetailSerializer(exam)
        center_serializer = ExamCenterSerializer(center)
        return Response({"message": "Passkey generated successfully.",
                         "user": user_serializer.data,
                         "center": center_serializer.data,

                         "exam": exam_serializer.data
                         },
                        status=status.HTTP_200_OK)
    
    def get(self, request, user_id=None):
        exam_id = request.query_params.get('exam_id')

        passkeys = Passkey.objects.all()

        if user_id:
            passkeys = passkeys.filter(user__id=user_id)
        if exam_id:
            passkeys = passkeys.filter(exam__id=exam_id)

        if not passkeys.exists():
            return Response({"message": "No passkeys found."}, status=status.HTTP_404_NOT_FOUND)

        data = [{
            "user": passkey.user.id,
            "exam_name": passkey.exam.name,
            "subject": passkey.exam.subject.subject_name,
            "class_category": passkey.exam.class_category.name if passkey.exam.class_category else None,
            "level": passkey.exam.level.name if passkey.exam.level else None,
            "level_code": passkey.exam.level.level_code if passkey.exam.level else None,
            "code": passkey.code,
            "center": passkey.center.center_name,
            "status": passkey.status
        } for passkey in passkeys]

        return Response(data, status=status.HTTP_200_OK)
    


class VerifyPasscodeView(APIView):
    def post(self, request):
        user_id = self.request.user.id
        # exam_id = request.data.get('exam_id')
        entered_passcode = request.data.get('entered_passcode')
        if not user_id or not entered_passcode:
            return Response(
                {"error": "Missing required fields: user_id, exam_id, or passcode."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            passkey_obj = Passkey.objects.get(user_id=user_id, code=entered_passcode, status='fulfilled')
        except Passkey.DoesNotExist:
            return Response({"error": "Invalid passcode or exam."}, status=status.HTTP_400_BAD_REQUEST)

        passkey_obj.status = 'isused'
        passkey_obj.save()
        exam = passkey_obj.exam
        exam_serializer = ExamSerializer(exam)
        return Response(
            {
                "message": "Passcode verified successfully.",
                "offline_exam": exam_serializer.data
            },
            status=status.HTTP_200_OK,
        )


class InterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Interview.objects.all().order_by('-id')
    serializer_class = InterviewSerializer

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = get_count(Interview)
        return Response({"Count": count})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        

    def send_interview_link(self, interview, recipient_email):
        subject = f"Your Interview for {interview.subject} {interview.class_category} has been scheduled!"

        message = format_html("""
            <html>
                <body>
                    <p>Dear {user},</p>
                    <p>Your interview for <strong>{subject}, {class_category}</strong> has been scheduled.</p>
                    <p><strong>Interview Time:</strong> {time}</p>
                    <p><strong>Interview Link:</strong> <a href="{link}">Join your interview here</a></p>
                    <p>Please make sure to join at the scheduled time.</p>
                    <p>Best regards,<br>The Interview Team</p>
                </body>
            </html>
        """, user=interview.user.username, subject=interview.subject, class_category=interview.class_category,
                              time=interview.time, link=interview.link)

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
        # Deserialize data
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid(raise_exception=True):
            user = request.user
            time = serializer.validated_data.get('time')
            subject = serializer.validated_data.get('subject')
            class_category = serializer.validated_data.get('class_category')
            check_exam_qualified = TeacherExamResult.objects.filter(user=user, exam__subject_id=subject,
                                                                    exam__class_category_id=class_category,
                                                                    exam__level__level_code=2.0, 
                                                                    exam__type='online').exists()
            if not check_exam_qualified:
                return Response({"error": "First qualify this classcategory subject level 2 online exams for Interview "})

            pending_interview = Interview.objects.filter(user=user, subject=subject,
                                                                    class_category=class_category, status__in=['requested', 'scheduled']).exists()
            if pending_interview:
                return Response(
                    {"error": "You already have a pending interview. Please complete it before scheduling another."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            previous_attempts = Interview.objects.filter(
                user=user,
                subject=subject,
                class_category=class_category
            ).count()

            serializer.save(user=user, attempt=previous_attempts + 1)
            return Response(
                {"message": "Your interview request is sent successfully.", "data": serializer.data},
                status=status.HTTP_201_CREATED
            )
        print("Validation errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get_queryset(self):
        user = self.request.user
        return Interview.objects.filter(user=user).exclude(status__in=['fulfilled', 'rejected'])
    
class TeacherExamCenters(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ExamCenter.objects.all()
    serializer_class = ExamCenterSerializer

    def get_queryset(self):
        center = ExamCenter.objects.filter(status=True)   
        return center if center.exists() else None

class ExamCenterViewSets(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ExamCenter.objects.all()
    serializer_class = ExamCenterSerializer

   
    def create(self, request, *args, **kwargs):
        user_data = request.data.get("user")
        # require user data
        if not user_data:
            raise DRFValidationError({"user": ["User data is required."]})

        user_serializer = CenterUserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()

        # Extract exam center data
        exam_center_data = request.data.get("exam_center")
        if not exam_center_data:
            raise DRFValidationError({"exam_center": ["Exam center data not provided."]})

        # Assign only the user ID to the exam center data
        exam_center_data["user"] = user.id

        # Validate exam center serializer (raise -> custom handler formats)
        exam_center_serializer = ExamCenterSerializer(data=exam_center_data)
        exam_center_serializer.is_valid(raise_exception=True)
        exam_center_serializer.save()

        return Response({
            "user": user_serializer.data,
            "exam_center": exam_center_serializer.data,
            "message": "User and Exam Center created successfully"
        }, status=status.HTTP_201_CREATED)

    
    def update(self, request, *args, **kwargs):
        try:
            examcenter = ExamCenter.objects.get(id=kwargs['pk'])
        except ExamCenter.DoesNotExist:
            return Response({"error": "ExamCenter not found"}, status=status.HTTP_404_NOT_FOUND)

        user_data = request.data.get("user")
        exam_center_data = request.data.get("exam_center")

        if user_data and examcenter.user:
            user_serializer = CenterUserSerializer(examcenter.user, data=user_data, partial=True)
            if user_serializer.is_valid(raise_exception=True):
                user_serializer.save()
            else:
                return Response({"user_errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            exam_center_data["user"] = examcenter.user.id  

        # Update exam center
        if exam_center_data:
            exam_center_serializer = ExamCenterSerializer(examcenter, data=exam_center_data, partial=True)
            if exam_center_serializer.is_valid():
                exam_center_serializer.save()
                return Response({
                    "user": CenterUserSerializer(examcenter.user).data,
                    "exam_center": exam_center_serializer.data,
                    "message": "User and Exam Center updated successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response({"exam_center_errors": exam_center_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Exam center data not provided"}, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = self.get_queryset()
        
        if user.is_staff:
            serializer = self.get_serializer(queryset, many=True)
        elif user.is_teacher:
            serializer = TeacherExamCenterSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "ExamCenter deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SelfExamCenterViewSets(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = ExamCenter.objects.all()
    serializer_class = ExamCenterSerializer

    def get_queryset(self):
        user = self.request.user
        return ExamCenter.objects.filter(user=user, status=True)  
    
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
                    return Response({"error": "You can only update the 'status' field."},
                                    status=status.HTTP_400_BAD_REQUEST)
                serializer = PasskeySerializer(passkey_instance, data=request.data, partial=True)
                if serializer.is_valid(raise_exception=True):
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            except Passkey.DoesNotExist:
                return create_object(PasskeySerializer, request.data, Passkey)
        else:
            return Response({"error": "ID field is required for PUT"}, status=status.HTTP_400_BAD_REQUEST)


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


class AllTeacherViewSet(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated, IsAdminUser]
    # authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllTeacherSerializer

    def get_queryset(self):
        queryset = CustomUser.objects.filter(is_teacher=True, is_staff=False)

        return_all = self.request.query_params.get('all', None)
        if return_all and return_all.lower() == 'true':
            return queryset

        filters = Q()

        # Filter by teacher name
        teacher_name = self.request.query_params.getlist('name[]', [])
        if teacher_name:
            name_query = Q()
            for name in teacher_name:
                name_parts = name.strip().lower().split()
                if len(name_parts) >= 2:
                    fname, lname = name_parts[0], name_parts[-1]
                    name_query |= Q(Fname__icontains=fname) & Q(Lname__icontains=lname)
                elif len(name_parts) == 1:
                    fname = name_parts[0]
                    name_query |= Q(Fname__icontains=fname) | Q(Lname__icontains=fname)

            filters &= name_query

        # Filter by teacher subjects
        teacher_subjects = self.request.query_params.getlist('subject[]', [])
        if teacher_subjects:
            subject_query = Q()
            for subject in teacher_subjects:
                subject_query |= Q(teachersubjects__subject__subject_name__iexact=subject.strip().lower())
            filters &= subject_query

        # Filter by teacher address (state)
        teacher_address = self.request.query_params.getlist('address[]', [])
        if teacher_address:
            address_query = Q()
            for state in teacher_address:
                address_query |= Q(teachersaddress__state__iexact=state.strip().lower())
            filters &= address_query

        # Filter by teacher qualifications
        teacher_qualifications = self.request.query_params.getlist('qualification[]', [])
        if teacher_qualifications:
            qualification_query = Q()
            for qualification in teacher_qualifications:
                qualification_query |= Q(teacherqualifications__qualification__iexact=qualification.strip().lower())
            filters &= qualification_query

        # Apply the filters to the queryset
        queryset = queryset.filter(filters)

        # Ensure distinct results to avoid duplicates
        return queryset.distinct()

class AssignedQuestionUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AssignedQuestionUserSerializer
    queryset = AssignedQuestionUser.objects.all()

    def create(self, request, *args, **kwargs):
        # Validate user data first
        user_serializer = QuestionUserSerializer(data=request.data.get("user"))
        if not user_serializer.is_valid():
            return Response({
                "error": user_serializer.errors,
                "message": "User creation failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        user = user_serializer.save()

        # Extract and validate class_category
        class_category_ids = request.data.get("class_category", [])
        if not isinstance(class_category_ids, list) or not class_category_ids:
            return Response({
                "error": "Class category not provided",
                "message": "Please provide at least one class category."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Extract and validate subjects
        assign_user_subjects = request.data.get("subject", [])
        if not isinstance(assign_user_subjects, list) or not assign_user_subjects:
            return Response({
                "error": "Subjects not provided",
                "message": "Please provide at least one subject."
            }, status=status.HTTP_400_BAD_REQUEST)

        existing_subjects = AssignedQuestionUser.objects.filter(user=user).values_list('subject__id', flat=True)
        already_assigned = set(assign_user_subjects) & set(existing_subjects)

        if already_assigned:
            return Response({
                "error": "User is already assigned to same subjects",
                "message": f"This user is already assigned to subjects with IDs: {list(already_assigned)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        assigned_user_subject, created = AssignedQuestionUser.objects.get_or_create(user=user)

        subjects_to_assign = Subject.objects.filter(id__in=assign_user_subjects)
        assigned_user_subject.subject.set(subjects_to_assign)

        class_categories_to_assign = ClassCategory.objects.filter(id__in=class_category_ids)
        assigned_user_subject.class_category.set(class_categories_to_assign)

        assign_user_subject_serializer = AssignedQuestionUserSerializer(assigned_user_subject)
        return Response({
            "data": assign_user_subject_serializer.data,
            "message": "User, subjects, and class categories assigned successfully"
        }, status=status.HTTP_201_CREATED)
    

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            if instance.user:
                user_data = request.data.get('user', {})
                user_serializer = QuestionUserSerializer(instance.user, data=user_data, partial=True)
                if user_serializer.is_valid():
                    user_serializer.save()
                else:
                    return Response({
                        "error": user_serializer.errors,
                        "message": "User update failed"
                    }, status=status.HTTP_400_BAD_REQUEST)

            # Validate and update status
            new_status = request.data.get('status')
            if new_status is None:
                return Response(
                    {"error": "Status value is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(new_status, bool):
                return Response(
                    {"error": "Invalid status value. Must be true or false."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            instance.status = new_status

            # Validate and update subjects
            new_subjects = request.data.get('subject')
            if new_subjects is None:
                return Response(
                    {"error": "Subject field is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(new_subjects, list):
                return Response(
                    {"error": "Invalid subject format. Must be a list of subject IDs."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Filter and set the subjects
            subjects_qs = Subject.objects.filter(id__in=new_subjects)
            instance.subject.set(subjects_qs)

            # Validate and update class categories
            new_class_categories = request.data.get('class_category')
            if new_class_categories is None:
                return Response(
                    {"error": "Class category field is required."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(new_class_categories, list):
                return Response(
                    {"error": "Invalid class category format. Must be a list of class category IDs."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Filter and set the class categories
            class_categories_qs = ClassCategory.objects.filter(id__in=new_class_categories)
            instance.class_category.set(class_categories_qs)

            # Save the updated instance
            instance.save()

            return Response({
                "detail": "Assigned question user updated successfully.",
                "data": AssignedQuestionUserSerializer(instance).data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        exam_created_user = Exam.objects.filter(assigneduser=instance).exists()
        if exam_created_user:
            return Response({"error": "This user is assigned to an exam and cannot be deleted."},
                            status=status.HTTP_400_BAD_REQUEST)
        instance.delete()
        return Response({"message": "Assigned question user deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    def get_queryset(self):
        return AssignedQuestionUser.objects.filter(user__is_staff=False)
    
class SelfAssignedQuestionUserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AssignedQuestionUserSerializer
    queryset = AssignedQuestionUser.objects.all()

    def get_queryset(self):
        user = self.request.user
        return AssignedQuestionUser.objects.filter(user=user)
    
class AllRecruiterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllRecruiterSerializer

    def get_queryset(self):
        return_all = self.request.query_params.get('all', None)

        queryset = CustomUser.objects.filter(is_recruiter=True)

        if return_all is None or return_all.lower() != 'true':
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

        return queryset

class HireRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = HireRequestSerializer
    queryset = HireRequest.objects.all()

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        allowed_fields = ['status']
        data = {field: request.data[field] for field in allowed_fields if field in request.data}

        serializer = self.get_serializer(instance, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data)

class RecHireRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = HireRequestSerializer
    queryset = HireRequest.objects.all()

    def create(self, request):
        recruiter_id = request.user.id
        data = request.data.copy()
        data['recruiter_id'] = recruiter_id
        data['status'] = "requested"
        serializer = HireRequestSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        recruiter_id = self.request.user
        return HireRequest.objects.filter(recruiter_id=recruiter_id)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        status_value = request.data.get("status")
        reject_reason = request.data.get("reject_reason")

        if status_value not in ['requested', 'fulfilled', 'rejected']:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = status_value
        if status_value == "rejected":
            if not reject_reason:
                return Response({"error": "Reject reason required when status is rejected"}, status=status.HTTP_400_BAD_REQUEST)
            instance.reject_reason = reject_reason
        else:
            instance.reject_reason = None

        instance.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    
class RecruiterEnquiryFormViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]  
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = RecruiterEnquiryFormSerializer
    queryset = RecruiterEnquiryForm.objects.all()

    def create(self, request, *args, **kwargs):
        return Response({"detail": "POST method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
class SelfRecruiterEnquiryFormViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterEnquiryFormSerializer
    queryset = RecruiterEnquiryForm.objects.all()
    permission_classes = [permissions.AllowAny] 

    # def list(self, request, *args, **kwargs):
    #     return Response({"detail": "GET method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request, *args, **kwargs):
        user = self.request.user
        data = request.data.copy()
        data['user'] = user.id
        serializer = self.get_serializer(data=data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ApplyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = ApplySerializer
    queryset = Apply.objects.all()

    def create(self, request):
        data = request.data.copy()
        user = request.user
        
        # Extract preferred_locations if present
        preferred_locations = data.pop('preferred_locations', [])
        
        # If no inline locations provided, enforce existing check
        if not preferred_locations and not JobPreferenceLocation.objects.filter(user=user).exists():
            return Response(
                {"error": "You must have at least one job preference location before applying."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data["user"] = user.id
        # Save the new application
        serializer = ApplySerializer(data=data, context={"request": request})
        if serializer.is_valid(raise_exception=True):
            apply_instance = serializer.save(user=user)
            
            # Save preferred locations if provided
            if preferred_locations:
                for loc_data in preferred_locations:
                    JobPreferenceLocation.objects.create(
                        user=user,
                        apply=apply_instance,
                        **loc_data
                    )
            
            return Response(ApplySerializer(apply_instance).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_queryset(self):
        return Apply.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Applied Data deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class AllApplyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = ApplySerializer
    queryset = Apply.objects.all()

    def create(self, request, *args, **kwargs):
        return Response({"detail": "POST method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
    
    def get_queryset(self):
        teacher_id  = self.request.query_params.get('teacher_id')
        if teacher_id:
            return Apply.objects.filter(user=teacher_id)
        return Apply.objects.all()

class CountDataViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]

    def list(self, request):
        last_month = timezone.now() - timedelta(days=30)
        count = {}

        if 'teachers' in request.query_params:
            count["teachers"] = {
                "total": CustomUser.objects.filter(is_teacher=True).count(),
                "pending": CustomUser.objects.filter(is_teacher=True, is_verified=False).count(),
                "thisMonth": CustomUser.objects.filter(is_teacher=True, date__gte=last_month).count(),
            }

        if 'recruiters' in request.query_params:
            count["recruiters"] = {
                "total": CustomUser.objects.filter(is_recruiter=True).count(),
                "pending": CustomUser.objects.filter(is_recruiter=True, is_verified=False).count(),
                "thisMonth": CustomUser.objects.filter(is_recruiter=True, date__gte=last_month).count(),
            }
        if 'interviews' in request.query_params:
            count["interviews"] = {
                "upcoming": Interview.objects.filter(time__gte=timezone.now(), grade__isnull=True).count(),
                "completed": Interview.objects.filter(grade__isnull=False).count(),
            }

        if 'passkeys' in request.query_params:
            count["passkeys"] = {
                "total": Passkey.objects.count(),
                "pending": Passkey.objects.filter(status=False).count(),
                "approved": Passkey.objects.filter(status=True).count(),
            }

        if 'examcenters' in request.query_params:
            count["examcenters"] = {
                "total_examcenter": ExamCenter.objects.count(),
            }

        if 'questioReports' in request.query_params:
            count["QuestioReports"] = {
                "total": Report.objects.count(),
            }
        
        if 'hireRequests' in request.query_params:
            count["HireRequests"] = {
                "total": HireRequest.objects.count(),
                "requested": HireRequest.objects.filter(status="requested").count(),
                "approved": HireRequest.objects.filter(status="approved").count(),
                "rejected": HireRequest.objects.filter(status="rejected").count(),
            }
        if 'teacherApply' in request.query_params:
            count["TeacherApply"] = {
                "total": Apply.objects.count(),
                "pending": Apply.objects.filter(status=False).count(),
                "approved": Apply.objects.filter(status=True).count(),
            }
        if 'recruiterEnquiry' in request.query_params:
            count["RecruiterEnquiryForm"] = {
                "total": RecruiterEnquiryForm.objects.count(),
            }
        if 'subjects' in request.query_params:
            count["subjects"] = {
                'total': Subject.objects.count(),
            }

        if 'class_categories' in request.query_params:
            count["class_categories"] = {
                'total': ClassCategory.objects.count(),
            }

        if 'assignedquestionusers' in request.query_params:
            count["assignedquestionusers"] = {
                'total': AssignedQuestionUser.objects.count(),
            }

        if 'skills' in request.query_params:
            count["skills"] = {
                'total': Skill.objects.count(),
            }

        return Response(count)
    
class checkPasskeyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    def create(self, request):
        user = request.user
        exam_id = request.data.get('exam')
        
        # try:
        #     exam = Exam.objects.get(id=exam_id)
        # except Exam.DoesNotExist:
        #     return Response({"exam": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)
      
        # passkey = Passkey.objects.filter(user=user,exam__id=exam.id,exam__subject_id=exam.subject.id,exam__class_category_id=exam.class_category.id, exam__level__level_code='2.5',exam__type='offline', status__in=['requested','fulfilled']).first()
        passkey = Passkey.objects.filter(user=user, status__in=['requested','fulfilled']).first()

        if passkey and passkey.center:
            center = {
                "id": passkey.center.id,
                "name": passkey.center.center_name,
                "phone": passkey.center.phone,
                "alt_phone": passkey.center.alt_phone,
                "pincode": passkey.center.pincode,
                "state": passkey.center.state,
                "city": passkey.center.city,
                "area": passkey.center.area
            }
            return Response({"passkey": True, "center": center, "status": passkey.status }, status=status.HTTP_200_OK)
        else:
            center = None
            return Response({
                "message": "No valid passkey found.",
                "passkey": False, 
                "status": False,
                }, status=status.HTTP_200_OK)

class TranslatorViewset(viewsets.ViewSet):
    def create(self, request):
        serializer = TranslatorSerializer(data=request.data)
        if serializer.is_valid():
            text = serializer.validated_data['text']
            source = serializer.validated_data['source']
            dest = serializer.validated_data['dest']

            translator = Translator()
            try:
                translated_text = translator.translate(text, src=source, dest=dest)
                return Response({
                    'text': text,
                    'translated': translated_text.text,
                    'source': source,
                    'destination': dest
                })
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NewExamSetterQuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Question.objects.all()
    serializer_class = NewQuestionSerializer

    def get_permissions(self):
        return [IsAdminUser()] if self.request.user.is_staff else [IsQuestionUser()]

    def create(self, request, *args, **kwargs):
        data = request.data
        exam_id = data.get("exam")
        order = data.get("order")
        questions = data.get("questions")

        if not exam_id or not questions or not isinstance(questions, list):
            return Response({"error": "Exam and questions array are required"}, status=400)

        if request.user.is_staff:  # Admin can create questions for any exam
            try:
                exam = Exam.objects.get(id=exam_id)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found"}, status=status.HTTP_404_NOT_FOUND)
        else:  # Question setter can only create questions for their assigned exam
            assigned_user = AssignedQuestionUser.objects.filter(user=request.user).first()
            if not assigned_user:
                return Response({"error": "You are not assigned as a question user."}, status=status.HTTP_403_FORBIDDEN)

            try:
                exam = Exam.objects.get(pk=exam_id, assigneduser=assigned_user)
            except Exam.DoesNotExist:
                return Response({"error": "Exam not found or you do not have permission."}, 
                                status=status.HTTP_404_NOT_FOUND)
        if exam.questions.count() >= exam.total_questions:
            return Response({"error": "Cannot add more questions than the total allowed for this exam."}, 
                            status=status.HTTP_400_BAD_REQUEST)

        errors = []
        english_instance = None
        hindi_instance = None  # Ensure hindi_instance is always defined

        for q in questions:
            q["exam"] = exam.id
            q['order'] = order 
            language = q.get("language", "").lower()

            serializer = self.get_serializer(data=q)
            if serializer.is_valid():
                # Save English first without related_question
                if language == "english":
                    english_instance = serializer.save()

                # Save Hindi with related_question set
                elif language == "hindi":
                    if english_instance:
                        q["related_question"] = english_instance.id
                    hindi_serializer = self.get_serializer(data=q)
                    if hindi_serializer.is_valid():
                        hindi_instance = hindi_serializer.save()
                    else:
                        errors.append(hindi_serializer.errors)
            else:
                errors.append(serializer.errors)

        if errors:
            return Response({"errors": errors}, status=400)

        return Response({
            "message": "Questions saved successfully",
            "english_data": NewQuestionSerializer(english_instance).data if english_instance else None,
            "hindi_data": NewQuestionSerializer(hindi_instance).data if hindi_instance else None
        }, status=201)



    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        base_instance = self.get_object()
        user = request.user

        # Permissions check
        if not user.is_staff and base_instance.exam.assigneduser.user != user:
            return Response({"error": "You do not have permission to update this exam."}, status=status.HTTP_403_FORBIDDEN)

        exam_id = request.data.get("exam")
        questions = request.data.get("questions", [])
        if not exam_id or not questions:
            return Response({"error": "Both 'exam' and 'questions' fields are required."}, status=status.HTTP_400_BAD_REQUEST)

        updated_data = {}
        errors = {}

        for item in questions:
            language = item.get("language")

            # Inject exam ID into question
            item["exam"] = exam_id

            if language == "English":
                serializer = self.get_serializer(base_instance, data=item, partial=partial)
                if serializer.is_valid():
                    english_instance = serializer.save()
                    try:
                        hindi_instance = Question.objects.get(related_question=base_instance.id)
                        hindi_instance.correct_option = base_instance.correct_option
                        hindi_instance.save()
                        updated_data["hindi_data"] = QuestionSerializer(hindi_instance).data
                    except Question.DoesNotExist:
                        errors["hindi_errors"] = None
                    updated_data["english_data"] = QuestionSerializer(english_instance).data
                else:
                    errors["english_errors"] = serializer.errors

            elif language == "Hindi":
                try:
                    if base_instance.language.lower() == "english":
                        hindi_instance = Question.objects.get(related_question=base_instance)
                    else:
                        hindi_instance = Question.objects.get(id=base_instance.id)
                except Question.DoesNotExist:
                    errors["hindi_errors"] = "Hindi question not found"
                    continue

                serializer = self.get_serializer(hindi_instance, data=item, partial=partial)
                if serializer.is_valid():
                    hindi_instance = serializer.save()
                    updated_data["hindi_data"] = QuestionSerializer(hindi_instance).data
                else:
                    errors["hindi_errors"] = serializer.errors

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Questions updated successfully",
            **updated_data
        }, status=status.HTTP_200_OK)


    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        exam = instance.exam

        if exam.status and not request.user.is_superuser:
            return Response({"error": "Only admin can delete questions from an active exam."}, status=status.HTTP_403_FORBIDDEN)

        try:
            if instance.related_question:
                related_question = instance.related_question
                related_question.delete()
                instance.delete()
                return Response({"message": "Question and its related question deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

            related_to_instance = Question.objects.filter(related_question=instance).first()
            if related_to_instance:
                related_to_instance.delete()

            instance.delete()
            return Response({"message": "Questions deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class QuestionReorderView(APIView):
    def put(self, request):
        new_order = request.data.get('order', [])
        if not isinstance(new_order, list):
            return Response({'error': 'Invalid order format'}, status=400)

        updated_pairs = [] 

        for idx, q_id in enumerate(new_order, start=1):
            try:
                question = Question.objects.get(id=q_id)
            except Question.DoesNotExist:
                continue  

            question.order = idx
            question.save()

            if question.language.lower() == 'english':
                related = Question.objects.filter(related_question=question).first()
            elif question.language.lower() == 'hindi' and question.related_question:
                related = question.related_question
            else:
                related = None

            if related:
                related.order = idx
                related.save()
                updated_pairs.append({
                    "english_id": question.id if question.language.lower() == "english" else related.id,
                    "hindi_id": related.id if question.language.lower() == "english" else question.id,
                    "order": idx
                })
            else:
                # Single question without a pair
                updated_pairs.append({
                    "english_id": question.id if question.language.lower() == "english" else None,
                    "hindi_id": question.id if question.language.lower() == "hindi" else None,
                    "order": idx
                })

        return Response({
            'message': 'Order updated successfully',
            'updated_order': updated_pairs
        }, status=200)


class ApplyEligibilityView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    
    def get(self, request, *args, **kwargs):
        user = request.user
        qualified_offline_exams = TeacherExamResult.objects.filter(
            user=user,
            exam__type='offline',
            isqualified=True
        ).values_list('exam__subject_id', 'exam__class_category_id').distinct()
        print(qualified_offline_exams)

        interview = Interview.objects.filter(
            user=user,
            grade__gte=6
        ).values_list('subject_id', 'class_category_id').distinct()
        print(interview)

        unique_data = set(qualified_offline_exams) | set(interview)
        qualified_list = []
        for subj_id, class_cat_id in unique_data:
            qualified_list.append({
                'subject_id': subj_id,
                'subject_name': Subject.objects.filter(id=subj_id).values_list('subject_name', flat=True).first(),
                'class_category_id': class_cat_id,
                'class_category_name': ClassCategory.objects.filter(id=class_cat_id).values_list('name', flat=True).first(),
                "eligible": True
            })

        return Response({
            "qualified_list": qualified_list
        })


# Teacher Filter API View
class TeacherFilterAPIView(APIView):

    def get(self, request):
        user = request.user if request.user.is_authenticated else None

        # Admin: return all teachers (or users) who have attempted any exam, with their exam progress.
        if user and user.is_staff:
            teachers_qs = CustomUser.objects.filter(teacherexamresult__isnull=False).distinct()

            results = []
            for teacher in teachers_qs:
                teacher_data = TeacherSerializer(teacher, context={'request': request}).data
                attempts_qs = TeacherExamResult.objects.filter(user=teacher).order_by('-created_at')
                attempts_data = TeacherAttempterializer(attempts_qs, many=True, context={'request': request}).data
                results.append({
                    "teacher": teacher_data,
                    "attempts": attempts_data
                })

            return Response({"count": len(results), "results": results}, status=status.HTTP_200_OK)

        # Recruiter/public flow (existing behavior)
        # Get required parameters
        class_category = request.query_params.getlist('class_category')
        subject = request.query_params.getlist('subject')
        state = request.query_params.getlist('state')

        missing = []
        if not class_category or not any(class_category):
            missing.append('class_category')
        if not subject or not any(subject):
            missing.append('subject')
        if not state or not any(state):
            missing.append('state')

        if missing:
            return Response({
                "detail": "These parameters are required.",
                "missing": missing,
                "message": "Please provide class_category, subject, and state to filter teachers."
            }, status=status.HTTP_400_BAD_REQUEST)

        queryset = CustomUser.objects.filter(is_teacher=True, is_staff=False, apply__status=True).distinct()
        filters = Q()

        def clean_values(values):
            return [v for v in values if v and str(v).strip()]

        # Gender filter
        gender = request.query_params.getlist('gender')
        gender = clean_values(gender)
        if gender:
            filters &= Q(profiles__gender__iexact=gender[0]) if len(gender) == 1 else Q(profiles__gender__in=gender)

        # Religion filter
        religion = request.query_params.getlist('religion')
        religion = clean_values(religion)
        if religion:
            filters &= Q(profiles__religion__iexact=religion[0]) if len(religion) == 1 else Q(profiles__religion__in=religion)

        marital_status = clean_values(request.query_params.getlist('marital_status'))
        if marital_status:
            filters &= Q(profiles__marital_status__iexact=marital_status[0]) if len(marital_status) == 1 else Q(profiles__marital_status__in=marital_status)

        # Language filter
        language = clean_values(request.query_params.getlist('language'))
        if language:
            filters &= Q(profiles__language__iexact=language[0]) if len(language) == 1 else Q(profiles__language__in=language)

        # JobPreferenceLocation address filters (support multiple values, ignore empty/null)
        jp_fields = ['state', 'city', 'sub_division', 'post_office', 'area', 'pincode']
        for field in jp_fields:
            values = clean_values(request.query_params.getlist(field))
            if values:
                field_name = f'jobpreferencelocation__{field}__iexact'
                q = Q()
                for value in values:
                    q |= Q(**{field_name: value})
                    print(f"Filtering {field_name} with value: {value}")
                filters |= q

        # Experience years range filter
        exp_min = request.query_params.get('experience_years[min]')
        exp_max = request.query_params.get('experience_years[max]')
        if exp_min or exp_max:
            queryset = queryset.annotate(
                total_exp=models.Sum(
                    models.F('teacherexperiences__end_date__year') - models.F('teacherexperiences__start_date__year')
                )
            )
            if exp_min and exp_min.strip():
                queryset = queryset.filter(total_exp__gte=int(exp_min))
            if exp_max and exp_max.strip():
                queryset = queryset.filter(total_exp__lte=int(exp_max))

        # Preference table filters (support multiple values, ignore empty/null)
        pref_filters = [
            ('class_category', 'apply__class_category__name__iexact'),
            ('subject', 'apply__subject__subject_name__iexact'),
            # ('job_role', 'preferences__job_role__jobrole_name__iexact'),
            ('teacher_job_type', 'apply__teacher_job_type__teacher_job_name__iexact'),
        ]
        for param, db_field in pref_filters:
            values = clean_values(request.query_params.getlist(param))
            if values:
                q = Q()
                for value in values:
                    q |= Q(**{db_field: value})
                filters &= q

        # Qualification filter (multiple, ignore empty/null)
        qualifications = clean_values(request.query_params.getlist('qualification'))
        if qualifications:
            q = Q()
            for qualification in qualifications:
                q |= Q(teacherqualifications__qualification__name__iexact=qualification)
            filters &= q

        # Skill filter (multiple, ignore empty/null)
        skills = clean_values(request.query_params.getlist('skill'))
        if skills:
            q = Q()
            for skill in skills:
                q |= Q(teacherskill__skill__name__iexact=skill)
            filters &= q

        # Apply all filters except total_marks
        queryset = queryset.filter(filters).distinct()

        # Total marks range filter (on related Exam objects)
        marks_min = request.query_params.get('total_marks[min]')
        marks_max = request.query_params.get('total_marks[max]')
        if marks_min or marks_max:
            exam_filter = Q()
            if marks_min and marks_min.strip():
                exam_filter &= Q(teacherexamresult__exam__total_marks__gte=int(marks_min))
            if marks_max and marks_max.strip():
                exam_filter &= Q(teacherexamresult__exam__total_marks__lte=int(marks_max))
            queryset = queryset.filter(exam_filter).distinct()

        serializer = TeacherFilterSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    

# API for teacher all details and their highest qualified exam attempts
class TeacherDetailAPIView(APIView):
    permission_classes = []

    def get(self, request, teacher_id):
        try:
            teacher = CustomUser.objects.get(id=teacher_id, is_teacher=True)
        except CustomUser.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)
        serializer = TeacherSerializer(teacher, context={'request': request})

        # For recruiters (non-admin), return only interview details
        if not request.user.is_authenticated or not request.user.is_staff:
            # Get all interviews with grades for this teacher
            interviews = Interview.objects.filter(
                user=teacher
            ).exclude(grade__isnull=True).order_by('-created_at')
            
            interview_data = InterviewSerializer(interviews, many=True, context={'request': request}).data
            return Response({"teacher": serializer.data, "attempts": interview_data}, status=200)
        
        # For admin, return exam attempt details
        exam_results_qs = TeacherExamResult.objects.filter(
            user=teacher, isqualified=True
        ).order_by(
            'exam__subject_id', 'exam__class_category_id', 'exam__level_id', '-correct_answer', '-created_at'
        )

        # Only keep the highest marks for each (subject, class_category, level)
        seen = set()
        highest_results = []
        for result in exam_results_qs:
            key = (result.exam.subject_id, result.exam.class_category_id, result.exam.level_id)
            if key not in seen:
                seen.add(key)
                highest_results.append(result)

        exam_results = TeacherAttempterializer(highest_results, many=True, context={'request': request}).data
        return Response({"teacher": serializer.data, "attempts": exam_results}, status=200)
    

# level 2 online and offline qualified users viewset
class QualifiedLevel2UsersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = QualifiedUserExamSerializer

    def get_queryset(self):
        # Get all qualified results for level 2 online/offline
        qs = TeacherExamResult.objects.filter(
            isqualified=True,
            exam__level__level_code__in=[2.0]
        ).distinct().select_related('user', 'exam__subject', 'exam__class_category')


# Teachers qualified for Level 2 (From Home) and ready for interview
class ReadyForInterviewViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        # Get users who qualified Level 2 (From Home) - level_code 2.0
        qualified_results = TeacherExamResult.objects.filter(
            isqualified=True,
            exam__level__level_code=2.0
        ).select_related('user', 'exam__subject', 'exam__class_category').values_list('user_id', flat=True).distinct()
        
        # Get users who don't have any interview scheduled/completed for their qualified subjects
        users_with_interviews = Interview.objects.filter(
            user_id__in=qualified_results
        ).values_list('user_id', flat=True).distinct()
        
        # Teachers who are qualified but don't have interviews yet
        ready_users = set(qualified_results) - set(users_with_interviews)
        
        return CustomUser.objects.filter(
            id__in=ready_users,
            is_teacher=True,
            is_verified=True
        ).prefetch_related(
            'teacherskill',
            'profiles',
            'teachersaddress',
            'teacherexperiences',
            'teacherqualifications',
            'preferences',
            'jobpreferencelocation',
            'apply'
        )
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Optional filters
        subject_id = request.query_params.get('subject_id')
        class_category_id = request.query_params.get('class_category_id')
        
        if subject_id or class_category_id:
            # Filter users based on their qualified exams
            filter_kwargs = {'isqualified': True, 'exam__level__level_code': 2.0}
            if subject_id:
                filter_kwargs['exam__subject_id'] = subject_id
            if class_category_id:
                filter_kwargs['exam__class_category_id'] = class_category_id
            
            filtered_user_ids = TeacherExamResult.objects.filter(
                **filter_kwargs
            ).values_list('user_id', flat=True).distinct()
            
            queryset = queryset.filter(id__in=filtered_user_ids)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'teachers': serializer.data
        }, status=200)
        


# def get_queryset(self):
#         # Get all qualified results for level 2 online/offline
#         qs = TeacherExamResult.objects.filter(
#             isqualified=True,
#             exam__level__level_code__in=[2.0, 2.5]
#         ).select_related('user', 'exam__subject', 'exam__class_category')

#         # Use values to get distinct (user, subject, class_category) combinations
#         distinct_keys = set()
#         distinct_results = []
#         for result in qs:
#             key = (result.user_id, result.exam.subject_id, result.exam.class_category_id)
#             if key not in distinct_keys:
#                 distinct_keys.add(key)
#                 distinct_results.append(result)
        # return distinct_results