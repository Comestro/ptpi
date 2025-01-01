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