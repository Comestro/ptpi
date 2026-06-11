import os
import django
from django.test import Client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ptpi.settings')
django.setup()

from teacherhire.models import CustomUser

user = CustomUser.objects.get(email="info@ptpinstitute.com")
print(f"User: {user.email}")

client = Client(SERVER_NAME='localhost')
client.force_login(user)

response = client.get('/api/examcenter/teachers/')
print(f"Status Code: {response.status_code}")
print(f"Content: {response.content.decode('utf-8')}")

