# accidents/auth_utils.py
"""
Authentication utilities and decorators for PNP system
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, AuditLog


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_user_action(request, action, description, **kwargs):
    """Log user action to audit trail"""
    user = request.user if request.user.is_authenticated else None
    profile = None

    if user and hasattr(user, 'profile'):
        profile = user.profile

    return AuditLog.log_action(
        user=user,
        action=action,
        description=description,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        station=profile.station if profile else None,
        province=profile.province if profile else None,
        **kwargs
    )


def pnp_login_required(view_func):
    """
    Decorator to require PNP login and check account status
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please login to access this page.')
            return redirect('login')

        # Check if user has profile
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Your account is not properly configured. Please contact administrator.')
            return redirect('login')

        # Reload profile from database to ensure we have the latest data
        profile = request.user.profile
        profile.refresh_from_db()

        # Check if account is active
        if not profile.is_active:
            messages.error(request, 'Your account has been deactivated. Please contact administrator.')
            return redirect('login')

        # Check if account is locked
        if profile.is_account_locked():
            messages.error(request, 'Your account is temporarily locked due to multiple failed login attempts.')
            return redirect('login')

        # Check if must change password
        if profile.must_change_password and request.path != '/change-password/':
            # Clear existing messages to avoid duplicates and show only password change requirement
            from django.contrib.messages import get_messages
            storage = get_messages(request)
            storage.used = True
            messages.warning(request, 'Your password has expired. Please change it before continuing.')
            return redirect('change_password')

        return view_func(request, *args, **kwargs)

    return wrapper


def permission_required(permission):
    """
    Decorator to check if user has specific permission
    Usage: @permission_required('edit')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login to access this page.')
                return redirect('login')

            profile = request.user.profile

            if not profile.has_permission(permission):
                messages.error(request, f'You do not have permission to {permission}.')
                log_user_action(
                    request,
                    'system_config',
                    f'Unauthorized access attempt: {permission}',
                    severity='warning',
                    success=False
                )
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def role_required(*allowed_roles):
    """
    Decorator to check if user has one of the allowed roles
    Usage: @role_required('super_admin', 'regional_director')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, 'Please login to access this page.')
                return redirect('login')

            profile = request.user.profile

            if profile.role not in allowed_roles:
                messages.error(request, 'Access denied. Insufficient privileges.')
                log_user_action(
                    request,
                    'system_config',
                    f'Unauthorized role access attempt. Required: {allowed_roles}, Has: {profile.role}',
                    severity='warning',
                    success=False
                )
                return redirect('dashboard')

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def handle_failed_login(username, ip_address):
    """Handle failed login attempt - increment counter and lock if needed"""
    try:
        user = User.objects.get(username=username)
        profile = user.profile

        profile.failed_login_attempts += 1

        # Lock account after 5 failed attempts for 30 minutes
        if profile.failed_login_attempts >= 5:
            profile.account_locked_until = timezone.now() + timedelta(minutes=30)
            profile.save()

            AuditLog.objects.create(
                user=user,
                username=username,
                action='login_failed',
                action_description=f'Account locked due to {profile.failed_login_attempts} failed attempts',
                severity='warning',
                ip_address=ip_address,
                success=False
            )

            return f'Account locked for 30 minutes due to multiple failed attempts.'
        else:
            profile.save()

            AuditLog.objects.create(
                user=user,
                username=username,
                action='login_failed',
                action_description=f'Failed login attempt ({profile.failed_login_attempts}/5)',
                severity='info',
                ip_address=ip_address,
                success=False
            )

            return f'Invalid credentials. {5 - profile.failed_login_attempts} attempts remaining.'
    except:
        # User doesn't exist
        AuditLog.objects.create(
            username=username,
            action='login_failed',
            action_description='Failed login attempt - username not found',
            severity='info',
            ip_address=ip_address,
            success=False
        )
        return 'Invalid credentials.'


def handle_successful_login(user, request):
    """Handle successful login - reset counters and log"""
    profile = user.profile
    profile.failed_login_attempts = 0
    profile.account_locked_until = None
    profile.last_login = timezone.now()
    profile.save()

    log_user_action(
        request,
        'login',
        f'{profile.get_full_name_with_rank()} logged in successfully',
        severity='info'
    )


def validate_password_strength(password):
    """Validate password meets PNP security requirements"""
    errors = []

    if len(password) < 8:
        errors.append('Password must be at least 8 characters long.')

    if not any(c.isupper() for c in password):
        errors.append('Password must contain at least one uppercase letter.')

    if not any(c.islower() for c in password):
        errors.append('Password must contain at least one lowercase letter.')

    if not any(c.isdigit() for c in password):
        errors.append('Password must contain at least one number.')

    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        errors.append('Password must contain at least one special character.')

    return errors


# Import User model here to avoid circular import
from django.contrib.auth.models import User
