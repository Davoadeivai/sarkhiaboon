from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """
    DRF's default handler, plus conversion of Django model ValidationErrors
    (raised from model.clean or service code) into HTTP 400 responses.
    """
    if isinstance(exc, DjangoValidationError):
        detail = exc.message_dict if hasattr(exc, "error_dict") else {"detail": exc.messages}
        return Response(detail, status=status.HTTP_400_BAD_REQUEST)
    return exception_handler(exc, context)
