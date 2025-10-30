from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path('login/', views.login, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.dashboard, name='dashboard'),

    # Accidents
    path('accidents/', views.accident_list, name='accident_list'),
    path('accidents/<int:pk>/', views.accident_detail, name='accident_detail'),

    # Hotspots
    path('hotspots/', views.hotspots_view, name='hotspots'),
    path('hotspots/<int:cluster_id>/', views.hotspot_detail, name='hotspot_detail'),

    # Map View - MAKE SURE THIS LINE EXISTS AND IS NOT COMMENTED
    path('map/', views.map_view, name='map_view'),
    path('map/heatmap/', views.heatmap_view, name='heatmap'),

    # Reporting
    path('report/', views.report_accident, name='report_accident'),
    path('report/success/<int:pk>/', views.report_success, name='report_success'),

    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    path('analytics/advanced/', views.advanced_analytics_view, name='advanced_analytics'),

    # Other pages
    path('about/', views.about, name='about'),
    path('help/', views.help_view, name='help'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile, name='profile'),
]