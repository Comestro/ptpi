from django.core.mail import EmailMessage, send_mail
import os
import random
from django.utils.timezone import now
from .models import CustomUser,BasicProfile ,TeachersAddress,Preference,JobPreferenceLocation,TeacherQualification

class Util:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            from_email=os.environ.get('EMAIL_FROM'),
            to=[data['to_email']]
        )
        email.send()

def send_otp_via_email(email):
    subject = "your account verification email"
    otp = random.randint(1000, 9999)
    message = f"Your OTP is {otp}"
    from_email=os.environ.get('EMAIL_FROM')
    send_mail(subject,message,from_email, [email])
    user_obj = CustomUser.objects.get(email=email)
    user_obj.otp = otp
    user_obj.otp_created_at = now()
    user_obj.save()

def calculate_profile_completed(user):
    completion_percentage = 0

    # Check CustomUser Profile
    if user:
        completion_percentage += 16  # Custom user field

    # Check Basic Profile
    basic_profile = BasicProfile.objects.filter(user=user).exists()
    if basic_profile:
        completion_percentage += 16  # Basic profile filled

    # Check Teacher Address
    teacher_address = TeachersAddress.objects.filter(user=user).exists()
    if teacher_address:
        completion_percentage += 16  # Teacher address filled

    # Check Teacher Job Preference
    job_preference = Preference.objects.filter(user=user).exists()
    if job_preference:
        completion_percentage += 16  # Job preference filled

    # Check Job Preference Location
    job_pref_location = JobPreferenceLocation.objects.filter(preference__user=user).exists()
    if job_pref_location:
        completion_percentage += 16  # Job preference location filled

    # Check Teacher Qualification
    qualification = TeacherQualification.objects.filter(user=user).exists()
    if qualification:
        completion_percentage += 20  # Qualification filled

    return min(completion_percentage, 100)  # Ensure it doesn't exceed 100%


# def calculate_profile_completed(user):
#     """
#     Calculate the profile completed percentage based on the user's associated data.
#     """
#     percentage = 0
#     if CustomUser.objects.filter(id=user.id).exists():
#         percentage += 16

#     if BasicProfile.objects.filter(user=user).exists():
#         percentage += 16

#     if TeachersAddress.objects.filter(user=user).exists():
#         percentage += 16
    
#     if Preference.objects.filter(user=user).exists():
#         percentage += 16

#     return percentage

#     # if JobPreferenceLocation.objects.filter(user=user).exists():
#     #     percentage += 20
#     # if TeacherQualification.objects.filter(user=user).exists():
#     #     percentage += 20
