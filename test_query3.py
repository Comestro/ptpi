import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import Passkey, ExamCenter, CustomUser
for center in ExamCenter.objects.all():
    print(f"Center Name: {center.center_name}, Owner: {center.user.email}")
