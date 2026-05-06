from django.core.mail import EmailMessage, send_mail
import os
import random
from django.utils.timezone import now
from django.template.loader import render_to_string
from django.template import Context, Template
from .models import BasicProfile ,TeachersAddress,Preference, CustomUser, EmailTemplate, EmailLog

class Util:
    @staticmethod
    def send_email(data):
        send_mail(
            subject=data['subject'],
            message=data['body'],
            from_email=os.environ.get('EMAIL_FROM'),
            recipient_list=[data['to_email']],
            html_message=data.get('html_message'),
            fail_silently=False
        )

def send_and_log_email(email, template_name, context_dict, default_subject, default_html_path, default_plain):
    try:
        user = CustomUser.objects.filter(email=email).first()
        template_obj = EmailTemplate.objects.filter(name=template_name).first()
        
        if template_obj:
            subject_line = template_obj.subject
            t = Template(template_obj.body_html)
            html_message = t.render(Context(context_dict))
        else:
            subject_line = default_subject
            html_message = render_to_string(default_html_path, context_dict)
            
        from_email = os.environ.get('EMAIL_FROM')
        
        send_mail(
            subject=subject_line,
            message=default_plain,  
            from_email=from_email,
            recipient_list=[email],
            html_message=html_message,  
            fail_silently=False,
        )
        
        if user:
            EmailLog.objects.create(
                user=user,
                template=template_obj,
                subject=subject_line,
                body_html=html_message,
                status='sent'
            )
        print(f"Email {template_name} sent to {email}.")
    except Exception as e:
        print(f"Failed to send email {template_name} to {email}: {e}")
        user = CustomUser.objects.filter(email=email).first()
        if user:
            EmailLog.objects.create(
                user=user,
                template=None,
                subject=default_subject,
                body_html=str(e),
                status='failed'
            )
        raise e

def send_otp_via_email(email):
    otp = random.randint(100000, 999999)
    try:
        send_and_log_email(
            email=email,
            template_name="otp_verification",
            context_dict={'otp': otp},
            default_subject="Your Account Verification Email",
            default_html_path='emails/otp_verification.html',
            default_plain=f"Your OTP is {otp}"
        )
        return otp
    except Exception as e:
        raise Exception(f"Failed to send OTP email: {str(e)}")


def verified_msg(email):
    plain_message = (
        "Yay!! Welcome to PTPI! 🎉\n\n"
        "We're absolutely thrilled to have you join our growing community of passionate educators. 🌟\n\n"
        "Your journey starts here! Log in to your account and explore features designed to empower you on this exciting path. "
    )
    send_and_log_email(
        email=email,
        template_name="account_verified",
        context_dict={},
        default_subject="🎉 Account Verified Successfully! Welcome to PTPI!",
        default_html_path='emails/account_verified.html',
        default_plain=plain_message
    )

def send_qualification_email(user, score, subject, level):
    plain_message = (
        f"Congratulations {user.Fname}!\n\n"
        f"You have successfully passed the exam for {subject} ({level}) with a score of {score}%.\n"
        "Log in to your dashboard to see the next steps.\n\n"
    )
    send_and_log_email(
        email=user.email,
        template_name="exam_qualified",
        context_dict={'score': score, 'subject': subject, 'level': level},
        default_subject="🎉 Congratulations! You have qualified for the next level!",
        default_html_path='emails/exam_qualified.html',
        default_plain=plain_message
    )

def send_incomplete_profile_email(user, missing_items):
    missing_text = "\n- ".join(missing_items)
    plain_message = (
        f"Hi {getattr(user, 'Fname', 'Teacher')},\n\n"
        f"We noticed that your teacher profile is missing some important details:\n\n"
        f"- {missing_text}\n\n"
        "Log in to your dashboard to update your profile.\n\n"
    )
    send_and_log_email(
        email=user.email,
        template_name="incomplete_profile",
        context_dict={
            'user_name': getattr(user, 'Fname', 'Teacher'),
            'missing_items': missing_items
        },
        default_subject="Action Required: Complete Your PTP Institute Profile",
        default_html_path='emails/incomplete_profile.html',
        default_plain=plain_message
    )

def calculate_profile_completed(user):
    if not user:
        return 0, ["User not found."]
    
    feedback = []
    complete_profile = 0
    
    try:
        # Get attributes safely
        fname = getattr(user, 'Fname', None)
        lname = getattr(user, 'Lname', None)
        
        # 1. Name fields (10%)
        if fname and lname:
            complete_profile += 10
        else:
            feedback.append({"id": "name", "step": "Personal Information", "label": "Add your first and last name", "link": "/teacher/personal-profile?tab=basic"})

        # 2. Basic Profile (20%)
        from .models import BasicProfile
        profile = BasicProfile.objects.filter(user=user).first()
        if profile:
            is_comp, missing = profile.is_complete()
            if is_comp:
                complete_profile += 20
            else:
                complete_profile += 10
                feedback.append({"id": "basic", "step": "Personal Information", "label": f"Complete your basic profile (Missing: {', '.join(missing)})", "link": "/teacher/personal-profile?tab=basic"})
        else:
            feedback.append({"id": "basic", "step": "Personal Information", "label": "Add your basic profile information", "link": "/teacher/personal-profile?tab=basic"})

        # 3. Address Information (15%)
        from .models import TeachersAddress
        addresses = TeachersAddress.objects.filter(user=user)
        has_current = addresses.filter(address_type='current').exists()
        has_permanent = addresses.filter(address_type='permanent').exists()
        
        if has_current and has_permanent:
            complete_profile += 15
        else:
            if has_current or has_permanent:
                complete_profile += 7
            feedback.append({"id": "address", "step": "Address Details", "label": "Add your address details (Current & Permanent)", "link": "/teacher/personal-profile?tab=address"})

        # 4. Academic Preferences (20%)
        from .models import Preference
        preference = Preference.objects.filter(user=user).first()
        if preference:
            is_complete, missing_fields = preference.is_complete()
            if is_complete:
                complete_profile += 20
            else:
                complete_profile += 10
                feedback.append({"id": "preference", "step": "Academic Preferences", "label": f"Select your Class Categories and Subjects (Missing: {', '.join(missing_fields)})", "link": "/teacher/personal-profile?tab=Subject Preference"})
        else:
            feedback.append({"id": "preference", "step": "Academic Preferences", "label": "Add your Academic Preferences (Class & Subjects)", "link": "/teacher/personal-profile?tab=Subject Preference"})

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

    except Exception as e:
        # Fallback if any error occurs
        if getattr(user, 'Fname', None) and getattr(user, 'Lname', None):
            complete_profile = max(complete_profile, 10)
        
    return min(complete_profile, 100), feedback

