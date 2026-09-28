from django.db import connection
from django.http import JsonResponse
from django.urls import path


def health(request):
    """Liveness/readiness probe for the load balancer and uptime monitor."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    status_code = 200 if db_ok else 503
    return JsonResponse({"status": "ok" if db_ok else "degraded", "database": db_ok}, status=status_code)


urlpatterns = [path("", health, name="health")]
