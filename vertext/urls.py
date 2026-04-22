from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView

def home(request):
    return JsonResponse({'app': 'Vertext API', 'status': 'online', 'version': '1.0.0'})

urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/', include('vertext_app.urls')),
    path('api/auth/refresh/', TokenRefreshView.as_view()),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
