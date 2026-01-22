from rest_framework import viewsets, permissions
from .missing_subject_logic import MissingSubject
from .missing_subject_serializer import MissingSubjectSerializer

class MissingSubjectViewSet(viewsets.ModelViewSet):
    queryset = MissingSubject.objects.all()
    serializer_class = MissingSubjectSerializer
    permission_classes = [permissions.AllowAny]  # Allow teachers/users to submit without strict restrictions if needed

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
