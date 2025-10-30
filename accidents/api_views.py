from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Accident, AccidentCluster, AccidentReport
from .serializers import AccidentSerializer, AccidentClusterSerializer, AccidentReportSerializer

class AccidentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for accidents
    """
    queryset = Accident.objects.all()
    serializer_class = AccidentSerializer
    filterset_fields = ['province', 'municipal', 'year', 'is_hotspot']
    search_fields = ['barangay', 'municipal', 'incident_type']
    ordering_fields = ['date_committed', 'victim_count']
    ordering = ['-date_committed']

    @action(detail=False, methods=['get'])
    def by_location(self, request):
        """Get accidents within a bounding box"""
        min_lat = request.query_params.get('min_lat')
        max_lat = request.query_params.get('max_lat')
        min_lng = request.query_params.get('min_lng')
        max_lng = request.query_params.get('max_lng')

        if not all([min_lat, max_lat, min_lng, max_lng]):
            return Response(
                {'error': 'Please provide min_lat, max_lat, min_lng, max_lng'},
                status=status.HTTP_400_BAD_REQUEST
            )

        accidents = self.queryset.filter(
            latitude__gte=float(min_lat),
            latitude__lte=float(max_lat),
            longitude__gte=float(min_lng),
            longitude__lte=float(max_lng)
        )

        serializer = self.get_serializer(accidents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get accident statistics"""
        total = self.queryset.count()
        fatal = self.queryset.filter(victim_killed=True).count()
        hotspots = self.queryset.filter(is_hotspot=True).count()

        return Response({
            'total_accidents': total,
            'fatal_accidents': fatal,
            'hotspot_accidents': hotspots,
            'injury_rate': (fatal / total * 100) if total > 0 else 0
        })


class AccidentClusterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for accident clusters (hotspots)
    """
    queryset = AccidentCluster.objects.all()
    serializer_class = AccidentClusterSerializer
    ordering = ['-severity_score']

    @action(detail=True, methods=['get'])
    def accidents(self, request, pk=None):
        """Get all accidents in this cluster"""
        cluster = self.get_object()
        accidents = Accident.objects.filter(cluster_id=cluster.cluster_id)
        serializer = AccidentSerializer(accidents, many=True)
        return Response(serializer.data)


class AccidentReportViewSet(viewsets.ModelViewSet):
    """
    API endpoint for accident reports
    """
    queryset = AccidentReport.objects.all()
    serializer_class = AccidentReportSerializer
    filterset_fields = ['status', 'province']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

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

        return Response({'status': 'Report verified'})