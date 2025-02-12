from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminUser(BasePermission):

    # Allows access only to admin users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff


class IsRecruiterUser(BasePermission):

    # Allows access only to recruiter users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_recruiter


class IsTeacherUser(BasePermission):

    # Allows access only to teacher users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_teacher


class IsCenterUser(BasePermission):

    # Allows access only to center users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_center_user


class IsQuestionUser(BasePermission):

    # Allows access only to question users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_question_user


class IsDefaultUser(BasePermission):

    # Allows access to users who are neither admins, recruiters, teachers, center users, nor question users.

    def has_permission(self, request, view):
        return (
                request.user.is_authenticated
                and not any([
            request.user.is_staff,
            request.user.is_recruiter,
            request.user.is_teacher,
            request.user.is_center_user,
            request.user.is_question_user
        ])
        )


class IsAdminOrTeacher(BasePermission):

    # Allows access to admins and teachers.

    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_teacher)


class IsAuthenticatedReadOnly(BasePermission):

    # Read-only access for authenticated users.

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.method in SAFE_METHODS
