from django.http import JsonResponse


class HealthCheckMiddleware:
    """Responde /health/ antes de que SecurityMiddleware valide ALLOWED_HOSTS."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return JsonResponse({"status": "ok"})
        return self.get_response(request)
