import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import CustomUser
from teacherhire.utils import calculate_profile_completed

users = CustomUser.objects.filter(is_teacher=True).order_by('-id')[:5]
for u in users:
    percentage, feedback = calculate_profile_completed(u)
    print(f"User {u.id} ({u.email}): {percentage}%")
    print(f"Feedback: {feedback}")
    print("-" * 20)
