import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import Passkey, ExamCenter
print(f"Total Passkeys: {Passkey.objects.count()}")
print(f"Passkeys with a center assigned: {Passkey.objects.filter(center__isnull=False).count()}")
for p in Passkey.objects.filter(center__isnull=False)[:5]:
    print(f"Passkey id={p.id}, user={p.user}, exam={p.exam}, center={p.center}, status={p.status}")
