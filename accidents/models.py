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
    vehicle_chassis_no = models.CharField(max_length=100, null=True, blank=True)
    vehicle_colorum = models.BooleanField(default=False)

    # Drug involvement
    drug_involved = models.BooleanField(default=False)

    # Detailed Information (stored as text)
    victim_details = models.TextField(null=True, blank=True)  # Already TextField - GOOD
    suspect_details = models.TextField(null=True, blank=True)  # Already TextField - GOOD
    narrative = models.TextField(blank=True, null=True)  # Already TextField - GOOD, ADDED null=True

    # Gender Information (extracted from victim_details and suspect_details)
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('UNKNOWN', 'Unknown/Not Specified'),
    ]

    driver_gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='UNKNOWN',
        help_text="Gender of primary driver/suspect involved in accident"
    )
    victim_gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        default='UNKNOWN',
        help_text="Gender of primary victim involved in accident"
    )

    # Additional demographic data
    driver_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        help_text="Age of primary driver (0-150)"
    )
    victim_age = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(150)],
        help_text="Age of primary victim (0-150)"
    )
    
    # Case Status
    CASE_STATUS_CHOICES = [
        ('Under Investigation', 'Under Investigation'),
        ('Solved', 'Solved'),
        ('Unsolved', 'Unsolved'),
    ]
    CASE_SOLVE_TYPE_CHOICES = [
        ('SOLVED (AMICABLY SETTLED)', 'Amicably Settled'),
        ('SOLVED (FILED IN COURT)', 'Filed in Court'),
        ('SOLVED (CLEARED BY ARREST)', 'Cleared by Arrest'),
        ('SOLVED (CLEARED BY OTHER MEANS)', 'Cleared by Other Means'),
    ]
    case_status = models.CharField(max_length=100, blank=True, null=True, default='Under Investigation')
    case_solve_type = models.CharField(max_length=200, null=True, blank=True)
    case_status_updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='case_status_updates')
    case_status_updated_at = models.DateTimeField(null=True, blank=True)

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
        ('cancelled', 'Cancelled'),
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

    INCIDENT_TYPE_CHOICES = [
        ('VEHICULAR_ACCIDENT', 'Vehicular Accident'),
        ('HIT_AND_RUN', 'Hit and Run'),
        ('RECKLESS_DRIVING', 'Reckless Driving'),
        ('ROAD_COLLISION', 'Road Collision'),
        ('PEDESTRIAN_ACCIDENT', 'Pedestrian Accident'),
        ('OTHER', 'Other'),
    ]

    PLACE_TYPE_CHOICES = [
        ('ALONG_STREET', 'Along the street'),
        ('HIGHWAY', 'Highway'),
        ('INTERSECTION', 'Intersection'),
        ('BRIDGE', 'Bridge'),
        ('CURVE_BEND', 'Curve/Bend'),
        ('PARKING_AREA', 'Parking Area'),
        ('RESIDENTIAL', 'Residential Area'),
        ('OTHER', 'Other'),
    ]

    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('UNKNOWN', 'Unknown'),
    ]

    VEHICLE_KIND_CHOICES = [
        ('MOTORCYCLE', 'Motorcycle'),
        ('TRICYCLE', 'Tricycle'),
        ('CAR', 'Car/Sedan'),
        ('SUV', 'SUV/Pickup'),
        ('VAN', 'Van'),
        ('TRUCK', 'Truck'),
        ('BUS', 'Bus'),
        ('JEEPNEY', 'Jeepney'),
        ('BICYCLE', 'Bicycle'),
        ('PEDESTRIAN', 'Pedestrian (No Vehicle)'),
        ('OTHER', 'Other'),
    ]

    incident_type = models.CharField(max_length=200, choices=INCIDENT_TYPE_CHOICES, default='VEHICULAR_ACCIDENT')
    incident_type_other = models.CharField(max_length=200, blank=True, null=True, help_text="Specify if Other is selected")
    type_of_place = models.CharField(max_length=200, choices=PLACE_TYPE_CHOICES, blank=True, null=True)
    type_of_place_other = models.CharField(max_length=200, blank=True, null=True, help_text="Specify if Other is selected")

    # Offense / Legal Classification
    OFFENSE_CHOICES = [
        ('RECKLESS_IMPRUDENCE_DAMAGE_PROPERTY', 'Reckless Imprudence Resulting to Damage to Property - RPC Art 365'),
        ('RECKLESS_IMPRUDENCE_PHYSICAL_INJURY', 'Reckless Imprudence Resulting to Physical Injury - RPC Art 365'),
        ('RECKLESS_IMPRUDENCE_HOMICIDE', 'Reckless Imprudence Resulting to Homicide - RPC Art 365'),
        ('RECKLESS_IMPRUDENCE_MULTIPLE_PHYSICAL_INJURY', 'Reckless Imprudence Resulting to Multiple Physical Injury - RPC Art 365'),
        ('RECKLESS_IMPRUDENCE_MULTIPLE_DAMAGE_PROPERTY', 'Reckless Imprudence Resulting to Multiple Damage to Property - RPC Art 365'),
        ('RECKLESS_IMPRUDENCE_MULTIPLE_HOMICIDE', 'Reckless Imprudence Resulting to Multiple Homicide - RPC Art 365'),
        ('ANTI_DRUNK_DRUGGED_DRIVING', 'Anti-Drunk and Drugged Driving Act of 2013 - RA 10586'),
        ('LAND_TRANSPORTATION_TRAFFIC_CODE', 'Land Transportation and Traffic Code - RA 4136'),
        ('OTHER', 'Other'),
    ]

    OFFENSE_TYPE_CHOICES = [
        ('CRIMES_AGAINST_PROPERTY', 'Crimes Against Property'),
        ('CRIMES_AGAINST_PERSONS', 'Crimes Against Persons'),
        ('REPUBLIC_ACT', 'Republic Act'),
        ('CRIMES_AGAINST_POPULAR_REPRESENTATION', 'Crimes Against Popular Representation'),
        ('CRIMES_AGAINST_PERSONAL_LIBERTY', 'Crimes Against Personal Liberty and Security'),
        ('PRESIDENTIAL_DECREE', 'Presidential Decree'),
        ('OTHER', 'Other'),
    ]

    offense = models.CharField(max_length=300, choices=OFFENSE_CHOICES, blank=True, null=True, help_text="Offense description")
    offense_other = models.CharField(max_length=500, blank=True, null=True, help_text="Specify if Other is selected")
    offense_type = models.CharField(max_length=300, choices=OFFENSE_TYPE_CHOICES, blank=True, null=True, help_text="Type of offense")
    offense_type_other = models.CharField(max_length=300, blank=True, null=True, help_text="Specify if Other is selected")

    STAGE_OF_FELONY_CHOICES = [
        ('ATTEMPTED', 'Attempted'),
        ('FRUSTRATED', 'Frustrated'),
        ('CONSUMMATED', 'Consummated'),
    ]
    stage_of_felony = models.CharField(max_length=100, choices=STAGE_OF_FELONY_CHOICES, blank=True, null=True)

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
    street_address = models.CharField(max_length=200, blank=True, null=True)
    
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

    # Victim Details (legacy single fields - kept for backward compat)
    victim_name = models.CharField(max_length=200, blank=True, null=True, help_text="Full name of victim")
    victim_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='UNKNOWN')
    victim_age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(150)])

    VICTIM_STATUS_CHOICES = [
        ('KILLED', 'Killed'),
        ('INJURED', 'Injured'),
        ('UNHARMED', 'Unharmed'),
    ]
    victim_status = models.CharField(max_length=20, choices=VICTIM_STATUS_CHOICES, blank=True, null=True)

    # Multi-victim/suspect data (JSON arrays matching CARAGA dataset format)
    victims_data = models.JSONField(default=list, blank=True, help_text="List of victims [{name, age, gender, status, nationality, occupation}]")
    suspects_data = models.JSONField(default=list, blank=True, help_text="List of suspects [{name, age, gender, status, nationality, occupation}]")

    # Suspect/Driver Details (legacy single fields - kept for backward compat)
    suspect_name = models.CharField(max_length=200, blank=True, null=True, help_text="Full name of suspect/driver")
    suspect_count = models.IntegerField(default=1, validators=[MinValueValidator(0), MaxValueValidator(50)])
    driver_gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='UNKNOWN')
    driver_age = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(150)])

    # Vehicle Information (structured)
    vehicle_kind = models.CharField(max_length=200, choices=VEHICLE_KIND_CHOICES, blank=True, null=True)
    vehicle_kind_other = models.CharField(max_length=200, blank=True, null=True, help_text="Specify if Other is selected")
    vehicle_make = models.CharField(max_length=100, blank=True, null=True)
    vehicle_make_other = models.CharField(max_length=100, blank=True, null=True, help_text="Specify if Other brand")
    vehicle_model = models.CharField(max_length=100, blank=True, null=True)
    vehicle_model_other = models.CharField(max_length=100, blank=True, null=True, help_text="Specify if Other model")
    vehicle_plate_no = models.CharField(max_length=50, blank=True, null=True)
    vehicle_chassis_no = models.CharField(max_length=100, blank=True, null=True, help_text="Vehicle chassis/serial number")
    vehicle_colorum = models.BooleanField(default=False, help_text="Vehicle operating without franchise (colorum)")

    # Drug involvement
    drug_involved = models.BooleanField(default=False, help_text="Whether drugs/alcohol were involved")

    # Vehicle involved (legacy JSON - kept for backward compatibility)
    vehicles_involved = models.JSONField(default=list, blank=True)

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
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection (if rejected)")
    
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


class ReportPhoto(models.Model):
    """Photos attached to an accident report (supports unlimited photos)"""
    report = models.ForeignKey(AccidentReport, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(
        upload_to='accident_reports/',
        validators=[validate_image_file_size, validate_image_file_extension],
        help_text="Photo of accident scene (max 5MB, jpg/png)"
    )
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_photos'
        ordering = ['order', 'uploaded_at']

    def __str__(self):
        return f"Photo {self.order + 1} for Report #{self.report_id}"


class Notification(models.Model):
    """In-app notifications for users"""

    TYPE_CHOICES = [
        ('report_submitted', 'New Report Submitted'),
        ('report_approved', 'Report Approved'),
        ('report_rejected', 'Report Rejected'),
        ('report_cancelled', 'Report Cancelled'),
        ('info', 'Information'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    url = models.CharField(max_length=500, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional: link to related report
    related_report = models.ForeignKey(
        'AccidentReport', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications'
    )

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.notification_type}] {self.title} → {self.recipient.username}"


class ReportActivityLog(models.Model):
    """Activity log tracking all report lifecycle events"""

    ACTION_CHOICES = [
        ('submitted', 'Report Submitted'),
        ('approved', 'Report Approved'),
        ('rejected', 'Report Rejected'),
        ('resubmitted', 'Report Resubmitted'),
        ('edited', 'Report Edited'),
        ('cancelled', 'Report Cancelled'),
    ]

    report = models.ForeignKey('AccidentReport', on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    actor_name = models.CharField(max_length=200)
    actor_role = models.CharField(max_length=100, blank=True)
    details = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'report_activity_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} - {self.actor_name}: {self.get_action_display()}"


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


class ClusterValidationMetrics(models.Model):
    """Stores clustering validation metrics for quality assessment"""

    # Relationship to clustering job (optional)
    clustering_job = models.OneToOneField(
        ClusteringJob,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='validation_metrics'
    )

    # Clustering metadata
    clustering_date = models.DateTimeField(auto_now_add=True)
    num_clusters = models.IntegerField(
        validators=[MinValueValidator(2)],
        help_text="Number of clusters in this analysis"
    )
    total_accidents = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Total accidents analyzed"
    )

    # Validation Metrics
    silhouette_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        help_text="Silhouette Score: -1 to 1, higher is better (measures cluster cohesion)"
    )
    davies_bouldin_index = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Davies-Bouldin Index: 0 to ∞, lower is better (measures cluster separation)"
    )
    calinski_harabasz_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text="Calinski-Harabasz Score: 0 to ∞, higher is better (variance ratio)"
    )

    # Quality interpretation
    cluster_quality = models.CharField(
        max_length=20,
        blank=True,
        help_text="Overall cluster quality assessment (Excellent, Good, Fair, Poor)"
    )

    # Clustering parameters used
    linkage_method = models.CharField(max_length=20, default="complete")
    distance_threshold = models.FloatField(
        validators=[validate_cluster_distance_threshold],
        help_text="Distance threshold used in clustering"
    )

    class Meta:
        db_table = 'cluster_validation_metrics'
        ordering = ['-clustering_date']
        verbose_name = 'Cluster Validation Metric'
        verbose_name_plural = 'Cluster Validation Metrics'

    def __str__(self):
        return f"Validation Metrics - {self.clustering_date.strftime('%Y-%m-%d %H:%M')} ({self.num_clusters} clusters)"

    def interpret_quality(self):
        """Provide human-readable interpretation of cluster quality"""
        if not self.silhouette_score or not self.davies_bouldin_index:
            return "Unknown"

        # Excellent: High silhouette (>0.7) AND low Davies-Bouldin (<0.5)
        if self.silhouette_score > 0.7 and self.davies_bouldin_index < 0.5:
            return "Excellent"
        # Good: Good silhouette (>0.5) AND reasonable Davies-Bouldin (<1.0)
        elif self.silhouette_score > 0.5 and self.davies_bouldin_index < 1.0:
            return "Good"
        # Fair: Moderate silhouette (>0.25)
        elif self.silhouette_score > 0.25:
            return "Fair"
        # Poor: Low silhouette or high Davies-Bouldin
        else:
            return "Poor"

    def save(self, *args, **kwargs):
        """Auto-calculate cluster quality on save"""
        if not self.cluster_quality:
            self.cluster_quality = self.interpret_quality()
        super().save(*args, **kwargs)


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

    UNIT_CHOICES = [
        ('', '--- Select Unit ---'),
        # Regional Directorial Staff Divisions (R1-R9)
        ('R1 - Regional Personnel and Records Management Division', 'R1 - Regional Personnel and Records Management Division'),
        ('R2 - Regional Intelligence Division', 'R2 - Regional Intelligence Division'),
        ('R3 - Regional Operation Management Division', 'R3 - Regional Operation Management Division'),
        ('R4 - Regional Logistics Research Development Division', 'R4 - Regional Logistics Research Development Division'),
        ('R5 - Regional Community Affairs Development Division', 'R5 - Regional Community Affairs Development Division'),
        ('R6 - Regional Comptrollership Division', 'R6 - Regional Comptrollership Division'),
        ('R7 - Regional Investigation Detective Management Division', 'R7 - Regional Investigation Detective Management Division'),
        ('R8 - Regional Learning and Doctrine Development Division', 'R8 - Regional Learning and Doctrine Development Division'),
        ('R9 - Regional Plans and Strategy Management Division', 'R9 - Regional Plans and Strategy Management Division'),
        # Regional Support Units/Offices
        ('Regional Headquarters Support Unit', 'Regional Headquarters Support Unit'),
        ('Regional Information and Communication Technology Management Division', 'Regional Information and Communication Technology Management Division'),
        ('Regional Health Service', 'Regional Health Service'),
        ('Public Information Office', 'Public Information Office'),
        # Operational/Special Units
        ('Regional Mobile Force Battalion', 'Regional Mobile Force Battalion'),
        ('Regional Drug Enforcement Unit', 'Regional Drug Enforcement Unit'),
        ('Regional Highway Patrol Unit', 'Regional Highway Patrol Unit'),
        ('Regional Maritime Unit', 'Regional Maritime Unit'),
        ('Regional Criminal Investigation and Detection Unit', 'Regional Criminal Investigation and Detection Unit'),
        ('Regional Forensic Unit', 'Regional Forensic Unit'),
        ('Regional Special Operations Unit', 'Regional Special Operations Unit'),
        ('Women and Children Protection Center', 'Women and Children Protection Center'),
        # Administrative Support Services
        ('Regional Internal Affairs Service', 'Regional Internal Affairs Service'),
        ('Regional Legal Service', 'Regional Legal Service'),
        ('Regional Finance Service', 'Regional Finance Service'),
        ('Regional Chaplain Service', 'Regional Chaplain Service'),
        ('Regional Communications and Electronics Unit', 'Regional Communications and Electronics Unit'),
        ('Regional Personnel Holding and Accounting Unit', 'Regional Personnel Holding and Accounting Unit'),
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
    office = models.CharField(max_length=200, blank=True, null=True, verbose_name="Office/Command",
        help_text="For Provincial Chief (PPO) and Regional Director (PRO). Leave blank for station-level personnel.")
    unit = models.CharField(max_length=200, blank=True, null=True, verbose_name="Unit/Office", choices=UNIT_CHOICES)

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

    # Report Access
    can_submit_reports = models.BooleanField(default=True, verbose_name='Can Submit Reports',
        help_text='Allow this user to access the report submission page')

    # Clustering Access
    can_run_clustering = models.BooleanField(default=False, verbose_name='Can Run Clustering',
        help_text='Allow this user to run the hotspot clustering algorithm')

    # Display Preferences (blank = use system default)
    VIEW_CHOICES = [('', 'System Default'), ('cards', 'Cards'), ('table', 'Table')]
    HOTSPOT_VIEW_CHOICES = [('', 'System Default'), ('grid', 'Grid'), ('list', 'List')]
    pref_accident_view = models.CharField(max_length=10, blank=True, default='', choices=VIEW_CHOICES, verbose_name='Accident page view')
    pref_hotspot_view = models.CharField(max_length=10, blank=True, default='', choices=HOTSPOT_VIEW_CHOICES, verbose_name='Hotspot page view')

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

    @property
    def assignment_display(self):
        """Return the appropriate assignment label based on role.
        Provincial Chief/Regional Director use office, others use station."""
        if self.role in ('provincial_chief', 'regional_director') and self.office:
            return self.office
        return self.station or ''

    @property
    def assignment_label(self):
        """Return the field label for this role's assignment."""
        if self.role in ('provincial_chief', 'regional_director'):
            return 'Office'
        return 'Station'

    def has_permission(self, permission):
        """
        Check if user has specific permission based on role

        Permission types:
        - view: View accident data
        - add: Create new accidents/reports
        - edit: Modify existing accidents
        - delete: Delete accidents (requires approval)
        - manage_users: Create, edit, activate/deactivate user accounts
        - delete_users: Permanently delete user accounts
        - run_clustering: Execute AGNES clustering algorithm
        - view_all_data: View data across entire region
        - view_province_data: View data within assigned province
        - view_station_data: View data within assigned station
        - view_own_data: View only own created records
        - generate_reports: Generate and export reports
        - view_audit_logs: View system audit logs
        - system_config: Change system configuration
        - verify_reports: Verify citizen accident reports
        - assign_jurisdiction: Assign users to provinces/stations
        """
        permissions = {
            'super_admin': [
                'view', 'add', 'edit', 'delete',
                'manage_users', 'delete_users', 'assign_jurisdiction',
                'run_clustering', 'view_all_data',
                'generate_reports', 'view_audit_logs', 'system_config',
                'verify_reports'
            ],
            'regional_director': [
                'view', 'add', 'edit',  # No delete - requires super_admin
                'manage_users', 'assign_jurisdiction',  # Can manage users in region
                'run_clustering', 'view_all_data',
                'generate_reports', 'view_audit_logs',
                'verify_reports'
            ],
            'provincial_chief': [
                'view', 'add', 'edit', 'delete',  # Can delete within province
                'manage_users',  # Can create/edit users in province
                'run_clustering', 'view_province_data',
                'generate_reports', 'view_audit_logs',
                'verify_reports'
            ],
            'station_commander': [
                'view', 'add', 'edit',  # No delete - requires provincial approval
                'manage_users',  # Can manage officers at station
                'view_station_data',
                'generate_reports',
                'verify_reports'
            ],
            'traffic_officer': [
                'view', 'add',  # Primary job: add accident reports
                'view_all_data',  # Can view all accident records for awareness
            ],
            'data_encoder': [
                'view', 'add', 'edit',  # Data entry from paper forms + correct errors
                'view_all_data',  # Need to see all data for verification
                'generate_reports',  # Can export data for reporting
                'run_clustering',  # Can run AGNES clustering to reduce admin workload
            ],
        }
        return permission in permissions.get(self.role, [])

    def can_view_accident(self, accident):
        """Check if user can view specific accident based on jurisdiction"""
        if self.role in ['super_admin', 'regional_director', 'data_encoder', 'traffic_officer']:
            return True
        if self.role == 'provincial_chief':
            return (accident.province or '').upper() == (self.province or '').upper()
        if self.role == 'station_commander':
            return (accident.station or '') == (self.station or '')
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
        # Authentication
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('login_failed', 'Failed Login Attempt'),
        ('password_change', 'Password Changed'),
        ('password_reset', 'Password Reset'),
        ('password_verify', 'Password Verified'),
        ('CHANGE_USERNAME', 'Username Changed'),
        ('FAILED_PASSWORD_CHANGE', 'Failed Password Change'),
        ('FAILED_USERNAME_CHANGE', 'Failed Username Change'),
        # Accident Records
        ('accident_create', 'Accident Created'),
        ('accident_edit', 'Accident Edited'),
        ('case_status_update', 'Case Status Updated'),
        # User Management
        ('user_create', 'User Created'),
        ('user_edit', 'User Edited'),
        ('user_status_change', 'User Status Changed'),
        ('user_profile_edit', 'User Profile Edited'),
        ('user_status_edit', 'User Status Edited'),
        ('username_change', 'Username Changed by Admin'),
        ('profile_picture_upload', 'Profile Picture Uploaded'),
        # Clustering
        ('clustering_run', 'Clustering Executed'),
        ('clustering_complete', 'Clustering Completed'),
        ('clustering_failed', 'Clustering Failed'),
        # Data & System
        ('export_data', 'Data Exported'),
        ('admin_dashboard_view', 'Admin Dashboard Viewed'),
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


class SystemSetting(models.Model):
    """System-wide settings managed by admin / regional director."""

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='system_settings_updated'
    )

    class Meta:
        ordering = ['key']
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return f"{self.key} = {self.value}"

    # ── Default values for every known key ──
    DEFAULTS = {
        'accident_default_view': 'cards',   # cards | table
        'hotspot_default_view': 'grid',     # grid | list
        'session_timeout': '60',            # minutes: 15 | 30 | 60 | 120 | 480
        'default_per_page': '15',           # items per page: 10 | 15 | 20 | 50
    }

    @classmethod
    def get(cls, key):
        """Return the value for *key*, falling back to DEFAULTS."""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return cls.DEFAULTS.get(key, '')