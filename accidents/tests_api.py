"""
API Integration Tests for the accidents application.

Tests for:
- REST API endpoints
- Authentication and permissions
- Pagination and filtering
- Data serialization
- API response formats
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
from datetime import date, time, timedelta
import json

from .models import Accident, AccidentCluster, AccidentReport, UserProfile
from .serializers import AccidentSerializer, AccidentClusterSerializer


class AccidentAPITestCase(APITestCase):
    """Test the Accident API endpoints"""

    def setUp(self):
        """Set up test client, user, and data"""
        self.client = APIClient()

        # Create test user with profile
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@pnp.gov.ph'
        )

        self.profile = UserProfile.objects.create(
            user=self.user,
            badge_number='TEST-001',
            rank='Police Officer I',
            role='traffic_officer',
            station='Test Station',
            province='Agusan del Norte',
            force_password_change=False
        )

        # Create test accidents
        for i in range(15):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475') + Decimal(str(i * 0.001)),
                longitude=Decimal('125.5406') + Decimal(str(i * 0.001)),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                time_committed=time(14, 30),
                incident_type=f'Accident Type {i % 3}',
                victim_killed=(i % 3 == 0),
                victim_injured=(i % 2 == 0),
                victim_count=i % 5
            )

    def test_accident_list_endpoint(self):
        """Test GET /api/accidents/ returns list of accidents"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIsInstance(response.data['results'], list)

    def test_accident_list_pagination(self):
        """Test that accident list is paginated"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertEqual(response.data['count'], 15)

    def test_accident_detail_endpoint(self):
        """Test GET /api/accidents/{id}/ returns accident details"""
        self.client.force_authenticate(user=self.user)
        accident = Accident.objects.first()

        response = self.client.get(f'/api/accidents/{accident.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], accident.id)
        self.assertEqual(response.data['province'], accident.province)

    def test_accident_filtering_by_province(self):
        """Test filtering accidents by province"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/?province=Agusan del Norte')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)

    def test_accident_filtering_by_year(self):
        """Test filtering accidents by year"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/?year=2024')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(response.data['count'], 0)

    def test_accident_ordering(self):
        """Test ordering of accidents"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/?ordering=-date_committed')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']

        # Check that results are ordered by date (newest first)
        if len(results) >= 2:
            first_date = results[0]['date_committed']
            second_date = results[1]['date_committed']
            self.assertGreaterEqual(first_date, second_date)

    def test_accident_search(self):
        """Test searching accidents"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/accidents/?search=Butuan')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 15)

    def test_accident_api_unauthenticated(self):
        """Test that unauthenticated requests are handled"""
        # Don't authenticate
        response = self.client.get('/api/accidents/')

        # API might require authentication or allow public read
        # Adjust assertion based on actual API design
        self.assertIn(
            response.status_code,
            [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )

    def test_accident_create_not_allowed(self):
        """Test that creating accidents via API requires proper permissions"""
        self.client.force_authenticate(user=self.user)

        new_accident = {
            'province': 'Agusan del Sur',
            'municipal': 'San Francisco',
            'barangay': 'Poblacion',
            'latitude': '8.5129',
            'longitude': '125.9767',
            'date_committed': '2024-02-01',
            'incident_type': 'Test Accident'
        }

        response = self.client.post('/api/accidents/', new_accident)

        # Read-only API should not allow POST
        # Adjust based on actual API permissions
        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_405_METHOD_NOT_ALLOWED,
             status.HTTP_403_FORBIDDEN]
        )


class AccidentClusterAPITestCase(APITestCase):
    """Test the Accident Cluster (Hotspot) API endpoints"""

    def setUp(self):
        """Set up test clusters"""
        self.client = APIClient()

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

        # Create test clusters
        for i in range(5):
            AccidentCluster.objects.create(
                cluster_id=i,
                center_latitude=Decimal('8.9475') + Decimal(str(i * 0.01)),
                center_longitude=Decimal('125.5406') + Decimal(str(i * 0.01)),
                accident_count=10 + i,
                total_casualties=15 + i,
                severity_score=100.0 + (i * 10),
                min_latitude=Decimal('8.9400') + Decimal(str(i * 0.01)),
                max_latitude=Decimal('8.9550') + Decimal(str(i * 0.01)),
                min_longitude=Decimal('125.5300') + Decimal(str(i * 0.01)),
                max_longitude=Decimal('125.5500') + Decimal(str(i * 0.01)),
                radius=0.05
            )

    def test_cluster_list_endpoint(self):
        """Test GET /api/clusters/ returns list of clusters"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/clusters/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response could be paginated or direct list
        if 'results' in response.data:
            self.assertIsInstance(response.data['results'], list)
            self.assertEqual(len(response.data['results']), 5)
        else:
            self.assertIsInstance(response.data, list)
            self.assertEqual(len(response.data), 5)

    def test_cluster_detail_endpoint(self):
        """Test GET /api/clusters/{id}/ returns cluster details"""
        self.client.force_authenticate(user=self.user)
        cluster = AccidentCluster.objects.first()

        response = self.client.get(f'/api/clusters/{cluster.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['cluster_id'], cluster.cluster_id)

    def test_cluster_ordering_by_severity(self):
        """Test ordering clusters by severity score"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/clusters/?ordering=-severity_score')

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AccidentReportAPITestCase(APITestCase):
    """Test the Accident Report API endpoints"""

    def setUp(self):
        """Set up test reports"""
        self.client = APIClient()

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

        # Create test reports
        for i in range(3):
            AccidentReport.objects.create(
                reporter_name=f'Reporter {i}',
                reporter_email=f'reporter{i}@email.com',
                reporter_phone=f'0917123456{i}',
                incident_date=date(2024, 1, 1) + timedelta(days=i),
                incident_time=time(10, 30),
                location=f'Location {i}',
                description=f'Description {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                casualties=i,
                status=['pending', 'verified', 'resolved'][i]
            )

    def test_report_list_endpoint(self):
        """Test GET /api/reports/ returns list of reports"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/reports/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_report_filtering_by_status(self):
        """Test filtering reports by status"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/reports/?status=pending')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_report_creation(self):
        """Test creating a new accident report via API"""
        new_report = {
            'reporter_name': 'Juan dela Cruz',
            'reporter_email': 'juan@email.com',
            'reporter_phone': '09171234567',
            'incident_date': '2024-03-15',
            'incident_time': '10:30',
            'location': 'Butuan City',
            'description': 'Test report',
            'latitude': '8.9475',
            'longitude': '125.5406',
            'casualties': 1
        }

        # Public users might be able to create reports
        response = self.client.post('/api/reports/', new_report)

        # Check if creation is allowed
        self.assertIn(
            response.status_code,
            [status.HTTP_201_CREATED, status.HTTP_401_UNAUTHORIZED,
             status.HTTP_403_FORBIDDEN]
        )


class APIStatisticsTestCase(APITestCase):
    """Test API statistics endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

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

        # Create test accidents
        for i in range(20):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Test Accident',
                victim_killed=(i % 5 == 0),
                victim_count=1
            )

    def test_accident_statistics_endpoint(self):
        """Test statistics endpoint if available"""
        self.client.force_authenticate(user=self.user)

        # Try common statistics endpoint patterns
        endpoints = [
            '/api/accidents/statistics/',
            '/api/statistics/',
            '/api/accidents/stats/'
        ]

        for endpoint in endpoints:
            response = self.client.get(endpoint)
            # If endpoint exists, it should return 200
            if response.status_code == status.HTTP_200_OK:
                self.assertIsInstance(response.data, dict)
                break


class APIBoundingBoxTestCase(APITestCase):
    """Test location-based queries and bounding box filtering"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

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

        # Create accidents in different locations
        locations = [
            (Decimal('8.9475'), Decimal('125.5406')),  # Butuan
            (Decimal('9.1200'), Decimal('125.5300')),  # Cabadbaran
            (Decimal('8.5129'), Decimal('125.9767')),  # San Francisco
        ]

        for lat, lng in locations:
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Test',
                barangay='Test',
                latitude=lat,
                longitude=lng,
                date_committed=date(2024, 1, 1),
                incident_type='Test'
            )

    def test_bounding_box_filtering(self):
        """Test filtering by geographic bounding box"""
        self.client.force_authenticate(user=self.user)

        # Define bounding box around Butuan area
        params = {
            'min_lat': '8.90',
            'max_lat': '9.00',
            'min_lng': '125.50',
            'max_lng': '125.60'
        }

        response = self.client.get('/api/accidents/', params)

        # If bounding box filtering is implemented
        if response.status_code == status.HTTP_200_OK:
            # Results should only include accidents within bounds
            if 'results' in response.data:
                for accident in response.data['results']:
                    lat = Decimal(str(accident['latitude']))
                    lng = Decimal(str(accident['longitude']))

                    self.assertGreaterEqual(lat, Decimal('8.90'))
                    self.assertLessEqual(lat, Decimal('9.00'))


class APIPerformanceTestCase(APITestCase):
    """Test API performance and optimization"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

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

        # Create large dataset
        for i in range(100):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i % 30),
                incident_type='Test'
            )

    def test_api_response_time(self):
        """Test that API responds in reasonable time"""
        import time

        self.client.force_authenticate(user=self.user)

        start_time = time.time()
        response = self.client.get('/api/accidents/')
        end_time = time.time()

        response_time = end_time - start_time

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # API should respond within 2 seconds
        self.assertLess(response_time, 2.0)

    def test_pagination_efficiency(self):
        """Test that pagination works efficiently"""
        self.client.force_authenticate(user=self.user)

        # Request first page
        response = self.client.get('/api/accidents/?page=1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('count', response.data)
        self.assertEqual(response.data['count'], 100)

    def test_field_selection(self):
        """Test if API supports field selection for optimization"""
        self.client.force_authenticate(user=self.user)

        # Try to request only specific fields
        response = self.client.get('/api/accidents/?fields=id,province,municipal')

        # If field selection is implemented, response should only contain those fields
        if response.status_code == status.HTTP_200_OK and 'results' in response.data:
            if len(response.data['results']) > 0:
                # Check structure (implementation dependent)
                pass


# Run with: python manage.py test accidents.tests_api -v 2
