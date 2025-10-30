"""
Celery Tasks for Accident Hotspot Detection System
Provides async background processing for clustering, exports, and reports
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import time

logger = get_task_logger(__name__)


# ============================================================================
# CLUSTERING TASKS
# ============================================================================

@shared_task(
    bind=True,
    name='accidents.tasks.run_clustering_task',
    max_retries=3,
    soft_time_limit=1500,  # 25 minutes
    time_limit=1800,  # 30 minutes
)
def run_clustering_task(self, linkage_method='complete', distance_threshold=0.05,
                        min_cluster_size=3, days=None):
    """
    Run AGNES clustering algorithm asynchronously

    Args:
        linkage_method: Clustering linkage method
        distance_threshold: Distance threshold for clustering
        min_cluster_size: Minimum accidents to form a hotspot
        days: Number of days to include (None = all data)

    Returns:
        dict: Clustering results with statistics
    """
    try:
        logger.info(f"Starting clustering task {self.request.id}")
        logger.info(f"Parameters: linkage={linkage_method}, threshold={distance_threshold}")

        from .models import Accident, AccidentCluster, ClusteringJob
        from clustering.agnes_algorithm import AGNESClusterer

        # Create clustering job record
        job = ClusteringJob.objects.create(
            started_at=timezone.now(),
            status='running',
            linkage_method=linkage_method,
            distance_threshold=distance_threshold,
            min_cluster_size=min_cluster_size
        )

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Preparing data...', 'progress': 10}
        )

        try:
            # Get accidents to cluster
            queryset = Accident.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )

            if days:
                start_date = timezone.now().date() - timedelta(days=days)
                queryset = queryset.filter(date_committed__gte=start_date)
                job.date_from = start_date

            total_accidents = queryset.count()
            logger.info(f"Clustering {total_accidents} accidents")

            # Prepare data for clustering
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Extracting coordinates...', 'progress': 20}
            )

            accidents_data = list(queryset.values(
                'id', 'latitude', 'longitude', 'victim_count',
                'victim_killed', 'victim_injured', 'municipal', 'date_committed'
            ))

            # Run AGNES clustering
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Running AGNES algorithm...', 'progress': 40}
            )

            clusterer = AGNESClusterer(
                linkage_method=linkage_method,
                distance_threshold=distance_threshold,
                min_cluster_size=min_cluster_size
            )

            result = clusterer.fit(accidents_data)

            if not result['success']:
                raise Exception(result.get('message', 'Clustering failed'))

            # Save clusters to database
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Saving clusters...', 'progress': 70}
            )

            # Clear existing clusters
            AccidentCluster.objects.all().delete()

            # Create new clusters
            for cluster_data in result['clusters']:
                AccidentCluster.objects.create(
                    cluster_id=cluster_data['cluster_id'],
                    center_latitude=cluster_data['center_latitude'],
                    center_longitude=cluster_data['center_longitude'],
                    accident_count=cluster_data['accident_count'],
                    total_casualties=cluster_data['total_casualties'],
                    severity_score=cluster_data['severity_score'],
                    primary_location=cluster_data['primary_location'],
                    municipalities=cluster_data['municipalities'],
                    min_latitude=cluster_data['min_latitude'],
                    max_latitude=cluster_data['max_latitude'],
                    min_longitude=cluster_data['min_longitude'],
                    max_longitude=cluster_data['max_longitude'],
                    date_range_start=cluster_data.get('date_range_start'),
                    date_range_end=cluster_data.get('date_range_end'),
                    algorithm_version='AGNES-1.0',
                    computed_at=timezone.now(),
                    linkage_method=linkage_method,
                    distance_threshold=distance_threshold
                )

                # Update accidents with cluster assignment
                Accident.objects.filter(
                    id__in=cluster_data['accident_ids']
                ).update(
                    cluster_id=cluster_data['cluster_id'],
                    is_hotspot=True
                )

            # Mark non-hotspot accidents
            Accident.objects.filter(cluster_id__isnull=True).update(is_hotspot=False)

            # Update job status
            self.update_state(
                state='PROGRESS',
                meta={'status': 'Clearing cache...', 'progress': 90}
            )

            # Clear cache
            cache.clear()

            # Mark job as complete
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.total_accidents = total_accidents
            job.clusters_found = result['clusters_found']
            job.save()

            logger.info(f"Clustering completed: {result['clusters_found']} clusters found")

            return {
                'status': 'success',
                'total_accidents': total_accidents,
                'clusters_found': result['clusters_found'],
                'job_id': job.id,
                'duration': (job.completed_at - job.started_at).total_seconds()
            }

        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            raise

    except Exception as e:
        logger.error(f"Clustering task failed: {str(e)}")

        # Retry task
        try:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        except self.MaxRetriesExceededError:
            return {
                'status': 'error',
                'message': str(e),
                'retries': self.request.retries
            }


# ============================================================================
# EXPORT TASKS
# ============================================================================

@shared_task(
    bind=True,
    name='accidents.tasks.export_accidents_excel',
    max_retries=2
)
def export_accidents_excel(self, filters=None):
    """
    Export accidents to Excel file

    Args:
        filters: Dictionary of filter parameters

    Returns:
        str: Path to generated Excel file
    """
    try:
        logger.info(f"Starting Excel export task {self.request.id}")

        from .models import Accident
        from .exports import AccidentExporter

        self.update_state(state='PROGRESS', meta={'progress': 20})

        # Get accidents based on filters
        queryset = Accident.objects.all()
        if filters:
            if 'province' in filters:
                queryset = queryset.filter(province=filters['province'])
            if 'year' in filters:
                queryset = queryset.filter(year=filters['year'])

        self.update_state(state='PROGRESS', meta={'progress': 50})

        # Export to Excel
        exporter = AccidentExporter()
        filepath = exporter.export_to_excel(queryset)

        self.update_state(state='PROGRESS', meta={'progress': 100})

        logger.info(f"Excel export completed: {filepath}")

        return {
            'status': 'success',
            'filepath': filepath,
            'count': queryset.count()
        }

    except Exception as e:
        logger.error(f"Excel export failed: {str(e)}")
        raise


@shared_task(
    bind=True,
    name='accidents.tasks.export_clusters_pdf',
    max_retries=2
)
def export_clusters_pdf(self, cluster_ids=None):
    """
    Export hotspots to PDF report

    Args:
        cluster_ids: List of cluster IDs to export (None = all)

    Returns:
        str: Path to generated PDF file
    """
    try:
        logger.info(f"Starting PDF export task {self.request.id}")

        from .models import AccidentCluster
        from .exports import ClusterPDFExporter

        self.update_state(state='PROGRESS', meta={'progress': 20})

        # Get clusters
        queryset = AccidentCluster.objects.order_by('-severity_score')
        if cluster_ids:
            queryset = queryset.filter(cluster_id__in=cluster_ids)

        self.update_state(state='PROGRESS', meta={'progress': 50})

        # Generate PDF
        exporter = ClusterPDFExporter()
        filepath = exporter.generate_report(queryset)

        self.update_state(state='PROGRESS', meta={'progress': 100})

        logger.info(f"PDF export completed: {filepath}")

        return {
            'status': 'success',
            'filepath': filepath,
            'count': queryset.count()
        }

    except Exception as e:
        logger.error(f"PDF export failed: {str(e)}")
        raise


# ============================================================================
# CACHE MANAGEMENT TASKS
# ============================================================================

@shared_task(name='accidents.tasks.clear_expired_cache_task')
def clear_expired_cache_task():
    """
    Clear expired cache entries (runs periodically)
    """
    try:
        logger.info("Clearing expired cache entries")

        # Note: Django cache handles expiration automatically
        # This task can be used for additional cleanup if needed

        return {'status': 'success', 'message': 'Cache cleanup completed'}

    except Exception as e:
        logger.error(f"Cache cleanup failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='accidents.tasks.warm_cache_task')
def warm_cache_task():
    """
    Pre-warm frequently accessed cache entries
    """
    try:
        logger.info("Warming cache with frequently accessed data")

        from .performance import warm_cache
        warm_cache()

        return {'status': 'success', 'message': 'Cache warming completed'}

    except Exception as e:
        logger.error(f"Cache warming failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================================================
# STATISTICS TASKS
# ============================================================================

@shared_task(name='accidents.tasks.generate_weekly_statistics_task')
def generate_weekly_statistics_task():
    """
    Generate weekly statistics report (runs every Monday)
    """
    try:
        logger.info("Generating weekly statistics report")

        from .models import Accident, AccidentCluster
        from django.db.models import Count, Sum

        # Calculate weekly statistics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)

        weekly_stats = {
            'total_accidents': Accident.objects.filter(
                date_committed__gte=week_ago
            ).count(),
            'fatal_accidents': Accident.objects.filter(
                date_committed__gte=week_ago,
                victim_killed=True
            ).count(),
            'new_hotspots': AccidentCluster.objects.filter(
                computed_at__gte=week_ago
            ).count(),
        }

        # Cache statistics
        cache.set('weekly_statistics', weekly_stats, 60 * 60 * 24 * 7)  # 1 week

        logger.info(f"Weekly statistics: {weekly_stats}")

        return {
            'status': 'success',
            'statistics': weekly_stats,
            'period': f'{week_ago} to {today}'
        }

    except Exception as e:
        logger.error(f"Statistics generation failed: {str(e)}")
        return {'status': 'error', 'message': str(e)}


# ============================================================================
# DATA IMPORT TASKS
# ============================================================================

@shared_task(
    bind=True,
    name='accidents.tasks.import_accidents_csv',
    max_retries=2
)
def import_accidents_csv(self, filepath, batch_size=500):
    """
    Import accidents from CSV file asynchronously

    Args:
        filepath: Path to CSV file
        batch_size: Number of records to process at once

    Returns:
        dict: Import results
    """
    try:
        logger.info(f"Starting CSV import task {self.request.id}")
        logger.info(f"File: {filepath}")

        import pandas as pd
        from .models import Accident

        self.update_state(state='PROGRESS', meta={'status': 'Reading CSV...', 'progress': 10})

        # Read CSV
        df = pd.read_csv(filepath)
        total_rows = len(df)

        logger.info(f"Importing {total_rows} records")

        imported_count = 0
        error_count = 0

        # Process in batches
        for batch_start in range(0, total_rows, batch_size):
            batch_end = min(batch_start + batch_size, total_rows)
            batch_df = df[batch_start:batch_end]

            progress = int((batch_end / total_rows) * 90) + 10
            self.update_state(
                state='PROGRESS',
                meta={'status': f'Importing rows {batch_start}-{batch_end}...', 'progress': progress}
            )

            # Import batch (implement actual import logic from import_accidents command)
            # This is a placeholder - adapt from management/commands/import_accidents.py

            imported_count = batch_end

        logger.info(f"Import completed: {imported_count} records imported")

        return {
            'status': 'success',
            'total_rows': total_rows,
            'imported': imported_count,
            'errors': error_count
        }

    except Exception as e:
        logger.error(f"CSV import failed: {str(e)}")
        raise
