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

# def calculate_profile_completed(user):
#     profile_score = 0
#     incomplete_sections = {}

#     weights = {
#         "customuser": 16,
#         "basic_profile": 16,
#         "teacher_address": 16,
#         "job_preference": 16,
#         "job_pref_location": 16,
#         "qualification": 20,
#     }

#     try:
#         def process_fields(fields, weight, section_key, divisor=1):
#             nonlocal profile_score, incomplete_sections
#             filled_fields = [key for key, value in fields.items() if value]
#             incomplete_fields = [key for key, value in fields.items() if not value]
#             profile_score += (len(filled_fields) / len(fields)) * (weight / divisor)
#             if incomplete_fields:
#                 incomplete_sections[section_key] = incomplete_fields

#         #custom fields
#         customuser = CustomUser.objects.filter(id=user.id).first()
#         if customuser:
#             fields = {
#                 "email": customuser.email,
#                 "username": customuser.username,
#                 "Fname": customuser.Fname,
#                 "Lname": customuser.Lname,
#             }
#             process_fields(fields, weights["customuser"], "customuser")

#         # Check BasicProfile fields
#         basic_profile = BasicProfile.objects.filter(user=user).first()
#         if basic_profile:
#             fields = {
#                 "bio": basic_profile.bio,
#                 "profile_picture": basic_profile.profile_picture,
#                 "phone_number": basic_profile.phone_number,
#                 "religion": basic_profile.religion,
#                 "date_of_birth": basic_profile.date_of_birth,
#                 "marital_status": basic_profile.marital_status,
#                 "gender": basic_profile.gender,
#                 "language": basic_profile.language,
#             }
#             process_fields(fields, weights["basic_profile"], "basic_profile")

#         # Check TeachersAddress fields
#         teacher_addresses = TeachersAddress.objects.filter(user=user)
#         if teacher_addresses.exists():
#             for address in teacher_addresses:
#                 fields = {
#                     "state": address.state,
#                     "division": address.division,
#                     "district": address.district,
#                     "block": address.block,
#                     "village": address.village,
#                     "area": address.area,
#                     "pincode": address.pincode,
#                 }
#                 process_fields(fields, weights["teacher_address"], "teacher_address", teacher_addresses.count())

#         # Check Preference fields
#         preference = Preference.objects.filter(user=user).first()
#         if preference:
#             fields = {
#                 "job_role": preference.job_role.exists(),
#                 "class_category": preference.class_category,
#                 "prefered_subject": preference.prefered_subject.exists(),
#                 "teacher_job_type": preference.teacher_job_type.exists(),
#             }
#             process_fields(fields, weights["job_preference"], "job_preference")

#         # Check JobPreferenceLocation fields
#         job_pref_locations = JobPreferenceLocation.objects.filter(preference__user=user)
#         if job_pref_locations.exists():
#             for location in job_pref_locations:
#                 fields = {
#                     "state": location.state,
#                     "city": location.city,
#                     "sub_division": location.sub_division,
#                     "block": location.block,
#                     "post_office": location.post_office,
#                     "area": location.area,
#                     "pincode": location.pincode,
#                 }
#                 process_fields(fields, weights["job_pref_location"], "job_pref_location", job_pref_locations.count())

#         # Check TeacherQualification fields
#         qualifications = TeacherQualification.objects.filter(user=user)
#         if qualifications.exists():
#             for qualification in qualifications:
#                 fields = {
#                     "qualification": qualification.qualification,
#                     "institution": qualification.institution,
#                     "year_of_passing": qualification.year_of_passing,
#                     "grade_or_percentage": qualification.grade_or_percentage,
#                 }
#                 process_fields(fields, weights["qualification"], "qualification", qualifications.count())

#     except Exception as e:
#         # Log the error for debugging
#         print(f"Error calculating profile completion: {e}")
#         incomplete_sections = {section: list(weights.keys()) for section in weights}

#     return {
#         "profile_completed": min(round(profile_score), 100),  
#         "incomplete_sections": incomplete_sections,        
#     }
from django.core.mail import send_mail
from django.conf import settings
import os

def verified_msg(email):
    try:
        subject = "🎉 Account Verified Successfully! Welcome to TeacherGotHire!"
        
        html_message = (
            "Yay!! Welcome to <strong style='color: #008080;'>TeacherGotHire</strong>! 🎉<br><br>"
            "We're absolutely thrilled to have you join our growing community of passionate educators. 🌟<br><br>"
            "<strong style='color: #008080;'>TeacherGotHire</strong> is your gateway to endless opportunities where you can:<br>"
            "- 🌍 Connect with learners from around the world.<br>"
            "- 📚 Share your knowledge and expertise.<br>"
            "- 🚀 Take your teaching career to new heights.<br><br>"
            "Take your teaching journey to the next level with the tools, resources, and support you need to succeed.<br><br>"
            "Your journey starts here! Log in to your account and explore features designed to empower you on this exciting path. "
            "Together, we can make a difference in education.<br><br>"
            "If you have any questions or need help, our team is always here to assist you.<br><br>"
            "Welcome aboard, and here's to your success with <strong style='color: #008080;'>TeacherGotHire</strong>! 🥳<br><br>"
            "Best regards,<br>"
            "The <strong style='color: #008080;'>TeacherGotHire</strong> Team"
        )
        
        plain_message = (
            "Yay!! Welcome to TeacherGotHire! 🎉\n\n"
            "We're absolutely thrilled to have you join our growing community of passionate educators. 🌟\n\n"
            "TeacherGotHire is your gateway to endless opportunities where you can:\n"
            "- 🌍 Connect with learners from around the world.\n"
            "- 📚 Share your knowledge and expertise.\n"
            "- 🚀 Take your teaching career to new heights.\n\n"
            "Take your teaching journey to the next level with the tools, resources, and support you need to succeed.\n\n"
            "Your journey starts here! Log in to your account and explore features designed to empower you on this exciting path. "
            "Together, we can make a difference in education.\n\n"
            "If you have any questions or need help, our team is always here to assist you.\n\n"
            "Welcome aboard, and here's to your success with TeacherGotHire! 🥳\n\n"
            "Best regards,\n"
            "The TeacherGotHire Team"
        )

        from_email = os.environ.get('EMAIL_FROM', settings.DEFAULT_FROM_EMAIL)

        send_mail(
            subject=subject,
            message=plain_message,  
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,  
            fail_silently=False,
        )
        print(f"Verification email sent to {email}.")
    except Exception as e:
        print(f"Failed to send verification email to {email}: {e}")

    

def calculate_profile_completed(user):
    complete_profile = 0
    if user:
        complete_profile += 16 

    basic_profile = BasicProfile.objects.filter(user=user).exists()
    if basic_profile:
        complete_profile += 16  

    teacher_address = TeachersAddress.objects.filter(user=user).exists()
    if teacher_address:
        complete_profile += 16  

    job_preference = Preference.objects.filter(user=user).exists()
    if job_preference:
        complete_profile += 16  

    job_pref_location = JobPreferenceLocation.objects.filter(preference__user=user).exists()
    if job_pref_location:
        complete_profile += 16  

    qualification = TeacherQualification.objects.filter(user=user).exists()
    if qualification:
        complete_profile += 20  

    return min(complete_profile, 100)