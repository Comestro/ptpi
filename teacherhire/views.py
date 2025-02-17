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
from translate import Translator
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

class RecruiterView(APIView):
    permission_classes = [IsRecruiterUser]

    def get(self, request):
        return Response({"message": "You are a recruiter!"}, status=status.HTTP_200_OK)


class TranslatorView(APIView):
    def get(self, request):
        translator = Translator(to_lang="hi")
        translation = translator.translate("What are the functions of a DBMS?")
        return Response(data={"translation": translation}, status=status.HTTP_200_OK)


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
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
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


# class RecruiterViewSet(viewsets.ModelViewSet):
#     permission_classes = [IsAuthenticated]
#     authentication_classes = [ExpiringTokenAuthentication]
#     queryset = CustomUser.objects.filter(is_recruiter=True)
#     serializer_class = RecruiterSerializer

class TeacherViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsRecruiterUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def get_queryset(self):
        return_all = self.request.query_params.get('all', None)
        queryset = CustomUser.objects.filter(teacherexamresult__isqualified=True, teacherexamresult__exam__level_id=3,teacherexamresult__exam__type='offline', is_staff=False)

        # Handle 'all' query parameter
        if return_all and return_all.lower() == 'true':
            pass  # No filtering needed if 'all' is true

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

        # Fuzzy matching and filtering by teacher skills
        teacher_skills = self.request.query_params.getlist('skill[]', [])
        if teacher_skills:
            teacher_skills = [skill.strip().lower() for skill in teacher_skills]
            skill_query = Q()
            for skill in teacher_skills:
                skill_query |= Q(teacherskill__skill__name__iexact=skill)
            queryset = queryset.filter(skill_query)

        # Filter by teacher qualifications
        teacher_qualifications = self.request.query_params.getlist('qualification[]', [])
        if teacher_qualifications:
            teacher_qualifications = [qualification.strip().lower() for qualification in teacher_qualifications]
            qualification_query = Q()
            for qualification in teacher_qualifications:
                qualification_query |= Q(teacherqualifications__qualification__name__iexact=qualification)
            queryset = queryset.filter(qualification_query)

        # Filters for other fields like state, district, etc.
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


class ClassCategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
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
        try:
            year_of_passing = int(data.get('year_of_passing'))
        except (ValueError, TypeError):
            return Response({"error": "Please Enter a valid year."}, status=status.HTTP_400_BAD_REQUEST)

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

    def create(self, request):
        data = request.data
        exam_id = data.get("exam")

        if not exam_id:
            return Response({"error": "Exam ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure the user is assigned to an `AssignedQuestionUser` instance
        try:
            assigned_user = AssignedQuestionUser.objects.get(user=request.user)
        except AssignedQuestionUser.DoesNotExist:
            return Response({"error": "You are not assigned as a question user."}, status=status.HTTP_403_FORBIDDEN)

        # Ensure the exam exists and is assigned to the correct `AssignedQuestionUser`
        try:
            exam = Exam.objects.get(pk=exam_id, assigneduser=assigned_user)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found or you do not have permission."},
                            status=status.HTTP_404_NOT_FOUND)

        translator = Translator(to_lang="hi")

        # Create English version
        english_serializer = QuestionSerializer(data=data)
        if english_serializer.is_valid():
            english_question = english_serializer.save()
        else:
            return Response(english_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create Hindi version if the question is in English
        hindi_serializer = None
        if data.get("language") == "English":
            hindi_data = data.copy()

            # Translate fields 
            hindi_data["text"] = translator.translate(data.get("text", ""))
            hindi_data["solution"] = translator.translate(data.get("solution", "")) if data.get("solution") else ""

            # Translate options
            hindi_options = {}
            if isinstance(data["options"], dict):
                for key, value in data["options"].items():
                    hindi_options[key] = translator.translate(value)
            elif isinstance(data["options"], list):
                hindi_options = [translator.translate(option) for option in data["options"]]

            hindi_data["options"] = hindi_options
            hindi_data["language"] = "Hindi"
            hindi_data["exam"] = exam_id

            hindi_serializer = QuestionSerializer(data=hindi_data)
            if hindi_serializer.is_valid():
                hindi_question = hindi_serializer.save()
            else:
                return Response(hindi_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Question stored in English and Hindi",
            "english_data": english_serializer.data,
            "hindi_data": hindi_serializer.data if hindi_serializer else None
        }, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        try:
            question = self.get_object()  # Get the question object
        except Question.DoesNotExist:
            return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        data = request.data

        # Ensure the user is an assigned question setter
        try:
            assigned_user = AssignedQuestionUser.objects.get(user=user)
        except AssignedQuestionUser.DoesNotExist:
            return Response({"error": "You are not an assigned question user."}, status=status.HTTP_403_FORBIDDEN)

        # Ensure the question belongs to an exam assigned to this user
        exam = question.exam

        if exam.assigneduser != assigned_user:
            return Response({"error": "You do not have permission to edit this question"},
                            status=status.HTTP_403_FORBIDDEN)

        # Partial update using the serializer
        serializer = QuestionSerializer(question, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Question deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class QuestionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def create(self, request):
        data = request.data
        exam_id = data.get("exam")

        # Ensure the user is assigned to an `AssignedQuestionUser` instance
        try:
            assigned_user = AssignedQuestionUser.objects.get(user=request.user)
        except AssignedQuestionUser.DoesNotExist:
            return Response({"error": "You are not assigned as a question user."}, status=status.HTTP_403_FORBIDDEN)

        # Ensure the exam exists and is assigned to the correct `AssignedQuestionUser`
        try:
            exam = Exam.objects.get(pk=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam not found "}, status=status.HTTP_404_NOT_FOUND)

        translator = Translator(to_lang="hi")

        # Create English version
        english_serializer = QuestionSerializer(data=data)
        if english_serializer.is_valid():
            english_question = english_serializer.save()
        else:
            return Response(english_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Create Hindi version if the question is in English
        hindi_serializer = None
        if data.get("language") == "English":
            hindi_data = data.copy()

            # Translate fields 
            hindi_data["text"] = translator.translate(data.get("text", ""))
            hindi_data["solution"] = translator.translate(data.get("solution", "")) if data.get("solution") else ""

            # Translate options
            hindi_options = {}
            if isinstance(data["options"], dict):
                for key, value in data["options"].items():
                    hindi_options[key] = translator.translate(value)
            elif isinstance(data["options"], list):
                hindi_options = [translator.translate(option) for option in data["options"]]

            hindi_data["options"] = hindi_options
            hindi_data["language"] = "Hindi"
            hindi_data["exam"] = exam_id

            hindi_serializer = QuestionSerializer(data=hindi_data)
            if hindi_serializer.is_valid():
                hindi_question = hindi_serializer.save()
            else:
                return Response(hindi_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Question stored in English and Hindi",
            "english_data": english_serializer.data,
            "hindi_data": hindi_serializer.data if hindi_serializer else None
        }, status=status.HTTP_201_CREATED)

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
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Role.objects.all()
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
        serializer = self.get_serializer(datRa=data)
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

class AllTeacherBasicProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllBasicProfileSerializer
    queryset = CustomUser.objects.filter(is_teacher=True,is_verified=True)

class AllRecruiterBasicProfileViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated,IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllBasicProfileSerializer
    queryset = CustomUser.objects.filter(is_recruiter=True,is_verified=True)


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
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherJobType.objects.all()
    serializer_class = TeacherJobTypeSerializer


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
            for class_category in user_preference.class_category.all():
                unlocked_levels = ["Level 1"]

                has_level_1 = qualified_exams.filter(exam__level_id=1, exam__type="online",
                                                    exam__subject=subject,
                                                    exam__class_category=class_category).exists()
                has_level_2_online = qualified_exams.filter(exam__level_id=2, exam__type="online",
                                                            exam__subject=subject,
                                                            exam__class_category=class_category).exists()
                has_level_2_offline = qualified_exams.filter(exam__level_id=2, exam__type="offline",
                                                            exam__subject=subject,
                                                            exam__class_category=class_category).exists()

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

class ExamSetterViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    queryset = Exam.objects.all()
    serializer_class = ExamSerializer

    def create(self, request):
        user = request.user
        subject = request.data.get('subject')  
        try:
            assigned_user = AssignedQuestionUser.objects.get(user=user, subject=subject)
        except AssignedQuestionUser.DoesNotExist:
            return Response({"error": "You are not assigned to post exam set for this subject."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = ExamSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(assigneduser=assigned_user)  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def count(self, request):
        count = Exam.objects.count()
        return Response({"Count": count})

    @action(detail=False, methods=['get'])
    def exams(self, request):
        user = request.user
        exams = Exam.objects.filter(assigneduser__user=user)
        serializer = ExamSerializer(exams, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        exam_id = request.data.get('id', None)
        user = request.user

        if not exam_id:
            return Response({"error": "ID field is required for PUT"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            exam_instance = Exam.objects.get(id=exam_id)

            # Check if the user is an admin
            if user.is_staff:
                serializer = ExamSerializer(exam_instance, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # Check if the user is assigned to this exam
            elif exam_instance.assigneduser.user == user:
                serializer = ExamSerializer(exam_instance, data=request.data)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                return Response({"error": "You do not have permission to update this exam."},
                                status=status.HTTP_403_FORBIDDEN)

        except Exam.DoesNotExist:
            return Response({"error": "Exam not found."}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Exam deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

    def put(self, request, *args, **kwargs):
        exam_id = request.data.get('id', None)


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
        offline_qualified_level_2 = TeacherExamResult.objects.filter(
            user=user, exam__type='offline', isqualified=True,
            exam__subject_id=subject_id, exam__class_category_id=class_category_id, exam__level_id=2
        ).exists()
        # Filter exams based on qualifications
        if not qualified_level_1:
            exams = exams.filter(level_id=1)  # If not qualified for Level 1, return only Level 1 exams
        elif qualified_level_1 and not online_qualified_level_2:
            exams = exams.filter(level_id__in=[1, 2], type='online')  # If qualified for Level 1, show Level 1 and Level 2 exams
        elif online_qualified_level_2 and not offline_qualified_level_2:
            exams = exams.filter(level_id__in=[1, 2, 3])  # If qualified for Level 2 online, show Level 2 offline exams
        # Exclude exams the user has already qualified for
        unqualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=False).values_list('exam_id',
                                                                                                          flat=True)
        exams = exams.exclude(id__in=unqualified_exam_ids)

        qualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=True).values_list('exam_id',
                                                                                                       flat=True)
        exams = exams.exclude(id__in=qualified_exam_ids)
        exam_set = exams.order_by('created_at')  # Get the first exam based on the creation date

        level_1_exam = exam_set.filter(level_id=1).first()
        level_2_online_exam = exam_set.filter(level_id=2, type='online').first()
        level_2_offline_exam = exam_set.filter(level_id=3, type='offline').first()

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


class ReportViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
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
        return Response({"error": "GET method is not allowed on this endpoint."},
                        status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def create(self, request):
        user = request.user
        question_id = request.data.get('question')
        try:
            question = Question.objects.get(id=question_id)
        except Question.DoesNotExist:
            return Response({"error": "Question not found."}, status=status.HTTP_400_BAD_REQUEST)
        if Report.objects.filter(user=user, question=question).exists():
            return Response({"error": "You have already submitted a report for this question."},
                            status=status.HTTP_400_BAD_REQUEST)
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

        level_1_qualified = TeacherExamResult.objects.filter(user=user, exam__level_id=1, exam__type="online",
                                                             isqualified=True).exists()
        level_2_online_qualified = TeacherExamResult.objects.filter(user=user, exam__level_id=2, exam__type="online",
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
            status=False,
        )
        exam_serializer = ExamSerializer(exam)
        center_serializer = ExamCenterSerializer(center)
        return Response({"message": "Passkey generated successfully.",
                         "center": center_serializer.data,

                         "exam": exam_serializer.data
                         },
                        status=status.HTTP_200_OK)


class ApprovePasscodeView(APIView):
    # permission_classes = [IsAdminUser]  # Only accessible by admin users

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
        passkey_status = Passkey.objects.filter(user=user_id, exam=exam_id, code=entered_passcode, status=False)
        if passkey_status.exists():
            return Response(
                {"error": "Passcode verification is allowed only if the passcode is approved by the exam center."})
        try:
            passkey_obj = Passkey.objects.get(user_id=user_id, exam_id=exam_id, code=entered_passcode)
        except Passkey.DoesNotExist:
            return Response({"error": "Invalid passcode or exam."}, status=status.HTTP_400_BAD_REQUEST)

        passkey_obj.status = False
        passkey_obj.save()
        exam = passkey_obj.exam
        exam_serializer = ExamSerializer(exam)
        if passkey_obj.status == False:
            passkey_obj.delete()
        # result = TeacherExamResult.objects.filter(user=user_id, exam=exam_id).first()
        # if result:
        #     passkey_obj.delete()
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
                return Response(
                    {"error": "You already have a pending interview. Please complete it before scheduling another."},
                    status=status.HTTP_400_BAD_REQUEST)
            if Interview.objects.filter(user=user, time=time, subject=subject, class_category=class_category).exists():
                return Response({"error": "Interview with the same details already exists."},
                                status=status.HTTP_400_BAD_REQUEST)
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
                    return Response({"error": "You can only update the 'status' field."},
                                    status=status.HTTP_400_BAD_REQUEST)
                serializer = PasskeySerializer(passkey_instance, data=request.data, partial=True)
                if serializer.is_valid():
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
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = AllTeacherSerializer

    def get_queryset(self):
        queryset = CustomUser.objects.filter(is_staff=False)

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
                else:
                    name_query |= Q(Fname__icontains=name) | Q(Lname__icontains=name)
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

        assign_user_subjects = request.data.get("subject", [])
        if not assign_user_subjects or not isinstance(assign_user_subjects, list):
            return Response({
                "error": "Subjects not provided",
                "message": "Please provide a subject."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Get existing assignments for this user
        existing_subjects = AssignedQuestionUser.objects.filter(user=user).values_list('subject__id', flat=True)

        # Check for duplicate assignments
        already_assigned = set(assign_user_subjects) & set(existing_subjects)
        if already_assigned:
            return Response({
                "error": "User is already assigned to some subjects",
                "message": f"This user is already assigned to subjects with IDs: {list(already_assigned)}"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Create or get AssignedQuestionUser instance
        assigned_user_subject, created = AssignedQuestionUser.objects.get_or_create(user=user)
        subjects_to_assign = Subject.objects.filter(id__in=assign_user_subjects)

        # Assign subjects to the user
        assigned_user_subject.subject.set(subjects_to_assign)

        # Serialize and return response
        assign_user_subject_serializer = AssignedQuestionUserSerializer(assigned_user_subject)
        return Response({
            "user": user_serializer.data,
            "subjects": assign_user_subject_serializer.data,
            "message": "User and subjects assigned successfully"
        }, status=status.HTTP_201_CREATED)


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

class RecHireRequestViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = HireRequestSerializer
    queryset = HireRequest.objects.all()

    def create(self, request):
        recruiter_id = request.user.id
        data = request.data.copy()
        data['recruiter_id'] = recruiter_id
        serializer = HireRequestSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_queryset(self):
        recruiter_id=self.request.user
        return HireRequest.objects.filter(recruiter_id=recruiter_id)
    
class RecruiterEnquiryFormViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterEnquiryFormSerializer
    queryset = RecruiterEnquiryForm.objects.all()
    permission_classes = [permissions.AllowAny]  

    def create(self, request, *args, **kwargs):
        return Response({"detail": "POST method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
class SelfRecruiterEnquiryFormViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterEnquiryFormSerializer
    queryset = RecruiterEnquiryForm.objects.all()
    permission_classes = [permissions.AllowAny]  # No authentication required

    def list(self, request, *args, **kwargs):
        return Response({"detail": "GET method not allowed"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the form without requiring authentication
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

