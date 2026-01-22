from rest_framework import serializers
from .missing_subject_logic import MissingSubject

class MissingSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = MissingSubject
        fields = ['id', 'user', 'subject_name', 'description', 'created_at']
        read_only_fields = ['user', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user'] = request.user
        return super().create(validated_data)
