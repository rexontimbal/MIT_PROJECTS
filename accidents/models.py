# accidents/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    
    # Temporal Information
    date_reported = models.DateField(null=True, blank=True)  # ADDED null=True
    time_reported = models.TimeField(null=True, blank=True)  # ADDED null=True
    date_committed = models.DateField()
    time_committed = models.TimeField(null=True, blank=True)  # ADDED null=True
    year = models.IntegerField(null=True, blank=True)  # ADDED null=True
    
    # Incident Details
    incident_type = models.CharField(max_length=500, blank=True, null=True)  # INCREASED - incident types can be long
    offense = models.TextField(blank=True, null=True)  # Already TextField - GOOD
    offense_type = models.CharField(max_length=300, blank=True, null=True)  # INCREASED
    stage_of_felony = models.CharField(max_length=100, blank=True, null=True)  # INCREASED
    
    # Casualties
    victim_killed = models.BooleanField(default=False)
    victim_injured = models.BooleanField(default=False)
    victim_unharmed = models.BooleanField(default=False)
    victim_count = models.IntegerField(default=0)
    suspect_count = models.IntegerField(default=0)
    
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
    accident_count = models.IntegerField(default=0)
    total_casualties = models.IntegerField(default=0)
    severity_score = models.FloatField(default=0.0)
    
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
    distance_threshold = models.FloatField()
    
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
    incident_date = models.DateField()
    incident_time = models.TimeField()
    
    # Location
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    province = models.CharField(max_length=100)
    municipal = models.CharField(max_length=100)
    barangay = models.CharField(max_length=100)
    street_address = models.CharField(max_length=200)
    
    # Incident Details
    incident_description = models.TextField()
    casualties_killed = models.IntegerField(default=0)
    casualties_injured = models.IntegerField(default=0)
    
    # Vehicle involved
    vehicles_involved = models.JSONField(default=list)  # List of vehicle details
    
    # Media attachments
    photo_1 = models.ImageField(upload_to='accident_reports/', null=True, blank=True)
    photo_2 = models.ImageField(upload_to='accident_reports/', null=True, blank=True)
    photo_3 = models.ImageField(upload_to='accident_reports/', null=True, blank=True)
    
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