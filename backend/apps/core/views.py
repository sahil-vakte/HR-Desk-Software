from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok"})


@never_cache
def csrf_token(request):
    if request.method != "GET":
        response = JsonResponse({"message": "Method not allowed.", "errors": {}}, status=405)
        response["Allow"] = "GET"
        return response
    # CSRF value is not an authentication token; session cookie stays HttpOnly.
    return JsonResponse({"csrfToken": get_token(request)})


class SpaView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    def get(self, request, path=""):
        from django.conf import settings
        from django.http import FileResponse
        index = settings.BASE_DIR.parent / "frontend" / "build" / "index.html"
        if not index.is_file():
            return Response({"message":"Build the frontend with npm run build before serving this URL.","errors":{}}, status=503)
        response = FileResponse(index.open("rb"), content_type="text/html")
        response["Cache-Control"] = "no-cache"
        return response
