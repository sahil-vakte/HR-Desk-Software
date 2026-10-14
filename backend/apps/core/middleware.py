import logging
import uuid
from django.conf import settings

logger = logging.getLogger("hrdesk")


class RequestMetadataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        if settings.ENVIRONMENT == "production":
            response["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
            )
        if response.status_code >= 400:
            # Route templates avoid leaking personal values in URL parameters.
            route = getattr(getattr(request, "resolver_match", None), "route", "unmatched")
            user_id = getattr(getattr(request, "user", None), "pk", None)
            logger.warning("HTTP %s request_id=%s user_id=%s route=%s",
                           response.status_code, request.request_id, user_id, route)
        return response
