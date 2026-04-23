"""
Custom Admin Panel Views for PNP IT Staff
User-friendly interface for system administration
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.cache import cache
from django.conf import settings
from datetime import timedelta
import json
import re
import subprocess
import os

from .models import (
    UserProfile, AuditLog, ClusteringJob,
    Accident, AccidentCluster, AccidentReport, ReportActivityLog,
    SystemSetting, DropdownOption
)
from .auth_utils import log_user_action


# ============================================================================
# PERMISSION CHECKS (ROLE-BASED)
# ============================================================================

def is_superuser(user):
    """Check if user is Django superuser"""
    return user.is_authenticated and user.is_superuser

def is_super_admin(user):
    """Check if user has super_admin role - can access Django admin and Admin Panel"""
    if not user.is_authenticated:
        return False

    # Check if user has super_admin role in their profile
    if hasattr(user, 'profile'):
        return user.profile.role == 'super_admin'

    return False

def is_admin(user):
    """Check if user can access Admin Panel (super_admin or regional_director)"""
    if not user.is_authenticated:
        return False

    # Check if user has admin role in their profile
    if hasattr(user, 'profile'):
        return user.profile.role in ['super_admin', 'regional_director']

    return False


def is_staff_or_superuser(user):
    """Check if user can access admin features (super_admin or regional_director)"""
    return is_admin(user)


def can_manage_users(user):
    """Check if user can manage personnel (admin roles + provincial_chief/station_commander for their jurisdiction)"""
    if not user.is_authenticated:
        return False
    if hasattr(user, 'profile'):
        return user.profile.role in ['super_admin', 'regional_director', 'provincial_chief', 'station_commander']
    return False


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
        'inactive_users': User.objects.filter(is_active=False).count(),
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
@user_passes_test(can_manage_users)
def user_management(request):
    """User management page - list all users (scoped by jurisdiction)"""

    # Search and Filter
    search_query = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')

    # Get all users with profiles, ordered by username
    users = User.objects.select_related('profile').all().order_by('username')

    # Jurisdiction-based scoping
    profile = getattr(request.user, 'profile', None)
    if profile and profile.role == 'provincial_chief':
        # Provincial Chief: manage station_commander, traffic_officer, data_encoder in their province
        manageable_roles = ['station_commander', 'traffic_officer', 'data_encoder']
        users = users.filter(profile__role__in=manageable_roles)
        if profile.province:
            users = users.filter(profile__province=profile.province)
    elif profile and profile.role == 'station_commander':
        # Station Commander: manage traffic_officer, data_encoder at their station only
        manageable_roles = ['traffic_officer', 'data_encoder']
        users = users.filter(
            profile__role__in=manageable_roles,
            profile__station=profile.station
        )
        if profile.province:
            users = users.filter(profile__province=profile.province)

    # Apply search - searches across multiple fields
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(profile__badge_number__icontains=search_query) |
            Q(profile__rank__icontains=search_query) |
            Q(profile__station__icontains=search_query)
        )

    # Apply role filter (sanitize for scoped roles)
    if role_filter:
        if profile and profile.role == 'station_commander' and role_filter not in ['traffic_officer', 'data_encoder']:
            role_filter = ''
        elif profile and profile.role == 'provincial_chief' and role_filter not in ['station_commander', 'traffic_officer', 'data_encoder']:
            role_filter = ''
        else:
            users = users.filter(profile__role=role_filter)

    # Apply status filter
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)

    # Pagination with configurable per-page (system default from settings)
    sys_default = SystemSetting.get('default_per_page')
    per_page = request.GET.get('per_page', sys_default)
    try:
        per_page = int(per_page)
        if per_page not in [10, 15, 20, 50]:
            per_page = int(sys_default)
    except (ValueError, TypeError):
        per_page = 15

    paginator = Paginator(users, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all roles for filter dropdown
    roles = UserProfile.ROLE_CHOICES

    uses_main_layout = profile and profile.role in ['station_commander', 'provincial_chief']
    base_template = 'base.html' if uses_main_layout else 'admin_panel/base.html'

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'ranks': UserProfile.RANK_CHOICES,
        'total_count': users.count(),
        'per_page': per_page,
        'base_template': base_template,
    }

    return render(request, 'admin_panel/user_management.html', context)


@login_required
@user_passes_test(can_manage_users)
def user_detail(request, user_id):
    """View and edit user details"""

    user = get_object_or_404(User, pk=user_id)
    profile = user.profile if hasattr(user, 'profile') else None

    # Jurisdiction checks for scoped roles
    requester = getattr(request.user, 'profile', None)
    if requester and requester.role == 'provincial_chief':
        if not profile or profile.role not in ['station_commander', 'traffic_officer', 'data_encoder'] or profile.province != requester.province:
            messages.error(request, 'You can only manage personnel in your province.')
            return redirect('admin_panel:users')
    elif requester and requester.role == 'station_commander':
        if not profile or profile.role not in ['traffic_officer', 'data_encoder'] or profile.station != requester.station:
            messages.error(request, 'You can only manage personnel at your station.')
            return redirect('admin_panel:users')

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
                        print(f"DEBUG: Removed profile picture for user: {user.username}")

                # Handle new picture upload
                if 'profile_picture' in request.FILES:
                    try:
                        import os
                        from django.conf import settings

                        # Ensure media directories exist
                        media_root = settings.MEDIA_ROOT
                        profile_pics_dir = os.path.join(media_root, 'profile_pictures')
                        os.makedirs(profile_pics_dir, exist_ok=True)

                        # Delete old picture if exists
                        if profile.profile_picture:
                            profile.profile_picture.delete(save=False)

                        uploaded_file = request.FILES['profile_picture']
                        profile.profile_picture = uploaded_file
                        print(f"DEBUG: Profile picture received for edit - Name: {uploaded_file.name}, Size: {uploaded_file.size} bytes")

                    except Exception as e:
                        print(f"DEBUG: Profile picture upload failed for {user.username} - {str(e)}")
                        messages.warning(request, f'Profile picture upload failed: {str(e)}')

                profile.save()
                print(f"DEBUG: Profile saved for user: {user.username}")

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
                old_role = profile.role
                new_role = request.POST.get('role', '')

                # Validate role assignment based on requester's jurisdiction
                if requester and requester.role == 'station_commander':
                    if new_role not in ['traffic_officer', 'data_encoder']:
                        new_role = old_role
                elif requester and requester.role == 'provincial_chief':
                    if new_role not in ['station_commander', 'traffic_officer', 'data_encoder']:
                        new_role = old_role

                profile.badge_number = request.POST.get('badge_number', '')
                profile.rank = request.POST.get('rank', '')
                profile.role = new_role
                profile.region = request.POST.get('region', '')
                profile.province = request.POST.get('province', '')
                profile.unit = request.POST.get('unit', '')
                profile.mobile_number = request.POST.get('mobile_number', '')
                profile.phone_number = request.POST.get('phone_number', '')

                # Handle station vs office based on role
                if profile.role == 'regional_director':
                    profile.office = request.POST.get('office_pro', '') or request.POST.get('office', '') or 'Police Regional Office CARAGA'
                    profile.station = ''  # Clear station for command-level roles
                elif profile.role == 'provincial_chief':
                    profile.office = request.POST.get('office', '')
                    profile.station = ''  # Clear station for command-level roles
                else:
                    profile.station = request.POST.get('station', '')
                    profile.office = ''  # Clear office for station-level roles

                profile.save()

                # Automatically update permissions based on role
                if profile.role == 'super_admin':
                    user.is_staff = True
                    user.is_superuser = True
                elif profile.role == 'regional_director':
                    user.is_staff = True
                    user.is_superuser = False
                else:
                    user.is_staff = False
                    user.is_superuser = False
                user.save()

                messages.success(request, f'Profile for {user.username} updated successfully!')

                log_user_action(
                    request=request,
                    action='user_profile_edit',
                    description=f'Updated profile for user: {user.username} (Role changed from {old_role} to {profile.role})',
                    severity='info'
                )

        elif action == 'update_permissions':
            # Update active status and report access
            user.is_active = request.POST.get('is_active') == 'on'
            user.save()

            if profile:
                profile.can_submit_reports = request.POST.get('can_submit_reports') == 'on'
                update_fields = ['can_submit_reports']
                if requester and requester.role in ('super_admin', 'regional_director'):
                    profile.can_run_clustering = request.POST.get('can_run_clustering') == 'on'
                    update_fields.append('can_run_clustering')
                profile.save(update_fields=update_fields)

            messages.success(request, f'Status for {user.username} updated successfully!')

            log_user_action(
                request=request,
                action='user_status_edit',
                description=f'Updated status for user: {user.username} (Active: {user.is_active}, Report Access: {profile.can_submit_reports if profile else "N/A"})',
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

        elif action == 'update_all':
            # Consolidated update - handles all sections in one save
            changes_made = []

            # 1. Update Basic Info
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.email = request.POST.get('email', '')

            # 2. Update Profile Picture
            if profile:
                # Check if user wants to remove current picture
                if request.POST.get('remove_picture'):
                    if profile.profile_picture:
                        profile.profile_picture.delete(save=False)
                        profile.profile_picture = None
                        changes_made.append('removed profile picture')

                # Handle new picture upload
                if 'profile_picture' in request.FILES:
                    try:
                        import os
                        from django.conf import settings

                        # Ensure media directories exist
                        media_root = settings.MEDIA_ROOT
                        profile_pics_dir = os.path.join(media_root, 'profile_pictures')
                        os.makedirs(profile_pics_dir, exist_ok=True)

                        # Delete old picture if exists
                        if profile.profile_picture:
                            profile.profile_picture.delete(save=False)

                        uploaded_file = request.FILES['profile_picture']
                        profile.profile_picture = uploaded_file
                        changes_made.append('updated profile picture')

                    except Exception as e:
                        messages.warning(request, f'Profile picture upload failed: {str(e)}')

            # 3. Update Profile Information
            if profile:
                old_role = profile.role
                new_role = request.POST.get('role', '')

                # Validate role assignment based on requester's jurisdiction
                if requester and requester.role == 'station_commander':
                    if new_role not in ['traffic_officer', 'data_encoder']:
                        new_role = old_role  # Reject unauthorized role change
                elif requester and requester.role == 'provincial_chief':
                    if new_role not in ['station_commander', 'traffic_officer', 'data_encoder']:
                        new_role = old_role  # Reject unauthorized role change

                profile.badge_number = request.POST.get('badge_number', '')
                profile.rank = request.POST.get('rank', '')
                profile.role = new_role
                profile.region = request.POST.get('region', '')
                profile.province = request.POST.get('province', '')
                profile.unit = request.POST.get('unit', '')
                profile.mobile_number = request.POST.get('mobile_number', '')
                profile.phone_number = request.POST.get('phone_number', '')

                # Handle station vs office based on role
                if profile.role == 'regional_director':
                    profile.office = request.POST.get('office_pro', '') or request.POST.get('office', '') or 'Police Regional Office CARAGA'
                    profile.station = ''
                elif profile.role == 'provincial_chief':
                    profile.office = request.POST.get('office', '')
                    profile.station = ''
                else:
                    profile.station = request.POST.get('station', '')
                    profile.office = ''

                # Track role change
                if old_role != profile.role:
                    changes_made.append(f'changed role from {old_role} to {profile.role}')

                # Update report access
                old_report_access = profile.can_submit_reports
                profile.can_submit_reports = request.POST.get('can_submit_reports') == 'on'
                if old_report_access != profile.can_submit_reports:
                    changes_made.append(f'{"enabled" if profile.can_submit_reports else "disabled"} report access')

                # Update clustering access (only super_admin and regional_director can grant this)
                if requester and requester.role in ('super_admin', 'regional_director'):
                    old_clustering_access = profile.can_run_clustering
                    profile.can_run_clustering = request.POST.get('can_run_clustering') == 'on'
                    if old_clustering_access != profile.can_run_clustering:
                        changes_made.append(f'{"enabled" if profile.can_run_clustering else "disabled"} clustering access')

                    old_edit_reports = profile.can_edit_reports
                    profile.can_edit_reports = request.POST.get('can_edit_reports') == 'on'
                    if old_edit_reports != profile.can_edit_reports:
                        changes_made.append(f'{"enabled" if profile.can_edit_reports else "disabled"} report edit access')

                # Automatically update permissions based on role
                if profile.role == 'super_admin':
                    user.is_staff = True
                    user.is_superuser = True
                elif profile.role == 'regional_director':
                    user.is_staff = True
                    user.is_superuser = False
                else:
                    user.is_staff = False
                    user.is_superuser = False

                profile.save()

            # 4. Update Active Status
            old_active = user.is_active
            user.is_active = request.POST.get('is_active') == 'on'
            if old_active != user.is_active:
                changes_made.append(f'changed status to {"active" if user.is_active else "inactive"}')

            # Save user
            user.save()

            # Success message
            changes_summary = ', '.join(changes_made) if changes_made else 'updated user information'
            messages.success(request, f'User {user.username} updated successfully! ({changes_summary})')

            # Log the action
            log_user_action(
                request=request,
                action='user_edit',
                description=f'Updated user: {user.username} - {changes_summary}',
                severity='info'
            )

        return redirect('admin_panel:user_detail', user_id=user.id)

    # Get user's recent audit logs
    recent_logs = AuditLog.objects.filter(user=user).order_by('-timestamp')

    uses_main_layout = requester and requester.role in ['station_commander', 'provincial_chief']
    base_template = 'base.html' if uses_main_layout else 'admin_panel/base.html'

    context = {
        'target_user': user,
        'profile': profile,
        'recent_logs': recent_logs,
        'ranks': UserProfile.RANK_CHOICES,
        'roles': UserProfile.ROLE_CHOICES,
        'base_template': base_template,
    }

    return render(request, 'admin_panel/user_detail.html', context)


@login_required
@user_passes_test(can_manage_users)
def user_create(request):
    """Create new user"""
    import re

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    _req_profile = getattr(request.user, 'profile', None)
    base_template = 'base.html' if (_req_profile and _req_profile.role in ['station_commander', 'provincial_chief']) else 'admin_panel/base.html'

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        badge_number = request.POST.get('badge_number', '').strip().upper()
        mobile_number = request.POST.get('mobile_number', '')

        # Validate badge number format (4-8 alphanumeric characters)
        badge_clean = re.sub(r'[^a-zA-Z0-9]', '', badge_number)
        if len(badge_clean) < 4 or len(badge_clean) > 8:
            error_msg = 'Badge number must be 4-8 alphanumeric characters.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'badge_number'})
            messages.error(request, error_msg)
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)
        badge_number = badge_clean

        # Debug: Log if profile picture is in request
        has_picture = 'profile_picture' in request.FILES
        if has_picture:
            file_info = request.FILES['profile_picture']
            print(f"DEBUG: Profile picture received - Name: {file_info.name}, Size: {file_info.size} bytes")
        else:
            print("DEBUG: No profile picture in request.FILES")

        # Validate passwords match
        if password != confirm_password:
            error_msg = 'Passwords do not match! Please try again.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'confirm_password'})
            messages.error(request, error_msg)
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            error_msg = f'Username "{username}" already exists!'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'username'})
            messages.error(request, error_msg)
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

        # Check if badge_number already exists
        if UserProfile.objects.filter(badge_number=badge_number).exists():
            error_msg = f'Badge/ID number "{badge_number}" already exists! Please use a unique badge number.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'badge_number'})
            messages.error(request, error_msg)
            # Return to form with preserved data and focus badge_number field
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'focus_field': 'badge_number',  # Focus on the error field
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

        # Validate mobile number is present and complete
        if not mobile_number or mobile_number.strip() == '':
            error_msg = 'Mobile number is required! Please enter a 10-digit number.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'mobile_number'})
            messages.error(request, error_msg)
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'focus_field': 'mobile_number',
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

        mobile_digits = re.sub(r'\D', '', mobile_number)
        if len(mobile_digits) != 10:
            error_msg = 'Mobile number must be exactly 10 digits (e.g., 917 555 0123).'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg, 'field': 'mobile_number'})
            messages.error(request, error_msg)
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'focus_field': 'mobile_number',
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

        # Jurisdiction-based role and location restrictions
        requester_profile = getattr(request.user, 'profile', None)
        requested_role = request.POST.get('role', 'traffic_officer')
        if requester_profile and requester_profile.role == 'provincial_chief':
            if requested_role not in ['station_commander', 'traffic_officer', 'data_encoder']:
                error_msg = 'You can only create Station Commander, Traffic Officer, or Data Encoder accounts.'
                if is_ajax:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('admin_panel:user_create')
        elif requester_profile and requester_profile.role == 'station_commander':
            if requested_role not in ['traffic_officer', 'data_encoder']:
                error_msg = 'You can only create Traffic Officer or Data Encoder accounts.'
                if is_ajax:
                    return JsonResponse({'success': False, 'error': error_msg})
                messages.error(request, error_msg)
                return redirect('admin_panel:user_create')

        # Create user and profile in a transaction to ensure both succeed or both fail
        from django.db import transaction
        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )

                # Enforce location based on requester's jurisdiction
                if requester_profile and requester_profile.role == 'station_commander':
                    create_province = requester_profile.province or ''
                    create_station = requester_profile.station or ''
                elif requester_profile and requester_profile.role == 'provincial_chief':
                    create_province = requester_profile.province or ''
                    create_station = request.POST.get('station', '')
                else:
                    create_province = request.POST.get('province', '')
                    create_station = request.POST.get('station', '')

                # Determine office field for command-level roles
                create_office = ''
                if requested_role == 'provincial_chief':
                    create_office = request.POST.get('office', '')
                    create_station = ''  # Provincial Chief has no station
                elif requested_role == 'regional_director':
                    create_office = request.POST.get('office_pro', '') or request.POST.get('office', '') or 'Police Regional Office CARAGA'
                    create_station = ''  # Regional Director has no station

                # Create profile
                profile = UserProfile.objects.create(
                    user=user,
                    badge_number=badge_number,
                    rank=request.POST.get('rank', 'pcpl'),
                    role=requested_role,
                    region=request.POST.get('region', 'Caraga'),
                    province=create_province,
                    station=create_station,
                    office=create_office,
                    unit=request.POST.get('unit', ''),
                    mobile_number=mobile_number,
                    phone_number=request.POST.get('phone_number', ''),
                    must_change_password='must_change_password' in request.POST,
                    can_submit_reports='can_submit_reports' in request.POST,
                    can_run_clustering='can_run_clustering' in request.POST and requester and requester.role in ('super_admin', 'regional_director'),
                    can_edit_reports='can_edit_reports' in request.POST and requester and requester.role in ('super_admin', 'regional_director'),
                    created_by=request.user
                )

                # Handle profile picture upload
                if 'profile_picture' in request.FILES:
                    try:
                        import os
                        from django.conf import settings

                        # Ensure media directories exist
                        media_root = settings.MEDIA_ROOT
                        profile_pics_dir = os.path.join(media_root, 'profile_pictures')
                        os.makedirs(profile_pics_dir, exist_ok=True)

                        uploaded_file = request.FILES['profile_picture']
                        profile.profile_picture = uploaded_file
                        profile.save()

                        print(f"DEBUG: Profile picture saved successfully to {profile.profile_picture.path}")

                        log_user_action(
                            request=request,
                            action='profile_picture_upload',
                            description=f'Uploaded profile picture for new user: {username} (Size: {uploaded_file.size} bytes)',
                            severity='info'
                        )
                    except Exception as e:
                        # Log the error but don't fail user creation
                        print(f"DEBUG: Profile picture upload failed - {str(e)}")
                        log_user_action(
                            request=request,
                            action='profile_picture_upload',
                            description=f'Failed to upload profile picture for user {username}: {str(e)}',
                            severity='warning',
                            success=False
                        )
                        messages.warning(request, f'User created but profile picture upload failed: {str(e)}')

                # Automatically set permissions based on role
                if profile.role == 'super_admin':
                    user.is_staff = True
                    user.is_superuser = True
                elif profile.role == 'regional_director':
                    user.is_staff = True
                    user.is_superuser = False
                else:
                    user.is_staff = False
                    user.is_superuser = False
                user.save()

                log_user_action(
                    request=request,
                    action='user_create',
                    description=f'Created new user: {username} with role {profile.get_role_display()}',
                    severity='info'
                )

                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': f'User "{username}" created successfully!',
                        'user_id': user.id,
                        'redirect_url': f'/admin-panel/users/{user.id}/'
                    })

                messages.success(request, f'User "{username}" created successfully!')
                return redirect('admin_panel:user_detail', user_id=user.id)

        except Exception as e:
            # Catch any other errors and show a user-friendly message
            error_msg = f'Error creating user: {str(e)}'
            if is_ajax:
                return JsonResponse({'success': False, 'error': error_msg})
            messages.error(request, error_msg)
            print(f"DEBUG: User creation failed - {str(e)}")
            context = {
                'ranks': UserProfile.RANK_CHOICES,
                'roles': UserProfile.ROLE_CHOICES,
                'form_data': request.POST,
                'base_template': base_template,
            }
            return render(request, 'admin_panel/user_create.html', context)

    context = {
        'ranks': UserProfile.RANK_CHOICES,
        'roles': UserProfile.ROLE_CHOICES,
        'base_template': base_template,
    }

    return render(request, 'admin_panel/user_create.html', context)


@login_required
@user_passes_test(can_manage_users)
def user_reset_password(request, user_id):
    """Reset user password"""

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        # Jurisdiction checks for password reset
        requester = getattr(request.user, 'profile', None)
        if requester and requester.role == 'provincial_chief':
            target_profile = getattr(user, 'profile', None)
            if not target_profile or target_profile.role not in ['station_commander', 'traffic_officer', 'data_encoder'] or target_profile.province != requester.province:
                return JsonResponse({'success': False, 'error': 'You can only reset passwords for personnel in your province.'})
        elif requester and requester.role == 'station_commander':
            target_profile = getattr(user, 'profile', None)
            if not target_profile or target_profile.role not in ['traffic_officer', 'data_encoder'] or target_profile.station != requester.station:
                return JsonResponse({'success': False, 'error': 'You can only reset passwords for personnel at your station.'})

        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
            new_password = data.get('new_password')
            must_change_password = data.get('must_change_password', True)
        else:
            new_password = request.POST.get('new_password')
            must_change_password = request.POST.get('must_change_password', 'on') == 'on'

        # Validate password
        if not new_password:
            return JsonResponse({'success': False, 'error': 'Password is required'})

        if len(new_password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long'})

        # Set new password
        user.set_password(new_password)
        user.save()

        # Update profile with must_change_password setting from checkbox
        if hasattr(user, 'profile'):
            user.profile.must_change_password = must_change_password
            user.profile.save()

        status_msg = 'User will be required to change password on next login.' if must_change_password else 'Password reset successfully. User can log in with new password immediately.'
        messages.success(request, f'Password for {user.username} reset successfully! {status_msg}')

        log_user_action(
            request=request,
            action='password_reset',
            description=f'Reset password for user: {user.username}',
            severity='warning'
        )

        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


@login_required
@user_passes_test(can_manage_users)
def user_toggle_active(request, user_id):
    """Activate or deactivate user"""

    if request.method == 'POST':
        user = get_object_or_404(User, pk=user_id)

        # Jurisdiction checks for toggling active status
        requester = getattr(request.user, 'profile', None)
        if requester and requester.role == 'provincial_chief':
            target_profile = getattr(user, 'profile', None)
            if not target_profile or target_profile.role not in ['station_commander', 'traffic_officer', 'data_encoder'] or target_profile.province != requester.province:
                return JsonResponse({'success': False, 'error': 'You can only manage personnel in your province.'})
        elif requester and requester.role == 'station_commander':
            target_profile = getattr(user, 'profile', None)
            if not target_profile or target_profile.role not in ['traffic_officer', 'data_encoder'] or target_profile.station != requester.station:
                return JsonResponse({'success': False, 'error': 'You can only manage personnel at your station.'})

        # Don't allow deactivating yourself
        if user == request.user:
            return JsonResponse({'success': False, 'error': 'You cannot deactivate your own account!'})

        # Toggle active status
        user.is_active = not user.is_active
        user.save()

        status = 'activated' if user.is_active else 'deactivated'
        # Note: Don't use messages.success() here since this is AJAX
        # The frontend JavaScript handles the notification display

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
    status_filter = request.GET.get('status', '')  # success or failed

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

    if status_filter == 'success':
        logs = logs.filter(success=True)
    elif status_filter == 'failed':
        logs = logs.filter(success=False)

    if date_from:
        logs = logs.filter(timestamp__gte=date_from)

    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    # Order by timestamp (newest first)
    logs = logs.order_by('-timestamp')

    # Pagination (system default from settings)
    sys_default = SystemSetting.get('default_per_page')
    per_page_param = request.GET.get('per_page', sys_default)
    try:
        per_page = int(per_page_param)
        if per_page not in (5, 10, 15, 25, 50):
            per_page = int(sys_default)
    except (ValueError, TypeError):
        per_page = 15

    paginator = Paginator(logs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get action choices from model
    action_choices = AuditLog.ACTION_CHOICES
    severities = [choice[0] for choice in AuditLog.SEVERITY_CHOICES]

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'action_filter': action_filter,
        'severity_filter': severity_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_filter': status_filter,
        'action_choices': action_choices,
        'severities': severities,
        'total_count': logs.count(),
        'per_page': per_page,
    }

    return render(request, 'admin_panel/audit_logs.html', context)


# ============================================================================
# REPORT ACTIVITY LOGS
# ============================================================================

@login_required
@user_passes_test(is_staff_or_superuser)
def report_activity_logs(request):
    """View all report activity logs with search and filters"""

    # Filters
    search_query = request.GET.get('search', '')
    action_filter = request.GET.get('action', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    logs = ReportActivityLog.objects.select_related('report', 'actor__profile').all()

    if search_query:
        logs = logs.filter(
            Q(actor_name__icontains=search_query) |
            Q(details__icontains=search_query) |
            Q(report__reporter_name__icontains=search_query) |
            Q(report__municipal__icontains=search_query) |
            Q(report__barangay__icontains=search_query)
        )

    if action_filter:
        logs = logs.filter(action=action_filter)

    if date_from:
        logs = logs.filter(timestamp__gte=date_from)

    if date_to:
        logs = logs.filter(timestamp__lte=date_to)

    logs = logs.order_by('-timestamp')

    # Pagination (system default from settings)
    sys_default = SystemSetting.get('default_per_page')
    per_page = request.GET.get('per_page', sys_default)
    try:
        per_page = int(per_page)
        if per_page not in (5, 10, 15, 25, 50):
            per_page = int(sys_default)
    except (ValueError, TypeError):
        per_page = 15
    paginator = Paginator(logs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'action_filter': action_filter,
        'date_from': date_from,
        'date_to': date_to,
        'action_choices': ReportActivityLog.ACTION_CHOICES,
        'total_count': logs.count(),
        'per_page': per_page,
    }

    return render(request, 'admin_panel/report_activity_logs.html', context)


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

    # Recent clustering jobs (all, client-side pagination)
    recent_jobs = ClusteringJob.objects.order_by('-started_at')

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
# MAINTENANCE TOOLS
# ============================================================================

@login_required
@user_passes_test(is_super_admin)
def clear_cache(request):
    """Clear the Django cache"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        cache.clear()

        # Also clear the file-based cache directory if it exists
        cache_dir = settings.BASE_DIR / 'cache'
        cleared_files = 0
        if cache_dir.exists():
            for f in cache_dir.iterdir():
                if f.is_file():
                    f.unlink()
                    cleared_files += 1

        log_user_action(
            request=request,
            action='system_config',
            description=f'Cleared system cache ({cleared_files} cache files removed)',
            severity='info'
        )

        return JsonResponse({
            'success': True,
            'message': f'Cache cleared successfully. {cleared_files} cache file{"s" if cleared_files != 1 else ""} removed.'
        })

    except Exception as e:
        log_user_action(
            request=request,
            action='system_config',
            description=f'Failed to clear cache: {str(e)}',
            severity='critical',
            success=False
        )
        return JsonResponse({
            'success': False,
            'error': f'Failed to clear cache: {str(e)}'
        }, status=500)


@login_required
@user_passes_test(is_super_admin)
def database_backup(request):
    """Create and download a PostgreSQL database backup"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

    try:
        db_settings = settings.DATABASES['default']
        db_engine = db_settings.get('ENGINE', '')

        if 'postgresql' not in db_engine:
            return JsonResponse({
                'success': False,
                'error': 'Database backup is only supported for PostgreSQL databases.'
            }, status=400)

        db_name = db_settings.get('NAME', '')
        db_user = db_settings.get('USER', '')
        db_password = db_settings.get('PASSWORD', '')
        db_host = db_settings.get('HOST', 'localhost')
        db_port = db_settings.get('PORT', '5432')

        # Find pg_dump executable
        import shutil
        pg_dump_path = shutil.which('pg_dump')
        if not pg_dump_path:
            # Search common PostgreSQL installation paths on Windows
            import glob
            pg_paths = glob.glob(r'C:/Program Files/PostgreSQL/*/bin/pg_dump.exe')
            if pg_paths:
                pg_dump_path = pg_paths[-1]  # Use the latest version
            else:
                raise FileNotFoundError('pg_dump not found')

        # Build pg_dump command
        cmd = [
            pg_dump_path,
            '--host', db_host,
            '--port', str(db_port),
            '--username', db_user,
            '--no-password',
            '--format', 'custom',
            '--compress', '6',
            db_name,
        ]

        # Set PGPASSWORD environment variable for authentication
        env = os.environ.copy()
        env['PGPASSWORD'] = db_password

        # Run pg_dump
        result = subprocess.run(
            cmd,
            capture_output=True,
            env=env,
            timeout=300,  # 5-minute timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr.decode('utf-8', errors='replace').strip()
            log_user_action(
                request=request,
                action='system_config',
                description=f'Database backup failed: {error_msg[:200]}',
                severity='critical',
                success=False
            )
            return JsonResponse({
                'success': False,
                'error': f'pg_dump failed: {error_msg[:200]}'
            }, status=500)

        # Generate filename with timestamp
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{db_name}_backup_{timestamp}.dump'

        log_user_action(
            request=request,
            action='system_config',
            description=f'Created database backup: {filename} ({len(result.stdout)} bytes)',
            severity='info'
        )

        # Stream the backup file as a download
        response = HttpResponse(result.stdout, content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(result.stdout)
        return response

    except subprocess.TimeoutExpired:
        log_user_action(
            request=request,
            action='system_config',
            description='Database backup timed out after 5 minutes',
            severity='critical',
            success=False
        )
        return JsonResponse({
            'success': False,
            'error': 'Database backup timed out. The database may be too large.'
        }, status=500)

    except FileNotFoundError:
        log_user_action(
            request=request,
            action='system_config',
            description='pg_dump not found on system PATH',
            severity='critical',
            success=False
        )
        return JsonResponse({
            'success': False,
            'error': 'pg_dump is not installed or not found in system PATH. Please ensure PostgreSQL client tools are installed.'
        }, status=500)

    except Exception as e:
        log_user_action(
            request=request,
            action='system_config',
            description=f'Database backup failed: {str(e)}',
            severity='critical',
            success=False
        )
        return JsonResponse({
            'success': False,
            'error': f'Backup failed: {str(e)}'
        }, status=500)


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


# ============================================================================
# SYSTEM SETTINGS (Display Preferences)
# ============================================================================

@login_required
@user_passes_test(is_admin)
def system_settings(request):
    """Manage system-wide display settings."""

    # Settings definitions: key → (label, description, choices)
    SETTING_DEFS = {
        'accident_default_view': {
            'label': 'Accident Page Default View',
            'description': 'Default display view when users open the Accidents page.',
            'choices': [('cards', 'Cards View'), ('table', 'Table View')],
            'icon': 'fas fa-car-crash',
        },
        'hotspot_default_view': {
            'label': 'Hotspot Page Default View',
            'description': 'Default display view when users open the Hotspots page.',
            'choices': [('grid', 'Grid View'), ('list', 'List View')],
            'icon': 'fas fa-fire',
        },
        'session_timeout': {
            'label': 'Session Timeout Duration',
            'description': 'How long an inactive user stays logged in before being automatically signed out.',
            'choices': [
                ('15', '15 Minutes'),
                ('30', '30 Minutes'),
                ('60', '1 Hour'),
                ('120', '2 Hours'),
                ('480', '8 Hours'),
            ],
            'icon': 'fas fa-clock',
        },
        'default_per_page': {
            'label': 'Default Items Per Page',
            'description': 'Default number of items shown per page across all list views (users, logs, reports, etc.).',
            'choices': [
                ('10', '10 Items'),
                ('15', '15 Items'),
                ('20', '20 Items'),
                ('50', '50 Items'),
            ],
            'icon': 'fas fa-list-ol',
        },
        'blotter_starting_number': {
            'label': 'Blotter Starting Number',
            'description': 'Starting blotter entry number for approved reports. The system will auto-increment from this value.',
            'input_type': 'number',
            'icon': 'fas fa-hashtag',
        },
    }

    if request.method == 'POST':
        changed_labels = []
        changed_keys = []
        for key, definition in SETTING_DEFS.items():
            new_value = request.POST.get(key, '').strip()

            # Validate based on input type
            if definition.get('input_type') == 'number':
                # Number input: must be a positive integer
                if not new_value or not new_value.isdigit() or int(new_value) < 1:
                    continue
            else:
                # Choice-based: must be in valid choices
                valid_values = [c[0] for c in definition.get('choices', [])]
                if new_value not in valid_values:
                    continue

            obj, created = SystemSetting.objects.update_or_create(
                key=key,
                defaults={
                    'value': new_value,
                    'description': definition['description'],
                    'updated_by': request.user,
                }
            )
            changed_labels.append(definition['label'])
            changed_keys.append(key)

        if changed_labels:
            # Clear the admin's own display preferences so system defaults apply
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                update_fields = []
                if 'accident_default_view' in changed_keys:
                    profile.pref_accident_view = ''
                    update_fields.append('pref_accident_view')
                if 'hotspot_default_view' in changed_keys:
                    profile.pref_hotspot_view = ''
                    update_fields.append('pref_hotspot_view')
                if update_fields:
                    profile.save(update_fields=update_fields)

            log_user_action(request, 'system_settings_update',
                f'Updated settings: {", ".join(changed_labels)}',
                object_type='SystemSetting')
            messages.success(request, f'Settings updated successfully.')
        return redirect('admin_panel:system_settings')

    # Build context with current values
    settings_list = []
    for key, definition in SETTING_DEFS.items():
        current_value = SystemSetting.get(key)
        entry = {
            'key': key,
            'label': definition['label'],
            'description': definition['description'],
            'choices': definition.get('choices', []),
            'current': current_value,
            'icon': definition['icon'],
            'input_type': definition.get('input_type', 'radio'),
        }
        # For blotter, show the next auto-assigned number
        if key == 'blotter_starting_number':
            entry['next_blotter'] = SystemSetting.next_blotter_number()
        settings_list.append(entry)

    return render(request, 'admin_panel/system_settings.html', {
        'settings_list': settings_list,
        'page_title': 'Display Settings',
    })


# ==============================================================================
# DROPDOWN OPTIONS MANAGEMENT
# ==============================================================================

@login_required
def dropdown_management(request):
    """Manage dropdown options for the report submission form."""
    profile = getattr(request.user, 'profile', None)
    if not (profile and (profile.role in ('super_admin', 'regional_director') or profile.can_edit_reports)):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    # Determine base template based on role
    uses_main_layout = profile.role in ('station_commander', 'provincial_chief')
    base_template = 'base.html' if uses_main_layout else 'admin_panel/base.html'

    # Seed defaults if table is empty
    if not DropdownOption.objects.exists():
        DropdownOption.seed_defaults()

    # Group options by field (exclude vehicle_make/model — shown under Vehicle Type)
    field_groups = []
    for value, label in DropdownOption.FIELD_CHOICES:
        if value in ('vehicle_make', 'vehicle_model'):
            continue
        options = DropdownOption.objects.filter(field_name=value).order_by('sort_order', 'label')
        field_groups.append({
            'field_name': value,
            'label': label,
            'options': options,
            'active_count': options.filter(is_active=True).count(),
            'total_count': options.count(),
        })

    # Build vehicle hierarchy as nested list for easy template iteration
    vehicle_kinds_qs = DropdownOption.objects.filter(
        field_name='vehicle_kind', is_active=True
    ).order_by('sort_order', 'label')

    vehicle_type_data = []
    for kind_opt in vehicle_kinds_qs:
        makes_qs = DropdownOption.objects.filter(
            field_name='vehicle_make', parent_value=kind_opt.value
        ).order_by('sort_order', 'label')
        makes_list = []
        for make_opt in makes_qs:
            parent_key = f'{kind_opt.value}__{make_opt.value}'
            models_qs = DropdownOption.objects.filter(
                field_name='vehicle_model', parent_value=parent_key
            ).order_by('sort_order', 'label')
            makes_list.append({
                'option': make_opt,
                'models': models_qs,
                'parent_key': parent_key,
                'kind_val': kind_opt.value,
            })
        vehicle_type_data.append({
            'kind_val': kind_opt.value,
            'kind_label': kind_opt.label,
            'makes': makes_list,
            'make_count': makes_qs.count(),
        })

    vehicle_make_count = DropdownOption.objects.filter(field_name='vehicle_make').count()
    vehicle_model_count = DropdownOption.objects.filter(field_name='vehicle_model').count()

    return render(request, 'admin_panel/dropdown_management.html', {
        'field_groups': field_groups,
        'page_title': 'Form Dropdown Options',
        'base_template': base_template,
        'vehicle_type_data': vehicle_type_data,
        'vehicle_make_count': vehicle_make_count,
        'vehicle_model_count': vehicle_model_count,
    })


@login_required
def dropdown_api(request):
    """API endpoint for CRUD operations on dropdown options."""
    profile = getattr(request.user, 'profile', None)
    if not (profile and (profile.role in ('super_admin', 'regional_director') or profile.can_edit_reports)):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            if action == 'add':
                field_name = data.get('field_name')
                value = data.get('value', '').strip().upper().replace(' ', '_')
                label = data.get('label', '').strip()
                parent_value = data.get('parent_value', '').strip()

                if not field_name or not value or not label:
                    return JsonResponse({'success': False, 'error': 'Field name, value, and label are required'})

                if DropdownOption.objects.filter(field_name=field_name, value=value, parent_value=parent_value).exists():
                    return JsonResponse({'success': False, 'error': 'An option with this value already exists'})

                max_order = DropdownOption.objects.filter(field_name=field_name, parent_value=parent_value).order_by('-sort_order').values_list('sort_order', flat=True).first() or 0
                opt = DropdownOption.objects.create(
                    field_name=field_name,
                    value=value,
                    label=label,
                    parent_value=parent_value,
                    sort_order=max_order + 10,
                    is_default=False,
                    is_active=True,
                    created_by=request.user,
                )

                log_user_action(request=request, action='dropdown_add',
                    description=f'Added dropdown option: {label} ({value}) to {field_name}', severity='info')

                return JsonResponse({'success': True, 'id': opt.id, 'message': f'Option "{label}" added successfully'})

            elif action == 'edit':
                opt_id = data.get('id')
                label = data.get('label', '').strip()
                if not opt_id or not label:
                    return JsonResponse({'success': False, 'error': 'ID and label are required'})

                opt = DropdownOption.objects.get(id=opt_id)
                old_label = opt.label
                opt.label = label
                opt.save(update_fields=['label'])

                log_user_action(request=request, action='dropdown_edit',
                    description=f'Edited dropdown option: "{old_label}" → "{label}" ({opt.field_name})', severity='info')

                return JsonResponse({'success': True, 'message': f'Option updated to "{label}"'})

            elif action == 'toggle':
                opt_id = data.get('id')
                opt = DropdownOption.objects.get(id=opt_id)
                opt.is_active = not opt.is_active
                opt.save(update_fields=['is_active'])

                status = 'enabled' if opt.is_active else 'disabled'
                log_user_action(request=request, action='dropdown_toggle',
                    description=f'{status.capitalize()} dropdown option: {opt.label} ({opt.field_name})', severity='info')

                return JsonResponse({'success': True, 'is_active': opt.is_active, 'message': f'Option {status}'})

            elif action == 'delete':
                opt_id = data.get('id')
                opt = DropdownOption.objects.get(id=opt_id)
                if opt.is_default:
                    return JsonResponse({'success': False, 'error': 'Cannot delete default system options. Disable it instead.'})
                label = opt.label
                field = opt.field_name
                opt.delete()

                log_user_action(request=request, action='dropdown_delete',
                    description=f'Deleted dropdown option: {label} ({field})', severity='warning')

                return JsonResponse({'success': True, 'message': f'Option "{label}" deleted'})

            elif action == 'reorder':
                items = data.get('items', [])
                for item in items:
                    DropdownOption.objects.filter(id=item['id']).update(sort_order=item['order'])
                return JsonResponse({'success': True, 'message': 'Order updated'})

            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'})

        except DropdownOption.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Option not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
