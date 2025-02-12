from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from datetime import timedelta
from django.utils import timezone
from django.conf import settings


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.get(key=key)
        except model.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')

        # Token expiration logic
        expiration_time = timedelta(seconds=settings.TOKEN_EXPIRATION_TIME)
        if timezone.now() > token.created + expiration_time:
            raise AuthenticationFailed('Access token has expired. Please log in again.')

        return token.user, token
