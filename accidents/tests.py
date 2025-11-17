# accidents/tests.py
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
import datetime
from .models import (
    Accident, AccidentCluster, AccidentReport, ClusteringJob, UserProfile, AuditLog
)
from .validators import (
    validate_philippine_latitude,
    validate_philippine_longitude,
    validate_date_not_future,
    validate_casualty_count,
    validate_year_range,
    validate_severity_score,
    validate_cluster_distance_threshold,
)


# ============================================================================
# VALIDATOR TESTS
# ============================================================================

class ValidatorTestCase(TestCase):
    """Test custom validators"""

    def test_philippine_latitude_valid(self):
        """Test valid Philippine latitudes"""
        validate_philippine_latitude(Decimal('14.5995'))  # Manila
        validate_philippine_latitude(Decimal('9.0000'))   # CARAGA
        validate_philippine_latitude(Decimal('7.0000'))   # Mindanao

    def test_philippine_latitude_invalid(self):
        """Test invalid Philippine latitudes"""
        with self.assertRaises(ValidationError):
            validate_philippine_latitude(Decimal('3.0'))  # Too south
        with self.assertRaises(ValidationError):
            validate_philippine_latitude(Decimal('25.0'))  # Too north

    def test_philippine_longitude_valid(self):
        """Test valid Philippine longitudes"""
        validate_philippine_longitude(Decimal('120.9842'))  # Manila
        validate_philippine_longitude(Decimal('125.5442'))  # CARAGA

    def test_philippine_longitude_invalid(self):
        """Test invalid Philippine longitudes"""
        with self.assertRaises(ValidationError):
            validate_philippine_longitude(Decimal('110.0'))  # Too west
        with self.assertRaises(ValidationError):
            validate_philippine_longitude(Decimal('130.0'))  # Too east

    def test_date_not_future_valid(self):
        """Test dates in the past are valid"""
        validate_date_not_future(datetime.date.today())
        validate_date_not_future(datetime.date(2020, 1, 1))

    def test_date_not_future_invalid(self):
        """Test future dates are invalid"""
        future_date = datetime.date.today() + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError):
            validate_date_not_future(future_date)

    def test_casualty_count_valid(self):
        """Test valid casualty counts"""
        validate_casualty_count(0)
        validate_casualty_count(10)
        validate_casualty_count(50)

    def test_casualty_count_invalid(self):
        """Test invalid casualty counts"""
        with self.assertRaises(ValidationError):
            validate_casualty_count(-1)  # Negative
        with self.assertRaises(ValidationError):
            validate_casualty_count(150)  # Too high

    def test_year_range_valid(self):
        """Test valid year ranges"""
        validate_year_range(2024)
        validate_year_range(2000)
        validate_year_range(1950)

    def test_year_range_invalid(self):
        """Test invalid year ranges"""
        with self.assertRaises(ValidationError):
            validate_year_range(1940)  # Too old
        with self.assertRaises(ValidationError):
            validate_year_range(2030)  # Future

    def test_severity_score_valid(self):
        """Test valid severity scores"""
        validate_severity_score(0.0)
        validate_severity_score(50.5)
        validate_severity_score(999.9)

    def test_severity_score_invalid(self):
        """Test invalid severity scores"""
        with self.assertRaises(ValidationError):
            validate_severity_score(-1.0)  # Negative
        with self.assertRaises(ValidationError):
            validate_severity_score(1500.0)  # Too high


# ============================================================================
# ACCIDENT MODEL TESTS
# ============================================================================

class AccidentModelTestCase(TestCase):
    """Test Accident model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_accident_creation(self):
        """Test creating an accident record"""
        accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Libertad',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=datetime.date(2024, 1, 15),
            incident_type='Vehicular Accident',
            victim_count=2,
            created_by=self.user
        )
        self.assertEqual(accident.province, 'Agusan del Norte')
        self.assertEqual(accident.victim_count, 2)
        self.assertFalse(accident.is_hotspot)

    def test_accident_str_representation(self):
        """Test string representation of accident"""
        accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Libertad',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=datetime.date(2024, 1, 15),
            incident_type='Vehicular Accident',
            created_by=self.user
        )
        expected = f"Vehicular Accident - Butuan City, 2024-01-15"
        self.assertEqual(str(accident), expected)

    def test_accident_casualty_flags(self):
        """Test casualty boolean flags"""
        accident = Accident.objects.create(
            province='Surigao del Sur',
            municipal='Tandag',
            barangay='Poblacion',
            latitude=Decimal('9.0767'),
            longitude=Decimal('126.2004'),
            date_committed=datetime.date(2024, 1, 20),
            victim_killed=True,
            victim_count=1,
            created_by=self.user
        )
        self.assertTrue(accident.victim_killed)
        self.assertFalse(accident.victim_injured)
        self.assertFalse(accident.victim_unharmed)

    def test_accident_latitude_validation(self):
        """Test latitude validation"""
        accident = Accident(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('30.0'),  # Invalid - outside Philippines
            longitude=Decimal('125.5'),
            date_committed=datetime.date(2024, 1, 15)
        )
        with self.assertRaises(ValidationError):
            accident.full_clean()

    def test_accident_longitude_validation(self):
        """Test longitude validation"""
        accident = Accident(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('140.0'),  # Invalid - outside Philippines
            date_committed=datetime.date(2024, 1, 15)
        )
        with self.assertRaises(ValidationError):
            accident.full_clean()

    def test_accident_future_date_validation(self):
        """Test that future dates are rejected"""
        future_date = datetime.date.today() + datetime.timedelta(days=30)
        accident = Accident(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            date_committed=future_date
        )
        with self.assertRaises(ValidationError):
            accident.full_clean()

    def test_accident_ordering(self):
        """Test accident ordering (newest first)"""
        acc1 = Accident.objects.create(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            date_committed=datetime.date(2024, 1, 10)
        )
        acc2 = Accident.objects.create(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            date_committed=datetime.date(2024, 1, 20)
        )
        accidents = list(Accident.objects.all())
        self.assertEqual(accidents[0].id, acc2.id)  # Newest first

    def test_accident_cluster_assignment(self):
        """Test assigning accident to cluster"""
        accident = Accident.objects.create(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            date_committed=datetime.date(2024, 1, 15),
            cluster_id=1,
            is_hotspot=True
        )
        self.assertEqual(accident.cluster_id, 1)
        self.assertTrue(accident.is_hotspot)


# ============================================================================
# ACCIDENT CLUSTER MODEL TESTS
# ============================================================================

class AccidentClusterModelTestCase(TestCase):
    """Test AccidentCluster model"""

    def test_cluster_creation(self):
        """Test creating an accident cluster"""
        cluster = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('9.0000'),
            center_longitude=Decimal('125.5000'),
            accident_count=5,
            total_casualties=10,
            severity_score=75.5,
            min_latitude=Decimal('8.9900'),
            max_latitude=Decimal('9.0100'),
            min_longitude=Decimal('125.4900'),
            max_longitude=Decimal('125.5100'),
            primary_location='Butuan City',
            linkage_method='complete',
            distance_threshold=0.05
        )
        self.assertEqual(cluster.cluster_id, 1)
        self.assertEqual(cluster.accident_count, 5)
        self.assertEqual(cluster.primary_location, 'Butuan City')

    def test_cluster_str_representation(self):
        """Test string representation of cluster"""
        cluster = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('9.0000'),
            center_longitude=Decimal('125.5000'),
            accident_count=5,
            primary_location='Butuan City',
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            linkage_method='complete',
            distance_threshold=0.05
        )
        expected = "Cluster 1 - Butuan City (5 accidents)"
        self.assertEqual(str(cluster), expected)

    def test_cluster_severity_validation(self):
        """Test severity score validation"""
        cluster = AccidentCluster(
            cluster_id=1,
            center_latitude=Decimal('9.0'),
            center_longitude=Decimal('125.5'),
            severity_score=1500.0,  # Invalid - too high
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            primary_location='Test',
            linkage_method='complete',
            distance_threshold=0.05
        )
        with self.assertRaises(ValidationError):
            cluster.full_clean()

    def test_cluster_ordering(self):
        """Test cluster ordering by severity and count"""
        c1 = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('9.0'),
            center_longitude=Decimal('125.5'),
            accident_count=3,
            severity_score=50.0,
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            primary_location='Cluster 1',
            linkage_method='complete',
            distance_threshold=0.05
        )
        c2 = AccidentCluster.objects.create(
            cluster_id=2,
            center_latitude=Decimal('9.0'),
            center_longitude=Decimal('125.5'),
            accident_count=5,
            severity_score=100.0,
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            primary_location='Cluster 2',
            linkage_method='complete',
            distance_threshold=0.05
        )
        clusters = list(AccidentCluster.objects.all())
        self.assertEqual(clusters[0].cluster_id, 2)  # Higher severity first

    def test_cluster_distance_threshold_validation(self):
        """Test distance threshold validation"""
        cluster = AccidentCluster(
            cluster_id=1,
            center_latitude=Decimal('9.0'),
            center_longitude=Decimal('125.5'),
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            primary_location='Test',
            linkage_method='complete',
            distance_threshold=2.0  # Invalid - too large
        )
        with self.assertRaises(ValidationError):
            cluster.full_clean()

    def test_cluster_municipalities_json(self):
        """Test municipalities JSON field"""
        cluster = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('9.0'),
            center_longitude=Decimal('125.5'),
            min_latitude=Decimal('8.99'),
            max_latitude=Decimal('9.01'),
            min_longitude=Decimal('125.49'),
            max_longitude=Decimal('125.51'),
            primary_location='Butuan City',
            municipalities=['Butuan City', 'Cabadbaran'],
            linkage_method='complete',
            distance_threshold=0.05
        )
        self.assertEqual(len(cluster.municipalities), 2)
        self.assertIn('Butuan City', cluster.municipalities)


# ============================================================================
# ACCIDENT REPORT MODEL TESTS
# ============================================================================

class AccidentReportModelTestCase(TestCase):
    """Test AccidentReport model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='reporter', password='testpass123')

    def test_report_creation(self):
        """Test creating an accident report"""
        report = AccidentReport.objects.create(
            reported_by=self.user,
            reporter_name='John Doe',
            reporter_contact='09171234567',
            incident_date=datetime.date(2024, 1, 15),
            incident_time=datetime.time(14, 30),
            latitude=Decimal('9.0767'),
            longitude=Decimal('126.2004'),
            province='Surigao del Sur',
            municipal='Tandag',
            barangay='Poblacion',
            street_address='National Highway',
            incident_description='Motorcycle collision',
            casualties_killed=0,
            casualties_injured=2,
            status='pending'
        )
        self.assertEqual(report.status, 'pending')
        self.assertEqual(report.casualties_injured, 2)

    def test_report_str_representation(self):
        """Test string representation of report"""
        report = AccidentReport.objects.create(
            reported_by=self.user,
            reporter_name='John Doe',
            reporter_contact='09171234567',
            incident_date=datetime.date(2024, 1, 15),
            incident_time=datetime.time(14, 30),
            latitude=Decimal('9.0767'),
            longitude=Decimal('126.2004'),
            province='Test',
            municipal='Test',
            barangay='Test',
            street_address='Test',
            incident_description='Test accident',
            status='pending'
        )
        expected = f"Report by John Doe - 2024-01-15 (pending)"
        self.assertEqual(str(report), expected)

    def test_report_status_choices(self):
        """Test report status workflow"""
        report = AccidentReport.objects.create(
            reported_by=self.user,
            reporter_name='Jane Smith',
            reporter_contact='09181234567',
            incident_date=datetime.date(2024, 1, 20),
            incident_time=datetime.time(10, 0),
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            province='Test',
            municipal='Test',
            barangay='Test',
            street_address='Test',
            incident_description='Test',
            status='pending'
        )

        # Test status transitions
        report.status = 'verified'
        report.verified_by = self.user
        report.verified_at = timezone.now()
        report.save()
        self.assertEqual(report.status, 'verified')
        self.assertIsNotNone(report.verified_at)

    def test_report_ordering(self):
        """Test report ordering (newest first)"""
        r1 = AccidentReport.objects.create(
            reported_by=self.user,
            reporter_name='Reporter 1',
            reporter_contact='09171234567',
            incident_date=datetime.date(2024, 1, 10),
            incident_time=datetime.time(10, 0),
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            province='Test',
            municipal='Test',
            barangay='Test',
            street_address='Test',
            incident_description='Test 1'
        )
        r2 = AccidentReport.objects.create(
            reported_by=self.user,
            reporter_name='Reporter 2',
            reporter_contact='09171234568',
            incident_date=datetime.date(2024, 1, 15),
            incident_time=datetime.time(11, 0),
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            province='Test',
            municipal='Test',
            barangay='Test',
            street_address='Test',
            incident_description='Test 2'
        )
        reports = list(AccidentReport.objects.all())
        self.assertEqual(reports[0].id, r2.id)  # Newest first


# ============================================================================
# USER PROFILE MODEL TESTS
# ============================================================================

class UserProfileModelTestCase(TestCase):
    """Test UserProfile model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='officer1',
            first_name='Juan',
            last_name='Dela Cruz',
            password='testpass123'
        )

    def test_profile_creation(self):
        """Test creating a user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PCAPTAIN',
            role='station_commander',
            region='CARAGA',
            province='Agusan del Norte',
            station='Butuan City Police Station',
            mobile_number='09171234567'
        )
        self.assertEqual(profile.badge_number, 'PNP-001234')
        self.assertEqual(profile.rank, 'PCAPTAIN')
        self.assertTrue(profile.is_active)

    def test_profile_str_representation(self):
        """Test string representation of profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PCAPTAIN',
            role='station_commander',
            mobile_number='09171234567'
        )
        self.assertIn('Police Captain', str(profile))
        self.assertIn('Juan Dela Cruz', str(profile))

    def test_profile_get_full_name_with_rank(self):
        """Test get_full_name_with_rank method"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PMAJOR',
            role='provincial_chief',
            mobile_number='09171234567'
        )
        expected = "Police Major Juan Dela Cruz"
        self.assertEqual(profile.get_full_name_with_rank(), expected)

    def test_profile_permission_checking(self):
        """Test has_permission method"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PCAPTAIN',
            role='super_admin',
            mobile_number='09171234567'
        )
        self.assertTrue(profile.has_permission('delete'))
        self.assertTrue(profile.has_permission('manage_users'))

        # Test limited permissions
        profile.role = 'traffic_officer'
        profile.save()
        self.assertTrue(profile.has_permission('view'))
        self.assertFalse(profile.has_permission('delete'))

    def test_profile_can_view_accident(self):
        """Test can_view_accident method"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PCAPTAIN',
            role='provincial_chief',
            province='Agusan del Norte',
            mobile_number='09171234567'
        )

        accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Test',
            latitude=Decimal('9.0'),
            longitude=Decimal('125.5'),
            date_committed=datetime.date(2024, 1, 15)
        )
        self.assertTrue(profile.can_view_accident(accident))

        # Different province
        accident.province = 'Surigao del Sur'
        self.assertFalse(profile.can_view_accident(accident))

    def test_profile_account_locking(self):
        """Test is_account_locked method"""
        profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-001234',
            rank='PATROLMAN',
            role='traffic_officer',
            mobile_number='09171234567'
        )

        # Not locked
        self.assertFalse(profile.is_account_locked())

        # Lock account
        profile.account_locked_until = timezone.now() + timezone.timedelta(hours=1)
        profile.save()
        self.assertTrue(profile.is_account_locked())


# ============================================================================
# CLUSTERING JOB MODEL TESTS
# ============================================================================

class ClusteringJobModelTestCase(TestCase):
    """Test ClusteringJob model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='admin', password='testpass123')

    def test_job_creation(self):
        """Test creating a clustering job"""
        job = ClusteringJob.objects.create(
            linkage_method='complete',
            distance_threshold=0.05,
            min_cluster_size=3,
            date_from=datetime.date(2024, 1, 1),
            date_to=datetime.date(2024, 12, 31),
            started_by=self.user,
            status='running'
        )
        self.assertEqual(job.status, 'running')
        self.assertEqual(job.linkage_method, 'complete')

    def test_job_str_representation(self):
        """Test string representation of job"""
        job = ClusteringJob.objects.create(
            linkage_method='complete',
            distance_threshold=0.05,
            min_cluster_size=3,
            date_from=datetime.date(2024, 1, 1),
            date_to=datetime.date(2024, 12, 31),
            started_by=self.user,
            status='completed'
        )
        self.assertIn('completed', str(job))

    def test_job_completion(self):
        """Test job completion"""
        job = ClusteringJob.objects.create(
            linkage_method='complete',
            distance_threshold=0.05,
            min_cluster_size=3,
            date_from=datetime.date(2024, 1, 1),
            date_to=datetime.date(2024, 12, 31),
            started_by=self.user,
            status='running'
        )

        # Complete the job
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.clusters_found = 5
        job.total_accidents = 25
        job.save()

        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.clusters_found, 5)
        self.assertIsNotNone(job.completed_at)


# ============================================================================
# AUDIT LOG MODEL TESTS
# ============================================================================

class AuditLogModelTestCase(TestCase):
    """Test AuditLog model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username='auditor', password='testpass123')

    def test_log_creation(self):
        """Test creating an audit log entry"""
        log = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='login',
            action_description='User logged in successfully',
            severity='info',
            ip_address='192.168.1.1',
            success=True
        )
        self.assertEqual(log.action, 'login')
        self.assertTrue(log.success)

    def test_log_str_representation(self):
        """Test string representation of log"""
        log = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='login',
            action_description='User logged in',
            severity='info'
        )
        self.assertIn('auditor', str(log))
        self.assertIn('User Login', str(log))

    def test_log_static_method(self):
        """Test log_action static method"""
        log = AuditLog.log_action(
            user=self.user,
            action='accident_create',
            description='Created new accident record',
            severity='info'
        )
        self.assertEqual(log.action, 'accident_create')
        self.assertEqual(log.username, 'auditor')

    def test_log_ordering(self):
        """Test log ordering (newest first)"""
        log1 = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='login',
            action_description='First login'
        )
        log2 = AuditLog.objects.create(
            user=self.user,
            username='auditor',
            action='logout',
            action_description='First logout'
        )
        logs = list(AuditLog.objects.all())
        self.assertEqual(logs[0].id, log2.id)  # Newest first
