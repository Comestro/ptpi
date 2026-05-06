from django.core.management.base import BaseCommand
from teacherhire.models import CustomUser
from teacherhire.utils import calculate_profile_completed, send_incomplete_profile_email

class Command(BaseCommand):
    help = 'Sends reminder emails to teachers with incomplete profiles (missing education, preferences, etc.)'

    def handle(self, *args, **kwargs):
        # Find all teachers
        teachers = CustomUser.objects.filter(is_teacher=True)
        count = 0

        for teacher in teachers:
            percentage, feedback = calculate_profile_completed(teacher)
            
            if percentage < 100:
                missing_labels = []
                for item in feedback:
                    # Check for specific missing items like education and preferences
                    if item.get('id') in ['education', 'academic_preference', 'basic', 'address']:
                        missing_labels.append(item.get('label'))
                
                if missing_labels:
                    send_incomplete_profile_email(teacher, missing_labels)
                    count += 1
                    self.stdout.write(self.style.SUCCESS(f'Sent reminder to {teacher.email}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully sent {count} reminder emails.'))
