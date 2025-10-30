from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Accident, AccidentCluster, AccidentReport, ClusteringJob, UserProfile, AuditLog

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


# ============================================================================
# PNP USER PROFILE ADMIN
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

    list_display = ['username', 'email', 'first_name', 'last_name', 'get_rank', 'get_station', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'date_joined']

    def get_rank(self, obj):
        """Get user's PNP rank"""
        if hasattr(obj, 'profile'):
            return obj.profile.get_rank_display()
        return '-'
    get_rank.short_description = 'Rank'

    def get_station(self, obj):
        """Get user's station"""
        if hasattr(obj, 'profile'):
            return obj.profile.station or '-'
        return '-'
    get_station.short_description = 'Station'


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Standalone UserProfile admin"""
    list_display = ['get_full_name_with_rank', 'badge_number', 'role', 'station', 'province', 'is_active', 'last_login']
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

    def get_full_name_with_rank(self, obj):
        return obj.get_full_name_with_rank()
    get_full_name_with_rank.short_description = 'Name'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin for viewing audit trail"""
    list_display = ['timestamp', 'user', 'action', 'action_description', 'ip_address', 'severity', 'success']
    list_filter = ['action', 'severity', 'success', 'timestamp', 'province', 'station']
    search_fields = ['username', 'action_description', 'ip_address', 'user__username']
    readonly_fields = ['timestamp', 'user', 'username', 'action', 'action_description', 'ip_address',
                       'user_agent', 'severity', 'success', 'station', 'province', 'changes']
    date_hierarchy = 'timestamp'

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

    def has_add_permission(self, request):
        """Don't allow manual creation of audit logs"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Don't allow deletion of audit logs (for security/compliance)"""
        return False