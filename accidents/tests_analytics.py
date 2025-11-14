"""
Unit tests for the analytics module.

Tests for:
- Hotspot effectiveness calculations
- Spatial concentration metrics
- Temporal pattern analysis
- Severity analysis
- Geographic distribution
"""

from django.test import TestCase
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date, time, datetime, timedelta
import math

from .models import Accident, AccidentCluster
from .analytics import (
    calculate_hotspot_effectiveness,
    calculate_spatial_concentration,
    analyze_temporal_patterns,
    calculate_severity_metrics,
    analyze_geographic_distribution
)


class HotspotEffectivenessTestCase(TestCase):
    """Test hotspot effectiveness calculations"""

    def setUp(self):
        """Set up test data with hotspot and non-hotspot accidents"""
        # Create a cluster
        self.cluster = AccidentCluster.objects.create(
            cluster_id=1,
            center_latitude=Decimal('8.9475'),
            center_longitude=Decimal('125.5406'),
            accident_count=10,
            total_casualties=15,
            severity_score=150.0,
            min_latitude=Decimal('8.9400'),
            max_latitude=Decimal('8.9550'),
            min_longitude=Decimal('125.5300'),
            max_longitude=Decimal('125.5500'),
            radius=0.05
        )

        # Create hotspot accidents (in cluster)
        for i in range(10):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475') + Decimal(str(i * 0.001)),
                longitude=Decimal('125.5406') + Decimal(str(i * 0.001)),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Vehicular Accident',
                victim_killed=(i % 3 == 0),
                victim_injured=(i % 2 == 0),
                victim_count=i % 3 + 1,
                cluster_id=1,
                is_hotspot=True
            )

        # Create non-hotspot accidents (scattered)
        for i in range(5):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Cabadbaran City',
                barangay=f'Barangay {i}',
                latitude=Decimal('9.1200') + Decimal(str(i * 0.01)),
                longitude=Decimal('125.5300') + Decimal(str(i * 0.01)),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Motorcycle Accident',
                victim_injured=True,
                victim_count=1,
                is_hotspot=False
            )

    def test_hotspot_effectiveness_basic(self):
        """Test basic hotspot effectiveness calculation"""
        result = calculate_hotspot_effectiveness()

        self.assertIsInstance(result, dict)
        self.assertIn('hotspot_percentage', result)
        self.assertIn('hotspot_accident_percentage', result)
        self.assertIn('effectiveness_ratio', result)

    def test_hotspot_percentage_calculation(self):
        """Test that hotspot percentage is correctly calculated"""
        result = calculate_hotspot_effectiveness()

        # 10 hotspot accidents out of 15 total = 66.67%
        expected_percentage = (10 / 15) * 100
        self.assertAlmostEqual(
            result['hotspot_accident_percentage'],
            expected_percentage,
            delta=0.1
        )

    def test_effectiveness_ratio(self):
        """Test effectiveness ratio calculation"""
        result = calculate_hotspot_effectiveness()

        # Effectiveness ratio should be > 1 if hotspots are effective
        self.assertGreater(result['effectiveness_ratio'], 0)


class SpatialConcentrationTestCase(TestCase):
    """Test spatial concentration metrics (Gini coefficient)"""

    def setUp(self):
        """Set up test data with concentrated and dispersed accidents"""
        # Concentrated cluster (same location)
        for i in range(10):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay='Libertad',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Vehicular Accident'
            )

        # Dispersed accidents
        for i in range(5):
            Accident.objects.create(
                province='Agusan del Sur',
                municipal=f'Municipality {i}',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.5000') + Decimal(str(i * 0.1)),
                longitude=Decimal('125.5000') + Decimal(str(i * 0.1)),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Motorcycle Accident'
            )

    def test_spatial_concentration_calculation(self):
        """Test spatial concentration calculation"""
        result = calculate_spatial_concentration()

        self.assertIsInstance(result, dict)
        self.assertIn('gini_coefficient', result)
        self.assertIn('concentration_level', result)

    def test_gini_coefficient_range(self):
        """Test that Gini coefficient is between 0 and 1"""
        result = calculate_spatial_concentration()

        gini = result['gini_coefficient']
        self.assertGreaterEqual(gini, 0.0)
        self.assertLessEqual(gini, 1.0)

    def test_concentration_level_classification(self):
        """Test concentration level classification"""
        result = calculate_spatial_concentration()

        valid_levels = ['low', 'medium', 'high', 'very_high']
        self.assertIn(result['concentration_level'], valid_levels)


class TemporalPatternTestCase(TestCase):
    """Test temporal pattern analysis"""

    def setUp(self):
        """Set up test data with temporal patterns"""
        # Create accidents at different times and days
        for day in range(7):
            for hour in range(24):
                if hour in [7, 8, 17, 18]:  # Rush hours
                    Accident.objects.create(
                        province='Agusan del Norte',
                        municipal='Butuan City',
                        barangay='Test',
                        latitude=Decimal('8.9475'),
                        longitude=Decimal('125.5406'),
                        date_committed=date(2024, 1, 1) + timedelta(days=day),
                        time_committed=time(hour, 0),
                        incident_type='Vehicular Accident'
                    )

    def test_hourly_distribution(self):
        """Test hourly accident distribution"""
        result = analyze_temporal_patterns()

        self.assertIn('hourly_distribution', result)
        hourly = result['hourly_distribution']

        # Check that rush hours have more accidents
        rush_hour_counts = [hourly.get(7, 0), hourly.get(8, 0),
                            hourly.get(17, 0), hourly.get(18, 0)]

        for count in rush_hour_counts:
            self.assertGreater(count, 0)

    def test_daily_distribution(self):
        """Test daily accident distribution"""
        result = analyze_temporal_patterns()

        self.assertIn('daily_distribution', result)
        daily = result['daily_distribution']

        # All days should have accidents
        self.assertEqual(len(daily), 7)

    def test_monthly_distribution(self):
        """Test monthly accident distribution"""
        result = analyze_temporal_patterns()

        self.assertIn('monthly_distribution', result)
        monthly = result['monthly_distribution']

        # At least January should have data
        self.assertIn(1, monthly)

    def test_peak_hours_identification(self):
        """Test identification of peak hours"""
        result = analyze_temporal_patterns()

        if 'peak_hours' in result:
            peak_hours = result['peak_hours']

            # Peak hours should include rush hours
            expected_peaks = {7, 8, 17, 18}
            self.assertTrue(any(h in expected_peaks for h in peak_hours))


class SeverityMetricsTestCase(TestCase):
    """Test severity analysis calculations"""

    def setUp(self):
        """Set up test data with different severity levels"""
        # Fatal accidents
        for i in range(5):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Fatal Accident',
                victim_killed=True,
                victim_count=1
            )

        # Injury accidents
        for i in range(10):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Injury Accident',
                victim_injured=True,
                victim_count=2
            )

        # Property damage only
        for i in range(15):
            Accident.objects.create(
                province='Agusan del Norte',
                municipal='Butuan City',
                barangay=f'Barangay {i}',
                latitude=Decimal('8.9475'),
                longitude=Decimal('125.5406'),
                date_committed=date(2024, 1, 1) + timedelta(days=i),
                incident_type='Property Damage',
                victim_unharmed=True,
                victim_count=0
            )

    def test_severity_distribution(self):
        """Test severity distribution calculation"""
        result = calculate_severity_metrics()

        self.assertIn('fatal_count', result)
        self.assertIn('injury_count', result)
        self.assertIn('pdo_count', result)  # Property damage only

        self.assertEqual(result['fatal_count'], 5)
        self.assertEqual(result['injury_count'], 10)

    def test_severity_percentages(self):
        """Test severity percentage calculations"""
        result = calculate_severity_metrics()

        if 'fatal_percentage' in result:
            # 5 fatal out of 30 total = 16.67%
            expected = (5 / 30) * 100
            self.assertAlmostEqual(
                result['fatal_percentage'],
                expected,
                delta=0.1
            )

    def test_average_severity_score(self):
        """Test average severity score calculation"""
        result = calculate_severity_metrics()

        if 'average_severity' in result:
            # Should be positive
            self.assertGreater(result['average_severity'], 0)


class GeographicDistributionTestCase(TestCase):
    """Test geographic distribution analysis"""

    def setUp(self):
        """Set up test data across different provinces"""
        provinces = [
            ('Agusan del Norte', 'Butuan City', 20),
            ('Agusan del Sur', 'San Francisco', 10),
            ('Surigao del Norte', 'Surigao City', 15),
            ('Surigao del Sur', 'Tandag City', 5)
        ]

        for province, municipal, count in provinces:
            for i in range(count):
                Accident.objects.create(
                    province=province,
                    municipal=municipal,
                    barangay=f'Barangay {i}',
                    latitude=Decimal('8.9475') + Decimal(str(i * 0.001)),
                    longitude=Decimal('125.5406') + Decimal(str(i * 0.001)),
                    date_committed=date(2024, 1, 1) + timedelta(days=i),
                    incident_type='Accident'
                )

    def test_province_distribution(self):
        """Test distribution by province"""
        result = analyze_geographic_distribution()

        self.assertIn('province_distribution', result)
        provinces = result['province_distribution']

        # Should have all 4 provinces
        self.assertEqual(len(provinces), 4)

        # Agusan del Norte should have the most (20)
        self.assertEqual(provinces['Agusan del Norte'], 20)

    def test_municipal_distribution(self):
        """Test distribution by municipality"""
        result = analyze_geographic_distribution()

        self.assertIn('municipal_distribution', result)
        municipalities = result['municipal_distribution']

        # Should have all 4 municipalities
        self.assertEqual(len(municipalities), 4)

    def test_top_locations(self):
        """Test identification of top accident locations"""
        result = analyze_geographic_distribution()

        if 'top_provinces' in result:
            top = result['top_provinces']

            # Agusan del Norte should be top (20 accidents)
            self.assertEqual(top[0]['province'], 'Agusan del Norte')
            self.assertEqual(top[0]['count'], 20)


class DataValidationTestCase(TestCase):
    """Test data validation and integrity"""

    def test_coordinate_bounds_validation(self):
        """Test that coordinates are within valid Philippine bounds"""
        # Philippines approximate bounds:
        # Latitude: 4.5° to 21° N
        # Longitude: 116° to 127° E

        accident = Accident.objects.create(
            province='Agusan del Norte',
            municipal='Butuan City',
            barangay='Test',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=date(2024, 1, 1),
            incident_type='Test'
        )

        # Check coordinates are in valid range
        self.assertGreaterEqual(accident.latitude, Decimal('4.5'))
        self.assertLessEqual(accident.latitude, Decimal('21.0'))
        self.assertGreaterEqual(accident.longitude, Decimal('116.0'))
        self.assertLessEqual(accident.longitude, Decimal('127.0'))

    def test_casualty_count_consistency(self):
        """Test that casualty counts are consistent with flags"""
        accident = Accident.objects.create(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=date(2024, 1, 1),
            incident_type='Test',
            victim_killed=True,
            victim_count=1
        )

        # If victim_killed is True, victim_count should be > 0
        if accident.victim_killed:
            self.assertGreater(accident.victim_count, 0)

    def test_date_validation(self):
        """Test that accident dates are not in the future"""
        from django.utils import timezone

        accident = Accident.objects.create(
            province='Test',
            municipal='Test',
            barangay='Test',
            latitude=Decimal('8.9475'),
            longitude=Decimal('125.5406'),
            date_committed=date(2024, 1, 1),
            incident_type='Test'
        )

        # Date should not be in future
        # (This test would need actual validator in model)
        self.assertLessEqual(
            accident.date_committed,
            timezone.now().date() + timedelta(days=1)
        )


# Run with: python manage.py test accidents.tests_analytics -v 2
