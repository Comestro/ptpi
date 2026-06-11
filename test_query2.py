import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import Passkey, ExamCenter, CustomUser
try:
    user = CustomUser.objects.get(email="sadique.hussain96@gmail.com")
    print(f"Found user: {user.email}")
    centers = ExamCenter.objects.filter(user=user)
    print(f"Centers for this user: {centers.count()}")
    for center in centers:
        print(f"Center ID: {center.id}, Name: {center.center_name}, Status: {center.status}")
        passkeys = Passkey.objects.filter(center=center)
        print(f"  Passkeys for this center: {passkeys.count()}")
        for p in passkeys:
            print(f"    Passkey ID: {p.id}, Status: {p.status}")
except Exception as e:
    print(f"Error: {e}")

