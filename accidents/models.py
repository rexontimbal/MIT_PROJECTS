# accidents/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import (
    validate_philippine_latitude,
    validate_philippine_longitude,
    validate_date_not_future,
    validate_casualty_count,
    validate_suspect_count,
    validate_year_range,
    validate_severity_score,
    validate_cluster_distance_threshold,
    validate_cluster_size,
    validate_image_file_size,
    validate_image_file_extension,
    validate_narrative_length,
)

class Accident(models.Model):
    """Main accident record model"""
    
    # Administrative/Police Info
    pro = models.CharField(max_length=100, verbose_name="PRO", blank=True, null=True)  # INCREASED
    ppo = models.CharField(max_length=200, verbose_name="PPO", blank=True, null=True)  # INCREASED
    station = models.CharField(max_length=200, verbose_name="Station", blank=True, null=True)  # INCREASED
    
    # Location Information
    region = models.CharField(max_length=100, default="CARAGA")
    province = models.CharField(max_length=100)
    municipal = models.CharField(max_length=200)  # INCREASED (some municipalities have long names)
    barangay = models.CharField(max_length=200)  # INCREASED
    street = models.CharField(max_length=500, null=True, blank=True)  # INCREASED
    type_of_place = models.CharField(max_length=200, verbose_name="Type of Place", blank=True, null=True)  # INCREASED
    
    # Coordinates (critical for GIS and AGNES clustering)
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[validate_philippine_latitude],
        help_text="Latitude in decimal degrees (Philippine bounds: 4.0° to 22.0° N)"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[validate_philippine_longitude],
        help_text="Longitude in decimal degrees (Philippine bounds: 115.0° to 128.0° E)"
    )
    
    # Temporal Information
    date_reported = models.DateField(
        null=True,
        blank=True,
        validators=[validate_date_not_future],
        help_text="Date when accident was reported"
    )
    time_reported = models.TimeField(null=True, blank=True, help_text="Time when accident was reported")
    date_committed = models.DateField(
        validators=[validate_date_not_future],
        help_text="Date when accident occurred"
    )
    time_committed = models.TimeField(null=True, blank=True, help_text="Time when accident occurred")
    year = models.IntegerField(
        null=True,
        blank=True,
        validators=[validate_year_range],
        help_text="Year of accident (1950-present)"
    )
    
    # Incident Details
    incident_type = models.CharField(max_length=500, blank=True, null=True)  # INCREASED - incident types can be long
    offense = models.TextField(blank=True, null=True)  # Already TextField - GOOD
    offense_type = models.CharField(max_length=300, blank=True, null=True)  # INCREASED
    stage_of_felony = models.CharField(max_length=100, blank=True, null=True)  # INCREASED
    
    # Casualties
    victim_killed = models.BooleanField(default=False, help_text="At least one victim was killed")
    victim_injured = models.BooleanField(default=False, help_text="At least one victim was injured")
    victim_unharmed = models.BooleanField(default=False, help_text="No victims were harmed")
    victim_count = models.IntegerField(
        default=0,
        validators=[validate_casualty_count, MinValueValidator(0), MaxValueValidator(100)],
        help_text="Total number of victims (0-100)"
    )
    suspect_count = models.IntegerField(
        default=0,
        validators=[validate_suspect_count, MinValueValidator(0), MaxValueValidator(50)],
        help_text="Total number of suspects (0-50)"
    )
    
    # Vehicle Information
    vehicle_kind = models.CharField(max_length=500, null=True, blank=True)  # INCREASED - multiple vehicles
    vehicle_make = models.CharField(max_length=300, null=True, blank=True)  # INCREASED
    vehicle_model = models.CharField(max_length=300, null=True, blank=True)  # INCREASED
    vehicle_plate_no = models.CharField(max_length=100, null=True, blank=True)  # INCREASED
    
    # Detailed Information (stored as text)
    victim_details = models.TextField(null=True, blank=True)  # Already TextField - GOOD
    suspect_details = models.TextField(null=True, blank=True)  # Already TextField - GOOD
    narrative = models.TextField(blank=True, null=True)  # Already TextField - GOOD, ADDED null=True
    
    # Case Status
    case_status = models.CharField(max_length=100, blank=True, null=True)  # INCREASED
    case_solve_type = models.CharField(max_length=200, null=True, blank=True)  # INCREASED
    
    # System Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reported_accidents')  # ADDED blank=True
    
    # Clustering assignment (will be populated by AGNES algorithm)
    cluster_id = models.IntegerField(null=True, blank=True)
    is_hotspot = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'accidents'
        ordering = ['-date_committed', '-time_committed']
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['date_committed']),
            models.Index(fields=['province', 'municipal']),
            models.Index(fields=['cluster_id']),
        ]
    
    def __str__(self):
        return f"{self.incident_type} - {self.municipal}, {self.date_committed}"


class AccidentCluster(models.Model):
    """Stores AGNES clustering results (hotspots)"""
    
    cluster_id = models.IntegerField(unique=True)
    
    # Cluster center (centroid)
    center_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    center_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Cluster statistics
    accident_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of accidents in this cluster"
    )
    total_casualties = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Total casualties across all accidents in cluster"
    )
    severity_score = models.FloatField(
        default=0.0,
        validators=[validate_severity_score],
        help_text="Calculated severity score (0-1000)"
    )
    
    # Geographic bounds
    min_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    max_latitude = models.DecimalField(max_digits=10, decimal_places=7)
    min_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    max_longitude = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Location description
    primary_location = models.CharField(max_length=200)
    municipalities = models.JSONField(default=list)  # List of municipalities in cluster
    
    # Temporal analysis
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    
    # Clustering metadata
    algorithm_version = models.CharField(max_length=50, default="AGNES")
    computed_at = models.DateTimeField(auto_now=True)
    linkage_method = models.CharField(max_length=20, default="complete")
    distance_threshold = models.FloatField(
        validators=[validate_cluster_distance_threshold],
        help_text="Distance threshold in decimal degrees (0.001-1.0)"
    )
    
    class Meta:
        db_table = 'accident_clusters'
        ordering = ['-severity_score', '-accident_count']
    
    def __str__(self):
        return f"Cluster {self.cluster_id} - {self.primary_location} ({self.accident_count} accidents)"


class AccidentReport(models.Model):
    """New accident reports submitted through the system"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('rejected', 'Rejected'),
    ]
    
    # Reporter Information
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reporter_name = models.CharField(max_length=200)
    reporter_contact = models.CharField(max_length=50)
    
    # Incident Basic Info
    incident_date = models.DateField(
        validators=[validate_date_not_future],
        help_text="Date of the accident"
    )
    incident_time = models.TimeField(help_text="Time of the accident")

    # Location
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[validate_philippine_latitude],
        help_text="Latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        validators=[validate_philippine_longitude],
        help_text="Longitude coordinate"
    )
    province = models.CharField(max_length=100)
    municipal = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    street_address = models.CharField(max_length=200)
    
    # Incident Details
    incident_description = models.TextField(help_text="Detailed description of the accident")
    casualties_killed = models.IntegerField(
        default=0,
        validators=[validate_casualty_count, MinValueValidator(0)],
        help_text="Number of fatalities"
    )
    casualties_injured = models.IntegerField(
        default=0,
        validators=[validate_casualty_count, MinValueValidator(0)],
        help_text="Number of injured persons"
    )

    # Vehicle involved
    vehicles_involved = models.JSONField(default=list)  # List of vehicle details

    # Media attachments
    photo_1 = models.ImageField(
        upload_to='accident_reports/',
        null=True,
        blank=True,
        validators=[validate_image_file_size, validate_image_file_extension],
        help_text="Photo of accident scene (max 5MB, jpg/png)"
    )
    photo_2 = models.ImageField(
        upload_to='accident_reports/',
        null=True,
        blank=True,
        validators=[validate_image_file_size, validate_image_file_extension],
        help_text="Additional photo (max 5MB, jpg/png)"
    )
    photo_3 = models.ImageField(
        upload_to='accident_reports/',
        null=True,
        blank=True,
        validators=[validate_image_file_size, validate_image_file_extension],
        help_text="Additional photo (max 5MB, jpg/png)"
    )
    
    # Status and Processing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_reports')
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Link to official accident record (after verification)
    accident = models.OneToOneField(Accident, on_delete=models.SET_NULL, null=True, blank=True, related_name='report')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'accident_reports'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report by {self.reporter_name} - {self.incident_date} ({self.status})"


class ClusteringJob(models.Model):
    """Track AGNES clustering job executions"""
    
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    
    # Parameters
    linkage_method = models.CharField(max_length=20)
    distance_threshold = models.FloatField()
    min_cluster_size = models.IntegerField()
    
    # Results
    total_accidents = models.IntegerField(default=0)
    clusters_found = models.IntegerField(default=0)
    error_message = models.TextField(null=True, blank=True)
    
    # Data range
    date_from = models.DateField()
    date_to = models.DateField()
    
    started_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'clustering_jobs'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Clustering Job {self.id} - {self.status}"


class UserProfile(models.Model):
    """Extended user profile for PNP personnel with roles and permissions"""

    ROLE_CHOICES = [
        ('super_admin', 'Super Admin'),
        ('regional_director', 'Regional Director'),
        ('provincial_chief', 'Provincial Chief'),
        ('station_commander', 'Station Commander'),
        ('traffic_officer', 'Traffic Officer'),
        ('data_encoder', 'Data Encoder'),
    ]

    RANK_CHOICES = [
        ('PGEN', 'Police General'),
        ('PLTGEN', 'Police Lieutenant General'),
        ('PMGEN', 'Police Major General'),
        ('PBGEN', 'Police Brigadier General'),
        ('PCOLONEL', 'Police Colonel'),
        ('PLTCOL', 'Police Lieutenant Colonel'),
        ('PMAJOR', 'Police Major'),
        ('PCAPTAIN', 'Police Captain'),
        ('PLIEUTENANT', 'Police Lieutenant'),
        ('PEXECUTIVE MASTER SERGEANT', 'Police Executive Master Sergeant'),
        ('PCHIEF MASTER SERGEANT', 'Police Chief Master Sergeant'),
        ('PSENIOR MASTER SERGEANT', 'Police Senior Master Sergeant'),
        ('PMASTER SERGEANT', 'Police Master Sergeant'),
        ('PSTAFF SERGEANT', 'Police Staff Sergeant'),
        ('PCORPORAL', 'Police Corporal'),
        ('PATROLMAN', 'Patrolman'),
        ('CIVILIAN', 'Civilian Personnel'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # PNP-specific fields
    badge_number = models.CharField(max_length=50, unique=True, verbose_name="Badge/ID Number")
    rank = models.CharField(max_length=50, choices=RANK_CHOICES, default='PATROLMAN')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default='traffic_officer')

    # Assignment/Jurisdiction
    region = models.CharField(max_length=100, default="CARAGA")
    province = models.CharField(max_length=100, blank=True, null=True)
    station = models.CharField(max_length=200, blank=True, null=True)
    unit = models.CharField(max_length=200, blank=True, null=True, verbose_name="Unit/Office")

    # Contact
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    mobile_number = models.CharField(max_length=20)

    # Profile Picture
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True, verbose_name="Profile Picture")

    # Security
    is_active = models.BooleanField(default=True)
    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_profiles')

    class Meta:
        db_table = 'user_profiles'
        ordering = ['rank', 'user__last_name']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.get_rank_display()} {self.user.get_full_name() or self.user.username} - {self.get_role_display()}"

    def get_full_name_with_rank(self):
        """Return rank + full name"""
        name = self.user.get_full_name() or self.user.username
        return f"{self.get_rank_display()} {name}"

    def has_permission(self, permission):
        """Check if user has specific permission based on role"""
        permissions = {
            'super_admin': ['view', 'add', 'edit', 'delete', 'manage_users', 'run_clustering', 'view_all_data'],
            'regional_director': ['view', 'add', 'edit', 'manage_users', 'run_clustering', 'view_all_data'],
            'provincial_chief': ['view', 'add', 'edit', 'delete', 'run_clustering', 'view_province_data'],
            'station_commander': ['view', 'add', 'edit', 'view_station_data'],
            'traffic_officer': ['view', 'add', 'view_own_data'],
            'data_encoder': ['view', 'add', 'view_all_data'],
        }
        return permission in permissions.get(self.role, [])

    def can_view_accident(self, accident):
        """Check if user can view specific accident based on jurisdiction"""
        if self.role in ['super_admin', 'regional_director', 'data_encoder']:
            return True
        if self.role == 'provincial_chief':
            return accident.province == self.province
        if self.role == 'station_commander':
            return accident.station == self.station
        if self.role == 'traffic_officer':
            return accident.station == self.station
        return False

    def is_account_locked(self):
        """Check if account is currently locked"""
        if self.account_locked_until:
            if timezone.now() < self.account_locked_until:
                return True
            else:
                # Auto-unlock if lock period expired
                self.account_locked_until = None
                self.failed_login_attempts = 0
                self.save()
        return False


class AuditLog(models.Model):
    """Comprehensive audit trail for all user actions"""

    ACTION_CHOICES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('login_failed', 'Failed Login Attempt'),
        ('password_change', 'Password Changed'),
        ('accident_create', 'Accident Created'),
        ('accident_edit', 'Accident Edited'),
        ('accident_delete', 'Accident Deleted'),
        ('accident_view', 'Accident Viewed'),
        ('user_create', 'User Created'),
        ('user_edit', 'User Edited'),
        ('user_delete', 'User Deleted'),
        ('user_activate', 'User Activated'),
        ('user_deactivate', 'User Deactivated'),
        ('clustering_run', 'Clustering Executed'),
        ('report_generate', 'Report Generated'),
        ('export_data', 'Data Exported'),
        ('system_config', 'System Configuration Changed'),
    ]

    SEVERITY_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    # Who
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    username = models.CharField(max_length=150)  # Store username in case user is deleted
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    # What
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    action_description = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='info')

    # When
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Where (for geographic tracking)
    station = models.CharField(max_length=200, blank=True, null=True)
    province = models.CharField(max_length=100, blank=True, null=True)

    # Details
    object_type = models.CharField(max_length=100, blank=True, null=True)  # e.g., "Accident", "User"
    object_id = models.IntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=500, blank=True, null=True)  # String representation
    changes = models.JSONField(null=True, blank=True)  # Store old/new values

    # Status
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.username}: {self.get_action_display()}"

    @staticmethod
    def log_action(user, action, description, **kwargs):
        """Convenience method to create audit log entry"""
        return AuditLog.objects.create(
            user=user,
            username=user.username if user else 'Anonymous',
            action=action,
            action_description=description,
            **kwargs
        )