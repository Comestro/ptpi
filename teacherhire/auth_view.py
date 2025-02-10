from rest_framework.views import APIView
from teacherhire.serializers import *
from rest_framework.response import Response
from rest_framework import status
from teacherhire.utils import calculate_profile_completed, send_otp_via_email, verified_msg
from rest_framework.permissions import IsAuthenticated
from .authentication import ExpiringTokenAuthentication
from rest_framework.authtoken.models import Token
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from datetime import date, timedelta
from django.conf import settings
from django.utils.timezone import now
import uuid

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
