from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import connection
from django.utils import timezone


class HealthCheckView(APIView):
    """
    API Health check endpoint returning status, version, and database connectivity.
    """
    permission_classes = []

    def get(self, request):
        db_ok = False
        try:
            connection.ensure_connection()
            db_ok = True
        except Exception:
            db_ok = False

        return Response({
            'status': 'healthy' if db_ok else 'degraded',
            'app_name': 'AdesHub Backend API',
            'version': '1.0.0',
            'environment': 'development' if settings.DEBUG else 'production',
            'database_connected': db_ok,
            'timestamp': timezone.now().isoformat(),
            'endpoints': {
                'health': '/api/health/',
                'auth': {
                    'register': '/api/accounts/register/',
                    'login': '/api/accounts/login/',
                    'logout': '/api/accounts/logout/',
                    'profile': '/api/accounts/me/',
                    'users': '/api/accounts/users/',
                },
                'admin': '/admin/'
            }
        }, status=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE)
