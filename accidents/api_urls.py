from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import AccidentViewSet, AccidentClusterViewSet, AccidentReportViewSet

router = DefaultRouter()
router.register(r'accidents', AccidentViewSet, basename='accident')
router.register(r'clusters', AccidentClusterViewSet, basename='cluster')
router.register(r'reports', AccidentReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),
]