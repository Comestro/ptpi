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
    complete_profile = 0
    if user:
        complete_profile += 16  # Custom user field

    basic_profile = BasicProfile.objects.filter(user=user).exists()
    if basic_profile:
        complete_profile += 16  # Basic profile filled

    teacher_address = TeachersAddress.objects.filter(user=user).exists()
    if teacher_address:
        complete_profile += 16  # Teacher address filled

    job_preference = Preference.objects.filter(user=user).exists()
    if job_preference:
        complete_profile += 16  # Job preference filled

    job_pref_location = JobPreferenceLocation.objects.filter(preference__user=user).exists()
    if job_pref_location:
        complete_profile += 16  # Job preference location filled

    qualification = TeacherQualification.objects.filter(user=user).exists()
    if qualification:
        complete_profile += 20  # Qualification filled

    return min(complete_profile, 100)  # Ensure it doesn't exceed 100%
