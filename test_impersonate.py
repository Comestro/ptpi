import os
import django

from rest_framework.test import APIRequestFactory, force_authenticate
from teacherhire.auth_view import ImpersonateUser
from teacherhire.models import CustomUser

factory = APIRequestFactory()
user_id = CustomUser.objects.filter(is_staff=False).first().id
request = factory.post(f'/api/admin/impersonate/{user_id}/')

admin_user = CustomUser.objects.filter(is_staff=True).first()
force_authenticate(request, user=admin_user)

view = ImpersonateUser.as_view()
response = view(request, user_id=user_id)

try:
    response.render()
    print("STATUS:", response.status_code)
    print("CONTENT:", response.content)
except Exception as e:
    import traceback
    traceback.print_exc()
