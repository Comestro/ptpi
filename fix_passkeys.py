import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import Passkey
import random

passkeys = Passkey.objects.filter(status='fulfilled', code__isnull=True)
count = 0
for p in passkeys:
    while True:
        new_code = str(random.randint(1000, 9999))
        if not Passkey.objects.filter(code=new_code).exists():
            p.code = new_code
            p.save()
            count += 1
            break

print(f"Fixed {count} passkeys with missing codes.")
