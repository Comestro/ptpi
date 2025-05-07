from django.core.mail import EmailMessage, send_mail
import os
import random
from django.utils.timezone import now
from django.template.loader import render_to_string
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
        subject = "🎉 Account Verified Successfully! Welcome to TeacherGotHire!"
        
        html_message = render_to_string('emails/account_verified.html')
        
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
    if user.Fname and user.Lname:
        complete_profile += 16
    else:
        feedback.append("Name fields (First and Last name) are incomplete.")

    if BasicProfile.objects.filter(user=user).exists():
        complete_profile += 16
    else:
        feedback.append("Basic Profile is incomplete.")

    # TeachersAddress and validate completeness
    teacher_address = TeachersAddress.objects.filter(user=user)
    if teacher_address.exists():
        address = teacher_address.first()
        is_complete, missing_fields = address.is_complete()
        if is_complete:
            complete_profile += 16
        # else:
        #     feedback.append(f"TeachersAddress is incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("Add Address")


    # Check Job Preferences
    preference = Preference.objects.filter(user=user).first()
    if preference:
        is_complete, missing_fields = preference.is_complete()
        if is_complete:
            complete_profile += 24
        # else:
        #     feedback.append(f"Job Preferences are incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("Add Job Preferences")


 
    # Ensure the total does not exceed 100%
    return min(complete_profile, 100), feedback

