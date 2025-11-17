from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count
from django.contrib import messages
from .models import Accident, AccidentCluster, AccidentReport, ClusteringJob, UserProfile, AuditLog


# ============================================================================
# ACCIDENT ADMIN
# ============================================================================

@admin.register(Accident)
class AccidentAdmin(admin.ModelAdmin):
    list_display = ['id', 'incident_type_short', 'location', 'date_committed', 'casualty_info', 'hotspot_badge', 'cluster_link']
    list_filter = ['province', 'year', 'is_hotspot', 'victim_killed', 'victim_injured', 'incident_type']
    search_fields = ['municipal', 'barangay', 'narrative', 'incident_type']
    list_per_page = 50
    date_hierarchy = 'date_committed'

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    fieldsets = (
        ('Location', {
            'fields': ('province', 'municipal', 'barangay', 'street', 'latitude', 'longitude')
        }),
        ('Incident Details', {
            'fields': ('date_committed', 'time_committed', 'incident_type', 'narrative')
        }),
        ('Casualties', {
            'fields': ('victim_killed', 'victim_injured', 'victim_unharmed', 'victim_count', 'suspect_count')
        }),
        ('Vehicle Information', {
            'fields': ('vehicle_kind', 'vehicle_make', 'vehicle_model', 'vehicle_plate_no'),
            'classes': ('collapse',)
        }),
        ('Case Status', {
            'fields': ('case_status', 'case_solve_type'),
            'classes': ('collapse',)
        }),
        ('Clustering', {
            'fields': ('cluster_id', 'is_hotspot')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_hotspot', 'unmark_as_hotspot', 'export_to_csv']

    def incident_type_short(self, obj):
        """Shortened incident type"""
        if obj.incident_type and len(obj.incident_type) > 40:
            return obj.incident_type[:40] + '...'
        return obj.incident_type or '-'
    incident_type_short.short_description = 'Incident Type'

    def location(self, obj):
        """Combined location display"""
        return f"{obj.municipal}, {obj.province}"
    location.short_description = 'Location'

    def casualty_info(self, obj):
        """Display casualty information with icons"""
        parts = []
        if obj.victim_killed:
            parts.append(f'☠️ {obj.victim_count} killed')
        elif obj.victim_injured:
            parts.append(f'🤕 {obj.victim_count} injured')
        elif obj.victim_unharmed:
            parts.append('✅ No casualties')
        else:
            parts.append(f'👥 {obj.victim_count}')
        return ' '.join(parts)
    casualty_info.short_description = 'Casualties'

    def hotspot_badge(self, obj):
        """Display hotspot status as badge"""
        if obj.is_hotspot:
            return format_html('<span style="background: #dc3545; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">🔥 HOTSPOT</span>')
        return format_html('<span style="color: #6c757d;">—</span>')
    hotspot_badge.short_description = 'Status'

    def cluster_link(self, obj):
        """Link to cluster if assigned"""
        if obj.cluster_id:
            url = reverse('admin:accidents_accidentcluster_changelist') + f'?cluster_id={obj.cluster_id}'
            return format_html('<a href="{}" style="color: #007bff;">Cluster #{}</a>', url, obj.cluster_id)
        return '-'
    cluster_link.short_description = 'Cluster'

    def mark_as_hotspot(self, request, queryset):
        """Mark selected accidents as hotspot"""
        updated = queryset.update(is_hotspot=True)
        self.message_user(request, f'{updated} accidents marked as hotspot.', messages.SUCCESS)
    mark_as_hotspot.short_description = '🔥 Mark selected as hotspot'

    def unmark_as_hotspot(self, request, queryset):
        """Unmark selected accidents as hotspot"""
        updated = queryset.update(is_hotspot=False)
        self.message_user(request, f'{updated} accidents unmarked as hotspot.', messages.SUCCESS)
    unmark_as_hotspot.short_description = '❄️ Unmark as hotspot'

    def export_to_csv(self, request, queryset):
        """Export selected to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="accidents_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Date', 'Time', 'Province', 'Municipal', 'Barangay', 'Incident Type', 'Casualties', 'Hotspot'])

        for obj in queryset:
            writer.writerow([
                obj.id,
                obj.date_committed,
                obj.time_committed or '',
                obj.province,
                obj.municipal,
                obj.barangay,
                obj.incident_type or '',
                obj.victim_count,
                'Yes' if obj.is_hotspot else 'No'
            ])

        self.message_user(request, f'{queryset.count()} accidents exported.', messages.SUCCESS)
        return response
    export_to_csv.short_description = '📥 Export selected to CSV'


# ============================================================================
# ACCIDENT CLUSTER ADMIN
# ============================================================================

@admin.register(AccidentCluster)
class AccidentClusterAdmin(admin.ModelAdmin):
    list_display = ['cluster_id', 'primary_location', 'accident_count_badge', 'severity_badge', 'algorithm_info', 'computed_at']
    list_filter = ['computed_at', 'linkage_method', 'algorithm_version']
    ordering = ['-severity_score', '-accident_count']
    search_fields = ['primary_location', 'cluster_id']

    readonly_fields = ['cluster_id', 'computed_at', 'accident_count', 'total_casualties', 'severity_score',
                       'center_latitude', 'center_longitude']

    fieldsets = (
        ('Cluster Identification', {
            'fields': ('cluster_id', 'primary_location', 'algorithm_version', 'linkage_method', 'distance_threshold')
        }),
        ('Statistics', {
            'fields': ('accident_count', 'total_casualties', 'severity_score')
        }),
        ('Geographic Info', {
            'fields': ('center_latitude', 'center_longitude', 'min_latitude', 'max_latitude',
                      'min_longitude', 'max_longitude')
        }),
        ('Temporal', {
            'fields': ('date_range_start', 'date_range_end', 'computed_at')
        }),
    )

    actions = ['view_accidents']

    def accident_count_badge(self, obj):
        """Display accident count as badge"""
        color = '#dc3545' if obj.accident_count >= 10 else '#ffc107' if obj.accident_count >= 5 else '#28a745'
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold;">{} accidents</span>',
            color, obj.accident_count
        )
    accident_count_badge.short_description = 'Accidents'

    def severity_badge(self, obj):
        """Display severity score as badge"""
        if obj.severity_score >= 100:
            color = '#dc3545'
            label = 'CRITICAL'
        elif obj.severity_score >= 50:
            color = '#ffc107'
            label = 'HIGH'
        else:
            color = '#28a745'
            label = 'MODERATE'

        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">{}: {:.1f}</span>',
            color, label, obj.severity_score
        )
    severity_badge.short_description = 'Severity'

    def algorithm_info(self, obj):
        """Display algorithm information"""
        return f"{obj.algorithm_version} ({obj.linkage_method})"
    algorithm_info.short_description = 'Algorithm'

    def view_accidents(self, request, queryset):
        """View accidents in selected clusters"""
        if queryset.count() > 1:
            self.message_user(request, 'Please select only one cluster.', messages.WARNING)
            return

        cluster = queryset.first()
        url = reverse('admin:accidents_accident_changelist') + f'?cluster_id={cluster.cluster_id}'
        from django.shortcuts import redirect
        return redirect(url)
    view_accidents.short_description = '👁️ View accidents in cluster'


# ============================================================================
# ACCIDENT REPORT ADMIN
# ============================================================================

@admin.register(AccidentReport)
class AccidentReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter_name', 'incident_date', 'location', 'status_badge', 'casualty_badge', 'created_at']
    list_filter = ['status', 'province', 'created_at', 'verified_at']
    search_fields = ['reporter_name', 'reporter_contact', 'municipal', 'barangay', 'incident_description']
    date_hierarchy = 'created_at'
    list_per_page = 50

    readonly_fields = ['created_at', 'updated_at', 'verified_at', 'verified_by']

    fieldsets = (
        ('Reporter Information', {
            'fields': ('reporter_name', 'reporter_contact', 'reported_by')
        }),
        ('Incident Details', {
            'fields': ('incident_date', 'incident_time', 'incident_description')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'province', 'municipal', 'barangay', 'street_address')
        }),
        ('Casualties & Vehicles', {
            'fields': ('casualties_killed', 'casualties_injured', 'vehicles_involved')
        }),
        ('Photos', {
            'fields': ('photo_1', 'photo_2', 'photo_3'),
            'classes': ('collapse',)
        }),
        ('Verification', {
            'fields': ('status', 'verified_by', 'verified_at', 'accident')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['verify_reports', 'reject_reports', 'set_investigating']

    def location(self, obj):
        """Display location"""
        return f"{obj.municipal}, {obj.province}"
    location.short_description = 'Location'

    def status_badge(self, obj):
        """Display status as colored badge"""
        colors = {
            'pending': '#ffc107',
            'verified': '#28a745',
            'investigating': '#007bff',
            'resolved': '#6c757d',
            'rejected': '#dc3545'
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 3px; font-weight: bold; font-size: 11px; text-transform: uppercase;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def casualty_badge(self, obj):
        """Display casualties"""
        if obj.casualties_killed > 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">☠️ {} killed</span>', obj.casualties_killed)
        elif obj.casualties_injured > 0:
            return format_html('<span style="color: #ffc107; font-weight: bold;">🤕 {} injured</span>', obj.casualties_injured)
        return '✅ No casualties'
    casualty_badge.short_description = 'Casualties'

    def verify_reports(self, request, queryset):
        """Mark selected reports as verified"""
        updated = queryset.filter(status='pending').update(
            status='verified',
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} reports verified.', messages.SUCCESS)
    verify_reports.short_description = '✅ Verify selected reports'

    def reject_reports(self, request, queryset):
        """Reject selected reports"""
        updated = queryset.exclude(status='resolved').update(status='rejected')
        self.message_user(request, f'{updated} reports rejected.', messages.SUCCESS)
    reject_reports.short_description = '❌ Reject selected reports'

    def set_investigating(self, request, queryset):
        """Set reports to investigating status"""
        updated = queryset.filter(status='verified').update(status='investigating')
        self.message_user(request, f'{updated} reports set to investigating.', messages.SUCCESS)
    set_investigating.short_description = '🔍 Set to investigating'


# ============================================================================
# CLUSTERING JOB ADMIN
# ============================================================================

@admin.register(ClusteringJob)
class ClusteringJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'started_at', 'status_badge', 'clusters_found', 'total_accidents', 'duration', 'started_by']
    list_filter = ['status', 'started_at', 'linkage_method']
    readonly_fields = ['started_at', 'completed_at', 'started_by']
    date_hierarchy = 'started_at'

    fieldsets = (
        ('Job Information', {
            'fields': ('started_by', 'started_at', 'completed_at', 'status')
        }),
        ('Parameters', {
            'fields': ('linkage_method', 'distance_threshold', 'min_cluster_size', 'date_from', 'date_to')
        }),
        ('Results', {
            'fields': ('clusters_found', 'total_accidents', 'error_message')
        }),
    )

    def status_badge(self, obj):
        """Display job status"""
        colors = {
            'pending': '#ffc107',
            'running': '#007bff',
            'completed': '#28a745',
            'failed': '#dc3545'
        }
        icons = {
            'pending': '⏳',
            'running': '▶️',
            'completed': '✅',
            'failed': '❌'
        }
        color = colors.get(obj.status, '#6c757d')
        icon = icons.get(obj.status, '•')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 3px; font-weight: bold; font-size: 11px;">{} {}</span>',
            color, icon, obj.status.upper()
        )
    status_badge.short_description = 'Status'

    def duration(self, obj):
        """Calculate job duration"""
        if obj.completed_at and obj.started_at:
            delta = obj.completed_at - obj.started_at
            seconds = int(delta.total_seconds())
            if seconds < 60:
                return f"{seconds}s"
            elif seconds < 3600:
                return f"{seconds//60}m {seconds%60}s"
            else:
                return f"{seconds//3600}h {(seconds%3600)//60}m"
        elif obj.status == 'running':
            return "In progress..."
        return "-"
    duration.short_description = 'Duration'

    def has_add_permission(self, request):
        """Don't allow manual creation - use clustering command"""
        return False


# ============================================================================
# USER PROFILE ADMIN
# ============================================================================

class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile - shown when editing User"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'PNP Profile'
    fk_name = 'user'

    fieldsets = (
        ('PNP Information', {
            'fields': ('badge_number', 'rank', 'role')
        }),
        ('Assignment', {
            'fields': ('region', 'province', 'station', 'unit')
        }),
        ('Contact Information', {
            'fields': ('mobile_number', 'phone_number')
        }),
        ('Security', {
            'fields': ('is_active', 'must_change_password', 'failed_login_attempts', 'account_locked_until', 'last_login')
        }),
    )

    readonly_fields = ['failed_login_attempts', 'account_locked_until', 'last_login']


class CustomUserAdmin(BaseUserAdmin):
    """Extended User admin with UserProfile inline"""
    inlines = (UserProfileInline,)

    list_display = ['username', 'email', 'first_name', 'last_name', 'get_rank', 'get_station', 'is_active_badge']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']

    def get_rank(self, obj):
        """Get user's PNP rank with error handling"""
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return obj.profile.get_rank_display()
        except UserProfile.DoesNotExist:
            pass
        return format_html('<span style="color: #dc3545;">⚠️ No profile</span>')
    get_rank.short_description = 'Rank'

    def get_station(self, obj):
        """Get user's station with error handling"""
        try:
            if hasattr(obj, 'profile') and obj.profile:
                return obj.profile.station or '-'
        except UserProfile.DoesNotExist:
            pass
        return '-'
    get_station.short_description = 'Station'

    def is_active_badge(self, obj):
        """Display active status as badge"""
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓ Active</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗ Inactive</span>')
    is_active_badge.short_description = 'Status'


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Standalone UserProfile admin"""
    list_display = ['get_full_name_with_rank', 'badge_number', 'role_badge', 'station', 'province', 'is_active_badge', 'last_login']
    list_filter = ['role', 'rank', 'province', 'is_active', 'region']
    search_fields = ['badge_number', 'user__username', 'user__first_name', 'user__last_name', 'station']
    readonly_fields = ['created_at', 'updated_at', 'failed_login_attempts', 'account_locked_until', 'last_login']

    fieldsets = (
        ('User Account', {
            'fields': ('user',)
        }),
        ('PNP Information', {
            'fields': ('badge_number', 'rank', 'role')
        }),
        ('Assignment/Jurisdiction', {
            'fields': ('region', 'province', 'station', 'unit')
        }),
        ('Contact Information', {
            'fields': ('mobile_number', 'phone_number')
        }),
        ('Security & Status', {
            'fields': ('is_active', 'must_change_password', 'failed_login_attempts', 'account_locked_until', 'last_login')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        }),
    )

    actions = ['activate_accounts', 'deactivate_accounts', 'reset_failed_attempts']

    def get_full_name_with_rank(self, obj):
        return obj.get_full_name_with_rank()
    get_full_name_with_rank.short_description = 'Name'

    def role_badge(self, obj):
        """Display role as badge"""
        colors = {
            'super_admin': '#dc3545',
            'regional_director': '#ffc107',
            'provincial_chief': '#007bff',
            'station_commander': '#17a2b8',
            'traffic_officer': '#28a745',
            'data_encoder': '#6c757d'
        }
        color = colors.get(obj.role, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'

    def is_active_badge(self, obj):
        """Display active status"""
        if obj.is_active:
            return format_html('<span style="color: #28a745; font-weight: bold;">✓</span>')
        return format_html('<span style="color: #dc3545; font-weight: bold;">✗</span>')
    is_active_badge.short_description = 'Active'

    def activate_accounts(self, request, queryset):
        """Activate selected accounts"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} accounts activated.', messages.SUCCESS)
    activate_accounts.short_description = '✓ Activate selected accounts'

    def deactivate_accounts(self, request, queryset):
        """Deactivate selected accounts"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} accounts deactivated.', messages.SUCCESS)
    deactivate_accounts.short_description = '✗ Deactivate selected accounts'

    def reset_failed_attempts(self, request, queryset):
        """Reset failed login attempts"""
        updated = queryset.update(failed_login_attempts=0, account_locked_until=None)
        self.message_user(request, f'{updated} accounts unlocked.', messages.SUCCESS)
    reset_failed_attempts.short_description = '🔓 Reset failed login attempts'


# ============================================================================
# AUDIT LOG ADMIN
# ============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for viewing audit trail"""
    list_display = ['timestamp', 'user', 'action_badge', 'action_description_short', 'ip_address', 'severity_badge', 'success_badge']
    list_filter = ['action', 'severity', 'success', 'timestamp', 'province', 'station']
    search_fields = ['username', 'action_description', 'ip_address', 'user__username']
    readonly_fields = ['timestamp', 'user', 'username', 'action', 'action_description', 'ip_address',
                       'user_agent', 'severity', 'success', 'station', 'province', 'changes']
    date_hierarchy = 'timestamp'
    list_per_page = 100

    fieldsets = (
        ('User Information', {
            'fields': ('user', 'username')
        }),
        ('Action Details', {
            'fields': ('action', 'action_description', 'timestamp', 'severity', 'success')
        }),
        ('Location', {
            'fields': ('station', 'province')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent', 'changes'),
            'classes': ('collapse',)
        }),
    )

    actions = ['export_logs']

    def action_badge(self, obj):
        """Display action as badge"""
        return format_html(
            '<code style="background: #f8f9fa; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</code>',
            obj.action
        )
    action_badge.short_description = 'Action'

    def action_description_short(self, obj):
        """Shortened description"""
        if len(obj.action_description) > 60:
            return obj.action_description[:60] + '...'
        return obj.action_description
    action_description_short.short_description = 'Description'

    def severity_badge(self, obj):
        """Display severity as colored badge"""
        colors = {
            'info': '#17a2b8',
            'warning': '#ffc107',
            'error': '#fd7e14',
            'critical': '#dc3545'
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color, obj.severity.upper()
        )
    severity_badge.short_description = 'Severity'

    def success_badge(self, obj):
        """Display success status"""
        if obj.success:
            return format_html('<span style="color: #28a745; font-size: 16px;">✓</span>')
        return format_html('<span style="color: #dc3545; font-size: 16px;">✗</span>')
    success_badge.short_description = 'Success'

    def export_logs(self, request, queryset):
        """Export audit logs to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'

        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'User', 'Action', 'Description', 'IP Address', 'Severity', 'Success'])

        for log in queryset:
            writer.writerow([
                log.timestamp,
                log.username,
                log.action,
                log.action_description,
                log.ip_address or '',
                log.severity,
                'Yes' if log.success else 'No'
            ])

        self.message_user(request, f'{queryset.count()} logs exported.', messages.SUCCESS)
        return response
    export_logs.short_description = '📥 Export selected logs'

    def has_add_permission(self, request):
        """Don't allow manual creation of audit logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of audit logs (for security/compliance)"""
        return request.user.is_superuser  # Only superuser can delete audit logs


# ============================================================================
# ADMIN SITE CUSTOMIZATION
# ============================================================================

admin.site.site_header = "PNP Caraga - Accident Hotspot Detection System"
admin.site.site_title = "PNP Caraga Admin"
admin.site.index_title = "System Administration"
