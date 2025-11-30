"""
URL Configuration for Custom Admin Panel
"""

from django.urls import path
from . import admin_views

app_name = 'admin_panel'

urlpatterns = [
    # Main Admin Dashboard
    path('', admin_views.admin_dashboard, name='dashboard'),

    # User Management
    path('users/', admin_views.user_management, name='users'),
    path('users/create/', admin_views.user_create, name='user_create'),
    path('users/<int:user_id>/', admin_views.user_detail, name='user_detail'),
    path('users/<int:user_id>/reset-password/', admin_views.user_reset_password, name='user_reset_password'),
    path('users/<int:user_id>/toggle-active/', admin_views.user_toggle_active, name='user_toggle_active'),

    # Audit Logs
    path('audit-logs/', admin_views.audit_logs, name='audit_logs'),

    # System Monitoring
    path('system/', admin_views.system_monitoring, name='system_monitoring'),

    # Data Import (CSV Upload)
    path('csv-upload/', admin_views.csv_upload, name='csv_upload'),
    path('csv-upload/process/', admin_views.csv_upload_process, name='csv_upload_process'),
    path('csv-upload/results/', admin_views.csv_upload_results, name='csv_upload_results'),
    path('data-view/', admin_views.data_view, name='data_view'),

    # AJAX Endpoints
    path('api/user-stats/', admin_views.get_user_stats, name='api_user_stats'),
    path('api/system-health/', admin_views.get_system_health, name='api_system_health'),
    path('api/verify-password/', admin_views.verify_password, name='verify_password'),
]
