from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import (
    AccidentViewSet,
    AccidentClusterViewSet,
    AccidentReportViewSet,
    ExportAccidentsView,
    ExportClustersView,
    TriggerClusteringView,
    TaskStatusView
)

router = DefaultRouter()
router.register(r'accidents', AccidentViewSet, basename='accident')
router.register(r'clusters', AccidentClusterViewSet, basename='cluster')
router.register(r'reports', AccidentReportViewSet, basename='report')

urlpatterns = [
    path('', include(router.urls)),

    # Export endpoints
    path('export/accidents/', ExportAccidentsView.as_view(), name='export-accidents'),
    path('export/clusters/', ExportClustersView.as_view(), name='export-clusters'),

    # Clustering endpoint
    path('clustering/run/', TriggerClusteringView.as_view(), name='trigger-clustering'),

    # Task status endpoint
    path('tasks/<str:task_id>/', TaskStatusView.as_view(), name='task-status'),
]