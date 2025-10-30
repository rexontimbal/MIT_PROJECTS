from django.contrib import admin
from .models import Accident, AccidentCluster, AccidentReport, ClusteringJob

@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
    list_display = ['incident_type', 'municipal', 'date_committed', 'victim_count', 'cluster_id']
    list_filter = ['province', 'year', 'is_hotspot']
    search_fields = ['municipal', 'barangay', 'narrative']
    list_per_page = 25

@admin.register(AccidentCluster)
class AccidentClusterAdmin(admin.ModelAdmin):
    list_display = ['cluster_id', 'primary_location', 'accident_count', 'severity_score', 'computed_at']
    list_filter = ['computed_at']
    ordering = ['-severity_score']

@admin.register(AccidentReport)
class AccidentReportAdmin(admin.ModelAdmin):
    list_display = ['reporter_name', 'incident_date', 'municipal', 'status', 'created_at']
    list_filter = ['status', 'province', 'created_at']
    search_fields = ['reporter_name', 'municipal', 'barangay']
    actions = ['verify_reports']
    
    def verify_reports(self, request, queryset):
        queryset.update(status='verified')
        self.message_user(request, f'{queryset.count()} reports verified.')
    verify_reports.short_description = 'Mark selected as verified'

@admin.register(ClusteringJob)
class ClusteringJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'started_at', 'status', 'clusters_found', 'total_accidents']
    list_filter = ['status', 'started_at']
    readonly_fields = ['started_at', 'completed_at']