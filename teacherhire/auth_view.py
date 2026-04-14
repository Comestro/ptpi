# Authentication and User Management Views 
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.timezone import now
from django.conf import settings
from datetime import timedelta
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.hashers import make_password
import uuid
from teacherhire.serializers import *
from teacherhire.utils import send_otp_via_email, verified_msg
from .authentication import ExpiringTokenAuthentication
from drf_spectacular.utils import extend_schema, OpenApiResponse

class RegisterUser(APIView):
    authentication_classes = []

    @extend_schema(
        request=[RecruiterRegisterSerializer, TeacherRegisterSerializer],
        responses={
            201: OpenApiResponse(description="User registered successfully"),
            400: OpenApiResponse(description="Invalid input data")
        },
        description="Register a user as recruiter or teacher based on role parameter."
    )
    def post(self, request, role=None):
        serializer_class = {
            'recruiter': RecruiterRegisterSerializer,
            'teacher': TeacherRegisterSerializer
        }.get(role, TeacherRegisterSerializer)

        serializer = serializer_class(data=request.data)

        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            fname = serializer.validated_data['Fname']
            lname = serializer.validated_data['Lname']
            
            # Generate OTP
            otp = send_otp_via_email(email)
            
            # Create or update pending registration
            pending_user, created = PendingRegistration.objects.update_or_create(
                email=email,
                defaults={
                    'password_hash': make_password(password),
                    'Fname': fname,
                    'Lname': lname,
                    'role': role,
                    'otp': otp,
                    'otp_created_at': now()
                }
            )

            return Response({
                "payload": serializer.data,
                "role": role,
                "message": "Check your email to verify your account."
            }, status=status.HTTP_201_CREATED)
        
        # Handle errors (same as before)
        errors = []
        for field, messages in serializer.errors.items():
            for message in messages:
                errors.append({
                    "code": "invalid",
                    "detail": str(message),
                    "attr": field
                })

        return Response({
            "status": "error",
            "type": "validation_error",
            "errors": errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()

            # Keep user logged in after password change
            update_session_auth_hash(request, request.user)

            return Response({"message": "Password updated successfully!"}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def generate_refresh_token():
    return str(uuid.uuid4())


class LoginUser(APIView):
    authentication_classes = []

    def post(self, request):
        email, password = request.data.get('email'), request.data.get('password')

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # Check if there is a pending registration
            pending = PendingRegistration.objects.filter(email=email).first()
            if pending:
                # Trigger a new OTP for the pending registration
                otp = send_otp_via_email(email)
                pending.otp = otp
                pending.otp_created_at = now()
                pending.save()
                
                return Response({
                    "message": "Please verify your account. A new OTP has been sent to your email.",
                    "is_verified": False,
                    "is_pending": True,
                    "email": email
                }, status=status.HTTP_400_BAD_REQUEST)
                
            raise ValidationError({
                "email": ["Invalid email or password."]
            })

        if not user.is_verified:
            # Trigger a new OTP if they are not verified in the main table
            otp = send_otp_via_email(user.email)
            user.otp = otp
            user.otp_created_at = now()
            user.save(update_fields=['otp', 'otp_created_at'])
            
            return Response({
                "message": "Please verify your account. A new OTP has been sent to your email.",
                "is_verified": user.is_verified,
                "email": user.email
            }, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(password):
            raise ValidationError({
                "password": ["Invalid email or password."]
            })

        if not user.is_active:
            return Response({
                "status": "error",
                "message": "Your account has been deactivated. Please contact the administrator.",
                "is_active": False
            }, status=status.HTTP_403_FORBIDDEN)

        token = Token.objects.filter(user=user).first()
        if token:
            # Check if existing token has expired
            from datetime import timedelta
            expiration_time = timedelta(seconds=settings.TOKEN_EXPIRATION_TIME)
            if now() > token.created + expiration_time:
                 token.delete()
                 token = Token.objects.create(user=user)
        else:
            token = Token.objects.create(user=user)
        refresh_token = str(uuid.uuid4())

        role = (
            "admin" if user.is_staff else
            "recruiter" if user.is_recruiter else
            "teacher" if user.is_teacher else
            "centeruser" if user.is_centeruser else
            "questionuser" if user.is_questionuser else "user"
        )

        return Response({
            "status": "success",
            "message": "Login successful",
            "data": {
                "access_token": token.key,
                "refresh_token": refresh_token,
                "Fname": user.Fname,
                "email": user.email,
                "role": role,
                "user_code": user.user_code,
                "is_active": user.is_active,
            }
        }, status=status.HTTP_200_OK)



class LogoutUser(APIView):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"success": "Logout successful"}, status=status.HTTP_200_OK)


class PasswordResetRequest(APIView):
    def post(self, request):
        serializer = SendPasswordResetEmailSerializer(data=request.data)
        if serializer.is_valid():
            return Response({'msg': 'Password reset link sent. Check your email.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetPasswordView(APIView):
    def post(self, request, uid, token):
        serializer = ResetPasswordSerializer(data=request.data, context={'uid': uid, 'token': token})
        if serializer.is_valid():
            return Response({"msg": "Password reset successful."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    authentication_classes = []

    def post(self, request):
        email = request.data.get("email")
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return Response({"error":"User not found"}, status=status.HTTP_400_BAD_REQUEST)
        if user.is_verified:
            return Response({"message":"Your account is already verified."}, status=status.HTTP_400_BAD_REQUEST)
        Token.objects.filter(user=user).delete()
        auth_token, _ = Token.objects.get_or_create(user=user)
        user.auth_token = auth_token
        user.save()
        verify_link = f"https://ptpinstitute.com/verify-account/{auth_token.key}"
        send_mail("Verify Your Account ",f"Click the link to verify your account: {verify_link}",settings.EMAIL_HOST_USER,[email])
        print(verify_link)
        return Response({"message": "Verification link sent to your email."},status=status.HTTP_200_OK)


class VerifyLinkView(APIView):
    def get(self, request, token):
        try:
            user = CustomUser.objects.get(auth_token=token)
            if user.is_verified:
                return Response({"message":"Your account is already verified."}, status=status.HTTP_400_BAD_REQUEST)
        except CustomUser.DoesNotExist:
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        user.is_verified = True
        # user.auth_token.delete()
        user.save()
        auth_token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "message": "Your account has been verified successfully.",
            "access_token": auth_token.key
        },
        status=status.HTTP_200_OK
        )


class VerifyOTP(APIView):
    authentication_classes = []

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        otp = serializer.validated_data['otp']

        # 1. Check existing users in the main table
        user = CustomUser.objects.filter(email=email).first()
        if user:
            if user.is_verified:
                raise ValidationError({"email": ["Your account is already verified."]})
            
            if user.otp != otp:
                raise ValidationError({"otp": ["Incorrect OTP provided."]})

            if now() > user.otp_created_at + timedelta(minutes=10):
                raise ValidationError({"otp": ["OTP expired. Please request a new OTP."]})

            user.is_verified = True
            user.save()
            return self.get_login_response(user)

        # 2. Check pending registrations
        pending = PendingRegistration.objects.filter(email=email).first()
        if pending:
            if pending.otp != otp:
                raise ValidationError({"otp": ["Incorrect OTP provided."]})

            if now() > pending.otp_created_at + timedelta(minutes=10):
                raise ValidationError({"otp": ["OTP expired. Please request a new OTP."]})

            # Create the actual User
            base_username = email.split('@')[0]
            username = base_username
            while CustomUser.objects.filter(username=username).exists():
                import random
                username = f"{base_username}{random.randint(1000, 9999)}"

            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=None, # Will set the raw hash directly
                Fname=pending.Fname,
                Lname=pending.Lname,
                is_teacher=(pending.role == 'teacher'),
                is_recruiter=(pending.role == 'recruiter'),
                is_verified=True
            )
            user.password = pending.password_hash # Copy the already hashed password
            user.save()
            
            # Delete the pending record
            pending.delete()
            
            return self.get_login_response(user)

        raise ValidationError({"email": ["Email not found or registration expired."]})

    def get_login_response(self, user):
        # Helper to generate the same login payload we use everywhere
        token = Token.objects.filter(user=user).first()
        if token:
            # Check if existing token has expired
            expiration_time = timedelta(seconds=settings.TOKEN_EXPIRATION_TIME)
            if now() > token.created + expiration_time:
                 token.delete()
                 token = Token.objects.create(user=user)
        else:
            token = Token.objects.create(user=user)
            
        refresh_token = str(uuid.uuid4())
        
        role = (
            "admin" if user.is_staff else
            "recruiter" if user.is_recruiter else
            "teacher" if user.is_teacher else
            "centeruser" if user.is_centeruser else
            "questionuser" if user.is_questionuser else "user"
        )

        verified_msg(user.email)

        return Response({
            "status": "success",
            "message": "Account verified and logged in successfully.",
            "data": {
                "access_token": token.key,
                "refresh_token": refresh_token,
                "Fname": user.Fname,
                "email": user.email,
                "role": role,
                "user_code": user.user_code,
                "is_active": user.is_active,
            }
        }, status=status.HTTP_200_OK)
    

class ResendOTP(APIView):
    authentication_classes = []

    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()

        if not user:
            # Check pending registrations
            pending = PendingRegistration.objects.filter(email=email).first()
            if not pending:
                raise ValidationError({"email": ["User not found."]})
            
            # Resend for pending
            otp = send_otp_via_email(email)
            pending.otp = otp
            pending.otp_created_at = now()
            pending.save()
            return Response({"status": "success", "message": "OTP resent successfully (Pending)."}, status=status.HTTP_200_OK)

        if user.is_verified:
            raise ValidationError({"email": ["Account already verified."]})

        otp = send_otp_via_email(user.email)
        user.otp = otp
        user.otp_created_at = now()
        user.save(update_fields=['otp', 'otp_created_at'])

        return Response({
            "status": "success",
            "message": "OTP resent successfully."
        }, status=status.HTTP_200_OK)



class UserVerify(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return Response({'error': 'User not found', 'message': 'Invalid email'}, status=status.HTTP_404_NOT_FOUND)
        if not user.is_verified:
            return Response({'error': 'User not verified', 'message': 'Verify your email first'},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "verified": True,
            "email": user.email,
            "username": user.username,
            "First name": user.Fname,
            "Last name": user.Lname,
            "message": 'User is verified'
        }, status=status.HTTP_200_OK)


class DeactivateAccount(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        user.is_active = False
        user.save()
        return Response({'message': 'Account deactivated successfully'}, status=status.HTTP_200_OK)