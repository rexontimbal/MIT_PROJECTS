# accidents/backends.py
"""
Custom authentication backend for PNP AGNES system
Allows login with either username or badge number
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from .models import UserProfile


class UsernameOrBadgeBackend(ModelBackend):
    """
    Custom authentication backend that accepts either username or badge number

    This allows PNP officers to log in using their badge number instead of username,
    making the system more user-friendly for law enforcement personnel.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate user by username or badge number

        Args:
            request: HTTP request object
            username: Can be either the Django username or the PNP badge number
            password: User's password

        Returns:
            User object if authentication successful, None otherwise
        """
        if username is None or password is None:
            return None

        user = None

        # First, try to authenticate with username (standard Django behavior)
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # Username not found, try badge number
            try:
                profile = UserProfile.objects.select_related('user').get(badge_number=username)
                user = profile.user
            except UserProfile.DoesNotExist:
                # Neither username nor badge number found
                # Run the default password hasher once to reduce timing attacks
                User().set_password(password)
                return None

        # Check if password is correct
        if user and user.check_password(password):
            return user

        return None

    def get_user(self, user_id):
        """
        Get user by primary key (required by Django authentication)
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
