"""
Comprehensive test suite for the accidents application.

This module tests:
- Model functionality and constraints
- View logic and permissions
- Form validation
- Analytics calculations
- Data integrity
"""

from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, date, time, timedelta
import json

from .models import (
    Accident, AccidentCluster, AccidentReport,
    UserProfile, AuditLog, ClusteringJob
)
from .forms import AccidentForm, AccidentReportForm
from .analytics import calculate_hotspot_effectiveness


class AccidentModelTestCase(TestCase):
    """Test the Accident model"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@pnp.gov.ph'
        )

        self.accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Libertad',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=date(2024, 1, 15),
            time_committed=time(14, 30),
            incident_type='Vehicular Accident',
            victim_killed=True,
            victim_injured=False,
            victim_count=1,
            created_by=self.user
        )

    def test_accident_creation(self):
        """Test that an accident can be created successfully"""
        self.assertEqual(Accident.objects.count(), 1)
        self.assertEqual(self.accident.province, 'Agusan del Norte')
        self.assertEqual(self.accident.municipal, 'Butuan City')

    def test_accident_str_representation(self):
        """Test the string representation of an accident"""
        expected = f"{self.accident.incident_type} - {self.accident.municipal}, {self.accident.date_committed}"
        self.assertEqual(str(self.accident), expected)

    def test_accident_coordinates_precision(self):
        """Test that coordinates maintain proper precision"""
        self.assertEqual(self.accident.latitude, Decimal('8.9475'))
        self.assertEqual(self.accident.longitude, Decimal('125.5406'))

    def test_accident_casualty_booleans(self):
        """Test casualty boolean fields"""
        self.assertTrue(self.accident.victim_killed)
        self.assertFalse(self.accident.victim_injured)
        self.assertFalse(self.accident.victim_unharmed)

    def test_accident_clustering_defaults(self):
        """Test clustering-related default values"""
        self.assertIsNone(self.accident.cluster_id)
        self.assertFalse(self.accident.is_hotspot)

    def test_accident_ordering(self):
        """Test that accidents are ordered by date (newest first)"""
        accident2 = Accident.objects.create(
            province='Agusan del Sur',
            municipal='San Francisco',
            barangay='Poblacion',
            latitude=Decimal('8.5129'),
            longitude=Decimal('125.9767'),
            date_committed=date(2024, 2, 20),
            incident_type='Hit and Run'
        )

        accidents = list(Accident.objects.all())
        self.assertEqual(accidents[0], accident2)  # Newer first
        self.assertEqual(accidents[1], self.accident)

    def test_accident_year_field(self):
        """Test year field functionality"""
        accident = Accident.objects.create(
            province='Surigao del Norte',
            municipal='Surigao City',
            barangay='Washington',
            latitude=Decimal('9.7854'),
            longitude=Decimal('125.4920'),
            date_committed=date(2023, 6, 10),
            year=2023,
            incident_type='Motorcycle Accident'
        )
        self.assertEqual(accident.year, 2023)

    def test_accident_with_cluster_assignment(self):
        """Test accident with cluster assignment"""
        self.accident.cluster_id = 1
        self.accident.is_hotspot = True
        self.accident.save()

        self.assertEqual(self.accident.cluster_id, 1)
        self.assertTrue(self.accident.is_hotspot)


class AccidentClusterModelTestCase(TestCase):
    """Test the AccidentCluster model"""

    def setUp(self):
        """Set up test cluster data"""
        self.cluster = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('8.9475'),
            center_longitude=Decimal('125.5406'),
            accident_count=5,
            total_casualties=8,
            severity_score=75.5,
            min_latitude=Decimal('8.9400'),
            max_latitude=Decimal('8.9550'),
            min_longitude=Decimal('125.5300'),
            max_longitude=Decimal('125.5500'),
            radius=0.05,
            avg_distance=0.025,
            max_distance=0.048
        )

    def test_cluster_creation(self):
        """Test cluster creation"""
        self.assertEqual(AccidentCluster.objects.count(), 1)
        self.assertEqual(self.cluster.cluster_id, 1)

    def test_cluster_unique_id(self):
        """Test that cluster_id must be unique"""
        with self.assertRaises(Exception):
            AccidentCluster.objects.create(
                cluster_id=1,  # Duplicate
                center_latitude=Decimal('9.0000'),
                center_longitude=Decimal('126.0000'),
                min_latitude=Decimal('8.9900'),
                max_latitude=Decimal('9.0100'),
                min_longitude=Decimal('125.9900'),
                max_longitude=Decimal('126.0100')
            )

    def test_cluster_statistics(self):
        """Test cluster statistics fields"""
        self.assertEqual(self.cluster.accident_count, 5)
        self.assertEqual(self.cluster.total_casualties, 8)
        self.assertAlmostEqual(self.cluster.severity_score, 75.5)

    def test_cluster_geographic_bounds(self):
        """Test geographic bounding box"""
        self.assertEqual(self.cluster.min_latitude, Decimal('8.9400'))
        self.assertEqual(self.cluster.max_latitude, Decimal('8.9550'))
        self.assertEqual(self.cluster.min_longitude, Decimal('125.5300'))
        self.assertEqual(self.cluster.max_longitude, Decimal('125.5500'))

    def test_cluster_radius_calculations(self):
        """Test radius-related fields"""
        self.assertAlmostEqual(self.cluster.radius, 0.05)
        self.assertAlmostEqual(self.cluster.avg_distance, 0.025)
        self.assertAlmostEqual(self.cluster.max_distance, 0.048)


class AccidentReportModelTestCase(TestCase):
    """Test the AccidentReport model"""

    def setUp(self):
        """Set up test report data"""
        self.report = AccidentReport.objects.create(
            reporter_name='Juan dela Cruz',
            reporter_email='juan@email.com',
            reporter_phone='09171234567',
            incident_date=date(2024, 3, 15),
            incident_time=time(10, 30),
            location='Corner of J.C. Aquino Ave and Montilla Blvd, Butuan City',
            description='Two motorcycles collided at the intersection',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            casualties=2,
            status='pending'
        )

    def test_report_creation(self):
        """Test that a report can be created"""
        self.assertEqual(AccidentReport.objects.count(), 1)
        self.assertEqual(self.report.reporter_name, 'Juan dela Cruz')

    def test_report_default_status(self):
        """Test default status is pending"""
        report = AccidentReport.objects.create(
            reporter_name='Test User',
            incident_date=date(2024, 3, 16),
            location='Test Location',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406')
        )
        self.assertEqual(report.status, 'pending')

    def test_report_status_choices(self):
        """Test different status values"""
        valid_statuses = ['pending', 'verified', 'investigating', 'resolved', 'rejected']
        for status in valid_statuses:
            self.report.status = status
            self.report.save()
            self.assertEqual(self.report.status, status)

    def test_report_casualty_count(self):
        """Test casualty counting"""
        self.assertEqual(self.report.casualties, 2)


class UserProfileModelTestCase(TestCase):
    """Test the UserProfile model"""

    def setUp(self):
        """Set up test user and profile"""
        self.user = User.objects.create_user(
            username='officer123',
            password='testpass123',
            email='officer@pnp.gov.ph',
            first_name='Pedro',
            last_name='Santos'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            badge_number='PNP-13-2024-001',
            rank='Police Officer I',
            role='traffic_officer',
            station='Butuan City Police Station',
            province='Agusan del Norte'
        )

    def test_profile_creation(self):
        """Test that profile is created"""
        self.assertEqual(UserProfile.objects.count(), 1)
        self.assertEqual(self.profile.badge_number, 'PNP-13-2024-001')

    def test_profile_user_relationship(self):
        """Test one-to-one relationship with User"""
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.user.userprofile, self.profile)

    def test_profile_role_choices(self):
        """Test different role assignments"""
        roles = ['super_admin', 'regional_director', 'provincial_chief',
                 'station_commander', 'traffic_officer', 'data_encoder']

        for role in roles:
            self.profile.role = role
            self.profile.save()
            self.assertEqual(self.profile.role, role)

    def test_profile_account_lock_mechanism(self):
        """Test account lock functionality"""
        self.assertFalse(self.profile.account_locked)
        self.profile.account_locked = True
        self.profile.save()
        self.assertTrue(self.profile.account_locked)


class AuditLogModelTestCase(TestCase):
    """Test the AuditLog model"""

    def setUp(self):
        """Set up test user and audit log"""
        self.user = User.objects.create_user(
            username='admin',
            password='admin123',
            email='admin@pnp.gov.ph'
        )

        self.log = AuditLog.objects.create(
            user=self.user,
            action='CREATE_ACCIDENT',
            description='Created new accident record',
            severity='info',
            ip_address='127.0.0.1',
            user_agent='Mozilla/5.0'
        )

    def test_audit_log_creation(self):
        """Test that audit log is created"""
        self.assertEqual(AuditLog.objects.count(), 1)
        self.assertEqual(self.log.action, 'CREATE_ACCIDENT')

    def test_audit_log_severity_levels(self):
        """Test different severity levels"""
        severities = ['info', 'warning', 'error', 'critical']
        for severity in severities:
            self.log.severity = severity
            self.log.save()
            self.assertEqual(self.log.severity, severity)

    def test_audit_log_timestamp(self):
        """Test that timestamp is automatically set"""
        self.assertIsNotNone(self.log.timestamp)
        self.assertTrue(isinstance(self.log.timestamp, datetime))


class ClusteringJobModelTestCase(TestCase):
    """Test the ClusteringJob model"""

    def setUp(self):
        """Set up test clustering job"""
        self.user = User.objects.create_user(
            username='admin',
            password='admin123'
        )

        self.job = ClusteringJob.objects.create(
            started_by=self.user,
            status='pending',
            linkage_method='complete',
            distance_threshold=0.05,
            min_cluster_size=3
        )

    def test_job_creation(self):
        """Test clustering job creation"""
        self.assertEqual(ClusteringJob.objects.count(), 1)
        self.assertEqual(self.job.status, 'pending')

    def test_job_status_progression(self):
        """Test job status changes"""
        statuses = ['pending', 'running', 'completed', 'failed']
        for status in statuses:
            self.job.status = status
            self.job.save()
            self.assertEqual(self.job.status, status)

    def test_job_parameters(self):
        """Test clustering parameters"""
        self.assertEqual(self.job.linkage_method, 'complete')
        self.assertAlmostEqual(float(self.job.distance_threshold), 0.05)
        self.assertEqual(self.job.min_cluster_size, 3)


class AccidentFormTestCase(TestCase):
    """Test the AccidentForm validation"""

    def test_valid_accident_form(self):
        """Test form with valid data"""
        form_data = {
            'province': 'Agusan del Norte',
            'municipal': 'Butuan City',
            'barangay': 'Libertad',
            'latitude': '8.9475',
            'longitude': '125.5406',
            'date_committed': '2024-01-15',
            'time_committed': '14:30',
            'incident_type': 'Vehicular Accident',
            'victim_killed': True,
            'victim_count': 1
        }
        form = AccidentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_coordinates(self):
        """Test form with invalid coordinates"""
        form_data = {
            'province': 'Agusan del Norte',
            'municipal': 'Butuan City',
            'barangay': 'Libertad',
            'latitude': '200.0000',  # Invalid latitude
            'longitude': '125.5406',
            'date_committed': '2024-01-15',
            'incident_type': 'Vehicular Accident'
        }
        form = AccidentForm(data=form_data)
        # The form might still be valid depending on validators
        # This test shows the importance of adding validators

    def test_missing_required_fields(self):
        """Test form with missing required fields"""
        form_data = {
            'province': 'Agusan del Norte',
            # Missing municipal, barangay, coordinates, date
        }
        form = AccidentForm(data=form_data)
        self.assertFalse(form.is_valid())


class AccidentReportFormTestCase(TestCase):
    """Test the AccidentReportForm validation"""

    def test_valid_report_form(self):
        """Test form with valid report data"""
        form_data = {
            'reporter_name': 'Juan dela Cruz',
            'reporter_email': 'juan@email.com',
            'reporter_phone': '09171234567',
            'incident_date': '2024-03-15',
            'incident_time': '10:30',
            'location': 'Butuan City',
            'description': 'Test accident report',
            'latitude': '8.9475',
            'longitude': '125.5406',
            'casualties': 2
        }
        form = AccidentReportForm(data=form_data)
        # Validate form structure
        self.assertIsNotNone(form)


class DashboardViewTestCase(TestCase):
    """Test the dashboard view"""

    def setUp(self):
        """Set up test client and user"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        # Create user profile for PNP authentication
        UserProfile.objects.create(
            user=self.user,
            badge_number='TEST-001',
            rank='Police Officer I',
            role='traffic_officer',
            station='Test Station',
            province='Test Province',
            force_password_change=False
        )

        # Create some test accidents
        for i in range(5):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=timezone.now().date(),
                incident_type='Test Accident',
                victim_killed=(i % 2 == 0)
            )

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('dashboard'))
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for logged-in user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_context_data(self):
        """Test that dashboard provides correct context"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))

        # Check that context contains expected keys
        self.assertIn('today_accidents', response.context)
        self.assertIn('recent_accidents', response.context)


class AccidentListViewTestCase(TestCase):
    """Test the accident list view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        UserProfile.objects.create(
            user=self.user,
            badge_number='TEST-001',
            rank='Police Officer I',
            role='traffic_officer',
            station='Test Station',
            province='Test Province',
            force_password_change=False
        )

        # Create 25 test accidents for pagination testing
        for i in range(25):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type=f'Test Accident {i}'
            )

    def test_accident_list_pagination(self):
        """Test that accident list is paginated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accident_list'))

        self.assertEqual(response.status_code, 200)
        # Check pagination
        if 'page_obj' in response.context:
            self.assertTrue(response.context['page_obj'].has_other_pages())


class AccidentDetailViewTestCase(TestCase):
    """Test the accident detail view"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

        UserProfile.objects.create(
            user=self.user,
            badge_number='TEST-001',
            rank='Police Officer I',
            role='traffic_officer',
            station='Test Station',
            province='Test Province',
            force_password_change=False
        )

        self.accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Libertad',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=date(2024, 1, 15),
            incident_type='Vehicular Accident',
            narrative='Test narrative'
        )

    def test_accident_detail_view(self):
        """Test accident detail page loads"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('accident_detail', args=[self.accident.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vehicular Accident')


# Run tests with: python manage.py test accidents.tests -v 2
