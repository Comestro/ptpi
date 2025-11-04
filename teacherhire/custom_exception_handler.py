from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
import re

def custom_exception_handler(exc, context):
    """
    Global Exception Handler for consistent JSON error formatting.
    """
    response = exception_handler(exc, context)

    # === Handle DRF & Django Validation Errors ===
    if isinstance(exc, (DRFValidationError, DjangoValidationError)):
        errors = []
        detail = getattr(exc, "detail", None) or getattr(exc, "message_dict", {}) or {}

        if isinstance(detail, dict):
            for field, messages in detail.items():
                if not isinstance(messages, (list, tuple)):
                    messages = [messages]
                for msg in messages:
                    errors.append({
                        "code": getattr(msg, "code", "invalid"),
                        "detail": str(msg),
                        "attr": field
                    })

        elif isinstance(detail, list):
            for msg in detail:
                errors.append({
                    "code": getattr(msg, "code", "invalid"),
                    "detail": str(msg),
                    "attr": None
                })

        return Response({
            "status": "error",
            "type": "validation_error",
            "errors": errors or [{
                "code": "invalid",
                "detail": str(exc),
                "attr": None
            }]
        }, status=status.HTTP_400_BAD_REQUEST)

    # === Handle IntegrityError (duplicate email, username, etc.) ===
    elif isinstance(exc, IntegrityError):
        message = str(exc)
        match = re.search(r'\.(\w+)\)', message)
        field_name = match.group(1) if match else "error"

        user_message = "A record with this information already exists."
        code = "unique"

        if "email" in message.lower():
            field_name = "email"
            user_message = "This email is already registered."
        elif "username" in message.lower():
            field_name = "username"
            user_message = "This username is already taken."

        return Response({
            "status": "error",
            "type": "validation_error",
            "errors": [
                {
                    "code": code,
                    "detail": user_message,
                    "attr": field_name
                }
            ]
        }, status=status.HTTP_400_BAD_REQUEST)

    # === Handle known DRF exceptions (404, 403, etc.) ===
    if response is not None:
        detail = response.data.get("detail", "An unexpected error occurred.")
        return Response({
            "status": "error",
            "type": "server_error",
            "errors": [
                {
                    "code": "error",
                    "detail": detail,
                    "attr": None
                }
            ]
        }, status=response.status_code)

    # === Handle all other exceptions ===
    return Response({
        "status": "error",
        "type": "server_error",
        "errors": [
            {
                "code": "server_error",
                "detail": str(exc),
                "attr": None
            }
        ]
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


