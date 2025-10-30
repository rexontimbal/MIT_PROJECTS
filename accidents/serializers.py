from rest_framework import serializers
from .models import Accident, AccidentCluster, AccidentReport

class AccidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Accident
        fields = [
            'id', 'latitude', 'longitude', 'incident_type',
            'date_committed', 'time_committed', 'barangay',
            'municipal', 'province', 'victim_count',
            'victim_killed', 'victim_injured', 'year',
            'vehicle_kind', 'case_status', 'is_hotspot',
            'cluster_id'
        ]

class AccidentClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccidentCluster
        fields = [
            'cluster_id', 'center_latitude', 'center_longitude',
            'accident_count', 'total_casualties', 'severity_score',
            'primary_location', 'municipalities', 'date_range_start',
            'date_range_end', 'computed_at'
        ]

class AccidentReportSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source='reported_by.username', read_only=True)

    class Meta:
        model = AccidentReport
        fields = [
            'id', 'reporter_name', 'reporter_contact',
            'incident_date', 'incident_time', 'latitude', 'longitude',
            'province', 'municipal', 'barangay', 'street_address',
            'incident_description', 'casualties_killed', 'casualties_injured',
            'vehicles_involved', 'status', 'created_at',
            'reported_by_name'
        ]
        read_only_fields = ['status', 'created_at']