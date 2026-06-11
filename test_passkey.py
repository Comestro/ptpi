import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import CustomUser, Exam, ExamCenter, Passkey

# 1. create dummy user, exam, center
user = CustomUser.objects.first()
exam = Exam.objects.first()
center = ExamCenter.objects.first()

# 2. create passkey with status 'requested'
passkey = Passkey.objects.create(user=user, exam=exam, center=center, status='requested')
print("Before approve code:", passkey.code)

# 3. simulate approve
passkey.status = 'fulfilled'
passkey.save()

print("After approve code:", passkey.code)

# cleanup
passkey.delete()
