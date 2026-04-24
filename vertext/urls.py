from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView
import os


def home(request):
    """Health check — shows DB connection status."""
    db_url = os.environ.get('SUPABASE_DB_URL') or os.environ.get('DATABASE_URL') or ''
    db_connected = False
    db_error = ''
    user_count = 0
    try:
        from vertext_app.models import User
        user_count = User.objects.count()
        db_connected = True
    except Exception as e:
        db_error = str(e)

    return JsonResponse({
        'app': 'Vertext API',
        'status': 'online',
        'version': '1.0.0',
        'database': {
            'connected': db_connected,
            'type': 'supabase_postgresql' if db_url else 'sqlite',
            'host': db_url.split('@')[1].split('/')[0] if '@' in db_url else 'local',
            'users': user_count,
            'error': db_error or None,
        },
        'endpoints': {
            'api': '/api/',
            'admin': '/admin/',
            'feed': '/api/feed/',
            'login': '/api/auth/login/',
            'register': '/api/auth/register/',
        }
    })


urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('vertext_app.urls')),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
