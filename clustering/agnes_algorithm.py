"""
AGNES (Agglomerative Nesting) Clustering Algorithm
for Traffic Accident Hotspot Detection
"""

import numpy as np
from scipy.spatial.distance import cdist
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class AGNESClusterer:
    """
    AGNES clustering implementation for accident hotspot detection
    """
    
    def __init__(self, linkage_method='complete', distance_threshold=0.05, 
                 min_cluster_size=3, severity_weights=None):
        """
        Initialize AGNES clusterer
        
        Args:
            linkage_method (str): Linkage method ('complete', 'single', 'average')
            distance_threshold (float): Maximum distance to merge clusters (~0.05 = 5km)
            min_cluster_size (int): Minimum accidents to form a hotspot
            severity_weights (dict): Weights for severity calculation
        """
        self.linkage_method = linkage_method
        self.distance_threshold = distance_threshold
        self.min_cluster_size = min_cluster_size
        
        # Default severity weights
        self.severity_weights = severity_weights or {
            'killed': 10,
            'injured': 5,
            'property_damage': 1
        }
        
        self.labels_ = None
        self.n_clusters_ = 0
        self.linkage_matrix_ = None
        
    def fit(self, accidents_data):
        """
        Perform AGNES clustering on accident data
        
        Args:
            accidents_data (list): List of accident dictionaries with lat, lng, etc.
            
        Returns:
            dict: Clustering results
        """
        logger.info(f"Starting AGNES clustering with {len(accidents_data)} accidents")
        
        if len(accidents_data) < self.min_cluster_size:
            logger.warning("Not enough accidents for clustering")
            return {
                'success': False,
                'message': 'Not enough accidents for clustering',
                'clusters': []
            }
        
        try:
            # Extract coordinates
            coordinates = np.array([
                [accident['latitude'], accident['longitude']]
                for accident in accidents_data
            ])
            
            # Perform hierarchical clustering
            logger.info(f"Performing {self.linkage_method} linkage clustering")
            self.linkage_matrix_ = linkage(
                coordinates, 
                method=self.linkage_method,
                metric='euclidean'
            )
            
            # Form flat clusters
            self.labels_ = fcluster(
                self.linkage_matrix_,
                t=self.distance_threshold,
                criterion='distance'
            )
            
            # Get unique clusters
            unique_labels = np.unique(self.labels_)
            self.n_clusters_ = len(unique_labels)
            
            logger.info(f"Found {self.n_clusters_} initial clusters")
            
            # Build cluster information
            clusters = self._build_clusters(accidents_data, coordinates)
            
            # Filter out small clusters
            valid_clusters = [
                c for c in clusters 
                if c['accident_count'] >= self.min_cluster_size
            ]
            
            logger.info(f"After filtering: {len(valid_clusters)} valid hotspots")
            
            return {
                'success': True,
                'total_accidents': len(accidents_data),
                'clusters_found': len(valid_clusters),
                'clusters': valid_clusters
            }
            
        except Exception as e:
            logger.error(f"Clustering failed: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'clusters': []
            }
    
    def _build_clusters(self, accidents_data, coordinates):
        """
        Build detailed cluster information
        
        Args:
            accidents_data (list): Original accident data
            coordinates (np.array): Coordinate array
            
        Returns:
            list: List of cluster dictionaries
        """
        clusters = []
        
        for cluster_id in np.unique(self.labels_):
            # Get accidents in this cluster
            mask = self.labels_ == cluster_id
            cluster_accidents = [
                accidents_data[i] 
                for i, in_cluster in enumerate(mask) 
                if in_cluster
            ]
            cluster_coords = coordinates[mask]
            
            # Skip if too small
            if len(cluster_accidents) < self.min_cluster_size:
                continue
            
            # Calculate cluster center (centroid)
            center_lat = np.mean(cluster_coords[:, 0])
            center_lng = np.mean(cluster_coords[:, 1])
            
            # Calculate bounds
            min_lat = np.min(cluster_coords[:, 0])
            max_lat = np.max(cluster_coords[:, 0])
            min_lng = np.min(cluster_coords[:, 1])
            max_lng = np.max(cluster_coords[:, 1])
            
            # Calculate statistics
            total_casualties = sum(
                acc.get('victim_count', 0) 
                for acc in cluster_accidents
            )
            
            killed_count = sum(
                1 for acc in cluster_accidents 
                if acc.get('victim_killed', False)
            )
            
            injured_count = sum(
                1 for acc in cluster_accidents 
                if acc.get('victim_injured', False)
            )
            
            # Calculate severity score
            severity_score = self._calculate_severity(
                len(cluster_accidents),
                killed_count,
                injured_count
            )
            
            # Get primary location (most common municipal)
            municipalities = [
                acc.get('municipal', 'Unknown') 
                for acc in cluster_accidents
            ]
            primary_location = max(set(municipalities), key=municipalities.count)
            
            # Get unique municipalities
            unique_municipalities = list(set(municipalities))
            
            # Get date range
            dates = [
                acc.get('date_committed') 
                for acc in cluster_accidents 
                if acc.get('date_committed')
            ]
            date_range_start = min(dates) if dates else None
            date_range_end = max(dates) if dates else None
            
            clusters.append({
                'cluster_id': int(cluster_id),
                'center_latitude': float(center_lat),
                'center_longitude': float(center_lng),
                'accident_count': len(cluster_accidents),
                'total_casualties': int(total_casualties),
                'killed_count': int(killed_count),
                'injured_count': int(injured_count),
                'severity_score': float(severity_score),
                'primary_location': primary_location,
                'municipalities': unique_municipalities,
                'min_latitude': float(min_lat),
                'max_latitude': float(max_lat),
                'min_longitude': float(min_lng),
                'max_longitude': float(max_lng),
                'date_range_start': date_range_start,
                'date_range_end': date_range_end,
                'accident_ids': [acc['id'] for acc in cluster_accidents]
            })
        
        # Sort by severity score (descending)
        clusters.sort(key=lambda x: x['severity_score'], reverse=True)
        
        return clusters
    
    def _calculate_severity(self, accident_count, killed_count, injured_count):
        """
        Calculate severity score for a cluster
        
        Args:
            accident_count (int): Number of accidents
            killed_count (int): Number of fatal accidents
            injured_count (int): Number of injury accidents
            
        Returns:
            float: Severity score (0-100)
        """
        # Base score from accident frequency
        frequency_score = min(accident_count * 2, 40)  # Max 40 points
        
        # Casualty severity score
        casualty_score = (
            killed_count * self.severity_weights['killed'] +
            injured_count * self.severity_weights['injured']
        )
        casualty_score = min(casualty_score, 60)  # Max 60 points
        
        # Total severity (0-100 scale)
        total_score = frequency_score + casualty_score
        
        return min(total_score, 100.0)
    
    def predict(self, new_coordinates):
        """
        Predict cluster assignment for new coordinates
        
        Args:
            new_coordinates (array): Array of [lat, lng] coordinates
            
        Returns:
            array: Cluster labels
        """
        if self.labels_ is None:
            raise ValueError("Model not fitted yet")
        
        # For new predictions, assign to nearest existing cluster
        # This is a simplified version
        return np.zeros(len(new_coordinates), dtype=int)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    
    Returns:
        float: Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def calculate_cluster_radius(coordinates):
    """
    Calculate the radius of a cluster in kilometers
    
    Args:
        coordinates (array): Array of [lat, lng] coordinates
        
    Returns:
        float: Radius in kilometers
    """
    if len(coordinates) < 2:
        return 0.0
    
    # Calculate center
    center_lat = np.mean(coordinates[:, 0])
    center_lng = np.mean(coordinates[:, 1])
    
    # Calculate distances from center
    distances = [
        haversine_distance(center_lat, center_lng, lat, lng)
        for lat, lng in coordinates
    ]
    
    # Return max distance (radius)
    return max(distances)