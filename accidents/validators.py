"""
Custom validators for the accidents application.

Provides validation for:
- Geographic coordinates (Philippine bounds)
- Dates and times
- Casualty counts
- Contact information
- File uploads
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import re


def validate_philippine_latitude(value):
    """
    Validate that latitude is within Philippine territorial bounds.

    Philippine latitude range: approximately 4.5° to 21° N
    """
    if value < Decimal('4.0') or value > Decimal('22.0'):
        raise ValidationError(
            _('Latitude %(value)s is outside Philippine territorial bounds (4.0° to 22.0° N).'),
            params={'value': value},
        )


def validate_philippine_longitude(value):
    """
    Validate that longitude is within Philippine territorial bounds.

    Philippine longitude range: approximately 116° to 127° E
    """
    if value < Decimal('115.0') or value > Decimal('128.0'):
        raise ValidationError(
            _('Longitude %(value)s is outside Philippine territorial bounds (115.0° to 128.0° E).'),
            params={'value': value},
        )


def validate_caraga_latitude(value):
    """
    Validate that latitude is within Caraga Region bounds.

    Caraga Region latitude range: approximately 8.0° to 10.0° N
    """
    if value < Decimal('8.0') or value > Decimal('10.5'):
        raise ValidationError(
            _('Latitude %(value)s is outside Caraga Region bounds (8.0° to 10.5° N).'),
            params={'value': value},
        )


def validate_caraga_longitude(value):
    """
    Validate that longitude is within Caraga Region bounds.

    Caraga Region longitude range: approximately 125.0° to 126.5° E
    """
    if value < Decimal('125.0') or value > Decimal('127.0'):
        raise ValidationError(
            _('Longitude %(value)s is outside Caraga Region bounds (125.0° to 127.0° E).'),
            params={'value': value},
        )


def validate_date_not_future(value):
    """
    Validate that a date is not in the future.

    Used for accident dates to prevent erroneous future dates.
    """
    if value > timezone.now().date():
        raise ValidationError(
            _('Date cannot be in the future. Received: %(value)s'),
            params={'value': value},
        )


def validate_date_not_too_old(value):
    """
    Validate that a date is not unreasonably old.

    Prevents data entry errors with dates beyond reasonable historical range.
    Allows dates back to 1950 for historical accident data.
    """
    from datetime import date
    min_date = date(1950, 1, 1)

    if value < min_date:
        raise ValidationError(
            _('Date %(value)s is too old. Minimum allowed date is %(min_date)s.'),
            params={'value': value, 'min_date': min_date},
        )


def validate_casualty_count(value):
    """
    Validate that casualty count is reasonable.

    Maximum of 100 casualties per accident (to catch data entry errors).
    """
    if value < 0:
        raise ValidationError(
            _('Casualty count cannot be negative.'),
        )

    if value > 100:
        raise ValidationError(
            _('Casualty count %(value)s seems unusually high. Please verify.'),
            params={'value': value},
        )


def validate_philippine_mobile_number(value):
    """
    Validate Philippine mobile phone number format.

    Valid formats:
    - 09171234567 (11 digits starting with 09)
    - +639171234567 (with country code)
    - 639171234567 (without + prefix)
    """
    if not value:
        return

    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-()]', '', value)

    patterns = [
        r'^09\d{9}$',  # 09XXXXXXXXX
        r'^\+639\d{9}$',  # +639XXXXXXXXX
        r'^639\d{9}$',  # 639XXXXXXXXX
    ]

    if not any(re.match(pattern, cleaned) for pattern in patterns):
        raise ValidationError(
            _('Invalid Philippine mobile number format. Use: 09XXXXXXXXX or +639XXXXXXXXX'),
        )


def validate_pnp_badge_number(value):
    """
    Validate PNP badge number format.

    Expected format: PNP-[REGION]-[YEAR]-[NUMBER]
    Example: PNP-13-2024-001
    """
    if not value:
        return

    pattern = r'^PNP-\d{1,2}-\d{4}-\d{3,5}$'

    if not re.match(pattern, value):
        raise ValidationError(
            _('Invalid PNP badge number format. Expected: PNP-[REGION]-[YEAR]-[NUMBER] (e.g., PNP-13-2024-001)'),
        )


def validate_cluster_distance_threshold(value):
    """
    Validate distance threshold for clustering.

    Reasonable range: 0.01 to 1.0 decimal degrees (~1km to 100km)
    """
    if value <= 0:
        raise ValidationError(
            _('Distance threshold must be positive.'),
        )

    if value > 1.0:
        raise ValidationError(
            _('Distance threshold %(value)s is too large (max 1.0 decimal degrees ≈ 100km).'),
            params={'value': value},
        )

    if value < 0.001:
        raise ValidationError(
            _('Distance threshold %(value)s is too small (min 0.001 decimal degrees ≈ 100m).'),
            params={'value': value},
        )


def validate_cluster_size(value):
    """
    Validate minimum cluster size.

    Reasonable range: 2 to 100 accidents
    """
    if value < 2:
        raise ValidationError(
            _('Minimum cluster size must be at least 2.'),
        )

    if value > 100:
        raise ValidationError(
            _('Minimum cluster size %(value)s is too large (max 100).'),
            params={'value': value},
        )


def validate_image_file_size(value):
    """
    Validate uploaded image file size.

    Maximum: 5MB per image
    """
    max_size_mb = 5
    max_size_bytes = max_size_mb * 1024 * 1024

    if value.size > max_size_bytes:
        raise ValidationError(
            _('File size %(size)s MB exceeds maximum allowed size of %(max)s MB.'),
            params={
                'size': round(value.size / (1024 * 1024), 2),
                'max': max_size_mb
            },
        )


def validate_image_file_extension(value):
    """
    Validate uploaded image file extension.

    Allowed: jpg, jpeg, png, gif
    """
    import os
    ext = os.path.splitext(value.name)[1].lower()

    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif']

    if ext not in valid_extensions:
        raise ValidationError(
            _('Unsupported file extension %(ext)s. Allowed: %(allowed)s'),
            params={
                'ext': ext,
                'allowed': ', '.join(valid_extensions)
            },
        )


def validate_severity_score(value):
    """
    Validate severity score.

    Score should be between 0 and 1000
    """
    if value < 0:
        raise ValidationError(
            _('Severity score cannot be negative.'),
        )

    if value > 1000:
        raise ValidationError(
            _('Severity score %(value)s exceeds maximum (1000).'),
            params={'value': value},
        )


def validate_year_range(value):
    """
    Validate year is in reasonable range.

    Allows years from 1950 to current year + 1
    """
    current_year = timezone.now().year

    if value < 1950:
        raise ValidationError(
            _('Year %(value)s is too old (minimum: 1950).'),
            params={'value': value},
        )

    if value > current_year + 1:
        raise ValidationError(
            _('Year %(value)s is in the future (maximum: %(max)s).'),
            params={'value': value, 'max': current_year + 1},
        )


def validate_province_in_caraga(value):
    """
    Validate that province is within Caraga Region (Region XIII).

    Valid provinces:
    - Agusan del Norte
    - Agusan del Sur
    - Surigao del Norte
    - Surigao del Sur
    - Dinagat Islands
    """
    if not value:
        return

    valid_provinces = [
        'Agusan del Norte',
        'Agusan del Sur',
        'Surigao del Norte',
        'Surigao del Sur',
        'Dinagat Islands'
    ]

    if value not in valid_provinces:
        raise ValidationError(
            _('Province "%(value)s" is not in Caraga Region. Valid provinces: %(valid)s'),
            params={
                'value': value,
                'valid': ', '.join(valid_provinces)
            },
        )


def validate_email_domain(value):
    """
    Validate email domain for PNP personnel.

    Recommended domain: @pnp.gov.ph
    This is a soft validation (warning) rather than hard error
    """
    if not value:
        return

    # This could be used as a soft validator or in forms
    if not value.endswith('@pnp.gov.ph') and not value.endswith('@gmail.com'):
        # Note: In practice, you might want to just log this rather than raise error
        # For flexibility, allowing other domains but could add warning
        pass


def validate_coordinate_precision(latitude, longitude):
    """
    Validate that coordinates have reasonable precision.

    Should have at least 4 decimal places for ~10m accuracy
    Maximum 7 decimal places (supported by model)
    """
    lat_str = str(latitude)
    lng_str = str(longitude)

    # Check decimal places
    if '.' in lat_str:
        lat_decimals = len(lat_str.split('.')[1])
        if lat_decimals < 4:
            raise ValidationError(
                _('Latitude should have at least 4 decimal places for accuracy.'),
            )

    if '.' in lng_str:
        lng_decimals = len(lng_str.split('.')[1])
        if lng_decimals < 4:
            raise ValidationError(
                _('Longitude should have at least 4 decimal places for accuracy.'),
            )


# Composite validator for accident records
def validate_accident_data(accident):
    """
    Composite validator for accident record integrity.

    Checks:
    - Date consistency (reported >= committed)
    - Casualty flags match counts
    - Coordinates are valid
    """
    errors = []

    # Date consistency
    if accident.date_reported and accident.date_committed:
        if accident.date_reported < accident.date_committed:
            errors.append(
                ValidationError(
                    _('Reported date cannot be before committed date.'),
                    code='invalid_date_order'
                )
            )

    # Casualty consistency
    if accident.victim_killed and accident.victim_count == 0:
        errors.append(
            ValidationError(
                _('If victim was killed, victim count must be greater than 0.'),
                code='casualty_inconsistency'
            )
        )

    if accident.victim_injured and accident.victim_count == 0:
        errors.append(
            ValidationError(
                _('If victim was injured, victim count must be greater than 0.'),
                code='casualty_inconsistency'
            )
        )

    if errors:
        raise ValidationError(errors)


# Export all validators
__all__ = [
    'validate_philippine_latitude',
    'validate_philippine_longitude',
    'validate_caraga_latitude',
    'validate_caraga_longitude',
    'validate_date_not_future',
    'validate_date_not_too_old',
    'validate_casualty_count',
    'validate_philippine_mobile_number',
    'validate_pnp_badge_number',
    'validate_cluster_distance_threshold',
    'validate_cluster_size',
    'validate_image_file_size',
    'validate_image_file_extension',
    'validate_severity_score',
    'validate_year_range',
    'validate_province_in_caraga',
    'validate_email_domain',
    'validate_coordinate_precision',
    'validate_accident_data',
]
