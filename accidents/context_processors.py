from .models import Notification, AccidentReport, Accident, ClusteringJob


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

    # Count new accidents since last clustering (for super_admin and regional_director)
    unclustered_count = 0
    if hasattr(request.user, 'profile') and request.user.profile.role in ('super_admin', 'regional_director'):
        last_job = ClusteringJob.objects.filter(status='completed').order_by('-completed_at').first()
        if last_job and last_job.completed_at:
            unclustered_count = Accident.objects.filter(created_at__gt=last_job.completed_at).count()
        else:
            unclustered_count = Accident.objects.count()

    return {
        'header_unread_count': unread_count,
        'header_pending_count': pending_count,
        'header_unclustered_count': unclustered_count,
    }
