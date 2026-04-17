from django.core.mail import EmailMessage, send_mail
import os
import random
from django.utils.timezone import now
from django.template.loader import render_to_string
from .models import BasicProfile ,TeachersAddress,Preference

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
    subject = "Your Account Verification Email"
    otp = random.randint(100000, 999999)
    
    html_message = render_to_string('emails/otp_verification.html', {'otp': otp})
    
    message = f"Your OTP is {otp}"
    
    from_email = os.environ.get('EMAIL_FROM')
    send_mail(subject, message, from_email, [email], html_message=html_message)
    # user_obj = CustomUser.objects.get(email=email)
    # user_obj.otp = otp
    # user_obj.otp_created_at = now()
    # user_obj.save()
    return otp

def verified_msg(email):
    try:
        subject = "🎉 Account Verified Successfully! Welcome to PTPI!"
        
        html_message = render_to_string('emails/account_verified.html')
        
        plain_message = (
            "Yay!! Welcome to PTPI! 🎉\n\n"
            "We're absolutely thrilled to have you join our growing community of passionate educators. 🌟\n\n"
            "PTPI is your gateway to endless opportunities where you can:\n"
            "- 🌍 Connect with learners from around the world.\n"
            "- 📚 Share your knowledge and expertise.\n"
            "- 🚀 Take your teaching career to new heights.\n\n"
            "Take your teaching journey to the next level with the tools, resources, and support you need to succeed.\n\n"
            "Your journey starts here! Log in to your account and explore features designed to empower you on this exciting path. "
            "Together, we can make a difference in education.\n\n"
            "If you have any questions or need help, our team is always here to assist you.\n\n"
            "Welcome aboard, and here's to your success with PTPI! 🥳\n\n"
            "Best regards,\n"
            "The PTPI Team"
        )
        
        from_email = os.environ.get('EMAIL_FROM')
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
    if not user:
        return 0, ["User not found."]

    complete_profile = 0
    feedback = []
    
    # 1. Name fields (10%)
    if user.Fname and user.Lname:
        complete_profile += 10
    else:
        feedback.append({"id": "name", "step": "Personal Information", "label": "Add your first and last name", "link": "/teacher/personal-profile?tab=basic"})

    # 2. Basic Profile (20%)
    basic_profile = BasicProfile.objects.filter(user=user).first()
    if basic_profile:
        is_complete, missing_fields = basic_profile.is_complete()
        if is_complete:
            complete_profile += 20
        else:
            complete_profile += 10
            feedback.append({"id": "basic", "step": "Personal Information", "label": f"Complete your basic profile (Missing: {', '.join(missing_fields)})", "link": "/teacher/personal-profile?tab=basic"})
    else:
        feedback.append({"id": "basic", "step": "Personal Information", "label": "Complete your basic profile details", "link": "/teacher/personal-profile?tab=basic"})

    # 3. Address Information (15%)
    addresses = TeachersAddress.objects.filter(user=user)
    has_current = addresses.filter(address_type='current').exists()
    has_permanent = addresses.filter(address_type='permanent').exists()
    
    current_complete = False
    if has_current:
        current_addr = addresses.filter(address_type='current').first()
        is_complete, _ = current_addr.is_complete()
        current_complete = is_complete
        
    permanent_complete = False
    if has_permanent:
        perm_addr = addresses.filter(address_type='permanent').first()
        is_complete, _ = perm_addr.is_complete()
        permanent_complete = is_complete

    if current_complete and permanent_complete:
        complete_profile += 15
    elif current_complete or permanent_complete:
        complete_profile += 7
        feedback.append({"id": "address", "step": "Address Details", "label": "Complete both current and permanent addresses", "link": "/teacher/personal-profile?tab=address"})
    else:
        feedback.append({"id": "address", "step": "Address Details", "label": "Add your address details (Current & Permanent)", "link": "/teacher/personal-profile?tab=address"})

    # 4. Job Preferences (20%)
    from .models import Preference
    preference = Preference.objects.filter(user=user).first()
    if preference:
        is_complete, missing_fields = preference.is_complete()
        if is_complete:
            complete_profile += 20
        else:
            complete_profile += 10
            feedback.append({"id": "preference", "step": "Job Preferences", "label": "Complete your job preferences", "link": "/teacher/personal-profile?tab=Subject Preference"})
    else:
        feedback.append({"id": "preference", "step": "Job Preferences", "label": "Add your job preferences", "link": "/teacher/personal-profile?tab=Subject Preference"})

    # 5. Educational Qualifications (20%)
    from .models import TeacherQualification
    if TeacherQualification.objects.filter(user=user).exists():
        complete_profile += 20
    else:
        feedback.append({"id": "qualification", "step": "Education", "label": "Add your educational qualifications", "link": "/teacher/personal-profile?tab=education"})

    # 6. Work Experience (15%)
    from .models import TeacherExperiences
    if TeacherExperiences.objects.filter(user=user).exists():
        complete_profile += 15
    else:
        feedback.append({"id": "experience", "step": "Experience", "label": "Add your professional experience", "link": "/teacher/personal-profile?tab=experience"})

    return min(complete_profile, 100), feedback

