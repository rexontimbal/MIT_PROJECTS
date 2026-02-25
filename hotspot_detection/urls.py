from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve as static_serve
import os

def service_worker_view(request):
    """Serve service worker from root URL with correct content type."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'js', 'service-worker.js')
    from django.http import HttpResponse
    with open(sw_path, 'r') as f:
        return HttpResponse(f.read(), content_type='application/javascript')

urlpatterns = [
    # PWA: Service worker must be served from root for full scope
    path('service-worker.js', service_worker_view, name='service_worker'),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),

    path('admin/', admin.site.urls),
    path('', include('accidents.urls')),  # This should handle the root URL
    path('api/', include('accidents.api_urls')),
    path('clustering/', include('clustering.urls')),  # Clustering validation metrics
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)