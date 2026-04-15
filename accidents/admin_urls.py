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

    # Report Activity Logs
    path('report-activity/', admin_views.report_activity_logs, name='report_activity_logs'),

    # Display Settings
    path('settings/', admin_views.system_settings, name='system_settings'),

    # System Monitoring
    path('system/', admin_views.system_monitoring, name='system_monitoring'),

    # Maintenance Tools
    path('system/clear-cache/', admin_views.clear_cache, name='clear_cache'),
    path('system/database-backup/', admin_views.database_backup, name='database_backup'),

    # AJAX Endpoints
    path('api/user-stats/', admin_views.get_user_stats, name='api_user_stats'),
    path('api/system-health/', admin_views.get_system_health, name='api_system_health'),
    path('api/verify-password/', admin_views.verify_password, name='verify_password'),
]
