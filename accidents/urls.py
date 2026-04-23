from django.urls import path, include
from . import views
from .ajax_chart_data import get_chart_data_ajax

urlpatterns = [
    # Authentication
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password, name='change_password'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Custom Admin Panel (PNP-themed, user-friendly)
    path('admin-panel/', include('accidents.admin_urls')),

    # Accidents
    path('accidents/', views.accident_list, name='accident_list'),
    path('accidents/<int:pk>/', views.accident_detail, name='accident_detail'),

    # Super Admin: CSV Upload & Edit (on accident page)
    path('accidents/csv-upload/', views.accident_csv_upload, name='accident_csv_upload'),
    path('accidents/<int:pk>/edit/', views.accident_edit, name='accident_edit'),
    path('accidents/<int:pk>/details-json/', views.accident_details_json, name='accident_details_json'),
    path('accidents/<int:pk>/update-case-status/', views.update_case_status, name='update_case_status'),

    # Hotspots
    path('hotspots/', views.hotspots_view, name='hotspots'),
    path('hotspots/<int:cluster_id>/', views.hotspot_detail, name='hotspot_detail'),
    path('hotspots/run-clustering/', views.run_clustering_view, name='run_clustering'),

    # Map View - MAKE SURE THIS LINE EXISTS AND IS NOT COMMENTED
    path('map/', views.map_view, name='map_view'),
    path('map/heatmap/', views.heatmap_view, name='heatmap'),

    # Reporting
    path('report/', views.report_accident, name='report_accident'),
    path('report/success/<int:pk>/', views.report_success, name='report_success'),
    path('my-reports/', views.my_reports, name='my_reports'),
    path('report/<int:pk>/', views.view_report_detail, name='report_detail'),
    path('report/<int:pk>/edit/', views.edit_report, name='edit_report'),
    path('report/<int:pk>/cancel/', views.cancel_report, name='cancel_report'),
    path('report/<int:pk>/delete/', views.delete_report, name='delete_report'),
    path('report/<int:pk>/download-pdf/', views.download_report_pdf, name='download_report_pdf'),
    path('report/<int:pk>/police-report/', views.generate_police_report_pdf, name='generate_police_report_pdf'),

    # Pending Reports Management (for Station Commanders, Provincial Chiefs, etc.)
    path('manage/pending-reports/', views.pending_reports, name='pending_reports'),
    path('manage/report/<int:pk>/approve/', views.approve_report, name='approve_report'),
    path('manage/report/<int:pk>/reject/', views.reject_report, name='reject_report'),
    path('manage/report/<int:pk>/cancel/', views.admin_cancel_report, name='admin_cancel_report'),
    path('manage/report/<int:pk>/go/', views.report_notification_redirect, name='report_notification_redirect'),
    path('manage/bulk-action/', views.bulk_action_reports, name='bulk_action_reports'),
    path('manage/resync-reports/', views.resync_reports, name='resync_reports'),
    path('api/check-duplicate/', views.check_duplicate_report, name='check_duplicate_report'),

    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    path('analytics/advanced/', views.advanced_analytics_view, name='advanced_analytics'),
    path('api/chart-data/', get_chart_data_ajax, name='get_chart_data_ajax'),  # AJAX endpoint for chart filtering

    # Other pages
    path('about/', views.about, name='about'),
    path('help/', views.help_view, name='help'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile, name='profile'),
    path('profile/change-username/', views.change_username, name='change_username'),
    path('profile/change-password/', views.change_password_api, name='change_password_api'),
    path('display-settings/', views.display_settings, name='display_settings'),

    # Export Endpoints
    path('export/accidents/csv/', views.export_accidents_csv, name='export_accidents_csv'),
    path('export/accidents/excel/', views.export_accidents_excel, name='export_accidents_excel'),
    path('export/hotspots/pdf/', views.export_hotspots_pdf, name='export_hotspots_pdf'),
    path('export/analytics/pdf/', views.export_analytics_pdf, name='export_analytics_pdf'),
    path('export/monthly-narrative/pdf/', views.export_monthly_narrative_pdf, name='export_monthly_narrative_pdf'),

    # Notifications
    path('notifications/', views.notifications_page, name='notifications'),

    # Notification API
    path('api/notifications/', views.get_notifications, name='get_notifications'),
    path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('api/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]