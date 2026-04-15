"""
Custom middleware for the AGNES accident hotspot detection system.
"""
import time
from django.conf import settings


class SessionTimeoutMiddleware:
    """
    Enforces a configurable session timeout based on the SystemSetting
    'session_timeout' value (in minutes).

    On each request the middleware checks the timestamp of the user's last
    activity.  If the gap exceeds the configured timeout the session is
    flushed and the user is effectively logged out — Django's
    AuthenticationMiddleware will then treat them as anonymous.

    The timeout value is read from the database via SystemSetting.get()
    and cached on the session itself so we only hit the DB once per
    session (refreshed whenever the admin changes the setting).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only apply to authenticated users with an active session
        if request.user.is_authenticated and hasattr(request, 'session'):
            now = time.time()
            last_activity = request.session.get('_last_activity')

            if last_activity is not None:
                timeout_minutes = self._get_timeout(request)
                elapsed = now - last_activity

                if elapsed > timeout_minutes * 60:
                    # Session expired — flush it
                    request.session.flush()
                    # Let the rest of the pipeline handle the anonymous user
                    # (they'll be redirected to login by @login_required)
                    return self.get_response(request)

            # Stamp current time
            request.session['_last_activity'] = now

        return self.get_response(request)

    @staticmethod
    def _get_timeout(request):
        """
        Return the session timeout in minutes.  Uses a session-cached
        value to avoid hitting the DB on every single request.
        """
        cached = request.session.get('_timeout_minutes')
        cached_at = request.session.get('_timeout_cached_at', 0)

        # Re-fetch from DB at most once every 5 minutes
        if cached is not None and (time.time() - cached_at) < 300:
            return cached

        try:
            from .models import SystemSetting
            val = SystemSetting.get('session_timeout')
            minutes = int(val)
        except (ValueError, TypeError):
            minutes = 60  # fallback: 1 hour

        request.session['_timeout_minutes'] = minutes
        request.session['_timeout_cached_at'] = time.time()
        return minutes
