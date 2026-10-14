from django.contrib.auth import logout
from django.utils import timezone

class SessionLifetimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        if request.user.is_authenticated:
            started = request.session.get("authenticated_at")
            if (not started or timezone.now().timestamp() - started >= 43200
                or request.user.is_deleted or not request.user.is_active
                or not request.user.role_id or not request.user.role.status or request.user.role.is_deleted
                or request.session.get("auth_version") != request.user.auth_version):
                logout(request)
        return self.get_response(request)
