from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from teacherhire.models import *
from rest_framework.exceptions import NotFound
from teacherhire.serializers import *
from .authentication import ExpiringTokenAuthentication
from rest_framework.decorators import action
from .permissions import IsRecruiterPermission, IsAdminPermission
import uuid
from .utils import *
from datetime import timedelta
from django.utils.timezone import now
from rest_framework.response import Response
from rest_framework.decorators import action
from django.http import JsonResponse
from django.db.models import F
from django.utils.crypto import get_random_string
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
import random
import string
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db.models import Q


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
            return Response({'message': 'Account is not verified. Please verify your account before logging in.'},
                            status=status.HTTP_403_FORBIDDEN)
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

class TeacherViewSet(viewsets.ModelViewSet):
    # permission_classes = [IsAuthenticated]
    # authentication_classes = [ExpiringTokenAuthentication]
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    @action(detail=False, methods=['get'])
    def teachers(self, request):
        # Get query parameters from the request
        skill_name = request.query_params.get('skill', None)
        preference_id = request.query_params.get('preference', None)
        educational_qualification = request.query_params.get('educationalQualification', None)
        address_id = request.query_params.get('address', None)
        address_state = request.query_params.getlist('state', None)
        address_division = request.query_params.getlist('division', None)
        address_district = request.query_params.getlist('district', None)  # Handle multiple districts
        address_block = request.query_params.getlist('block', None)
        address_village = request.query_params.getlist('village', None)
        job_role_name = request.query_params.getlist('job_role', None)
        class_category_name = request.query_params.get('class_category_name', None)
        prefered_subject_name = request.query_params.getlist('prefered_subject', None)
        teacher_job_type_name = request.query_params.getlist('teacher_job_type', None)

        queryset = Teacher.objects.all()
        filter_messages = {}

        if skill_name:
            queryset = queryset.filter(skill__name__icontains=skill_name)
            filter_messages['skill'] = skill_name
        
        # Filter by preference
        if preference_id:
            queryset = queryset.filter(preference_id=preference_id)
            filter_messages['preference'] = preference_id
        
        # Filter by educational qualification
        if educational_qualification:
            queryset = queryset.filter(educationalQualification__name__icontains=educational_qualification)
            filter_messages['educationalQualification'] = educational_qualification
        
        if address_id:
            queryset = queryset.filter(address_id=address_id)
            filter_messages['address'] = address_id
        
        # Filter by address fields (e.g., state, division, district, etc.)
        if address_state:
            queryset = queryset.filter(address__state__icontains='|'.join(address_state))
            filter_messages['state'] = address_state
        if address_division:
            queryset = queryset.filter(address__division__icontains= '|'.join(address_division))
            filter_messages['division'] = address_division
        if address_district:
            queryset = queryset.filter(address__district__icontains='|'.join(address_district))
            filter_messages['district'] = address_district
        if address_block:
            queryset = queryset.filter(address__block__icontains= '|'.join(address_block))
            filter_messages['block'] = address_block
        if address_village:
            queryset = queryset.filter(address__village__icontains= '|'.join(address_village))
            filter_messages['village'] = address_village
        
        # Filter by job role
        if job_role_name:
            queryset = queryset.filter(preference__job_role__name__in=job_role_name)
            filter_messages['job_role'] = job_role_name
        
        # Filter by class category
        if class_category_name:
            queryset = queryset.filter(preference__class_category__name=class_category_name)
            filter_messages['class_category_name'] = class_category_name
        
        # Filter by preferred subject
        if prefered_subject_name:
            queryset = queryset.filter(preference__prefered_subject__name__in=prefered_subject_name)
            filter_messages['prefered_subject'] = prefered_subject_name
        
        # Filter by teacher job type
        if teacher_job_type_name:
            queryset = queryset.filter(preference__teacher_job_type__name__in=teacher_job_type_name)
            filter_messages['teacher_job_type'] = teacher_job_type_name
        
        # If no teachers match the filters
        if not queryset.exists():
            return Response({
                "filters": filter_messages,
                "message": "No teachers found matching the given criteria."
            })

        # If no filters were applied, show all teachers
        if not filter_messages:
            filter_messages["message"] = "No applied filters. Showing all teachers."

        # Serialize the filtered queryset
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "filters": filter_messages,
            "data": serializer.data
        })



class SingleTeacherViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = TeacherSerializer

    def put(self, request, *args, **kwargs):
        data = request.data.copy()
        data['user'] = request.user.id

        teacher = Teacher.objects.filter(user=request.user).first()

        if teacher:
            return update_auth_data(
                serialiazer_class=self.get_serializer_class(),
                instance=teacher,
                request_data=data,
                user=request.user
            )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=Teacher
            )

    def get_queryset(self):
        return Teacher.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def get_object(self):
        try:
            return Teacher.objects.get(user=self.request.user)
        except Teacher.DoesNotExist:
            raise Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
       
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

    def get_queryset(self):
        return TeacherQualification.objects.filter(user=self.request.user)

    # def list(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)

    # def get_object(self):
    #     try:
    #         return TeacherQualification.objects.get(user=self.request.user)
    #     except TeacherQualification.DoesNotExist:
    #         raise Response({"detail": "Qualification not found."}, status=status.HTTP_404_NOT_FOUND)


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

        # Check if the user already has a preference
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

        if 'teacher_job_type' in data and isinstance(data['teacher_job_type'], str):
            data['teacher_job_type'] = [data['teacher_job_type']]
        if 'prefered_subject' in data and isinstance(data['prefered_subject'], str):
            data['prefered_subject'] = [data['prefered_subject']]

        if 'job_role' in data and isinstance(data['job_role'], str):
            data['job_role'] = [data['job_role']]

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
        # if TeacherSubject.objects.filter(user=request.user).exists():
        #     return Response({"detail": "SingleTeacherSubject already exists. "}, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def list(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)
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

    # def list(self, request, *args, **kwargs):
    #     return self.retrieve(request, *args, **kwargs)
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

        # Example counts
        level1_count = TeacherExamResult.objects.filter(user=user, isqualified=True).count()
        level2_count = TeacherExamResult.objects.filter(user=user, isqualified=False).count()

        response_data = {
            "level1": level1_count,
            "level2": level2_count,
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
            raise Response({"detail": "Profile not found and could not be created."},
                           status=status.HTTP_400_BAD_REQUEST)

    # def get_object(self):
    #     try:
    #         return BasicProfile.objects.get(user=self.request.user)
    #     except BasicProfile.DoesNotExist:
    #         raise Response({"detail": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)
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
            reset_password_link = f'http://localhost:5173/reset-password/{uidb64}/{token}'
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
        user_subjects = user_preference.prefered_subject.all()
        level_1_subjects = [{"subject_id": subject.id, "subject_name": subject.subject_name} for subject in
                            user_subjects]

        qualified_exams = TeacherExamResult.objects.filter(user=user, isqualified=True)

        level_2_subjects = qualified_exams.values(subject_id=F('exam__subject__id'),
                                                  subject_name=F('exam__subject__subject_name')).distinct()
        if qualified_exams:
            levels = [
                {
                    "level_id": 1,
                    "level_name": "Level 1",
                    "subjects": level_1_subjects
                },
                {
                    "level_id": 2,
                    "level_name": "Level 2",
                    "subjects": level_2_subjects
                }
            ]
        else:
            levels = [
                {
                    "level_id": 1,
                    "level_name": "Level 1",
                    "subjects": level_1_subjects
                }
            ]

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
        level_id = request.query_params.get('level_id', None)
        subject_id = request.query_params.get('subject_id', None)
        type = request.query_params.get('type', None)

        exams = Exam.objects.all()

        # If no subject_id is provided, return error
        if not subject_id:
            return Response({"message": "Please choose a subject."}, status=status.HTTP_400_BAD_REQUEST)

        exams = exams.filter(subject_id=subject_id)

        # Get teacher class category preference
        teacher_class_category = Preference.objects.filter(user=user).first()
        if not teacher_class_category:
            return Response(
                {"message": "Please choose a class category first."},
                status=status.HTTP_400_BAD_REQUEST
            )
        exams = exams.filter(class_category=teacher_class_category.class_category)

        # Check qualification for Level 1 and Level 2 exams
        qualified_level_1 = TeacherExamResult.objects.filter(user=user, isqualified=True, exam__subject_id=subject_id,
                                                             exam__level_id=1).exists()
        qualified_level_2 = TeacherExamResult.objects.filter(user=user, isqualified=True, exam__subject_id=subject_id,
                                                             exam__level_id=2).exists()

        # Handle level filter
        if level_id:
            if level_id == '1':
                exams = exams.filter(level__id=1)
            elif level_id == '2':
                if type:
                    if type not in ['online', 'offline']:
                        return Response({"message": "Invalid type. Choose 'online' or 'offline'."}, status=status.HTTP_400_BAD_REQUEST)

                    if type == 'offline' and not qualified_level_2:
                        return Response({"message": "You must qualify Level 2 online exam before taking the offline exam."},
                                        status=status.HTTP_404_NOT_FOUND)

                    exams = exams.filter(type=type)
                if qualified_level_1:
                    level_2_exams = exams.filter(level__id=2)
                    attempted_exam_ids = TeacherExamResult.objects.filter(user=user).values_list('exam_id', flat=True)
                    level_2_exams = level_2_exams.exclude(id__in=attempted_exam_ids)

                    online_exam = level_2_exams.filter(type='online').order_by('created_at').first()
                    
                    offline_exam = level_2_exams.filter(type='offline').order_by('created_at').first()
                    if not online_exam and not offline_exam:
                        return Response({"message": "No new exams available for Level 2."},
                                        status=status.HTTP_404_NOT_FOUND)

                    # Serialize exams separately
                    response_data = {}

                    if online_exam:
                        response_data['online_exam'] = ExamSerializer(online_exam).data
                    if offline_exam:
                        response_data['offline_exam'] = ExamSerializer(offline_exam).data

                    return Response(response_data, status=status.HTTP_200_OK)
                else:
                    return Response({"message": "You must complete Level 1 before accessing Level 2."},
                                    status=status.HTTP_404_NOT_FOUND)
            else:
                return Response({"error": "Invalid level ID."}, status=status.HTTP_400_BAD_REQUEST)

        unqualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=False).values_list('exam_id',
                                                                                                          flat=True)
        exams = exams.exclude(id__in=unqualified_exam_ids)

        qualified_exam_ids = TeacherExamResult.objects.filter(user=user, isqualified=True).values_list('exam_id',
                                                                                                       flat=True)
        exams = exams.exclude(id__in=qualified_exam_ids)

        exam_set = exams.order_by('created_at').first()
        if not exam_set:
            return Response({"message": "No exams available for the given criteria."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExamSerializer(exam_set)
        return Response(serializer.data, status=status.HTTP_200_OK)


def insert_data(request):
    data_to_insert = {
        "class_categories": {
            "model": ClassCategory,
            "field": "name",
            "data": ["1 to 5", "6 to 10", "11 to 12", "BCA", "MCA"]
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
            ]
        },
    }

    response_data = {}

    # Insert class categories, levels, etc.
    for key, config in data_to_insert.items():
        model = config["model"]
        field = config["field"]
        entries = config["data"]

        added_count = 0
        for entry in entries:
            if isinstance(entry, dict):
                name = entry.get("name")
                total_marks = entry.get("total_marks")
                duration = entry.get("duration")
                type = entry.get("type")


                class_category_name = entry.get("class_category")
                level_name = entry.get("level")
                subject_name = entry.get("subject")

                class_category, created = ClassCategory.objects.get_or_create(name=class_category_name)
                level, created = Level.objects.get_or_create(name=level_name)
                subject, created = Subject.objects.get_or_create(subject_name=subject_name)

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
            else:
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
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of India?",
                "options": ["New Delhi", "Mumbai", "Kolkata", "Chennai"],
                "solution": "New Delhi is the capital of India.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 3,
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
                "time": 3,
                "language": "English",
                "text": "Which SQL command is used to retrieve data from a database?",
                "options": ["SELECT", "INSERT", "UPDATE", "DELETE"],
                "solution": "The correct SQL command to retrieve data from a database is 'SELECT'.",
                "correct_option": 1
            },
            {
                "exam": exams[5],
                "time": 3,
                "language": "English",
                "text": "What is normalization in DBMS?",
                "options": ["The process of organizing data to reduce redundancy",
                            "The process of copying data for backup", "The process of making data available online",
                            "The process of encrypting data"],
                "solution": "Normalization is the process of organizing data in a database to reduce redundancy and improve data integrity.",
                "correct_option": 1
            },
            {
                "exam": exams[6],
                "time": 2.5,
                "language": "English",
                "text": "Which of the following is a type of join in SQL?",
                "options": ["INNER JOIN", "OUTER JOIN", "CROSS JOIN", "All of the above"],
                "solution": "The correct answer is 'All of the above'. INNER JOIN, OUTER JOIN, and CROSS JOIN are all types of SQL joins.",
                "correct_option": 3
            },
            {
                "exam": exams[7],
                "time": 3.0,
                "language": "Hindi",
                "text": "भारत की राजधानी क्या है?",
                "options": ["नई दिल्ली", "मुंबई", "कोलकाता", "चेन्नई"],
                "solution": "नई दिल्ली भारत की राजधानी है।",
                "correct_option": 1
            },
            {
                "exam": exams[8],
                "time": 2.0,
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
                "time": 2,
                "language": "Hindi",
                "text": "भारत का सबसे बड़ा राज्य कौन सा है?",
                "options": ["राजस्थान", "उत्तर प्रदेश", "मध्य प्रदेश", "महाराष्ट्र"],
                "solution": "भारत का सबसे बड़ा राज्य राजस्थान है।",
                "correct_option": 1
            },
            {
                "exam": exams[10],
                "time": 2,
                "language": "Hindi",
                "text": "भारत का पहला प्रधानमंत्री कौन थे?",
                "options": ["लाल बहादुर शास्त्री", "पंडित नेहरू", "इंदिरा गांधी", "राजीव गांधी"],
                "solution": "भारत के पहले प्रधानमंत्री पंडित नेहरू थे।",
                "correct_option": 2
            },
            {
                "exam": exams[11],
                "time": 2,
                "language": "Hindi",
                "text": "एक ट्रेन 60 किमी/घंटे की गति से 2 घंटे में कितनी दूरी तय करेगी?",
                "options": ["60 किमी", "120 किमी", "180 किमी", "240 किमी"],
                "solution": "ट्रेन 120 किमी की दूरी तय करेगी।",
                "correct_option": 2
            },
            {
                "exam": exams[5],
                "time": 2.5,
                "language": "English",
                "text": "If a train travels at 60 km/hr for 2 hours, what distance does it cover?",
                "options": ["60 km", "120 km", "180 km", "240 km"],
                "solution": "The train covers 120 km.",
                "correct_option": 2
            },
            {
                "exam": exams[0],
                "time": 2,
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
                "time": 2,
                "language": "Hindi",
                "text": "100 और 250 का औसत क्या है?",
                "options": ["175", "150", "200", "225"],
                "solution": "100 और 250 का औसत 175 है।",
                "correct_option": 1
            },
            {
                "exam": exams[3],
                "time": 2,
                "language": "English",
                "text": "What is the average of 100 and 250?",
                "options": ["175", "150", "200", "225"],
                "solution": "The average of 100 and 250 is 175.",
                "correct_option": 1
            },
            {
                "exam": exams[4],
                "time": 2.5,
                "language": "Hindi",
                "text": "प्रकाश की गति क्या है?",
                "options": ["3 × 10^6 मीटर/सेकेंड", "3 × 10^8 मीटर/सेकेंड", "3 × 10^9 मीटर/सेकेंड",
                            "3 × 10^7 मीटर/सेकेंड"],
                "solution": "प्रकाश की गति 3 × 10^8 मीटर/सेकेंड है।",
                "correct_option": 2
            },
            {
                "exam": exams[5],
                "time": 2,
                "language": "English",
                "text": "What is the speed of light?",
                "options": ["3 × 10^6 m/s", "3 × 10^8 m/s", "3 × 10^9 m/s", "3 × 10^7 m/s"],
                "solution": "The speed of light is 3 × 10^8 m/s.",
                "correct_option": 2
            },
            {
                "exam": exams[6],
                "time": 2,
                "language": "Hindi",
                "text": "न्यूटन के गति का दूसरा नियम क्या है?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "न्यूटन के गति का दूसरा नियम F = ma है।",
                "correct_option": 1
            },
            {
                "exam": exams[7],
                "time": 2.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                "exam": exams[8],
                "time": 2.5,
                "language": "English",
                "text": "What is Newton's second law of motion?",
                "options": ["F = ma", "F = mv", "F = m/v", "F = ma^2"],
                "solution": "Newton's second law of motion is F = ma.",
                "correct_option": 1
            },
            {
                "exam": exams[9],
                "time": 3.0,
                "language": "English",
                "text": "Which of the following is the largest planet in our solar system?",
                "options": ["Earth", "Mars", "Jupiter", "Saturn"],
                "solution": "Jupiter is the largest planet in our solar system.",
                "correct_option": 3
            },
            {
                "exam": exams[10],
                "time": 2.0,
                "language": "English",
                "text": "Who is the author of the play 'Romeo and Juliet'?",
                "options": ["William Shakespeare", "Charles Dickens", "Jane Austen", "Mark Twain"],
                "solution": "The author of 'Romeo and Juliet' is William Shakespeare.",
                "correct_option": 1
            },
            {
                "exam": exams[1],
                "time": 2.0,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 3.0,
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
                "time": 2.0,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 3.0,
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
                "time": 2.0,
                "language": "English",
                "text": "What is the chemical symbol for water?",
                "options": ["H2O", "HO2", "O2H", "H2"],
                "solution": "The chemical symbol for water is H2O.",
                "correct_option": 1
            },
            {
                "exam": exams[2],
                "time": 3.0,
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
                "time": 2.0,
                "language": "English",
                "text": "What is the capital of France?",
                "options": ["Berlin", "Madrid", "Paris", "Rome"],
                "solution": "The capital of France is Paris.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 3.0,
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
                "time": 2.0,
                "language": "English",
                "text": "What is the boiling point of water at sea level?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The boiling point of water at sea level is 100°C.",
                "correct_option": 2
            },
            {
                "exam": exams[8],
                "time": 3.0,
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
                "time": 3.0,
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
                "time": 3,
                "language": "English",
                "text": "What is the square root of 144?",
                "options": ["10", "11", "12", "13"],
                "solution": "The square root of 144 is 12.",
                "correct_option": 3
            },
            {
                "exam": exams[2],
                "time": 3,
                "language": "English",
                "text": "Solve: 5 + 3 × 2.",
                "options": ["11", "16", "21", "13"],
                "solution": "According to the order of operations (BODMAS), 5 + 3 × 2 = 11.",
                "correct_option": 1
            },
            {
                "exam": exams[3],
                "time": 3.5,
                "language": "English",
                "text": "What is 15% of 200?",
                "options": ["25", "30", "35", "40"],
                "solution": "15% of 200 is 30.",
                "correct_option": 2
            },
            {
                "exam": exams[4],
                "time": 4,
                "language": "English",
                "text": "If x + 5 = 12, what is the value of x?",
                "options": ["5", "6", "7", "8"],
                "solution": "Subtracting 5 from both sides gives x = 7.",
                "correct_option": 3
            },
            {
                "exam": exams[5],
                "time": 4,
                "language": "English",
                "text": "Solve: 9 × (3 + 2).",
                "options": ["36", "40", "45", "50"],
                "solution": "Using BODMAS, 9 × (3 + 2) = 45.",
                "correct_option": 3
            },
            {
                "exam": exams[6],
                "time": 3.5,
                "language": "English",
                "text": "What is the perimeter of a rectangle with length 10 and width 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The perimeter of a rectangle is 2 × (length + width). So, 2 × (10 + 5) = 30.",
                "correct_option": 3
            },
            {
                "exam": exams[7],
                "time": 4,
                "language": "English",
                "text": "What is the value of 2³?",
                "options": ["6", "8", "9", "12"],
                "solution": "2³ means 2 × 2 × 2 = 8.",
                "correct_option": 2
            },
            {
                "exam": exams[8],
                "time": 3.5,
                "language": "English",
                "text": "What is the area of a triangle with base 8 and height 5?",
                "options": ["20", "25", "30", "35"],
                "solution": "The area of a triangle is ½ × base × height. So, ½ × 8 × 5 = 20.",
                "correct_option": 1
            },
            {
                "exam": exams[9],
                "time": 3,
                "language": "English",
                "text": "What is the value of 100 ÷ 4?",
                "options": ["20", "25", "30", "40"],
                "solution": "100 ÷ 4 = 25.",
                "correct_option": 2
            },
            {
                "exam": exams[12],
                "time": 3,
                "language": "English",
                "text": "What is the unit of force?",
                "options": ["Newton", "Pascal", "Joule", "Watt"],
                "solution": "The SI unit of force is the Newton (N), named after Isaac Newton.",
                "correct_option": 0
            },
            {
                "exam": exams[12],
                "time": 3,
                "language": "English",
                "text": "What is the acceleration due to gravity on Earth?",
                "options": ["9.8 m/s²", "8.9 m/s²", "10.2 m/s²", "7.6 m/s²"],
                "solution": "The acceleration due to gravity on Earth is approximately 9.8 m/s².",
                "correct_option": 0
            },
            {
                "exam": exams[13],
                "time": 4,
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
                "time": 5,
                "language": "English",
                "text": "Which of the following is a scalar quantity?",
                "options": ["Velocity", "Force", "Speed", "Momentum"],
                "solution": "Speed is a scalar quantity because it has only magnitude, not direction.",
                "correct_option": 2
            },
            {
                "exam": exams[14],
                "time": 4,
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
                "time": 3,
                "language": "English",
                "text": "What is the speed of light in a vacuum?",
                "options": [
                    "3 × 10⁸ m/s",
                    "2 × 10⁸ m/s",
                    "1.5 × 10⁸ m/s",
                    "4 × 10⁸ m/s"
                ],
                "solution": "The speed of light in a vacuum is approximately 3 × 10⁸ meters per second.",
                "correct_option": 0
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
                    time=question["time"],
                    language=question["language"],
                    text=question["text"],
                    options=question["options"],
                    solution=question["solution"],
                    correct_option=question["correct_option"]
                )
                question_added_count += 1
            else:
                print(f"Question already exists: {question['text']}")

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
 
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User with this Id does not exist."}, status=status.HTTP_400_BAD_REQUEST)
 
        try:
            exam = Exam.objects.get(id=exam_id)
        except Exam.DoesNotExist:
            return Response({"error": "Exam with this ID does not exist."}, status=status.HTTP_400_BAD_REQUEST)
 
        # Check if the user has qualified in any attempt
        results = TeacherExamResult.objects.filter(user=user, exam=exam)
        if not results.exists():
            return Response({"error": "No exam results found for this user."}, status=status.HTTP_400_BAD_REQUEST)
 
        # Check qualification status across all attempts
        qualified = results.filter(isqualified=True).exists()
        if not qualified:
            return Response({"error": "User did not score the required 60% or above in any attempt."},
                status=status.HTTP_400_BAD_REQUEST)
 
        # Check if user qualifies at level 2 and if the qualification type is 'online'
        level_2_results = results.filter(isqualified=True, exam__level_id=2)
        qualified_level_2_offline = level_2_results.filter(exam__type="online").exists()
        if not qualified_level_2_offline:
            return Response({"error": "User did not qualify at level 2 online."}, status=status.HTTP_400_BAD_REQUEST)
 
        # Check if a passkey already exists
        existing_passkey = Passkey.objects.filter(user=user, exam=exam).first()
        if existing_passkey:
            return Response({"error": "A passkey has already been generated for this exam."},
                            status=status.HTTP_400_BAD_REQUEST)
 
        # Generate a new passkey
        passkey = random.randint(1000, 9999)
 
        passkey_obj = Passkey.objects.create(
            user=user,
            exam=exam,
            code=str(passkey),
            status=False,
        )
 
        # # Email setup
        # subject = "Your Exam Access Passcode"
        # message = f"Your passcode for accessing the exam is {passkey}. It is valid for 10 minutes. Please use it to verify your access."
        # html_message = f"""
        # <div style="max-width: 600px; margin: 20px auto; padding: 20px; border-radius: 10px; background-color: #f9f9f9; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); text-align: center; font-family: Arial, sans-serif; color: #333;">
        #     <h2 style="color: #008080; font-size: 24px; margin-bottom: 10px;">Purnia Private Teacher Institution</h2>
        #     <p style="font-size: 16px; margin-bottom: 20px;">Use the passcode below to complete your verification process for the exam.</p>
        #     <p style="display: inline-block; padding: 10px 20px; font-size: 36px; font-weight: bold; color: #ffffff; background-color: #008080; border-radius: 8px; text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);">
        #         {passkey}
        #     </p>
        #     <p style="margin-top: 20px; font-size: 14px; color: #555;">This passcode is valid for 10 minutes. Please do not share it with anyone.</p>
        # </div>
        # """
 
        # from_email = os.environ.get('EMAIL_FROM', settings.DEFAULT_FROM_EMAIL)
 
        # send_mail(
        #     subject,
        #     message,
        #     from_email,
        #     [user.email],
        #     html_message=html_message
        # )
 
        return Response({"message": "Passkey generated successfully."}, status=status.HTTP_200_OK)
 
class ApprovePasscodeView(APIView):
    #permission_classes = [IsAdminPermission]  # Only accessible by admin users
 
    def post(self, request):
        user_id = request.data.get('user_id')
        exam_id = request.data.get('exam_id')
 
        try:
            # Fetch the passkey object
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
            return Response({"error": "Missing required fields: user_id, exam_id, or passcode."},
            status=status.HTTP_400_BAD_REQUEST)
 
        try:
            # Fetch the passkey objectIsAdminUser
            passkey_obj = Passkey.objects.get(user_id=user_id, exam_id=exam_id, code=entered_passcode)
        except Passkey.DoesNotExist:
            return Response({"error": "Invalid passcode or exam."}, status=status.HTTP_400_BAD_REQUEST)
 
        # Check if the passkey is approved by the admin
        if not passkey_obj.status:
            return Response({"error": "Passcode is not approved by the admin ."},
            status=status.HTTP_400_BAD_REQUEST)
 
        # Mark the passkey as used after successful validation
        passkey_obj.status = False
        passkey_obj.save()
 
        return Response({"message": "Passcode verified successfully."}, status=status.HTTP_200_OK)
 