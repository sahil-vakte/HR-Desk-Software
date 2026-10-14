import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import JsonResponse
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger("hrdesk")


def exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = ValidationError(getattr(exc, "message_dict", {"non_field_errors": exc.messages}))
    response = drf_exception_handler(exc, context)
    if response is None:
        request_id = getattr(context.get("request"), "request_id", "unknown")
        logger.error("Unhandled API error request_id=%s type=%s", request_id, type(exc).__name__)
        return Response({"message": "Something went wrong. Please try again.",
                         "errors": {}, "request_id": request_id}, status=500)
    if isinstance(exc, ValidationError):
        response.status_code = 422
        errors = response.data if isinstance(response.data, dict) else {"non_field_errors": response.data}
        response.data = {"message": "The given data was invalid.", "errors": errors}
    else:
        messages = {401: "Authentication required.",
                    403: "You do not have permission to perform this action.",
                    404: "Record not found."}
        detail = response.data.get("detail", "Request failed.") if isinstance(response.data, dict) else "Request failed."
        response.data = {"message": messages.get(response.status_code, str(detail)), "errors": {}}
    return response


def csrf_failure(request, reason=""):
    return JsonResponse({"message": "CSRF verification failed. Refresh the page and try again.", "errors": {}}, status=403)


def bad_request(request, exception):
    return JsonResponse({"message": "Something went wrong with the request.", "errors": {}}, status=400)


def permission_denied(request, exception):
    return JsonResponse({"message": "You do not have permission to perform this action.", "errors": {}}, status=403)


def not_found(request, exception):
    return JsonResponse({"message": "Record not found.", "errors": {}}, status=404)


def server_error(request):
    return JsonResponse({"message": "Something went wrong. Please try again.", "errors": {},
                         "request_id": getattr(request, "request_id", "unknown")}, status=500)
