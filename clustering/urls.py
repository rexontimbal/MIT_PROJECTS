from django.urls import path
from . import views

app_name = 'clustering'

urlpatterns = [
    path('validation-metrics/', views.cluster_validation_metrics, name='validation_metrics'),
]
