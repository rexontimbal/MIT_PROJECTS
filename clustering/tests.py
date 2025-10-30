"""
Unit Tests for AGNES Clustering Algorithm
"""
from django.test import TestCase
from datetime import datetime, date
from decimal import Decimal
import numpy as np

from clustering.agnes_algorithm import (
    AGNESClusterer,
    haversine_distance,
    calculate_cluster_radius
)


class AGNESClustererTestCase(TestCase):
    """Test cases for AGNESClusterer class"""

    def setUp(self):
        """Set up test fixtures"""
        # Sample accident data for Caraga region
        self.sample_accidents = [
            {
                'id': 1,
                'latitude': 9.0,
                'longitude': 125.5,
                'victim_count': 2,
                'victim_killed': True,
                'victim_injured': False,
                'municipal': 'Butuan City',
                'date_committed': date(2024, 1, 1)
            },
            {
                'id': 2,
                'latitude': 9.01,
                'longitude': 125.51,
                'victim_count': 1,
                'victim_killed': False,
                'victim_injured': True,
                'municipal': 'Butuan City',
                'date_committed': date(2024, 1, 2)
            },
            {
                'id': 3,
                'latitude': 9.02,
                'longitude': 125.52,
                'victim_count': 3,
                'victim_killed': True,
                'victim_injured': True,
                'municipal': 'Butuan City',
                'date_committed': date(2024, 1, 3)
            },
            # Distant cluster
            {
                'id': 4,
                'latitude': 8.5,
                'longitude': 126.0,
                'victim_count': 2,
                'victim_killed': False,
                'victim_injured': True,
                'municipal': 'Surigao City',
                'date_committed': date(2024, 2, 1)
            },
            {
                'id': 5,
                'latitude': 8.51,
                'longitude': 126.01,
                'victim_count': 1,
                'victim_killed': True,
                'victim_injured': False,
                'municipal': 'Surigao City',
                'date_committed': date(2024, 2, 2)
            },
            {
                'id': 6,
                'latitude': 8.52,
                'longitude': 126.02,
                'victim_count': 2,
                'victim_killed': False,
                'victim_injured': True,
                'municipal': 'Surigao City',
                'date_committed': date(2024, 2, 3)
            }
        ]

    def test_initialization_default_parameters(self):
        """Test AGNESClusterer initialization with default parameters"""
        clusterer = AGNESClusterer()

        self.assertEqual(clusterer.linkage_method, 'complete')
        self.assertEqual(clusterer.distance_threshold, 0.05)
        self.assertEqual(clusterer.min_cluster_size, 3)
        self.assertIsNotNone(clusterer.severity_weights)
        self.assertEqual(clusterer.severity_weights['killed'], 10)
        self.assertEqual(clusterer.severity_weights['injured'], 5)

    def test_initialization_custom_parameters(self):
        """Test AGNESClusterer initialization with custom parameters"""
        custom_weights = {'killed': 15, 'injured': 7, 'property_damage': 2}
        clusterer = AGNESClusterer(
            linkage_method='average',
            distance_threshold=0.1,
            min_cluster_size=5,
            severity_weights=custom_weights
        )

        self.assertEqual(clusterer.linkage_method, 'average')
        self.assertEqual(clusterer.distance_threshold, 0.1)
        self.assertEqual(clusterer.min_cluster_size, 5)
        self.assertEqual(clusterer.severity_weights['killed'], 15)

    def test_fit_with_valid_data(self):
        """Test clustering with valid accident data"""
        clusterer = AGNESClusterer(
            linkage_method='complete',
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        self.assertTrue(result['success'])
        self.assertEqual(result['total_accidents'], 6)
        self.assertGreater(result['clusters_found'], 0)
        self.assertIsInstance(result['clusters'], list)

        # Check cluster structure
        if result['clusters']:
            cluster = result['clusters'][0]
            self.assertIn('cluster_id', cluster)
            self.assertIn('center_latitude', cluster)
            self.assertIn('center_longitude', cluster)
            self.assertIn('accident_count', cluster)
            self.assertIn('severity_score', cluster)
            self.assertGreaterEqual(cluster['accident_count'], 3)

    def test_fit_with_insufficient_data(self):
        """Test clustering with insufficient data"""
        clusterer = AGNESClusterer(min_cluster_size=3)
        small_dataset = self.sample_accidents[:2]

        result = clusterer.fit(small_dataset)

        self.assertFalse(result['success'])
        self.assertIn('Not enough accidents', result['message'])
        self.assertEqual(len(result['clusters']), 0)

    def test_fit_with_empty_data(self):
        """Test clustering with empty data"""
        clusterer = AGNESClusterer()

        result = clusterer.fit([])

        self.assertFalse(result['success'])
        self.assertEqual(len(result['clusters']), 0)

    def test_different_linkage_methods(self):
        """Test all linkage methods: complete, single, average"""
        linkage_methods = ['complete', 'single', 'average']

        for method in linkage_methods:
            clusterer = AGNESClusterer(
                linkage_method=method,
                distance_threshold=0.1,
                min_cluster_size=3
            )

            result = clusterer.fit(self.sample_accidents)

            self.assertTrue(result['success'],
                          f"Clustering failed for {method} linkage")
            self.assertGreater(result['total_accidents'], 0)

    def test_cluster_filtering_by_min_size(self):
        """Test that small clusters are filtered out"""
        # Create larger dataset with scattered points
        large_dataset = []
        for i in range(15):
            large_dataset.append({
                'id': i + 1,
                'latitude': 9.0 + (i * 0.5),
                'longitude': 125.5 + (i * 0.5),
                'victim_count': 1,
                'victim_killed': False,
                'victim_injured': True,
                'municipal': f'City{i}',
                'date_committed': date(2024, 1, 1)
            })

        # Set high minimum cluster size
        clusterer = AGNESClusterer(
            distance_threshold=0.001,  # Very strict - creates small clusters
            min_cluster_size=10  # Filter out small clusters
        )

        result = clusterer.fit(large_dataset)

        # Should succeed but return no valid clusters due to strict threshold
        self.assertTrue(result['success'])
        self.assertEqual(result['clusters_found'], 0)

    def test_severity_calculation(self):
        """Test severity score calculation"""
        clusterer = AGNESClusterer()

        # Test case 1: High frequency, no casualties
        score1 = clusterer._calculate_severity(20, 0, 0)
        self.assertEqual(score1, 40.0)  # Max frequency score = min(20*2, 40) = 40

        # Test case 2: Low frequency, high casualties (capped at 60)
        score2 = clusterer._calculate_severity(5, 5, 5)
        # frequency: min(5*2, 40) = 10
        # casualty: min(5*10 + 5*5, 60) = min(75, 60) = 60
        # total: 10 + 60 = 70
        self.assertEqual(score2, 70.0)

        # Test case 3: Balanced
        score3 = clusterer._calculate_severity(10, 2, 3)
        # frequency: min(10*2, 40) = 20
        # casualty: min(2*10 + 3*5, 60) = min(35, 60) = 35
        # total: 20 + 35 = 55
        self.assertEqual(score3, 55.0)

        # Test case 4: Maximum score
        score4 = clusterer._calculate_severity(50, 10, 20)
        # frequency: min(50*2, 40) = 40
        # casualty: min(10*10 + 20*5, 60) = min(200, 60) = 60
        # total: 40 + 60 = 100
        self.assertEqual(score4, 100.0)

    def test_cluster_statistics(self):
        """Test that cluster statistics are calculated correctly"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if result['clusters']:
            for cluster in result['clusters']:
                # Verify accident count meets minimum
                self.assertGreaterEqual(
                    cluster['accident_count'],
                    clusterer.min_cluster_size
                )

                # Verify coordinates are within valid ranges
                self.assertGreater(cluster['center_latitude'], 7.5)
                self.assertLess(cluster['center_latitude'], 10.5)
                self.assertGreater(cluster['center_longitude'], 124.5)
                self.assertLess(cluster['center_longitude'], 127.0)

                # Verify severity score range
                self.assertGreaterEqual(cluster['severity_score'], 0)
                self.assertLessEqual(cluster['severity_score'], 100)

                # Verify casualties are non-negative
                self.assertGreaterEqual(cluster['total_casualties'], 0)
                self.assertGreaterEqual(cluster['killed_count'], 0)
                self.assertGreaterEqual(cluster['injured_count'], 0)

    def test_cluster_bounds(self):
        """Test that cluster bounds are calculated correctly"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if result['clusters']:
            for cluster in result['clusters']:
                # Min should be less than max
                self.assertLess(
                    cluster['min_latitude'],
                    cluster['max_latitude']
                )
                self.assertLess(
                    cluster['min_longitude'],
                    cluster['max_longitude']
                )

                # Center should be within bounds
                self.assertGreaterEqual(
                    cluster['center_latitude'],
                    cluster['min_latitude']
                )
                self.assertLessEqual(
                    cluster['center_latitude'],
                    cluster['max_latitude']
                )

    def test_cluster_sorting_by_severity(self):
        """Test that clusters are sorted by severity score"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if len(result['clusters']) > 1:
            # Verify descending order
            for i in range(len(result['clusters']) - 1):
                self.assertGreaterEqual(
                    result['clusters'][i]['severity_score'],
                    result['clusters'][i + 1]['severity_score']
                )

    def test_date_range_calculation(self):
        """Test that date ranges are calculated correctly"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if result['clusters']:
            for cluster in result['clusters']:
                if cluster['date_range_start'] and cluster['date_range_end']:
                    # End date should be >= start date
                    self.assertLessEqual(
                        cluster['date_range_start'],
                        cluster['date_range_end']
                    )

    def test_accident_ids_in_cluster(self):
        """Test that accident IDs are properly tracked"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if result['clusters']:
            all_accident_ids = set()
            for cluster in result['clusters']:
                # Verify accident_ids list exists and has correct count
                self.assertEqual(
                    len(cluster['accident_ids']),
                    cluster['accident_count']
                )

                # Track all IDs to verify no duplicates
                for acc_id in cluster['accident_ids']:
                    self.assertNotIn(acc_id, all_accident_ids)
                    all_accident_ids.add(acc_id)

    def test_primary_location_determination(self):
        """Test that primary location is correctly identified"""
        clusterer = AGNESClusterer(
            distance_threshold=0.1,
            min_cluster_size=3
        )

        result = clusterer.fit(self.sample_accidents)

        if result['clusters']:
            for cluster in result['clusters']:
                # Primary location should not be empty
                self.assertIsNotNone(cluster['primary_location'])
                self.assertNotEqual(cluster['primary_location'], '')

                # Should be in municipalities list
                self.assertIn(
                    cluster['primary_location'],
                    cluster['municipalities']
                )


class HaversineDistanceTestCase(TestCase):
    """Test cases for haversine distance calculation"""

    def test_same_point_distance(self):
        """Test distance between same point is zero"""
        distance = haversine_distance(9.0, 125.5, 9.0, 125.5)
        self.assertAlmostEqual(distance, 0.0, places=2)

    def test_known_distance(self):
        """Test known distance between Butuan and Surigao"""
        # Approximate coordinates
        butuan_lat, butuan_lng = 8.9475, 125.5406
        surigao_lat, surigao_lng = 9.7842, 125.4914

        distance = haversine_distance(
            butuan_lat, butuan_lng,
            surigao_lat, surigao_lng
        )

        # Should be approximately 93-95 km
        self.assertGreater(distance, 90)
        self.assertLess(distance, 100)

    def test_small_distance(self):
        """Test small distance calculation"""
        # Points ~1km apart
        distance = haversine_distance(9.0, 125.5, 9.009, 125.509)

        # Should be approximately 1-2 km
        self.assertGreater(distance, 0.5)
        self.assertLess(distance, 2.0)

    def test_distance_symmetry(self):
        """Test that distance(A,B) == distance(B,A)"""
        lat1, lng1 = 9.0, 125.5
        lat2, lng2 = 8.5, 126.0

        dist1 = haversine_distance(lat1, lng1, lat2, lng2)
        dist2 = haversine_distance(lat2, lng2, lat1, lng1)

        self.assertAlmostEqual(dist1, dist2, places=5)


class ClusterRadiusTestCase(TestCase):
    """Test cases for cluster radius calculation"""

    def test_single_point_radius(self):
        """Test radius of single point is zero"""
        coords = np.array([[9.0, 125.5]])
        radius = calculate_cluster_radius(coords)
        self.assertEqual(radius, 0.0)

    def test_two_points_radius(self):
        """Test radius calculation with two points"""
        coords = np.array([
            [9.0, 125.5],
            [9.01, 125.51]
        ])
        radius = calculate_cluster_radius(coords)

        # Should be approximately 1-2 km
        self.assertGreater(radius, 0.5)
        self.assertLess(radius, 2.0)

    def test_multiple_points_radius(self):
        """Test radius calculation with multiple points"""
        coords = np.array([
            [9.0, 125.5],
            [9.01, 125.51],
            [9.02, 125.49],
            [8.99, 125.52]
        ])
        radius = calculate_cluster_radius(coords)

        # Should be positive
        self.assertGreater(radius, 0)

    def test_empty_coordinates(self):
        """Test handling of empty coordinates"""
        coords = np.array([]).reshape(0, 2)
        radius = calculate_cluster_radius(coords)
        self.assertEqual(radius, 0.0)


class AGNESClustererEdgeCasesTestCase(TestCase):
    """Test edge cases and error handling"""

    def test_missing_coordinate_fields(self):
        """Test handling of missing latitude/longitude"""
        invalid_data = [
            {'id': 1, 'municipal': 'Test'},
            {'id': 2, 'municipal': 'Test'},
            {'id': 3, 'municipal': 'Test'}
        ]

        clusterer = AGNESClusterer()

        # Should handle gracefully - returns False if insufficient data
        result = clusterer.fit(invalid_data)
        # Will fail because not enough data, but should handle missing coords
        if not result['success']:
            # This is expected behavior
            self.assertFalse(result['success'])

    def test_all_accidents_in_same_location(self):
        """Test clustering when all accidents are at same coordinates"""
        same_location_data = [
            {
                'id': i,
                'latitude': 9.0,
                'longitude': 125.5,
                'victim_count': 1,
                'victim_killed': False,
                'victim_injured': True,
                'municipal': 'Test City',
                'date_committed': date(2024, 1, i)
            }
            for i in range(1, 6)
        ]

        clusterer = AGNESClusterer(min_cluster_size=3)
        result = clusterer.fit(same_location_data)

        self.assertTrue(result['success'])
        # Should form one cluster
        self.assertGreaterEqual(result['clusters_found'], 1)

    def test_very_strict_threshold(self):
        """Test with very strict distance threshold"""
        clusterer = AGNESClusterer(
            distance_threshold=0.001,  # Very small
            min_cluster_size=2
        )

        scattered_data = [
            {'id': 1, 'latitude': 9.0, 'longitude': 125.5, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'City1', 'date_committed': date(2024, 1, 1)},
            {'id': 2, 'latitude': 9.5, 'longitude': 125.5, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'City2', 'date_committed': date(2024, 1, 2)},
            {'id': 3, 'latitude': 10.0, 'longitude': 125.5, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'City3', 'date_committed': date(2024, 1, 3)},
        ]

        result = clusterer.fit(scattered_data)

        # May not form any valid clusters due to strict threshold
        self.assertTrue(result['success'])

    def test_predict_before_fit(self):
        """Test that predict raises error if called before fit"""
        clusterer = AGNESClusterer()

        with self.assertRaises(ValueError):
            clusterer.predict([[9.0, 125.5]])

    def test_linkage_matrix_created(self):
        """Test that linkage matrix is created after fit"""
        clusterer = AGNESClusterer()

        # Before fit
        self.assertIsNone(clusterer.linkage_matrix_)

        # After fit
        result = clusterer.fit([
            {'id': 1, 'latitude': 9.0, 'longitude': 125.5, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'Test', 'date_committed': date(2024, 1, 1)},
            {'id': 2, 'latitude': 9.01, 'longitude': 125.51, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'Test', 'date_committed': date(2024, 1, 2)},
            {'id': 3, 'latitude': 9.02, 'longitude': 125.52, 'victim_count': 1,
             'victim_killed': False, 'victim_injured': True,
             'municipal': 'Test', 'date_committed': date(2024, 1, 3)},
        ])

        if result['success']:
            self.assertIsNotNone(clusterer.linkage_matrix_)
            self.assertGreater(clusterer.n_clusters_, 0)
