from .models import Notification, AccidentReport, Accident, ClusteringJob, SystemSetting


def badge_counts(request):
    """Provide notification and pending report counts for header badges."""
    if not request.user.is_authenticated:
        return {}

    from .views import can_approve_reports, get_reports_for_jurisdiction

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    pending_count = 0
    if can_approve_reports(request.user):
        pending_queryset = AccidentReport.objects.filter(status='pending')
        pending_count = get_reports_for_jurisdiction(request.user, pending_queryset).count()

    # Count new accidents since last clustering (for roles that can run clustering)
    unclustered_count = 0
    if hasattr(request.user, 'profile') and (request.user.profile.role in ('super_admin', 'regional_director') or request.user.profile.can_run_clustering):
        last_job = ClusteringJob.objects.filter(status='completed').order_by('-completed_at').first()
        if last_job and last_job.completed_at:
            unclustered_count = Accident.objects.filter(created_at__gt=last_job.completed_at).count()
        else:
            unclustered_count = Accident.objects.count()

    # Display settings: user preference → system default → built-in fallback
    sys_accident_view = SystemSetting.get('accident_default_view')
    sys_hotspot_view = SystemSetting.get('hotspot_default_view')

    profile = getattr(request.user, 'profile', None)
    accident_default_view = (profile.pref_accident_view if profile and profile.pref_accident_view else sys_accident_view)
    hotspot_default_view = (profile.pref_hotspot_view if profile and profile.pref_hotspot_view else sys_hotspot_view)

    can_submit_reports = profile.can_submit_reports if profile else True
    can_edit_reports = profile.can_edit_reports if profile else False

    # Pagination default
    default_per_page = SystemSetting.get('default_per_page')

    return {
        'header_unread_count': unread_count,
        'header_pending_count': pending_count,
        'header_unclustered_count': unclustered_count,
        'accident_default_view': accident_default_view,
        'hotspot_default_view': hotspot_default_view,
        'can_submit_reports': can_submit_reports,
        'can_edit_reports': can_edit_reports,
        'default_per_page': default_per_page,
    }
