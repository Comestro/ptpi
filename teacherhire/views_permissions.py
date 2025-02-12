from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication

from .permissions import (
    IsAdminUser,
    IsRecruiterUser,
    IsTeacherUser,
    IsCenterUser,
    IsQuestionUser,
    IsDefaultUser,
    IsAdminOrTeacher
)


# Admin-Only API
class AdminOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        return Response({"message": "Welcome, Admin!"}, status=status.HTTP_200_OK)


# Recruiter-Only API
class RecruiterOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsRecruiterUser]

    def get(self, request):
        return Response({"message": "Welcome, Recruiter!"}, status=status.HTTP_200_OK)


# Teacher-Only API
class TeacherOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsTeacherUser]

    def get(self, request):
        return Response({"message": "Welcome, Teacher!"}, status=status.HTTP_200_OK)


# Center User-Only API
class CenterUserOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsCenterUser]

    def get(self, request):
        return Response({"message": "Welcome, Center User!"}, status=status.HTTP_200_OK)


# Question User-Only API
class QuestionUserOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsQuestionUser]

    def get(self, request):
        return Response({"message": "Welcome, Question User!"}, status=status.HTTP_200_OK)


# Default User-Only API
class DefaultUserOnlyView(APIView):
    permission_classes = [IsAuthenticated, IsDefaultUser]

    def get(self, request):
        return Response({"message": "Welcome, Default User!"}, status=status.HTTP_200_OK)


# Admin or Teacher Access API
class AdminOrTeacherView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrTeacher]

    def get(self, request):
        return Response({"message": "Welcome, Admin or Teacher!"}, status=status.HTTP_200_OK)


# Read-Only API for All Authenticated Users
class ReadOnlyForAuthenticatedUsers(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are authenticated and can read this!"}, status=status.HTTP_200_OK)


# Public API (No Authentication Required)
class PublicView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"message": "This is a public API, no authentication required!"}, status=status.HTTP_200_OK)


"""
optimized code

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .permissions import *

class RoleBasedView(APIView):
    role_permission_map = {
        'admin': IsAdminUser,
        'recruiter': IsRecruiterUser,
        'teacher': IsTeacherUser,
        'centeruser': IsCenterUser,
        'questionuser': IsQuestionUser,
        'default': IsDefaultUser,
        'admin_teacher': IsAdminOrTeacher
    }

    def get_permission_class(self, role):
        return self.role_permission_map.get(role, IsAuthenticated)

    def get(self, request, role):
        self.permission_classes = [IsAuthenticated, self.get_permission_class(role)]
        self.check_permissions(request)
        return Response({"message": f"Welcome, {role.capitalize()}!"}, status=status.HTTP_200_OK)

class PublicView(APIView):
    permission_classes = []

    def get(self, request):
        return Response({"message": "This is a public API, no authentication required!"}, status=status.HTTP_200_OK)


"""