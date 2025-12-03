from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from accidents.models import ClusterValidationMetrics


@login_required
def cluster_validation_metrics(request):
    """
    API endpoint to retrieve the latest clustering validation metrics

    Returns JSON with:
    - Latest validation metrics (Silhouette, Davies-Bouldin, Calinski-Harabasz)
    - Cluster quality assessment
    - Clustering metadata (date, num clusters, total accidents)
    """
    try:
        # Get the most recent validation metrics
        latest_metrics = ClusterValidationMetrics.objects.first()

        if not latest_metrics:
            return JsonResponse({
                'success': False,
                'error': 'No validation metrics available. Please run clustering first.'
            }, status=404)

        # Build response
        response_data = {
            'success': True,
            'metrics': {
                'silhouette_score': latest_metrics.silhouette_score,
                'davies_bouldin_index': latest_metrics.davies_bouldin_index,
                'calinski_harabasz_score': latest_metrics.calinski_harabasz_score
            },
            'quality': {
                'overall': latest_metrics.interpret_quality(),
                'rating': latest_metrics.cluster_quality or latest_metrics.interpret_quality()
            },
            'metadata': {
                'clustering_date': latest_metrics.clustering_date.strftime('%Y-%m-%d %H:%M'),
                'num_clusters': latest_metrics.num_clusters,
                'total_accidents': latest_metrics.total_accidents,
                'linkage_method': latest_metrics.linkage_method,
                'distance_threshold': float(latest_metrics.distance_threshold)
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
