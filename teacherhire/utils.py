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
    otp = random.randint(10000, 99999)
    message = f"Your OTP is {otp}"
    html_message = f"""
        <div style="
            max-width: 600px; 
            margin: 20px auto; 
            padding: 20px; 
            border-radius: 10px; 
            background-color: #f9f9f9; 
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); 
            text-align: center;
            font-family: Arial, sans-serif;
            color: #333;">
            
            <h2 style="color: #008080; font-size: 24px; margin-bottom: 10px;">TeacherGotHire Verification Code</h2>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Use the code below to complete your verification process.
            </p>
            
            <p style="
                display: inline-block; 
                padding: 10px 20px; 
                font-size: 36px; 
                font-weight: bold; 
                color: #ffffff; 
                background-color: #008080; 
                border-radius: 8px; 
                text-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);">
                {otp}
            </p>
            
            <p style="margin-top: 20px; font-size: 14px; color: #555;">
                This OTP is valid for 10 minutes. Please do not share it with anyone.
            </p>
        </div>
        """
    from_email=os.environ.get('EMAIL_FROM')
    send_mail(subject,message,from_email, [email],html_message=html_message)
    user_obj = CustomUser.objects.get(email=email)
    user_obj.otp = otp
    user_obj.otp_created_at = now()
    user_obj.save()

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