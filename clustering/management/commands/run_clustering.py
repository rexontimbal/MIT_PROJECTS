from django.core.management.base import BaseCommand
from django.utils import timezone
from accidents.models import Accident, AccidentCluster, ClusteringJob
from clustering.agnes_algorithm import AGNESClusterer
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Run AGNES clustering to detect accident hotspots'

    def add_arguments(self, parser):
        parser.add_argument(
            '--linkage',
            type=str,
            default='complete',
            help='Linkage method (complete, single, average)'
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.05,
            help='Distance threshold in decimal degrees (~0.05 = 5km)'
        )
        parser.add_argument(
            '--min-size',
            type=int,
            default=3,
            help='Minimum cluster size'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Only cluster accidents from last N days'
        )

    def handle(self, *args, **options):
        linkage_method = options['linkage']
        distance_threshold = options['threshold']
        min_cluster_size = options['min_size']
        days = options['days']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('AGNES CLUSTERING - Accident Hotspot Detection'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        # Create clustering job record
        date_from = None
        date_to = timezone.now().date()
        
        if days:
            date_from = date_to - timedelta(days=days)
        
        job = ClusteringJob.objects.create(
            linkage_method=linkage_method,
            distance_threshold=distance_threshold,
            min_cluster_size=min_cluster_size,
            date_from=date_from or Accident.objects.earliest('date_committed').date_committed,
            date_to=date_to,
            status='running'
        )
        
        try:
            # Get accidents
            accidents_query = Accident.objects.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )
            
            if date_from:
                accidents_query = accidents_query.filter(
                    date_committed__gte=date_from
                )
            
            accidents = list(accidents_query.values(
                'id', 'latitude', 'longitude', 'victim_count',
                'victim_killed', 'victim_injured', 'municipal',
                'date_committed'
            ))
            
            self.stdout.write(f'\n📊 Total accidents to cluster: {len(accidents)}')
            
            if len(accidents) < min_cluster_size:
                raise ValueError(f'Not enough accidents (need at least {min_cluster_size})')
            
            # Run AGNES clustering
            self.stdout.write('\n🔬 Running AGNES algorithm...')
            clusterer = AGNESClusterer(
                linkage_method=linkage_method,
                distance_threshold=distance_threshold,
                min_cluster_size=min_cluster_size
            )
            
            result = clusterer.fit(accidents)
            
            if not result['success']:
                raise Exception(result.get('message', 'Clustering failed'))
            
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Clustering complete!'
            ))
            self.stdout.write(f'   - Clusters found: {result["clusters_found"]}')
            
            # Clear old clusters
            self.stdout.write('\n🗑️  Clearing old clusters...')
            AccidentCluster.objects.all().delete()
            Accident.objects.all().update(cluster_id=None, is_hotspot=False)
            
            # Save new clusters
            self.stdout.write('\n💾 Saving hotspots to database...')
            clusters_created = 0
            
            for cluster_data in result['clusters']:
                # Create cluster record
                cluster = AccidentCluster.objects.create(
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
                    date_range_start=cluster_data['date_range_start'],
                    date_range_end=cluster_data['date_range_end'],
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
                
                clusters_created += 1
                
                self.stdout.write(
                    f'   ✓ Hotspot #{cluster_data["cluster_id"]}: '
                    f'{cluster_data["accident_count"]} accidents at '
                    f'{cluster_data["primary_location"]} '
                    f'(severity: {cluster_data["severity_score"]:.1f})'
                )
            
            # Update job status
            job.status = 'completed'
            job.completed_at = timezone.now()
            job.total_accidents = len(accidents)
            job.clusters_found = clusters_created
            job.save()
            
            self.stdout.write(self.style.SUCCESS(
                f'\n🎉 SUCCESS! Created {clusters_created} hotspots'
            ))
            self.stdout.write(self.style.WARNING('=' * 70))
            
        except Exception as e:
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            
            self.stdout.write(self.style.ERROR(f'\n❌ ERROR: {str(e)}'))
            raise