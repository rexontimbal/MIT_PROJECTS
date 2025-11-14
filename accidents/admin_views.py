"""
Custom Admin Panel Views for PNP IT Staff
User-friendly interface for system administration
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from datetime import timedelta
import json

from .models import (
    UserProfile, AuditLog, ClusteringJob,
    Accident, AccidentCluster, AccidentReport
)
from .auth_utils import log_user_action


# ============================================================================
# PERMISSION CHECKS
# ============================================================================

def is_superuser(user):
    """Check if user is Django superuser"""
    return user.is_authenticated and user.is_superuser

def is_admin(user):
    """Check if user is admin (Django superuser OR has super_admin role)"""
    if not user.is_authenticated:
        return False

    # Django superusers always have access
    if user.is_superuser:
        return True

    # Check if user has super_admin role in their profile
    if hasattr(user, 'profile'):
        return user.profile.role == 'super_admin'

    return False


def is_staff_or_superuser(user):
    """Check if user is staff or superuser"""
    return user.is_authenticated and (user.is_staff or user.is_superuser)


# ============================================================================
# ADMIN DASHBOARD
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def admin_dashboard(request):
    """Main admin dashboard with system overview"""

    # System Statistics
    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
        'total_accidents': Accident.objects.count(),
        'total_hotspots': AccidentCluster.objects.count(),
        'pending_reports': AccidentReport.objects.filter(status='pending').count(),
        'recent_logins': AuditLog.objects.filter(
            action='login',
            timestamp__gte=timezone.now() - timedelta(days=7)
        ).count(),
    }

    # Recent Activity (Last 10 audit logs)
    recent_activity = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]

    # Recent Clustering Jobs
    recent_jobs = ClusteringJob.objects.order_by('-started_at')[:5]

    # User Role Distribution
    role_distribution = UserProfile.objects.values('role').annotate(
        count=Count('role')
    ).order_by('-count')

    # Recent Users (Last 7 days)
    recent_users = User.objects.filter(
        date_joined__gte=timezone.now() - timedelta(days=7)
    ).select_related('profile').order_by('-date_joined')[:5]

    context = {
        'stats': stats,
        'recent_activity': recent_activity,
        'recent_jobs': recent_jobs,
        'role_distribution': role_distribution,
        'recent_users': recent_users,
    }

    log_user_action(
        request=request,
        action='admin_dashboard_view',
        description='Viewed admin dashboard',
        severity='info'
    )

    return render(request, 'admin_panel/dashboard.html', context)


# ============================================================================
# USER MANAGEMENT
# ============================================================================

@login_required
@user_passes_test(is_admin)
def user_management(request):
    """User management page - list all users"""

    # Search and Filter
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    # Get all users with profiles, ordered by username
    users = User.objects.select_related('profile').all().order_by('username')

    # Apply search
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(profile__badge_number__icontains=search_query)
        )

    # Apply role filter
    if role_filter:
        users = users.filter(profile__role=role_filter)

    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'staff':
        users = users.filter(is_staff=True)
    elif status_filter == 'superuser':
        users = users.filter(is_superuser=True)

    # Pagination
    paginator = Paginator(users, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all roles for filter dropdown
    roles = UserProfile.ROLE_CHOICES

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'total_count': users.count(),
    }

    return render(request, 'admin_panel/user_management.html', context)


@login_required
@user_passes_test(is_admin)
def user_detail(request, user_id):
    """View and edit user details"""

    user = get_object_or_404(User, pk=user_id)
    profile = user.profile if hasattr(user, 'profile') else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_basic':
            # Update basic user info
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')
            user.save()

            # Handle profile picture
            if profile:
                # Check if user wants to remove current picture
                if request.POST.get('remove_picture'):
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                        profile.profile_picture = None

                # Handle new picture upload
                if 'profile_picture' in request.FILES:
                    # Delete old picture if exists
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                    profile.profile_picture = request.FILES['profile_picture']

                profile.save()

            messages.success(request, f'User {user.username} updated successfully!')

            log_user_action(
                request=request,
                action='user_edit',
                description=f'Updated basic info for user: {user.username}',
                severity='info'
            )

        elif action == 'update_profile':
            # Update user profile
            if profile:
                profile.badge_number = request.POST.get('badge_number', '')
                profile.rank = request.POST.get('rank', '')
                profile.role = request.POST.get('role', '')
                profile.region = request.POST.get('region', '')
                profile.province = request.POST.get('province', '')
                profile.station = request.POST.get('station', '')
                profile.unit = request.POST.get('unit', '')
                profile.mobile_number = request.POST.get('mobile_number', '')
                profile.phone_number = request.POST.get('phone_number', '')
                profile.save()

                messages.success(request, f'Profile for {user.username} updated successfully!')

                log_user_action(
                    request=request,
                    action='user_profile_edit',
                    description=f'Updated profile for user: {user.username}',
                    severity='info'
                )

        elif action == 'update_permissions':
            # Update permissions
            user.is_staff = request.POST.get('is_staff') == 'on'
            user.is_superuser = request.POST.get('is_superuser') == 'on'
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()

            messages.success(request, f'Permissions for {user.username} updated successfully!')

            log_user_action(
                request=request,
                action='user_permissions_edit',
                description=f'Updated permissions for user: {user.username} (Staff: {user.is_staff}, Superuser: {user.is_superuser}, Active: {user.is_active})',
                severity='warning'
            )

        elif action == 'update_username':
            # Handle username editing (after password confirmation on frontend)
            old_username = user.username
            new_username = request.POST.get('username', '').strip()

            # Validate new username
            if not new_username:
                messages.error(request, 'Username cannot be empty!')
            elif new_username == old_username:
                messages.info(request, 'Username was not changed.')
            elif User.objects.filter(username=new_username).exists():
                messages.error(request, f'Username "{new_username}" is already taken!')
            else:
                # Update username
                user.username = new_username
                user.save()

                messages.success(request, f'Username changed from "{old_username}" to "{new_username}" successfully!')

                log_user_action(
                    request=request,
                    action='username_change',
                    description=f'Changed username from "{old_username}" to "{new_username}"',
                    severity='warning'
                )

        return redirect('admin_panel:user_detail', user_id=user.id)

    # Get user's recent audit logs
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')[:20]

    context = {
        'target_user': user,
        'profile': profile,
        'recent_logs': recent_logs,
        'ranks': UserProfile.RANK_CHOICES,
        'roles': UserProfile.ROLE_CHOICES,
    }

    return render(request, 'admin_panel/user_detail.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    """Create new user"""

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')

        # Validate passwords match
        if password != confirm_password:
            messages.error(request, 'Passwords do not match! Please try again.')
            return redirect('admin_panel:user_create')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" already exists!')
            return redirect('admin_panel:user_create')

        # Create user
        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name
        )

        # Create profile
        profile = UserProfile.objects.create(
            user=user,
            badge_number=request.POST.get('badge_number', ''),
            rank=request.POST.get('rank', 'pcpl'),
            role=request.POST.get('role', 'traffic_officer'),
            region=request.POST.get('region', 'Caraga'),
            province=request.POST.get('province', ''),
            station=request.POST.get('station', ''),
            unit=request.POST.get('unit', ''),
            mobile_number=request.POST.get('mobile_number', ''),
            phone_number=request.POST.get('phone_number', ''),
            created_by=request.user
        )

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()

        # Set permissions
        user.is_staff = request.POST.get('is_staff') == 'on'
        user.is_superuser = request.POST.get('is_superuser') == 'on'
        user.save()

        messages.success(request, f'User "{username}" created successfully!')

        log_user_action(
            request=request,
            action='user_create',
            description=f'Created new user: {username} with role {profile.get_role_display()}',
            severity='info'
        )

        return redirect('admin_panel:user_detail', user_id=user.id)

    context = {
        'ranks': UserProfile.RANK_CHOICES,
        'roles': UserProfile.ROLE_CHOICES,
    }

    return render(request, 'admin_panel/user_create.html', context)


@login_required
@user_passes_test(is_admin)
def user_reset_password(request, user_id):
    """Reset user password"""

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_password = data.get('new_password')
        else:
            new_password = request.POST.get('new_password')

        # Validate password
        if not new_password:
            return JsonResponse({'success': False, 'error': 'Password is required'})

        if len(new_password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long'})

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update profile to force password change
        if hasattr(user, 'profile'):
            user.profile.must_change_password = True
            user.profile.save()

        messages.success(request, f'Password for {user.username} reset successfully! User will be required to change password on next login.')

        log_user_action(
            request=request,
            action='password_reset',
            description=f'Reset password for user: {user.username}',
            severity='warning'
        )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(is_admin)
def user_toggle_active(request, user_id):
    """Activate or deactivate user"""

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        # Don't allow deactivating yourself
        if user == request.user:
            return JsonResponse({'success': False, 'error': 'You cannot deactivate your own account!'})

        # Toggle active status
        user.is_active = not user.is_active
        user.save()

        status = 'activated' if user.is_active else 'deactivated'
        messages.success(request, f'User {user.username} {status} successfully!')

        log_user_action(
            request=request,
            action='user_status_change',
            description=f'{status.capitalize()} user: {user.username}',
            severity='warning'
        )

        return JsonResponse({'success': True, 'is_active': user.is_active})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
def verify_password(request):
    """Verify user password for sensitive operations"""
    import json

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            password = data.get('password')

            if not password:
                return JsonResponse({'valid': False, 'error': 'Password required'})

            # Check if user's password matches
            if request.user.check_password(password):
                # Log the verification attempt
                log_user_action(
                    request=request,
                    action='password_verify',
                    description='User verified password for sensitive operation',
                    severity='info'
                )
                return JsonResponse({'valid': True})
            else:
                # Log failed attempt
                log_user_action(
                    request=request,
                    action='password_verify',
                    description='Failed password verification attempt',
                    severity='warning',
                    success=False
                )
                return JsonResponse({'valid': False, 'error': 'Incorrect password'})

        except json.JSONDecodeError:
            return JsonResponse({'valid': False, 'error': 'Invalid request'})

    return JsonResponse({'valid': False, 'error': 'Invalid request method'})


# ============================================================================
# AUDIT LOG VIEWER
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def audit_logs(request):
    """View audit logs with search and filters"""

    # Filters
    search_query = request.GET.get('search', '')
    action_filter = request.GET.get('action', '')
    severity_filter = request.GET.get('severity', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    user_filter = request.GET.get('user', '')

    logs = AuditLog.objects.select_related('user').all()

    # Apply filters
    if search_query:
        logs = logs.filter(
            Q(action_description__icontains=search_query) |
            Q(username__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )

    if action_filter:
        logs = logs.filter(action=action_filter)

    if severity_filter:
        logs = logs.filter(severity=severity_filter)

    if user_filter:
        logs = logs.filter(user_id=user_filter)

    if date_from:
        logs = logs.filter(timestamp__gte=date_from)

    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    # Order by timestamp (newest first)
    logs = logs.order_by('-timestamp')

    # Pagination
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get unique actions and users for filters
    actions = AuditLog.objects.values_list('action', flat=True).distinct()
    severities = ['info', 'warning', 'critical']

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'action_filter': action_filter,
        'severity_filter': severity_filter,
        'date_from': date_from,
        'date_to': date_to,
        'actions': actions,
        'severities': severities,
        'total_count': logs.count(),
    }

    return render(request, 'admin_panel/audit_logs.html', context)


# ============================================================================
# SYSTEM MONITORING
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def system_monitoring(request):
    """System monitoring dashboard"""

    # Clustering Jobs Statistics
    jobs_stats = {
        'total': ClusteringJob.objects.count(),
        'running': ClusteringJob.objects.filter(status='running').count(),
        'completed': ClusteringJob.objects.filter(status='completed').count(),
        'failed': ClusteringJob.objects.filter(status='failed').count(),
    }

    # Recent clustering jobs
    recent_jobs = ClusteringJob.objects.order_by('-started_at')[:10]

    # System health metrics
    health = {
        'database': 'healthy',  # Would check actual DB connection
        'celery': 'unknown',  # Would check Celery workers
        'cache': 'unknown',  # Would check cache
    }

    # Error logs (critical audit logs)
    error_logs = AuditLog.objects.filter(
        severity='critical',
        success=False
    ).order_by('-timestamp')[:10]

    context = {
        'jobs_stats': jobs_stats,
        'recent_jobs': recent_jobs,
        'health': health,
        'error_logs': error_logs,
    }

    return render(request, 'admin_panel/system_monitoring.html', context)


# ============================================================================
# AJAX ENDPOINTS
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def get_user_stats(request):
    """Get user statistics for dashboard"""

    stats = {
        'total': User.objects.count(),
        'active': User.objects.filter(is_active=True).count(),
        'staff': User.objects.filter(is_staff=True).count(),
        'by_role': list(UserProfile.objects.values('role').annotate(count=Count('role'))),
    }

    return JsonResponse(stats)


@login_required
@user_passes_test(is_staff_or_superuser)
def get_system_health(request):
    """Get system health status"""

    # This would be expanded with actual health checks
    health = {
        'status': 'healthy',
        'database': True,
        'celery': True,
        'cache': True,
        'timestamp': timezone.now().isoformat(),
    }

    return JsonResponse(health)
