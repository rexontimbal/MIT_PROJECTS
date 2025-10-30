from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from .models import Accident, AccidentCluster, AccidentReport
from .serializers import AccidentSerializer, AccidentClusterSerializer, AccidentReportSerializer


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for API endpoints
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for large datasets (maps, exports)
    """
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 5000


class AccidentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for accidents with optimized queries and pagination
    """
    serializer_class = AccidentSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['province', 'municipal', 'year', 'is_hotspot']
    search_fields = ['barangay', 'municipal', 'incident_type']
    ordering_fields = ['date_committed', 'victim_count']
    ordering = ['-date_committed']

    def get_queryset(self):
        """
        Optimized queryset with selective field loading
        """
        # Only load necessary fields for list views
        if self.action == 'list':
            return Accident.objects.only(
                'id', 'latitude', 'longitude', 'date_committed',
                'incident_type', 'victim_count', 'province', 'municipal',
                'is_hotspot', 'victim_killed', 'victim_injured'
            ).select_related()

        # Load all fields for detail views
        return Accident.objects.select_related()

    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """
        Get accidents within a bounding box (optimized with spatial indexing)
        """
        min_lat = request.query_params.get('min_lat')
        max_lat = request.query_params.get('max_lat')
        min_lng = request.query_params.get('min_lng')
        max_lng = request.query_params.get('max_lng')

        if not all([min_lat, max_lat, min_lng, max_lng]):
            return Response(
                {'error': 'Please provide min_lat, max_lat, min_lng, max_lng'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Use cache key based on bounding box
        cache_key = f'accidents_location_{min_lat}_{max_lat}_{min_lng}_{max_lng}'
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        # Optimized query with only necessary fields
        accidents = Accident.objects.filter(
            latitude__gte=float(min_lat),
            latitude__lte=float(max_lat),
            longitude__gte=float(min_lng),
            longitude__lte=float(max_lng)
        ).only(
            'id', 'latitude', 'longitude', 'incident_type',
            'victim_count', 'date_committed', 'municipal'
        )[:1000]  # Limit to 1000 results for performance

        serializer = self.get_serializer(accidents, many=True)

        # Cache for 5 minutes
        cache.set(cache_key, serializer.data, 300)

        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    @method_decorator(cache_page(60 * 15))  # Cache for 15 minutes
    def statistics(self, request):
        """
        Get accident statistics (cached and optimized with aggregation)
        """
        from django.db.models import Count, Avg, Sum

        stats = Accident.objects.aggregate(
            total_accidents=Count('id'),
            fatal_accidents=Count('id', filter=Q(victim_killed=True)),
            injury_accidents=Count('id', filter=Q(victim_injured=True)),
            hotspot_accidents=Count('id', filter=Q(is_hotspot=True)),
            total_casualties=Sum('victim_count'),
            avg_casualties=Avg('victim_count')
        )

        total = stats['total_accidents'] or 1  # Avoid division by zero

        return Response({
            'total_accidents': stats['total_accidents'],
            'fatal_accidents': stats['fatal_accidents'],
            'injury_accidents': stats['injury_accidents'],
            'hotspot_accidents': stats['hotspot_accidents'],
            'total_casualties': stats['total_casualties'],
            'avg_casualties': round(stats['avg_casualties'] or 0, 2),
            'fatal_rate': round((stats['fatal_accidents'] / total * 100), 2),
            'injury_rate': round((stats['injury_accidents'] / total * 100), 2),
            'hotspot_rate': round((stats['hotspot_accidents'] / total * 100), 2),
        })


class AccidentClusterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for accident clusters (hotspots) with optimization
    """
    serializer_class = AccidentClusterSerializer
    pagination_class = StandardResultsSetPagination
    ordering = ['-severity_score']

    def get_queryset(self):
        """
        Optimized queryset for clusters
        """
        if self.action == 'list':
            return AccidentCluster.objects.only(
                'cluster_id', 'center_latitude', 'center_longitude',
                'accident_count', 'severity_score', 'primary_location',
                'total_casualties'
            )

        return AccidentCluster.objects.all()

    @action(detail=True, methods=['get'])
    def accidents(self, request, pk=None):
        """
        Get all accidents in this cluster (cached and paginated)
        """
        cluster = self.get_object()
        cache_key = f'cluster_{cluster.cluster_id}_accidents'
        cached_result = cache.get(cache_key)

        if cached_result:
            return Response(cached_result)

        # Optimized query with only necessary fields
        accidents = Accident.objects.filter(
            cluster_id=cluster.cluster_id
        ).only(
            'id', 'latitude', 'longitude', 'date_committed',
            'incident_type', 'victim_count', 'municipal', 'barangay'
        ).order_by('-date_committed')

        serializer = AccidentSerializer(accidents, many=True)

        # Cache for 10 minutes
        cache.set(cache_key, serializer.data, 600)

        return Response(serializer.data)


class AccidentReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for accident reports with pagination
    """
    serializer_class = AccidentReportSerializer
    pagination_class = StandardResultsSetPagination
    filterset_fields = ['status', 'province']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Optimized queryset for reports
        """
        if self.action == 'list':
            # Use select_related for foreign keys
            return AccidentReport.objects.select_related(
                'verified_by'
            ).only(
                'id', 'reporter_name', 'incident_date', 'province',
                'municipal', 'status', 'created_at'
            )

        return AccidentReport.objects.select_related('verified_by')

    def perform_create(self, serializer):
        """Save report with current user"""
        if self.request.user.is_authenticated:
            serializer.save(reported_by=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a report (staff only)"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only staff can verify reports'},
                status=status.HTTP_403_FORBIDDEN
            )

        report = self.get_object()
        report.status = 'verified'
        report.verified_by = request.user
        report.save()

        # Clear cache
        cache.delete('pending_reports_count')

        return Response({'status': 'Report verified successfully'})


# ============================================================================
# EXPORT & TASK API ENDPOINTS
# ============================================================================

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.http import FileResponse
import os


class ExportAccidentsView(APIView):
    """
    API endpoint to export accidents to Excel/CSV
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Trigger accident export

        Request body:
            format: 'excel' or 'csv'
            filters: dict of filter parameters
            async: bool - run as background task
        """
        from .exports import AccidentExporter
        from .tasks import export_accidents_excel
        from .models import Accident

        export_format = request.data.get('format', 'excel')
        filters = request.data.get('filters', {})
        run_async = request.data.get('async', False)

        # Build queryset
        queryset = Accident.objects.all()
        if 'province' in filters:
            queryset = queryset.filter(province=filters['province'])
        if 'year' in filters:
            queryset = queryset.filter(year=filters['year'])
        if 'is_hotspot' in filters:
            queryset = queryset.filter(is_hotspot=filters['is_hotspot'])

        if run_async:
            # Run as background task
            task = export_accidents_excel.delay(filters=filters)
            return Response({
                'status': 'processing',
                'task_id': task.id,
                'message': 'Export started in background'
            })
        else:
            # Run synchronously
            exporter = AccidentExporter()
            if export_format == 'excel':
                filepath = exporter.export_to_excel(queryset)
            else:
                filepath = exporter.export_to_csv(queryset)

            # Return file download
            if os.path.exists(filepath):
                response = FileResponse(
                    open(filepath, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(filepath)
                )
                return response

            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ExportClustersView(APIView):
    """
    API endpoint to export clusters to PDF
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Trigger cluster export

        Request body:
            cluster_ids: list of cluster IDs (optional)
            async: bool - run as background task
        """
        from .exports import ClusterPDFExporter
        from .tasks import export_clusters_pdf
        from .models import AccidentCluster

        cluster_ids = request.data.get('cluster_ids')
        run_async = request.data.get('async', False)

        # Build queryset
        queryset = AccidentCluster.objects.order_by('-severity_score')
        if cluster_ids:
            queryset = queryset.filter(cluster_id__in=cluster_ids)

        if run_async:
            # Run as background task
            task = export_clusters_pdf.delay(cluster_ids=cluster_ids)
            return Response({
                'status': 'processing',
                'task_id': task.id,
                'message': 'PDF generation started in background'
            })
        else:
            # Run synchronously
            exporter = ClusterPDFExporter()
            filepath = exporter.generate_report(queryset)

            # Return file download
            if os.path.exists(filepath):
                response = FileResponse(
                    open(filepath, 'rb'),
                    as_attachment=True,
                    filename=os.path.basename(filepath)
                )
                return response

            return Response(
                {'error': 'Export failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TriggerClusteringView(APIView):
    """
    API endpoint to trigger AGNES clustering
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Trigger clustering task

        Request body:
            linkage_method: 'complete', 'single', or 'average'
            distance_threshold: float
            min_cluster_size: int
            days: int (optional - limit to recent data)
            async: bool - run as background task (default: true)
        """
        from .tasks import run_clustering_task

        linkage_method = request.data.get('linkage_method', 'complete')
        distance_threshold = float(request.data.get('distance_threshold', 0.05))
        min_cluster_size = int(request.data.get('min_cluster_size', 3))
        days = request.data.get('days')
        run_async = request.data.get('async', True)

        if run_async:
            # Run as background task (recommended)
            task = run_clustering_task.delay(
                linkage_method=linkage_method,
                distance_threshold=distance_threshold,
                min_cluster_size=min_cluster_size,
                days=days
            )

            return Response({
                'status': 'processing',
                'task_id': task.id,
                'message': 'Clustering started in background',
                'check_status_url': f'/api/tasks/{task.id}/'
            })
        else:
            # Run synchronously (not recommended for large datasets)
            result = run_clustering_task(
                linkage_method=linkage_method,
                distance_threshold=distance_threshold,
                min_cluster_size=min_cluster_size,
                days=days
            )

            return Response(result)


class TaskStatusView(APIView):
    """
    API endpoint to check task status
    """

    def get(self, request, task_id):
        """
        Get task status

        Returns task state, progress, and result
        """
        from celery.result import AsyncResult

        task = AsyncResult(task_id)

        response_data = {
            'task_id': task_id,
            'state': task.state,
            'ready': task.ready(),
        }

        if task.state == 'PENDING':
            response_data['status'] = 'Task is waiting to be executed'
        elif task.state == 'PROGRESS':
            response_data['status'] = task.info.get('status', '')
            response_data['progress'] = task.info.get('progress', 0)
        elif task.state == 'SUCCESS':
            response_data['status'] = 'Task completed successfully'
            response_data['result'] = task.result
        elif task.state == 'FAILURE':
            response_data['status'] = 'Task failed'
            response_data['error'] = str(task.info)
        else:
            response_data['status'] = task.state

        return Response(response_data)