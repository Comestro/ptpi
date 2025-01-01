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
from django.db.utils import IntegrityError




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
        email=serializer.data['email']
        send_otp_via_email(email)
        # request.session['email'] = email
        user = CustomUser.objects.get(email=email)

        return Response({
            'payload': serializer.data,
            'message': 'Your data is saved. Please check your email and verify your account first.'
        },status=status.HTTP_200_OK)

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
        email=serializer.data['email']
        user = CustomUser.objects.get(email=email)

        return Response({
            'payload': serializer.data,
            'message': 'Your data is saved. Please check your email and verify your account first.'
        },status=status.HTTP_200_OK)
    
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
      
            is_admin =  user.is_staff          
            roles = {                
                'is_admin': user.is_staff,
                'is_recruiter': user.is_recruiter,
                'is_user': not (user.is_staff and user.is_recruiter)
                
            }
            if user.is_staff :
                role = 'admin'
            elif user.is_recruiter:
                role = 'recruiter'
            else:
                role = 'user'
            return Response({
                'access_token': token.key,
                'refresh_token': refresh_token,
                'Fname':user.Fname, 
                'email':user.email, 
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
        
#TeacerAddress GET ,CREATE ,DELETE 
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
        data['user'] = request.user.id
        
        address = TeachersAddress.objects.filter(user=request.user).first()

        if address:
           return update_auth_data(
               serialiazer_class=self.get_serializer_class(),
               instance=address,
               request_data=data,
               user=request.user
           )
        else:
            return create_auth_data(
                serializer_class=self.get_serializer_class(),
                request_data=data,
                user=request.user,
                model_class=TeachersAddress
            )
    def get_queryset(self):
        return TeachersAddress.objects.filter(user=self.request.user)

    def list(self, request, *args, **kwargs):
        current_address = self.get_queryset().filter(address_type='current').first()
        permanent_address = self.get_queryset().filter(address_type='permanent').first()

        current_address_data = self.get_serializer(current_address).data if current_address else None
        permanent_address_data = self.get_serializer(permanent_address).data if permanent_address else None

        data = {
            "current_address" : current_address_data,
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
    
    @action(detail=True, methods=['get'], url_path=r'classes/(?P<class_category_id>[^/.]+)/?subject/(?P<subject_id>[^/.]+)/?questions')
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
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(Subject)
        return Response({"Count":count})
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "subject deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class TeacherViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset= Teacher.objects.all().select_related('user')
    serializer_class = TeacherSerializer

    # def create(self,request):
    #     return create_object(TeacherSerializer,request.data,Teacher)
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(Teacher)
        return Response({"Count":count})
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacher deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
class SingleTeacherViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    serializer_class = TeacherSerializer

    def create(self,request,*args, **kwargs):
        return create_auth_data(self, TeacherSerializer, request.data, Teacher)
    
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

    def create(self,request):
        return create_object(ClassCategorySerializer,request.data,ClassCategory)
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(ClassCategory)
        return Response({"Count":count})
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
            qualification= TeacherQualification.objects.get(id=qualification_id, user=user)
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
                {"error": f"A record with qualification '{qualification}' and year of passing '{year_of_passing}' already exists."},
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

    def create(self,request,*args, **kwargs):
        return create_object(TeacherExperiencesSerializer,request.data,TeacherExperiences)
   
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(TeacherExperiences)
        return Response({"Count":count}) 
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

    # @action(
    #     detail=False,
    #     methods=['get'],
    #     url_path='questions',
    # )
    # def questions(self, request):
    #     questions = Question.objects.all()

    #     level_id = request.query_params.get('level', None)
    #     if level_id:
    #         try:
    #             level = Level.objects.get(pk=level_id)
    #         except Level.DoesNotExist:
    #             return Response({"error": "Level not found"}, status=status.HTTP_404_NOT_FOUND)
    #         questions = questions.filter(level=level)

    #     subject_id = request.query_params.get('subject', None)
    #     if subject_id:
    #         try:
    #             subject = Subject.objects.get(pk=subject_id)
    #         except Subject.DoesNotExist:
    #             return Response({"error": "Subject not found"}, status=status.HTTP_404_NOT_FOUND)
    #         questions = questions.filter(subject=subject)

    #     class_category_id = request.query_params.get('classCategory', None)
    #     if class_category_id:
    #         try:
    #             class_category = ClassCategory.objects.get(pk=class_category_id)
    #         except ClassCategory.DoesNotExist:
    #             return Response({"error": "Class Category not found"}, status=status.HTTP_404_NOT_FOUND)
    #         questions = questions.filter(classCategory=class_category)

    #     language = request.query_params.get('language', None)
    #     if language:
    #         if language not in ['Hindi', 'English']:
    #             return Response({"error": "Invalid language. Choose 'Hindi' or 'English'."}, status=status.HTTP_400_BAD_REQUEST)
    #         questions = questions.filter(language=language)

    #     serializer = QuestionSerializer(questions, many=True)
    #     return Response(serializer.data, status=status.HTTP_200_OK)
    
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
        
        teacher_class_category = TeacherClassCategory.objects.filter(user=user, class_category=exam.class_category).exists()
        teacher_subject = TeacherSubject.objects.filter(user=user, subject=exam.subject).exists()

        if not teacher_class_category or not teacher_subject:
            return Response(
                {"error": "You do not have permission to access this exam."},
                status=status.HTTP_403_FORBIDDEN
            )

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
    def create(self,request):
        return create_object(RoleSerializer,request.data,Role)
    
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(Role)
        return Response({"Count":count})
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
    def create(self,request):
        return create_object(TeacherSubjectSerializer,request.data,TeacherSubject)
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(TeacherSubject)
        return Response({"Count":count})
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
        if TeacherSubject.objects.filter(user=request.user).exists():
            return Response({"detail": "SingleTeacherSubject already exists. "}, status=status.HTTP_400_BAD_REQUEST)
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
    def create(self,request):
        return create_object(TeacherClassCategorySerializer,request.data,TeacherClassCategory)
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(TeacherClassCategory)
        return Response({"Count":count})
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
            return Response({"detail": "SingleTeacher class category already exists. "}, status=status.HTTP_400_BAD_REQUEST)
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
        
    
    @action (detail=False,methods=['get'])
    def count(self,request):
        count = get_count(TeacherExamResult)
        return Response({"Count":count}) 
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Teacher exam result deleted successfully"}, status=status.HTTP_204_NO_CONTENT)   

class JobPreferenceLocationViewSet(viewsets.ModelViewSet):    
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication] 
    queryset= JobPreferenceLocation.objects.all()
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
            return Response({"error": "You can only update locations linked to your preference."}, status=status.HTTP_403_FORBIDDEN)

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
            raise Response({"detail": "Profile not found and could not be created."}, status=status.HTTP_400_BAD_REQUEST)


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
    # permission_classes = [IsAuthenticated]    
    # authentication_classes = [ExpiringTokenAuthentication]
    queryset = TeacherJobType.objects.all()
    serializer_class = TeacherJobTypeSerializer

class SendPasswordResetEmailViewSet(APIView):
    def post(self, request, formate=None):
        serializer = SendPasswordResetEmailSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            return Response({'msg': 'Password reset link send. Please check email.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordViewSet(APIView):
    def post(self, request, uidb64, token, fomate=None):
        serializer = ResetPasswordSerializer(data=request.data, context={'uid': uidb64, 'token': token})
        if serializer.is_valid(raise_exception=True):
            return Response({'msg': 'Password reset Successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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

    @action(detail=False, methods=['get'])
    def exams(self, request):
        user = request.user
        level_id = request.query_params.get('level_id', None)
        class_category_id = request.query_params.get('class_category_id', None)
        subject_id = request.query_params.get('subject_id', None)
        
        exams = Exam.objects.all()

        if class_category_id:
            teacher_class_category = TeacherClassCategory.objects.filter(user=user, pk=class_category_id).first()
            if not teacher_class_category:
                return Response(
                    {"message": "Please choose a valid class category."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            exams = exams.filter(class_category=teacher_class_category.class_category)
        
        if subject_id:
            teacher_subject = TeacherSubject.objects.filter(user=user, pk=subject_id).first()
            if not teacher_subject:
                return Response(
                    {"message": "Please choose a valid subject."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            exams = exams.filter(subject=teacher_subject.subject)
        
        # exams = Exam.objects.filter(
        #     class_category=teacher_class_category.class_category,
        #     subject=teacher_subject.subject
        # )

        if level_id:
            try:
                level = Level.objects.get(pk=level_id)
                exams = exams.filter(level=level)
            except Level.DoesNotExist:
                return Response({"error": "Level not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ExamSerializer(exams, many=True)
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
                {"name": "Final Exam", "total_marks": 100, "duration": 180},
                {"name": "Mid Term", "total_marks": 50, "duration": 90},
                {"name": "Quiz", "total_marks": 20, "duration": 30},
                {"name": "Semester Exam", "total_marks": 200, "duration": 240},
                {"name": "Practical Exam", "total_marks": 50, "duration": 120}
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
            if isinstance(entry, dict):  # Handle entries with multiple fields (e.g., exams)
                name = entry.get("name")
                total_marks = entry.get("total_marks")
                duration = entry.get("duration")
                
                # Get a class category (you may need a more specific logic here)
                class_category = ClassCategory.objects.first()  # Example: choosing the first available class category
                
                # Get a level (ensure there is at least one level in the database)
                level = Level.objects.first()  # Example: choosing the first available level
                subject =Subject.objects.first()

                if not model.objects.filter(name=name).exists():
                    model.objects.create(
                        name=name,
                        total_marks=total_marks,
                        duration=duration,
                        class_category=class_category,
                        level=level ,
                        subject=subject # Ensure the level is assigned to the exam
                    )
                    added_count += 1
            else:  # Handle other entries (e.g., class categories, roles)
                if not model.objects.filter(**{field: entry}).exists():
                    model.objects.create(**{field: entry})
                    added_count += 1

        response_data[key] = {
            "message": f'{added_count} {key.replace("_", " ")} added successfully.' if added_count > 0 else f'All {key.replace("_", " ")} already exist.',
            "added_count": added_count
        }
         # Insert 5 Questions into the database
    exams = Exam.objects.all()  # Get all exams in the database
    if exams.exists():
        # Data for inserting 5 questions
        questions_data = [
            {
                "exam": exams[0],  # Associate with the first exam
                "time": 2.5,
                "language": "English",
                "text": "What is the capital of India?",
                "options": ["New Delhi", "Mumbai", "Kolkata", "Chennai"],
                "solution": "New Delhi is the capital of India.",
                "correct_option": 1
            },
            {
                "exam": exams[0],
                "time": 3.0,
                "language": "Hindi",
                "text": "भारत की राजधानी क्या है?",
                "options": ["नई दिल्ली", "मुंबई", "कोलकाता", "चेन्नई"],
                "solution": "नई दिल्ली भारत की राजधानी है।",
                "correct_option": 1
            },
            {
                "exam": exams[1],  # Associate with the second exam
                "time": 2.0,
                "language": "English",
                "text": "What is 5 + 5?",
                "options": ["8", "9", "10", "11"],
                "solution": "The correct answer is 10.",
                "correct_option": 3
            },
            {
                "exam": exams[2],  # Associate with the third exam
                "time": 1.5,
                "language": "English",
                "text": "What is the boiling point of water?",
                "options": ["90°C", "100°C", "110°C", "120°C"],
                "solution": "The correct answer is 100°C.",
                "correct_option": 2
            },
            {
                "exam": exams[3],  # Associate with the fourth exam
                "time": 2.5,
                "language": "Hindi",
                "text": "भारत में सबसे लंबी नदी कौन सी है?",
                "options": ["गंगा", "यमुना", "सिंधु", "नर्मदा"],
                "solution": "गंगा भारत की सबसे लंबी नदी है।",
                "correct_option": 1
            }
        ]

        # Insert the questions
        question_added_count = 0
        for question in questions_data:
            question_obj = Question.objects.create(
                exam=question["exam"],
                time=question["time"],
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
