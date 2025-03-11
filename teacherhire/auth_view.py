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
import uuid
from teacherhire.serializers import *
from teacherhire.utils import send_otp_via_email, verified_msg
from .authentication import ExpiringTokenAuthentication
from django.shortcuts import get_object_or_404

class RegisterUser(APIView):
    def post(self, request, role=None):
        serializer_class = {
            'recruiter': RecruiterRegisterSerializer,
            'teacher': TeacherRegisterSerializer
        }.get(role, TeacherRegisterSerializer)

        serializer = serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': serializer.errors, 
                'message': 'Something went wrong'
            }, status=status.HTTP_409_CONFLICT)
            return Response({'message': serializer.errors},
                            status=status.HTTP_400_BAD_REQUEST)


        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user) 
        role = "admin" if user.is_staff else \
            "recruiter" if user.is_recruiter else \
                "teacher" if user.is_teacher else \
                    "centeruser" if user.is_centeruser else \
                        "questionuser" if user.is_questionuser else "user"

        # user = serializer.save()
        # otp = send_otp_via_email(user.email)
        # user.otp = otp
        # user.otp_created_at = now()
        # user.save(update_fields=['otp', 'otp_created_at'])
        return Response({
            'payload': serializer.data,
            'role': role,
            'access_token': token.key,
            'message': 'Check your email to verify your account.'
        }, status=status.HTTP_200_OK)
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [ExpiringTokenAuthentication]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            return Response({"message": "Password updated successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def generate_refresh_token():
    return str(uuid.uuid4())


class LoginUser(APIView):
    def post(self, request):
        email, password = request.data.get('email'), request.data.get('password')
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_verified:
            return Response({'message': 'Please verify your account before logging in.'},
                            status=status.HTTP_403_FORBIDDEN)

        if not user.check_password(password):
            return Response({'message': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        refresh_token = generate_refresh_token()

        role = "admin" if user.is_staff else \
            "recruiter" if user.is_recruiter else \
                "teacher" if user.is_teacher else \
                    "centeruser" if user.is_centeruser else \
                        "questionuser" if user.is_questionuser else "user"

        return Response({
            'access_token': token.key,
            'refresh_token': refresh_token,
            'Fname': user.Fname,
            'email': user.email,
            'role': role,
            'is_active': user.is_active,
            'message': 'Login successful'
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
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors, 'message': 'Invalid data provided'},
                            status=status.HTTP_400_BAD_REQUEST)

        email, otp = serializer.data['email'], serializer.data['otp']
        user = CustomUser.objects.filter(email=email).first()
        if user.is_verified:
            return Response({'message': 'Your Account is already verified.'}, status=status.HTTP_200_OK)
        if not user or user.otp != otp:
            return Response({'error': 'Invalid OTP', 'message': 'Incorrect OTP provided'},
                            status=status.HTTP_400_BAD_REQUEST)
        if now() > user.otp_created_at + timedelta(minutes=10):
            return Response({'error': 'OTP expired', 'message': 'Request a new OTP'},
                            status=status.HTTP_400_BAD_REQUEST)
        user.is_verified = True
        user.save()
        verified_msg(email)
        return Response({'message': 'Account verified successfully'}, status=status.HTTP_200_OK)


class ResendOTP(APIView):
    def post(self, request):
        email = request.data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        if not user:
            return Response({'error': 'User not found', 'message': 'Invalid email'}, status=status.HTTP_403_FORBIDDEN)
        if user.is_verified:
            return Response({'error': 'Already verified', 'message': 'Account already verified'},
                            status=status.HTTP_400_BAD_REQUEST)

        otp = send_otp_via_email(user.email)
        user.otp=otp
        user.otp_created_at = now()
        user.save(update_fields=['otp', 'otp_created_at'])
        return Response({'otp': user.otp,'message': 'OTP resent successfully'}, status=status.HTTP_200_OK)


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
