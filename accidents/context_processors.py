from .models import Notification, AccidentReport


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

    return {
        'header_unread_count': unread_count,
        'header_pending_count': pending_count,
    }
