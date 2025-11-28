"""
AJAX endpoint for fetching filtered chart data
Allows real-time chart filtering in modals without page reload
"""
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth, TruncQuarter, TruncWeek, TruncDay, ExtractWeekDay, ExtractHour
from .models import Accident
from .auth_utils import pnp_login_required
import calendar


@pnp_login_required
def get_chart_data_ajax(request):
    """
    Returns chart data in JSON format based on filters
    Used for real-time chart filtering in modals
    """
    try:
        # Get parameters
        chart_type = request.GET.get('chart_type')  # 'hourly', 'dow', 'trend', etc.
        from_date_str = request.GET.get('from_date')
        to_date_str = request.GET.get('to_date')
        severity_filter = request.GET.get('severity', 'all')
        province_filter = request.GET.get('province', 'all')
        municipal_filter = request.GET.get('municipal', 'all')
        granularity = request.GET.get('granularity', 'monthly')

        # Parse dates
        if from_date_str:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        else:
            earliest = Accident.objects.order_by('date_committed').first()
            from_date = earliest.date_committed if earliest else (timezone.now() - timedelta(days=365)).date()

        if to_date_str:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        else:
            latest = Accident.objects.order_by('-date_committed').first()
            to_date = latest.date_committed if latest else timezone.now().date()

        # Build queryset
        accidents = Accident.objects.filter(
            date_committed__gte=from_date,
            date_committed__lte=to_date
        )

        # Apply filters
        if severity_filter == 'fatal':
            accidents = accidents.filter(victim_killed=True)
        elif severity_filter == 'injury':
            accidents = accidents.filter(victim_injured=True)
        elif severity_filter == 'property':
            accidents = accidents.filter(victim_killed=False, victim_injured=False)

        if province_filter and province_filter != 'all':
            accidents = accidents.filter(province=province_filter)

        if municipal_filter and municipal_filter != 'all':
            accidents = accidents.filter(municipal=municipal_filter)

        # Generate chart data based on chart_type
        chart_data = {}

        if chart_type == 'hourly':
            # Hourly distribution
            hourly_data = accidents.annotate(
                hour=ExtractHour('time_committed')
            ).values('hour').annotate(
                count=Count('id')
            ).order_by('hour')

            # Create full 24-hour data
            hourly_counts = {item['hour']: item['count'] for item in hourly_data}
            chart_data = {
                'labels': [f"{h:02d}:00" for h in range(24)],
                'data': [hourly_counts.get(h, 0) for h in range(24)]
            }

        elif chart_type == 'dow':
            # Day of week analysis
            dow_data = accidents.annotate(
                dow=ExtractWeekDay('date_committed')
            ).values('dow').annotate(
                count=Count('id')
            ).order_by('dow')

            # Map to day names (1=Sunday, 7=Saturday in Django)
            days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
            dow_counts = {item['dow']: item['count'] for item in dow_data}
            chart_data = {
                'labels': days,
                'data': [dow_counts.get(i + 1, 0) for i in range(7)]
            }

        elif chart_type == 'trend':
            # Accident trend with granularity
            if granularity == 'daily':
                trunc_func = TruncDay
            elif granularity == 'weekly':
                trunc_func = TruncWeek
            elif granularity == 'quarterly':
                trunc_func = TruncQuarter
            else:  # monthly
                trunc_func = TruncMonth

            trend_data = accidents.annotate(
                period=trunc_func('date_committed')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period')

            chart_data = {
                'labels': [item['period'].strftime('%b %Y') if granularity == 'monthly' else
                          item['period'].strftime('%Y-%m-%d') for item in trend_data],
                'data': [item['count'] for item in trend_data]
            }

        elif chart_type == 'comparison':
            # Fatal vs Injury comparison
            comparison_data = accidents.aggregate(
                fatal=Count('id', filter=Q(victim_killed=True)),
                injury=Count('id', filter=Q(victim_injured=True)),
                property=Count('id', filter=Q(victim_killed=False, victim_injured=False))
            )

            chart_data = {
                'labels': ['Fatal', 'Injury', 'Property Damage'],
                'data': [
                    comparison_data['fatal'],
                    comparison_data['injury'],
                    comparison_data['property']
                ]
            }

        elif chart_type == 'forecast':
            # Simple forecast based on trend
            if granularity == 'monthly':
                trunc_func = TruncMonth
            else:
                trunc_func = TruncMonth  # Default to monthly

            trend_data = list(accidents.annotate(
                period=trunc_func('date_committed')
            ).values('period').annotate(
                count=Count('id')
            ).order_by('period'))

            # Return actual data for now (frontend can calculate forecast)
            chart_data = {
                'labels': [item['period'].strftime('%b %Y') for item in trend_data],
                'data': [item['count'] for item in trend_data]
            }

        elif chart_type == 'severity':
            # Severity Distribution (Fatal, Injury, Property Damage)
            severity_data = accidents.aggregate(
                fatal=Count('id', filter=Q(victim_killed=True)),
                injury=Count('id', filter=Q(victim_injured=True)),
                property=Count('id', filter=Q(victim_killed=False, victim_injured=False))
            )

            chart_data = {
                'labels': ['Fatal', 'Injury', 'Property Damage'],
                'data': [
                    severity_data['fatal'],
                    severity_data['injury'],
                    severity_data['property']
                ]
            }

        elif chart_type == 'vehicle':
            # Vehicle Types Involved
            vehicle_data = accidents.values('vehicle_kind').annotate(
                count=Count('id')
            ).exclude(vehicle_kind__isnull=True).exclude(vehicle_kind='').order_by('-count')[:10]

            chart_data = {
                'labels': [item['vehicle_kind'] for item in vehicle_data],
                'data': [item['count'] for item in vehicle_data]
            }

        elif chart_type == 'provinceComparison':
            # Province Comparison - Fatal vs Injury
            province_data = accidents.values('province').annotate(
                fatal=Count('id', filter=Q(victim_killed=True)),
                injury=Count('id', filter=Q(victim_injured=True))
            ).order_by('province')

            chart_data = {
                'labels': [item['province'] for item in province_data],
                'fatal': [item['fatal'] for item in province_data],
                'injury': [item['injury'] for item in province_data]
            }

        elif chart_type == 'incidentType':
            # Top 5 Incident Types
            incident_data = accidents.values('incident_type').annotate(
                count=Count('id')
            ).exclude(incident_type__isnull=True).exclude(incident_type='').order_by('-count')[:5]

            chart_data = {
                'labels': [item['incident_type'] for item in incident_data],
                'data': [item['count'] for item in incident_data]
            }

        elif chart_type == 'trendComparison':
            # Trend Comparison (Fatal vs Injury over time)
            if granularity == 'monthly':
                trunc_func = TruncMonth
            elif granularity == 'quarterly':
                trunc_func = TruncQuarter
            else:
                trunc_func = TruncMonth

            trend_data = accidents.annotate(
                period=trunc_func('date_committed')
            ).values('period').annotate(
                fatal=Count('id', filter=Q(victim_killed=True)),
                injury=Count('id', filter=Q(victim_injured=True))
            ).order_by('period')

            chart_data = {
                'labels': [item['period'].strftime('%b %Y') for item in trend_data],
                'fatal': [item['fatal'] for item in trend_data],
                'injury': [item['injury'] for item in trend_data]
            }

        else:
            return JsonResponse({'error': 'Invalid chart type'}, status=400)

        return JsonResponse({
            'success': True,
            'chart_data': chart_data,
            'total_accidents': accidents.count(),
            'date_range': {
                'from': from_date.strftime('%Y-%m-%d'),
                'to': to_date.strftime('%Y-%m-%d')
            }
        })

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error fetching chart data: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
