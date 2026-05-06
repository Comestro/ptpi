import os
from django.core.management.base import BaseCommand
from django.conf import settings
from teacherhire.models import EmailTemplate

class Command(BaseCommand):
    help = 'Seeds email templates from HTML files into the database'

    def handle(self, *args, **kwargs):
        templates_dir = os.path.join(settings.BASE_DIR, 'teacherhire', 'templates', 'emails')
        
        # Mapping template filename -> (name_key, subject)
        template_map = {
            'otp_verification.html': {
                'name': 'otp_verification',
                'subject': 'Your Account Verification Email'
            },
            'account_verified.html': {
                'name': 'account_verified',
                'subject': '🎉 Account Verified Successfully! Welcome to PTPI!'
            },
            'exam_qualified.html': {
                'name': 'exam_qualified',
                'subject': '🎉 Congratulations! You have qualified for the next level!'
            },
            'incomplete_profile.html': {
                'name': 'incomplete_profile',
                'subject': 'Action Required: Complete Your PTP Institute Profile'
            },
            'password_reset.html': {
                'name': 'password_reset',
                'subject': 'Password Reset Requested'
            }
        }

        count = 0
        for filename, info in template_map.items():
            filepath = os.path.join(templates_dir, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                obj, created = EmailTemplate.objects.update_or_create(
                    name=info['name'],
                    defaults={
                        'subject': info['subject'],
                        'body_html': html_content
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created template: {info['name']}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Updated template: {info['name']}"))
                count += 1
            else:
                self.stdout.write(self.style.WARNING(f"File not found: {filepath}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} templates.'))
