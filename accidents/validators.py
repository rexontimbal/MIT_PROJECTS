# accidents/validators.py
"""
Custom validators for accident data integrity and compliance with Philippine context.
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import datetime
import re


# ============================================================================
# GEOGRAPHIC VALIDATORS
# ============================================================================

def validate_philippine_latitude(value):
    """Validate that latitude is within Philippine territorial bounds."""
    if value < Decimal('4.0') or value > Decimal('22.0'):
        raise ValidationError(
            _('Latitude %(value)s is outside Philippine territorial bounds (4.0° to 22.0° N).'),
            params={'value': value},
        )


def validate_philippine_longitude(value):
    """Validate that longitude is within Philippine territorial bounds."""
    if value < Decimal('115.0') or value > Decimal('128.0'):
        raise ValidationError(
            _('Longitude %(value)s is outside Philippine territorial bounds (115.0° to 128.0° E).'),
            params={'value': value},
        )


def validate_caraga_latitude(value):
    """Validate that latitude is within CARAGA Region bounds (more strict)."""
    if value < Decimal('8.0') or value > Decimal('10.5'):
        raise ValidationError(
            _('Latitude %(value)s is outside CARAGA Region bounds (8.0° to 10.5° N).'),
            params={'value': value},
        )


def validate_caraga_longitude(value):
    """Validate that longitude is within CARAGA Region bounds (more strict)."""
    if value < Decimal('125.0') or value > Decimal('126.5'):
        raise ValidationError(
            _('Longitude %(value)s is outside CARAGA Region bounds (125.0° to 126.5° E).'),
            params={'value': value},
        )


# ============================================================================
# TEMPORAL VALIDATORS
# ============================================================================

def validate_date_not_future(value):
    """Validate that date is not in the future."""
    today = datetime.date.today()
    if value > today:
        raise ValidationError(
            _('Date cannot be in the future. Provided: %(value)s, Today: %(today)s'),
            params={'value': value, 'today': today},
        )


def validate_year_range(value):
    """Validate that year is within reasonable range (1950 to present)."""
    current_year = datetime.date.today().year
    if value < 1950 or value > current_year:
        raise ValidationError(
            _('Year %(value)s must be between 1950 and %(current_year)s.'),
            params={'value': value, 'current_year': current_year},
        )


def validate_time_format(value):
    """Validate time format (HH:MM or HH:MM:SS)."""
    if value is None:
        return
    # Django TimeField handles this, but adding for completeness
    time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):[0-5][0-9](:[0-5][0-9])?$')
    if isinstance(value, str) and not time_pattern.match(value):
        raise ValidationError(
            _('Invalid time format. Use HH:MM or HH:MM:SS format.'),
        )


# ============================================================================
# CASUALTY & COUNT VALIDATORS
# ============================================================================

def validate_casualty_count(value):
    """Validate casualty count is reasonable."""
    if value < 0:
        raise ValidationError(
            _('Casualty count cannot be negative.'),
        )
    if value > 100:
        raise ValidationError(
            _('Casualty count %(value)s seems unusually high. Please verify.'),
            params={'value': value},
        )


def validate_suspect_count(value):
    """Validate suspect count is reasonable."""
    if value < 0:
        raise ValidationError(
            _('Suspect count cannot be negative.'),
        )
    if value > 50:
        raise ValidationError(
            _('Suspect count %(value)s seems unusually high. Please verify.'),
            params={'value': value},
        )


# ============================================================================
# CLUSTERING VALIDATORS
# ============================================================================

def validate_severity_score(value):
    """Validate severity score is within expected range."""
    if value < 0 or value > 1000:
        raise ValidationError(
            _('Severity score must be between 0 and 1000. Got: %(value)s'),
            params={'value': value},
        )


def validate_cluster_distance_threshold(value):
    """Validate clustering distance threshold."""
    if value <= 0 or value > 1.0:
        raise ValidationError(
            _('Distance threshold must be between 0.001 and 1.0 (decimal degrees). Got: %(value)s'),
            params={'value': value},
        )


def validate_cluster_size(value):
    """Validate minimum cluster size."""
    if value < 2:
        raise ValidationError(
            _('Minimum cluster size must be at least 2.'),
        )
    if value > 100:
        raise ValidationError(
            _('Minimum cluster size %(value)s is too large.'),
            params={'value': value},
        )


# ============================================================================
# CONTACT VALIDATORS (Philippine-specific)
# ============================================================================

def validate_philippine_mobile(value):
    """Validate Philippine mobile number format."""
    if not value:
        return

    # Remove common separators
    cleaned = re.sub(r'[\s\-\(\)]', '', value)

    # Philippine mobile patterns:
    # +639XXXXXXXXX or 09XXXXXXXXX or 9XXXXXXXXX
    patterns = [
        r'^\+639\d{9}$',      # +639171234567
        r'^09\d{9}$',         # 09171234567
        r'^9\d{9}$',          # 9171234567
    ]

    if not any(re.match(pattern, cleaned) for pattern in patterns):
        raise ValidationError(
            _('Invalid Philippine mobile number. Use format: +639XXXXXXXXX, 09XXXXXXXXX, or 9XXXXXXXXX'),
        )


def validate_pnp_badge_number(value):
    """Validate PNP badge/ID number format."""
    if not value:
        raise ValidationError(_('Badge number is required.'))

    # Basic validation: alphanumeric, 5-20 characters
    if not re.match(r'^[A-Z0-9\-]{5,20}$', value.upper()):
        raise ValidationError(
            _('Badge number must be 5-20 alphanumeric characters.'),
        )


# ============================================================================
# FILE VALIDATORS
# ============================================================================

def validate_image_file_size(value):
    """Validate image file size (max 5MB)."""
    if value:
        filesize = value.size
        max_size = 5 * 1024 * 1024  # 5MB in bytes

        if filesize > max_size:
            raise ValidationError(
                _('Image file size cannot exceed 5MB. Current size: %(size).2f MB'),
                params={'size': filesize / (1024 * 1024)},
            )


def validate_image_file_extension(value):
    """Validate image file extension."""
    if value:
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
        ext = value.name.lower()[-4:]

        if not any(ext.endswith(allowed_ext) for allowed_ext in allowed_extensions):
            raise ValidationError(
                _('Only JPG, JPEG, PNG, and GIF files are allowed.'),
            )


# ============================================================================
# DATA INTEGRITY VALIDATORS
# ============================================================================

def validate_plate_number(value):
    """Validate Philippine vehicle plate number format."""
    if not value:
        return

    # Philippine plate formats (simplified):
    # ABC 1234, AB 1234, ABC-1234, etc.
    cleaned = value.upper().replace(' ', '').replace('-', '')

    if len(cleaned) < 4 or len(cleaned) > 8:
        raise ValidationError(
            _('Invalid plate number length. Should be 4-8 characters.'),
        )


def validate_non_empty_string(value):
    """Validate that string is not empty or just whitespace."""
    if value and not value.strip():
        raise ValidationError(
            _('This field cannot be empty or contain only whitespace.'),
        )


def validate_positive_number(value):
    """Validate that number is positive."""
    if value is not None and value < 0:
        raise ValidationError(
            _('Value must be positive or zero.'),
        )


def validate_narrative_length(value):
    """Validate narrative has sufficient detail."""
    if value and len(value.strip()) < 10:
        raise ValidationError(
            _('Narrative must be at least 10 characters long.'),
        )
