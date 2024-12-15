from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken import views

urlpatterns = [
    path('api-token-auth/', views.obtain_auth_token),
    path('api/', include('teacherhire.urls')),
    path('admin/', admin.site.urls),  # Ensure this line is present only once
]