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
            
            <h2 style="color: #008080; font-size: 24px; margin-bottom: 10px;">Purnia Private Teacher Institution</h2>
            
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
            "Congratulations Yay!! Welcome to <strong style='color: #008080;'>TeacherGotHire</strong>! 🎉<br><br>"
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
        else:
            feedback.append(f"TeachersAddress is incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("No TeachersAddress found for the user.")


    # Check Job Preferences
    preference = Preference.objects.filter(user=user).first()
    if preference:
        is_complete, missing_fields = preference.is_complete()
        if is_complete:
            complete_profile += 16
        else:
            feedback.append(f"Job Preferences are incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("Job Preferences are missing entirely.")


    # Check JobPreferenceLocation
    job_preference_location = JobPreferenceLocation.objects.filter(preference__user=user).first()
    if job_preference_location:
        is_complete, missing_fields = job_preference_location.is_complete()
        if is_complete:
            complete_profile += 16
        else:
            feedback.append(f"Job Preference Location is incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("Job Preference Location is incomplete.")


    # Check TeacherQualification
    teacher_qualification = TeacherQualification.objects.filter(user=user).first()
    if teacher_qualification:
        is_complete, missing_fields = teacher_qualification.is_complete()
        if is_complete:
            complete_profile += 20
        else:
            feedback.append(f"Teacher Qualification is incomplete. Missing fields: {', '.join(missing_fields)}")
    else:
        feedback.append("Teacher Qualification is incomplete.")

    # Ensure the total does not exceed 100%
    return min(complete_profile, 100), feedback

