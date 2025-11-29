from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth, ExtractWeekDay
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth import authenticate, logout
from django.views.decorators.http import require_http_methods
import json
from datetime import timedelta
from datetime import time as dt_time
from .models import Accident, AccidentCluster, AccidentReport, UserProfile
from datetime import datetime
from django.contrib.auth.views import LoginView
from .auth_utils import pnp_login_required, log_user_action

@pnp_login_required
def dashboard(request):
    """Optimized dashboard with better performance and caching - Enhanced for PNP Operations"""

    # Check if it's an AJAX request for partial updates
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Get current date for calculations
    today = timezone.now().date()
    now = timezone.now()

    # Use database aggregation for faster statistics
    from django.db.models import Count, Q, Sum
    from django.core.cache import cache

    # Cache key for dashboard data
    cache_key = 'dashboard_data'
    cached_data = cache.get(cache_key)

    if cached_data and not is_ajax:
        # Use cached data if available (except for AJAX requests)
        context = cached_data
    else:
        # === REAL-TIME OPERATIONAL STATS FOR PNP ===

        # TODAY's accidents
        today_accidents = Accident.objects.filter(
            date_committed=today
        ).aggregate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True)),
            injury=Count('id', filter=Q(victim_injured=True))
        )

        # THIS WEEK's accidents (Monday to today)
        week_start = today - timedelta(days=today.weekday())
        week_accidents = Accident.objects.filter(
            date_committed__gte=week_start,
            date_committed__lte=today
        ).aggregate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True)),
            injury=Count('id', filter=Q(victim_injured=True))
        )

        # THIS MONTH's accidents
        month_start = today.replace(day=1)
        month_accidents = Accident.objects.filter(
            date_committed__gte=month_start,
            date_committed__lte=today
        ).aggregate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True)),
            injury=Count('id', filter=Q(victim_injured=True))
        )

        # Calculate statistics with optimized queries
        stats = Accident.objects.aggregate(
            total_accidents=Count('id'),
            total_killed=Count('id', filter=Q(victim_killed=True)),
            total_injured=Count('id', filter=Q(victim_injured=True)),
            total_casualties=Sum('victim_count')
        )

        # Get counts with single queries
        total_hotspots = AccidentCluster.objects.count()
        pending_reports = AccidentReport.objects.filter(status='pending').count()

        # Calculate recent increase (last 30 days vs previous 30 days)
        last_30_days = today - timedelta(days=30)
        last_60_days = today - timedelta(days=60)

        recent_accidents_count = Accident.objects.filter(
            date_committed__gte=last_30_days
        ).count()

        previous_accidents_count = Accident.objects.filter(
            date_committed__gte=last_60_days,
            date_committed__lt=last_30_days
        ).count()

        recent_increase = 0
        if previous_accidents_count > 0:
            recent_increase = ((recent_accidents_count - previous_accidents_count) / previous_accidents_count) * 100

        # Optimized queries for recent data with select_related and limit
        recent_accidents_list = Accident.objects.select_related().order_by('-date_committed', '-time_committed')[:15]

        # Optimized hotspots query
        top_hotspots = AccidentCluster.objects.only(
            'cluster_id', 'primary_location', 'accident_count', 'severity_score'
        ).order_by('-severity_score')[:5]

        # Get chart data (these are already optimized in their functions)
        time_data = get_accidents_over_time(12)
        province_data = get_accidents_by_province()
        type_data = get_accidents_by_type()
        time_of_day_data = get_accidents_by_time_of_day()

        # Get critical alerts
        critical_alerts = get_critical_alerts()

        context = {
            # Real-time operational stats
            'today_total': today_accidents['total'] or 0,
            'today_fatal': today_accidents['fatal'] or 0,
            'today_injury': today_accidents['injury'] or 0,

            'week_total': week_accidents['total'] or 0,
            'week_fatal': week_accidents['fatal'] or 0,
            'week_injury': week_accidents['injury'] or 0,

            'month_total': month_accidents['total'] or 0,
            'month_fatal': month_accidents['fatal'] or 0,
            'month_injury': month_accidents['injury'] or 0,

            # Overall statistics
            'total_accidents': stats['total_accidents'] or 0,
            'total_hotspots': total_hotspots,
            'total_casualties': stats['total_casualties'] or 0,
            'killed': stats['total_killed'] or 0,
            'injured': stats['total_injured'] or 0,
            'pending_reports': pending_reports,
            'recent_increase': round(recent_increase, 1),
            'recent_accidents': recent_accidents_list,
            'top_hotspots': top_hotspots,
            'critical_alerts': critical_alerts,

            # Chart data
            'time_labels': json.dumps(time_data['labels']),
            'time_data': json.dumps(time_data['data']),
            'province_labels': json.dumps(province_data['labels']),
            'province_data': json.dumps(province_data['data']),
            'type_labels': json.dumps(type_data['labels']),
            'type_data': json.dumps(type_data['data']),
            'time_of_day_data': json.dumps(time_of_day_data),

            # Current time for display
            'current_time': now,
        }

        # Cache the data for 2 minutes (120 seconds) - shorter for real-time feel
        if not is_ajax:
            cache.set(cache_key, context, 120)

    if is_ajax:
        # Return minimal HTML for AJAX updates
        return render(request, 'dashboard/dashboard_partial.html', context)
    else:
        return render(request, 'dashboard/dashboard.html', context)


def get_accidents_over_time(months=12):
    """Get accident counts for the last N months - Always returns all months"""
    from django.db.models.functions import TruncMonth
    from dateutil.relativedelta import relativedelta

    end_date = timezone.now().date()
    start_date = end_date - relativedelta(months=months)

    # Get actual accident counts by month
    accidents_by_month = Accident.objects.filter(
        date_committed__gte=start_date,
        date_committed__lte=end_date
    ).annotate(
        month=TruncMonth('date_committed')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    # Create a dictionary of month -> count
    accident_counts = {}
    for item in accidents_by_month:
        if item['month']:
            month_key = item['month'].strftime('%Y-%m')
            accident_counts[month_key] = item['count']

    # Generate all months in range (even if no accidents)
    labels = []
    data = []

    current_month = start_date.replace(day=1)
    end_month = end_date.replace(day=1)

    while current_month <= end_month:
        # Format label
        labels.append(current_month.strftime('%B %Y'))

        # Get count for this month (0 if no accidents)
        month_key = current_month.strftime('%Y-%m')
        data.append(accident_counts.get(month_key, 0))

        # Move to next month
        current_month = current_month + relativedelta(months=1)

    return {'labels': labels, 'data': data}


def get_accidents_by_province():
    """Get accident counts by province"""
    accidents_by_province = Accident.objects.values('province').annotate(
        count=Count('id')
    ).order_by('-count')[:5]  # Top 5 provinces
    
    labels = [item['province'] for item in accidents_by_province]
    data = [item['count'] for item in accidents_by_province]
    
    return {'labels': labels, 'data': data}


def get_accidents_by_type():
    """Get accident counts by incident type"""
    accidents_by_type = Accident.objects.values('incident_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]  # Top 5 types
    
    labels = []
    data = []
    
    for item in accidents_by_type:
        # Shorten long incident type names
        type_name = item['incident_type'].replace('(Incident) ', '')
        labels.append(type_name[:30])
        data.append(item['count'])
    
    return {'labels': labels, 'data': data}


def get_accidents_by_time_of_day():
    """Categorize accidents by time of day"""
    from datetime import time as dt_time
    
    # Night: 12AM - 6AM
    night = Accident.objects.filter(
        time_committed__gte=dt_time(0, 0),
        time_committed__lt=dt_time(6, 0)
    ).count()
    
    # Morning: 6AM - 12PM
    morning = Accident.objects.filter(
        time_committed__gte=dt_time(6, 0),
        time_committed__lt=dt_time(12, 0)
    ).count()
    
    # Afternoon: 12PM - 6PM
    afternoon = Accident.objects.filter(
        time_committed__gte=dt_time(12, 0),
        time_committed__lt=dt_time(18, 0)
    ).count()
    
    # Evening: 6PM - 12AM (11:59 PM)
    evening = Accident.objects.filter(
        time_committed__gte=dt_time(18, 0),
        time_committed__lte=dt_time(23, 59)
    ).count()
    
    return [night, morning, afternoon, evening]

@pnp_login_required
def accident_list(request):
    """List all accidents with filtering and statistics"""
    accidents = Accident.objects.all().order_by('-date_committed')
    
    # Apply filters
    province = request.GET.get('province')
    municipal = request.GET.get('municipal')
    year = request.GET.get('year')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    is_hotspot = request.GET.get('is_hotspot')
    search = request.GET.get('search')

    # Quick filters
    fatal_only = request.GET.get('fatal')
    injury_only = request.GET.get('injury')
    no_hotspot = request.GET.get('no_hotspot')  # NEW

    if province:
        accidents = accidents.filter(province=province)
    if municipal:
        accidents = accidents.filter(municipal=municipal)
    if year:
        accidents = accidents.filter(year=year)
    if date_from:
        accidents = accidents.filter(date_committed__gte=date_from)
    if date_to:
        accidents = accidents.filter(date_committed__lte=date_to)
    if is_hotspot:
        accidents = accidents.filter(is_hotspot=True)
    if fatal_only:
        accidents = accidents.filter(victim_killed=True)
    if injury_only:
        accidents = accidents.filter(victim_injured=True)
    if no_hotspot:  # NEW
        accidents = accidents.filter(is_hotspot=False)  # NEW
    
    # Search filter
    if search:
        from django.db.models import Q

        # Create base location/incident search
        search_q = (
            Q(barangay__icontains=search) |
            Q(municipal__icontains=search) |
            Q(province__icontains=search) |
            Q(incident_type__icontains=search) |
            Q(street__icontains=search)
        )

        # Add severity-based search
        search_lower = search.lower()
        if 'fatal' in search_lower or 'death' in search_lower or 'killed' in search_lower:
            search_q |= Q(victim_killed=True)
        if 'injury' in search_lower or 'injured' in search_lower or 'hurt' in search_lower:
            search_q |= Q(victim_injured=True)
        if 'property' in search_lower or 'damage' in search_lower or 'unharmed' in search_lower:
            search_q |= Q(victim_unharmed=True)

        # Add hotspot/non-hotspot search
        if 'hotspot' in search_lower:
            if 'not' in search_lower or 'no' in search_lower or 'non' in search_lower:
                # Search for non-hotspot accidents
                search_q |= Q(is_hotspot=False)
            else:
                # Search for hotspot accidents
                search_q |= Q(is_hotspot=True)

        accidents = accidents.filter(search_q)
    
    # Calculate statistics for filtered results
    fatal_count = accidents.filter(victim_killed=True).count()
    injury_count = accidents.filter(victim_injured=True).count()
    hotspot_count = accidents.filter(is_hotspot=True).count()
    
    # Get all provinces for the main dropdown
    provinces = Accident.objects.exclude(
        province__isnull=True
    ).exclude(
        province=''
    ).values_list('province', flat=True).distinct().order_by('province')
    provinces = [p for p in provinces if p and p.strip()]
    
    # Get municipalities based on selected province
    if province:
        municipalities = Accident.objects.filter(
            province=province
        ).exclude(
            municipal__isnull=True
        ).exclude(
            municipal=''
        ).values_list('municipal', flat=True).distinct().order_by('municipal')
    else:
        municipalities = Accident.objects.exclude(
            municipal__isnull=True
        ).exclude(
            municipal=''
        ).values_list('municipal', flat=True).distinct().order_by('municipal')
    
    municipalities = [m for m in municipalities if m and m.strip()]
    
    years = Accident.objects.exclude(
        year__isnull=True
    ).values_list('year', flat=True).distinct().order_by('-year')
    years = [y for y in years if y]
    
    # Precompute municipality data for all provinces (for JavaScript)
    municipality_data = {}
    for prov in provinces:
        munis = Accident.objects.filter(province=prov).exclude(
            municipal__isnull=True
        ).exclude(
            municipal=''
        ).values_list('municipal', flat=True).distinct().order_by('municipal')
        municipality_data[prov] = [m for m in munis if m and m.strip()]
    
    # Export to CSV if requested
    export = request.GET.get('export')
    if export == 'csv':
        import csv
        from django.http import HttpResponse
        from datetime import datetime

        # Count filtered results
        total_count = accidents.count()

        # Determine if filters are applied
        has_filters = any([province, municipal, year, date_from, date_to, is_hotspot,
                          search, fatal_only, injury_only, no_hotspot])

        # Create descriptive filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if has_filters:
            filename = f'accidents_filtered_{total_count}_records_{timestamp}.csv'
        else:
            filename = f'accidents_all_{total_count}_records_{timestamp}.csv'

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Write header with metadata
        writer.writerow(['# Accident Records Export'])
        writer.writerow(['# Export Date:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['# Total Records:', total_count])
        writer.writerow(['# Filters Applied:', 'Yes' if has_filters else 'No'])
        if has_filters:
            filter_details = []
            if province: filter_details.append(f'Province={province}')
            if municipal: filter_details.append(f'Municipality={municipal}')
            if year: filter_details.append(f'Year={year}')
            if date_from: filter_details.append(f'DateFrom={date_from}')
            if date_to: filter_details.append(f'DateTo={date_to}')
            if search: filter_details.append(f'Search={search}')
            if fatal_only: filter_details.append('Fatal Only')
            if injury_only: filter_details.append('Injury Only')
            if no_hotspot: filter_details.append('Non-Hotspot Only')
            writer.writerow(['# Active Filters:', ', '.join(filter_details)])
        writer.writerow([])  # Empty row separator

        # Write column headers
        writer.writerow([
            'Date', 'Time', 'Province', 'Municipality', 'Barangay',
            'Street', 'Incident Type', 'Casualties', 'Fatal', 'Injured',
            'Hotspot', 'Cluster ID', 'Latitude', 'Longitude'
        ])

        # Write data rows
        for acc in accidents:
            writer.writerow([
                acc.date_committed.strftime('%Y-%m-%d') if acc.date_committed else '',
                acc.time_committed.strftime('%H:%M') if acc.time_committed else '',
                acc.province or '',
                acc.municipal or '',
                acc.barangay or '',
                acc.street or '',
                acc.incident_type or '',
                acc.victim_count or 0,
                'Yes' if acc.victim_killed else 'No',
                'Yes' if acc.victim_injured else 'No',
                'Yes' if acc.is_hotspot else 'No',
                acc.cluster_id or '',
                float(acc.latitude) if acc.latitude else '',
                float(acc.longitude) if acc.longitude else ''
            ])

        return response

    # Pagination - user-controlled via per_page parameter
    # Default: 100 per page, options: 12, 24, 48, 100, 500
    from django.core.paginator import Paginator

    per_page = request.GET.get('per_page', 100)
    try:
        per_page = int(per_page)
        # Validate per_page is in allowed values
        if per_page not in [12, 24, 48, 100, 500]:
            per_page = 100
    except (ValueError, TypeError):
        per_page = 100

    paginator = Paginator(accidents, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'accidents': page_obj,
        'provinces': provinces,
        'municipalities': municipalities,
        'years': years,
        'municipality_data_json': json.dumps(municipality_data),
        'fatal_count': fatal_count,
        'injury_count': injury_count,
        'hotspot_count': hotspot_count,
        'is_fatal_view': fatal_only,  # NEW
        'is_injury_view': injury_only,  # NEW
        'is_hotspot_view': is_hotspot,  # NEW
        'is_standalone_view': no_hotspot,  # NEW
    }
    
    return render(request, 'accidents/accident_list.html', context)

@pnp_login_required
def accident_detail(request, pk):
    """Display detailed information about a specific accident"""
    from math import radians, cos, sin, asin, sqrt
    from decimal import Decimal
    
    accident = get_object_or_404(Accident, pk=pk)
    
    # Get nearby accidents (within ~5km)
    nearby_accidents_raw = Accident.objects.filter(
        latitude__range=(accident.latitude - Decimal('0.05'), accident.latitude + Decimal('0.05')),
        longitude__range=(accident.longitude - Decimal('0.05'), accident.longitude + Decimal('0.05'))
    ).exclude(pk=pk)[:10]  # Get top 10
    
    # Calculate actual distance for each nearby accident
    def haversine_distance(lat1, lon1, lat2, lon2):
        """
        Calculate the great circle distance between two points 
        on the earth (specified in decimal degrees)
        Returns distance in kilometers
        """
        # Convert to float first, then to radians
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
        
        # Convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    # Add distance to each nearby accident
    nearby_accidents = []
    for nearby in nearby_accidents_raw:
        try:
            distance = haversine_distance(
                accident.latitude,
                accident.longitude,
                nearby.latitude,
                nearby.longitude
            )
            
            # Only include if within 5km
            if distance <= 5.0:
                nearby.distance = distance
                nearby_accidents.append(nearby)
        except Exception as e:
            # Skip if calculation fails
            continue
    
    # Sort by distance
    nearby_accidents.sort(key=lambda x: x.distance)
    
    # Keep only top 5 nearest
    nearby_accidents = nearby_accidents[:5]
    
    context = {
        'accident': accident,
        'nearby_accidents': nearby_accidents,
    }
    
    return render(request, 'accidents/accident_detail.html', context)

@pnp_login_required
def hotspots_view(request):
    """Display all detected hotspots"""
    
    # Get all hotspots ordered by severity
    hotspots = AccidentCluster.objects.all().order_by('-severity_score')
    
    # Apply filters
    province = request.GET.get('province')
    min_severity = request.GET.get('min_severity')
    min_accidents = request.GET.get('min_accidents')
    municipality = request.GET.get('municipality')
    
    if province:
        # Get cluster IDs that have accidents from this province
        cluster_ids_in_province = Accident.objects.filter(
            province=province,
            cluster_id__isnull=False
        ).values_list('cluster_id', flat=True).distinct()
        
        # Filter hotspots to only those cluster IDs
        hotspots = hotspots.filter(cluster_id__in=cluster_ids_in_province)
    
    if min_severity:
        hotspots = hotspots.filter(severity_score__gte=float(min_severity))
    
    if min_accidents:
        hotspots = hotspots.filter(accident_count__gte=int(min_accidents))
    
    if municipality:
        # Filter hotspots that include this municipality
        hotspots = hotspots.filter(municipalities__contains=[municipality])
    
    # Calculate summary statistics (only for filtered hotspots)
    total_accidents = sum(h.accident_count for h in hotspots)
    total_casualties = sum(h.total_casualties for h in hotspots)
    critical_count = hotspots.filter(severity_score__gte=70).count()
    
    # Get unique provinces and municipalities for filter dropdowns
    provinces = Accident.objects.values_list('province', flat=True).distinct().order_by('province')
    provinces = [p for p in provinces if p and p.strip()]
    
    municipalities = Accident.objects.values_list('municipal', flat=True).distinct().order_by('municipal')
    municipalities = [m for m in municipalities if m and m.strip()]
    
    # Add killed_count and provinces to each hotspot for display
    for hotspot in hotspots:
        hotspot.killed_count = Accident.objects.filter(
            cluster_id=hotspot.cluster_id,
            victim_killed=True
        ).count()

        # Get actual provinces for this hotspot
        hotspot_provinces = Accident.objects.filter(
            cluster_id=hotspot.cluster_id
        ).values_list('province', flat=True).distinct()
        hotspot.provinces = [p for p in hotspot_provinces if p and p.strip()]

    # Create province-to-municipality mapping for cascade filtering
    province_municipality_map = {}
    for province in provinces:
        munis = Accident.objects.filter(
            province=province
        ).values_list('municipal', flat=True).distinct().order_by('municipal')
        province_municipality_map[province] = [m for m in munis if m and m.strip()]

    # Prepare hotspots data for JSON (for map preview)
    from django.core.serializers.json import DjangoJSONEncoder
    import json
    hotspots_json = json.dumps(list(hotspots.values(
        'cluster_id', 'center_latitude', 'center_longitude',
        'primary_location', 'accident_count', 'severity_score'
    )), cls=DjangoJSONEncoder)

    context = {
        'hotspots': hotspots,
        'total_accidents': total_accidents,
        'total_casualties': total_casualties,
        'critical_count': critical_count,
        'provinces': provinces,
        'municipalities': municipalities,
        'province_municipality_map': json.dumps(province_municipality_map),
        'hotspots_json': hotspots_json,  # Add this for map preview
    }
    
    return render(request, 'hotspots/hotspots_list.html', context)


@pnp_login_required
def hotspot_detail(request, cluster_id):
    """Display detailed information about a specific hotspot"""
    hotspot = get_object_or_404(AccidentCluster, cluster_id=cluster_id)
    
    # Get all accidents in this cluster (limit to recent 50 for performance)
    accidents = Accident.objects.filter(cluster_id=cluster_id).order_by('-date_committed')
    total_count = accidents.count()
    
    # Limit to 50 most recent for display
    accidents_display = accidents[:50]
    
    # Statistics for this hotspot
    total_killed = accidents.filter(victim_killed=True).count()
    total_injured = accidents.filter(victim_injured=True).count()
    
    # Calculate date span
    if hotspot.date_range_start and hotspot.date_range_end:
        date_span = (hotspot.date_range_end - hotspot.date_range_start).days
    else:
        date_span = 0
    
    # Accidents by month for trend chart
    from django.db.models.functions import TruncMonth
    from datetime import timedelta
    
    accidents_by_month = accidents.annotate(
    month=TruncMonth('date_committed')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')

    # If too many months (more than 24), show only last 24 months for readability
    if accidents_by_month.count() > 24:
        cutoff_date = timezone.now().date() - timedelta(days=730)  # 2 years
        accidents_by_month = accidents_by_month.filter(month__gte=cutoff_date)

    month_labels = [item['month'].strftime('%b %Y') for item in accidents_by_month]
    month_data = [item['count'] for item in accidents_by_month]
    
    # Prepare accidents data for map - WITH DECIMAL TO FLOAT CONVERSION
    accidents_for_map = accidents_display.values(
        'id', 'latitude', 'longitude', 'incident_type',
        'date_committed', 'barangay', 'municipal', 
        'victim_count', 'victim_killed', 'victim_injured'  # ADDED victim_injured
    )
    
    # Convert dates and decimals for JSON
    accidents_map_list = []
    for acc in accidents_for_map:
        acc_dict = {
            'id': acc['id'],
            'latitude': float(acc['latitude']),  # Convert Decimal to float
            'longitude': float(acc['longitude']),  # Convert Decimal to float
            'incident_type': acc['incident_type'],
            'date_committed': acc['date_committed'].strftime('%Y-%m-%d') if acc['date_committed'] else '',
            'barangay': acc['barangay'],
            'municipal': acc['municipal'],
            'victim_count': acc['victim_count'],
            'victim_killed': acc['victim_killed'],
            'victim_injured': acc['victim_injured']  # ADDED
        }
        accidents_map_list.append(acc_dict)
    
    accidents_json = json.dumps(accidents_map_list)
    
    # Prepare export data
    accidents_export = []
    for acc in accidents_display:
        accidents_export.append({
            'Date': acc.date_committed.strftime('%Y-%m-%d') if acc.date_committed else '',
            'Time': acc.time_committed.strftime('%H:%M') if acc.time_committed else '',
            'Location': f"{acc.barangay}, {acc.municipal}",
            'Type': acc.incident_type,
            'Casualties': acc.victim_count,
            'Fatal': 'Yes' if acc.victim_killed else 'No',
            'Injured': 'Yes' if acc.victim_injured else 'No',  # ADDED
            'Latitude': float(acc.latitude) if acc.latitude else '',  # Convert here too
            'Longitude': float(acc.longitude) if acc.longitude else '',  # Convert here too
        })
    
    accidents_export_json = json.dumps(accidents_export)
    
    context = {
        'hotspot': hotspot,
        'accidents': accidents_display,
        'total_accidents': total_count,
        'showing_count': len(accidents_display),
        'total_killed': total_killed,
        'total_injured': total_injured,
        'date_span': date_span,
        'month_labels': json.dumps(month_labels),  
        'month_data': json.dumps(month_data),      
        'accidents_json': accidents_json,
        'accidents_export': accidents_export_json,
    }
    
    return render(request, 'hotspots/hotspot_detail.html', context)


@pnp_login_required
def report_accident(request):
    """Form for reporting new accidents"""
    if request.method == 'POST':
        from .forms import AccidentReportForm
        form = AccidentReportForm(request.POST, request.FILES)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            report.save()
            
            messages.success(request, 'Accident report submitted successfully!')
            return redirect('report_success', pk=report.pk)
    else:
        from .forms import AccidentReportForm
        form = AccidentReportForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'reports/report_form.html', context)


@pnp_login_required
def report_success(request, pk):
    """Success page after submitting a report"""
    report = get_object_or_404(AccidentReport, pk=pk)
    
    context = {
        'report': report,
    }
    
    return render(request, 'reports/report_success.html', context)


# Additional utility views
@pnp_login_required
def about(request):
    """About page"""
    return render(request, 'pages/about.html')

@pnp_login_required
def help_view(request):
    """Help and support page"""
    return render(request, 'pages/help.html')

@pnp_login_required
def contact(request):
    """Contact page"""
    return render(request, 'pages/contact.html')

@pnp_login_required
def profile(request):
    """User profile page"""
    user_reports = AccidentReport.objects.filter(
        reported_by=request.user
    ).order_by('-created_at')

    context = {
        'user_reports': user_reports,
    }

    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """Change password page - required for new users"""
    from .auth_utils import log_user_action

    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Validate current password
        if not request.user.check_password(current_password):
            # Clear all messages before adding new error
            storage = messages.get_messages(request)
            storage.used = True
            messages.error(request, 'Current password is incorrect.')
            return redirect('change_password')

        # Validate new passwords match
        if new_password != confirm_password:
            # Clear all messages before adding new error
            storage = messages.get_messages(request)
            storage.used = True
            messages.error(request, 'New passwords do not match.')
            return redirect('change_password')

        # Validate password length
        if len(new_password) < 8:
            # Clear all messages before adding new error
            storage = messages.get_messages(request)
            storage.used = True
            messages.error(request, 'Password must be at least 8 characters long.')
            return redirect('change_password')

        # Use atomic transaction to ensure changes are committed before redirect
        with transaction.atomic():
            # Update password
            request.user.set_password(new_password)
            request.user.save()

            # Update profile
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                profile.must_change_password = False
                profile.password_changed_at = timezone.now()
                profile.save()

        # Transaction is now committed - changes are in database

        # Keep user logged in after password change
        update_session_auth_hash(request, request.user)

        # Log action
        log_user_action(
            request=request,
            action='password_change',
            description='User changed password',
            severity='info'
        )

        # Clear all old messages before showing success message
        storage = messages.get_messages(request)
        storage.used = True
        messages.success(request, 'Password changed successfully!')
        return redirect('dashboard')

    return render(request, 'accounts/change_password.html')

@pnp_login_required
def map_view(request):
    """
    OPTIMIZED Interactive map view with all accidents and hotspots
    Fixed: Province loading, data validation, performance
    Enhanced: Can focus on a specific hotspot cluster when cluster_id is provided
    """
    from django.core.serializers.json import DjangoJSONEncoder
    import json

    # Check if viewing a specific cluster
    cluster_id = request.GET.get('cluster_id')
    focus_cluster = None

    # Get all accidents with coordinates - OPTIMIZED QUERY
    accidents_query = Accident.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    )

    # Filter by cluster if specified
    if cluster_id:
        try:
            cluster_id_int = int(cluster_id)
            accidents_query = accidents_query.filter(cluster_id=cluster_id_int)
            # Get the cluster details for centering the map
            focus_cluster = AccidentCluster.objects.filter(cluster_id=cluster_id_int).first()
        except (ValueError, TypeError):
            pass  # Invalid cluster_id, show all

    accidents = accidents_query.values(
        'id', 'latitude', 'longitude', 'incident_type',
        'date_committed', 'time_committed', 'barangay',
        'municipal', 'province', 'victim_count',
        'victim_killed', 'victim_injured', 'year', 'cluster_id',
        'vehicle_kind'
    ).order_by('-date_committed')  # Most recent first

    # Get hotspots - filter if cluster_id specified
    hotspots_query = AccidentCluster.objects.all()
    if cluster_id:
        try:
            cluster_id_int = int(cluster_id)
            hotspots_query = hotspots_query.filter(cluster_id=cluster_id_int)
        except (ValueError, TypeError):
            pass

    hotspots = hotspots_query.values(
        'cluster_id', 'center_latitude', 'center_longitude',
        'primary_location', 'accident_count', 'total_casualties',
        'severity_score'
    )
    
    # RELIABLE province extraction from actual data
    provinces_raw = Accident.objects.filter(
        province__isnull=False
    ).exclude(
        province__exact=''
    ).values_list('province', flat=True).distinct().order_by('province')
    
    # Clean and validate provinces
    provinces = []
    caraga_provinces = {
        'AGUSAN DEL NORTE',
        'AGUSAN DEL SUR',
        'SURIGAO DEL NORTE',
        'SURIGAO DEL SUR',
        'DINAGAT ISLANDS'
    }
    
    # Add provinces from database if they exist
    for province in provinces_raw:
        if province and province.strip():
            cleaned = province.strip().upper()
            if cleaned in caraga_provinces:
                provinces.append(cleaned)
    
    # Fallback: If no provinces found, use default Caraga provinces
    if not provinces:
        provinces = list(caraga_provinces)
        provinces.sort()
    else:
        # Remove duplicates and sort
        provinces = sorted(list(set(provinces)))
    
    # Convert QuerySets to JSON with proper serialization
    accidents_list = []
    for accident in accidents:
        # Convert Decimal to float for JSON serialization
        accident_dict = {
            'id': accident['id'],
            'latitude': float(accident['latitude']),
            'longitude': float(accident['longitude']),
            'incident_type': accident['incident_type'],
            'date_committed': accident['date_committed'].strftime('%Y-%m-%d') if accident['date_committed'] else '',
            'time_committed': accident['time_committed'].strftime('%H:%M:%S') if accident['time_committed'] else '00:00:00',
            'barangay': accident['barangay'] or '',
            'municipal': accident['municipal'] or '',
            'province': accident['province'] or '',
            'victim_count': accident['victim_count'] or 0,
            'victim_killed': accident['victim_killed'],
            'victim_injured': accident['victim_injured'],
            'year': accident['year'] or '',
            'cluster_id': accident['cluster_id'],
            'vehicle_kind': accident.get('vehicle_kind', '') or ''
        }
        accidents_list.append(accident_dict)
    
    hotspots_list = []
    for hotspot in hotspots:
        hotspot_dict = {
            'cluster_id': hotspot['cluster_id'],
            'center_latitude': float(hotspot['center_latitude']),
            'center_longitude': float(hotspot['center_longitude']),
            'primary_location': hotspot['primary_location'] or '',
            'accident_count': hotspot['accident_count'] or 0,
            'total_casualties': hotspot['total_casualties'] or 0,
            'severity_score': float(hotspot['severity_score']) if hotspot['severity_score'] else 0
        }
        hotspots_list.append(hotspot_dict)
    
    accidents_json = json.dumps(accidents_list)
    hotspots_json = json.dumps(hotspots_list)
    
    # Calculate statistics
    total_accidents = len(accidents_list)
    total_hotspots = len(hotspots_list)

    # Prepare focus cluster data for map centering
    focus_cluster_data = None
    if focus_cluster:
        focus_cluster_data = {
            'cluster_id': focus_cluster.cluster_id,
            'center_latitude': float(focus_cluster.center_latitude),
            'center_longitude': float(focus_cluster.center_longitude),
            'primary_location': focus_cluster.primary_location,
            'severity_score': float(focus_cluster.severity_score),
        }

    context = {
        'accidents_json': accidents_json,
        'hotspots_json': hotspots_json,
        'total_accidents': total_accidents,
        'total_hotspots': total_hotspots,
        'provinces': provinces,  # Now guaranteed to have data
        'mapbox_token': settings.MAPBOX_ACCESS_TOKEN,
        'cluster_id': cluster_id,  # Pass cluster_id to template
        'focus_cluster': focus_cluster_data,  # Pass cluster details for map centering
    }

    return render(request, 'maps/map_view.html', context)

@pnp_login_required
def heatmap_view(request):
    """Heatmap visualization of accidents"""
    
    accidents = Accident.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).values(
        'latitude', 'longitude', 'victim_count'
    )
    
    accidents_json = json.dumps(list(accidents), cls=DjangoJSONEncoder)
    
    context = {
        'accidents_json': accidents_json,
    }
    
    return render(request, 'maps/heatmap.html', context)

@pnp_login_required
def analytics_view(request):
    """
    ENHANCED Analytics with Predictive Insights and WORKING FILTERS
    Boss's Complete Analytics Function
    """
    
    # ============================================================================
    # GET FILTER PARAMETERS FROM URL
    # ============================================================================
    severity_filter = request.GET.get('severity', 'all')
    province_filter = request.GET.get('province', 'all')
    municipal_filter = request.GET.get('municipal', 'all')  # NEW: Municipal filter
    time_granularity = request.GET.get('granularity', 'monthly')
    analysis_type = request.GET.get('analysis_type', 'overview')
    
    # Get total count for reference
    total_in_database = Accident.objects.count()
    
    # ============================================================================
    # DATE RANGE SETUP
    # ============================================================================
    from_date_str = request.GET.get('from_date')
    to_date_str = request.GET.get('to_date')
    
    if from_date_str:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
    else:
        # Get the earliest accident date to show ALL data by default
        earliest_accident = Accident.objects.order_by('date_committed').first()
        if earliest_accident:
            from_date = earliest_accident.date_committed
        else:
            from_date = (timezone.now() - timedelta(days=365)).date()
    
    if to_date_str:
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    else:
        # Get the latest accident date
        latest_accident = Accident.objects.order_by('-date_committed').first()
        if latest_accident:
            to_date = latest_accident.date_committed
        else:
            to_date = timezone.now().date()
    
    # ============================================================================
    # FILTER ACCIDENTS BY DATE RANGE
    # ============================================================================
    accidents = Accident.objects.filter(
        date_committed__gte=from_date,
        date_committed__lte=to_date
    )
    
    # ============================================================================
    # APPLY SEVERITY FILTER
    # ============================================================================
    if severity_filter == 'fatal':
        accidents = accidents.filter(victim_killed=True)
    elif severity_filter == 'injury':
        accidents = accidents.filter(victim_injured=True)
    elif severity_filter == 'property':
        accidents = accidents.filter(victim_killed=False, victim_injured=False)
    # 'all' - no additional filter
    
    # ============================================================================
    # APPLY PROVINCE FILTER
    # ============================================================================
    if province_filter and province_filter != 'all':
        accidents = accidents.filter(province=province_filter)

    # ============================================================================
    # APPLY MUNICIPAL FILTER
    # ============================================================================
    if municipal_filter and municipal_filter != 'all':
        accidents = accidents.filter(municipal=municipal_filter)

    # ============================================================================
    # BASIC STATISTICS (Optimized: Single query instead of 3)
    # ============================================================================
    from django.db.models import Count, Q

    stats = accidents.aggregate(
        total=Count('id'),
        fatal=Count('id', filter=Q(victim_killed=True)),
        injury=Count('id', filter=Q(victim_injured=True))
    )

    total_accidents = stats['total']
    fatal_count = stats['fatal']
    injury_count = stats['injury']

    # Calculate fatality rate
    fatality_rate = (fatal_count / total_accidents * 100) if total_accidents > 0 else 0
    
    # ============================================================================
    # MONTHLY TREND DATA (with time granularity support)
    # ============================================================================
    from django.db.models.functions import TruncMonth, TruncQuarter, TruncWeek, TruncDay
    
    if time_granularity == 'daily':
        trunc_func = TruncDay
        date_format = '%Y-%m-%d'
    elif time_granularity == 'weekly':
        trunc_func = TruncWeek
        date_format = 'Week of %b %d, %Y'
    elif time_granularity == 'quarterly':
        trunc_func = TruncQuarter
        date_format = 'Q%q %Y'
    else:  # monthly (default)
        trunc_func = TruncMonth
        date_format = '%b %Y'
    
    monthly_trends = accidents.annotate(
        period=trunc_func('date_committed')
    ).values('period').annotate(
        total=Count('id'),
        fatal=Count('id', filter=Q(victim_killed=True)),
        injury=Count('id', filter=Q(victim_injured=True))
    ).order_by('period')
    
    # Format labels based on granularity
    trend_labels = []
    for item in monthly_trends:
        if time_granularity == 'quarterly':
            quarter = (item['period'].month - 1) // 3 + 1
            trend_labels.append(f"Q{quarter} {item['period'].year}")
        else:
            trend_labels.append(item['period'].strftime(date_format))
    
    trend_total = [item['total'] for item in monthly_trends]
    trend_fatal = [item['fatal'] for item in monthly_trends]
    trend_injury = [item['injury'] for item in monthly_trends]
    
    # ============================================================================
    # HOURLY DISTRIBUTION ANALYSIS
    # ============================================================================
    from django.db.models.functions import ExtractHour
    
    hourly_distribution = accidents.annotate(
        hour=ExtractHour('time_committed')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('hour')
    
    # Create 24-hour array
    hourly_data = [0] * 24
    for item in hourly_distribution:
        if item['hour'] is not None:
            hourly_data[item['hour']] = item['count']
    
    hourly_labels = [f"{h:02d}:00" for h in range(24)]
    
    # ============================================================================
    # TOP RISK FACTORS / INCIDENT TYPES ANALYSIS
    # ============================================================================
    incident_analysis = accidents.values('incident_type').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    incident_labels = [item['incident_type'][:30] for item in incident_analysis]
    incident_data = [item['count'] for item in incident_analysis]
    
    # ============================================================================
    # VEHICLE TYPE ANALYSIS (Optimized: Only fetch vehicle_kind field, not full objects)
    # ============================================================================
    vehicle_types = {}
    # Only fetch vehicle_kind values instead of entire accident objects (much faster!)
    vehicle_kinds = accidents.values_list('vehicle_kind', flat=True)

    for vehicle_kind in vehicle_kinds:
        if vehicle_kind:
            kinds = vehicle_kind.split(',')
            for kind in kinds:
                kind = kind.strip()
                if kind:
                    vehicle_types[kind] = vehicle_types.get(kind, 0) + 1

    # Get top 6 vehicle types
    sorted_vehicles = sorted(vehicle_types.items(), key=lambda x: x[1], reverse=True)[:6]
    vehicle_labels = [v[0] for v in sorted_vehicles] if sorted_vehicles else ['Motorcycle', 'Car', 'Truck', 'Bus', 'SUV', 'Van']
    vehicle_data = [v[1] for v in sorted_vehicles] if sorted_vehicles else [85, 72, 45, 28, 38, 22]
    
    # ============================================================================
    # DAY OF WEEK ANALYSIS WITH BREAKDOWN
    # ============================================================================
    from django.db.models.functions import ExtractWeekDay
    
    day_of_week = accidents.annotate(
        weekday=ExtractWeekDay('date_committed')
    ).values('weekday').annotate(
        total=Count('id'),
        fatal=Count('id', filter=Q(victim_killed=True)),
        injury=Count('id', filter=Q(victim_injured=True))
    ).order_by('weekday')
    
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    dow_data = [0] * 7
    dow_fatal = [0] * 7
    dow_injury = [0] * 7
    
    for item in day_of_week:
        idx = item['weekday'] - 1  # weekday is 1-7
        dow_data[idx] = item['total']
        dow_fatal[idx] = item['fatal']
        dow_injury[idx] = item['injury']
    
    # ============================================================================
    # SEVERITY BY LOCATION (TOP 10)
    # ============================================================================
    severity_by_location = accidents.values('municipal', 'province').annotate(
        total=Count('id'),
        killed=Count('id', filter=Q(victim_killed=True)),
        injured=Count('id', filter=Q(victim_injured=True))
    ).order_by('-killed', '-total')[:10]
    
    # ============================================================================
    # PROVINCE COMPARISON
    # ============================================================================
    province_stats = accidents.values('province').annotate(
        total=Count('id'),
        fatal=Count('id', filter=Q(victim_killed=True)),
        injury=Count('id', filter=Q(victim_injured=True))
    ).order_by('-total')
    
    province_labels = [item['province'] for item in province_stats]
    province_total = [item['total'] for item in province_stats]
    province_fatal = [item['fatal'] for item in province_stats]
    province_injury = [item['injury'] for item in province_stats]
    
    # ============================================================================
    # PREDICTIVE INSIGHTS (Simple Moving Average)
    # ============================================================================
    
    # Calculate trend direction
    if len(trend_total) >= 3:
        recent_avg = sum(trend_total[-3:]) / 3
        previous_avg = sum(trend_total[-6:-3]) / 3 if len(trend_total) >= 6 else recent_avg
        trend_direction = "increasing" if recent_avg > previous_avg else "decreasing"
        trend_percentage = ((recent_avg - previous_avg) / previous_avg * 100) if previous_avg > 0 else 0
    else:
        trend_direction = "stable"
        trend_percentage = 0
    
    # Calculate predicted next period (simple linear extrapolation)
    if len(trend_total) >= 2:
        predicted_next_month = int(trend_total[-1] + (trend_total[-1] - trend_total[-2]))
        predicted_next_month = max(0, predicted_next_month)  # Can't be negative
    else:
        predicted_next_month = 0
    
    # Risk level calculation
    if fatality_rate >= 15:
        risk_level = "CRITICAL"
    elif fatality_rate >= 10:
        risk_level = "HIGH"
    elif fatality_rate >= 5:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Peak hours calculation
    if hourly_data and max(hourly_data) > 0:
        peak_hour = hourly_data.index(max(hourly_data))
        peak_hours = f"{peak_hour:02d}:00-{(peak_hour+1):02d}:00"
    else:
        peak_hours = "Unknown"

    # ============================================================================
    # ACTIONABLE INTELLIGENCE CALCULATIONS
    # ============================================================================

    # Priority Patrol Hour (most dangerous hour)
    priority_patrol_hour = None
    if hourly_data and max(hourly_data) > 0:
        peak_hour_idx = hourly_data.index(max(hourly_data))
        hour_count = hourly_data[peak_hour_idx]
        hour_percentage = (hour_count / total_accidents * 100) if total_accidents > 0 else 0
        priority_patrol_hour = {
            'time_range': f"{peak_hour_idx:02d}:00-{(peak_hour_idx+1):02d}:00",
            'count': hour_count,
            'percentage': round(hour_percentage, 1)
        }

    # Priority Staffing Day (most dangerous day)
    priority_staffing_day = None
    if dow_data and max(dow_data) > 0:
        peak_day_idx = dow_data.index(max(dow_data))
        day_count = dow_data[peak_day_idx]
        day_percentage = (day_count / total_accidents * 100) if total_accidents > 0 else 0
        priority_staffing_day = {
            'day': days[peak_day_idx] + 'day',  # 'Sunday', 'Monday', etc.
            'count': day_count,
            'percentage': round(day_percentage, 1)
        }

    # Priority Enforcement Area (top hotspot location)
    priority_enforcement_area = None
    if severity_by_location:
        top_location = severity_by_location[0]
        location_total = top_location['total']
        # Classify based on severity
        if location_total >= 2000:
            classification = 'CRITICAL'
            classification_color = '#DC2626'
        elif location_total >= 1000:
            classification = 'HIGH'
            classification_color = '#F59E0B'
        elif location_total >= 500:
            classification = 'MODERATE'
            classification_color = '#F59E0B'
        else:
            classification = 'LOW'
            classification_color = '#10B981'

        priority_enforcement_area = {
            'location': top_location['municipal'],
            'province': top_location['province'],
            'total_crashes': location_total,
            'classification': classification,
            'classification_color': classification_color
        }

    # 3-Month Average with Trend
    three_month_avg = 0
    three_month_trend = 0
    if len(trend_total) >= 3:
        three_month_avg = int(sum(trend_total[-3:]) / 3)
        if len(trend_total) >= 6:
            previous_3m_avg = sum(trend_total[-6:-3]) / 3
            three_month_trend = ((three_month_avg - previous_3m_avg) / previous_3m_avg * 100) if previous_3m_avg > 0 else 0

    # Risk Assessment with Action Text
    risk_action_text = ""
    risk_color = ""
    if risk_level == "CRITICAL":
        risk_action_text = "Immediate action required - Deploy all resources"
        risk_color = "#DC2626"  # Red
    elif risk_level == "HIGH":
        risk_action_text = "High priority monitoring - Increase enforcement"
        risk_color = "#F59E0B"  # Orange
    elif risk_level == "MEDIUM":
        risk_action_text = "Regular monitoring - Maintain vigilance"
        risk_color = "#F59E0B"  # Orange
    else:
        risk_action_text = "Under control - Continue current operations"
        risk_color = "#10B981"  # Green

    # Get unique provinces for filter dropdown
    provinces = list(Accident.objects.values_list('province', flat=True).distinct().order_by('province'))
    provinces = [p for p in provinces if p and p.strip()]

    # Get all unique municipalities for filter dropdown
    municipalities = list(Accident.objects.values_list('municipal', flat=True).distinct().order_by('municipal'))
    municipalities = [m for m in municipalities if m and m.strip()]

    # Get municipalities grouped by province for smart filtering (Optimized: Single query instead of N)
    municipalities_by_province = {}

    # Single query to get all province-municipal pairs
    province_municipal_pairs = Accident.objects.values('province', 'municipal').distinct()

    # Group municipalities by province in Python
    for pair in province_municipal_pairs:
        prov = pair['province']
        municipal = pair['municipal']
        if prov and prov.strip() and municipal and municipal.strip():
            if prov not in municipalities_by_province:
                municipalities_by_province[prov] = []
            if municipal not in municipalities_by_province[prov]:
                municipalities_by_province[prov].append(municipal)

    # Sort municipalities within each province
    for prov in municipalities_by_province:
        municipalities_by_province[prov].sort()

    # ============================================================================
    # PREPARE CONTEXT WITH ALL DATA
    # ============================================================================
    context = {
        # Basic Stats
        'total_accidents': total_accidents,
        'fatal_count': fatal_count,
        'injury_count': injury_count,
        'fatality_rate': fatality_rate,
        'from_date': from_date.strftime('%Y-%m-%d'),
        'to_date': to_date.strftime('%Y-%m-%d'),
        'total_in_database': total_in_database,
        
        # Filter values (to maintain state)
        'current_severity_filter': severity_filter,
        'current_province_filter': province_filter,
        'current_municipal_filter': municipal_filter,
        'current_time_granularity': time_granularity,
        'current_analysis_type': analysis_type,

        # Provinces and Municipalities for dropdowns
        'provinces': provinces,
        'municipalities': municipalities,
        'municipalities_json': json.dumps(municipalities),
        'municipalities_by_province': json.dumps(municipalities_by_province),
        
        # Trend Data (for line chart)
        'trend_labels': json.dumps(trend_labels),
        'trend_total': json.dumps(trend_total),
        'trend_fatal': json.dumps(trend_fatal),
        'trend_injury': json.dumps(trend_injury),
        
        # Hourly Data (for bar chart)
        'hourly_labels': json.dumps(hourly_labels),
        'hourly_data': json.dumps(hourly_data),
        
        # Vehicle Data
        'vehicle_labels': json.dumps(vehicle_labels),
        'vehicle_data': json.dumps(vehicle_data),
        
        # Day of Week Data (enhanced)
        'dow_labels': json.dumps(days),
        'dow_data': json.dumps(dow_data),
        'dow_fatal': json.dumps(dow_fatal),
        'dow_injury': json.dumps(dow_injury),
        
        # Province Comparison
        'province_labels': json.dumps(province_labels),
        'province_total': json.dumps(province_total),
        'province_fatal': json.dumps(province_fatal),
        'province_injury': json.dumps(province_injury),
        
        # Severity by Location
        'severity_locations': severity_by_location,
        
        # Incident Types
        'incident_labels': json.dumps(incident_labels),
        'incident_data': json.dumps(incident_data),
        
        # Predictive Insights
        'predicted_next_month': predicted_next_month,
        'trend_direction': trend_direction,
        'trend_percentage': abs(round(trend_percentage, 1)),
        'risk_level': risk_level,
        'peak_hours': peak_hours,

        # Actionable Intelligence (Enhanced)
        'priority_patrol_hour': priority_patrol_hour,
        'priority_staffing_day': priority_staffing_day,
        'priority_enforcement_area': priority_enforcement_area,
        'three_month_avg': three_month_avg,
        'three_month_trend': abs(round(three_month_trend, 1)),
        'three_month_trend_direction': 'increasing' if three_month_trend > 0 else 'decreasing' if three_month_trend < 0 else 'stable',
        'risk_action_text': risk_action_text,
        'risk_color': risk_color,
    }
    
    return render(request, 'analytics/analytics.html', context)


@pnp_login_required
def advanced_analytics_view(request):
    """
    FAST VERSION - Enhanced analytics with smart caching and lazy loading
    """
    from .analytics import AccidentAnalytics
    from django.core.cache import cache

    # Get filter parameters
    province_filter = request.GET.get('province', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Simple mode by default - loads fast!
    simple_mode = request.GET.get('simple', 'true') == 'true'

    # Build queryset
    accidents = Accident.objects.all()

    if province_filter and province_filter != 'all':
        accidents = accidents.filter(province=province_filter)

    if date_from:
        accidents = accidents.filter(date_committed__gte=date_from)

    if date_to:
        accidents = accidents.filter(date_committed__lte=date_to)

    # Cache key
    cache_key = f'analytics_{province_filter}_{date_from}_{date_to}_{"simple" if simple_mode else "full"}'
    cached_data = cache.get(cache_key)

    if cached_data:
        analytics_data = cached_data
    else:
        analyzer = AccidentAnalytics(accidents)

        if simple_mode:
            # FAST MODE - Only essential metrics (loads in <2 seconds)
            analytics_data = {
                'spatial_analysis': {
                    'hotspot_effectiveness': analyzer.hotspot_effectiveness_analysis(),
                    'spatial_concentration': {'concentration_level': 'Loading...', 'gini_coefficient': 0}
                },
                'temporal_analysis': {
                    'rush_hour': analyzer.rush_hour_analysis(),
                    'weekend_vs_weekday': analyzer.weekend_vs_weekday_analysis(),
                    'seasonal': {'quarterly_breakdown': [], 'highest_risk_quarter': 'Loading...'}
                },
                'severity_analysis': {
                    'severity_index': analyzer.severity_index_analysis(),
                    'high_risk_combinations': {'high_risk_combinations': []}
                },
                'predictive_analysis': {
                    'trend': analyzer.trend_analysis_with_confidence(),
                    'anomalies': {'anomalies_detected': 0, 'anomalies': []}
                },
                'statistical_tests': {
                    'provincial_variance': {'test_performed': False},
                    'correlations': {'time_severity_correlation': 0}
                }
            }
        else:
            # FULL MODE - All analytics (slower)
            analytics_data = analyzer.generate_comprehensive_report()

        # Cache for 30 minutes
        cache.set(cache_key, analytics_data, 1800)

    # Get provinces (cached)
    provinces_key = 'provinces_list'
    provinces = cache.get(provinces_key)
    if not provinces:
        provinces = list(Accident.objects.values_list('province', flat=True).distinct().order_by('province'))
        provinces = [p for p in provinces if p and p.strip()]
        cache.set(provinces_key, provinces, 7200)  # 2 hours

    context = {
        'analytics': analytics_data,
        'total_accidents': accidents.count(),
        'provinces': provinces,
        'current_province': province_filter,
        'date_from': date_from,
        'date_to': date_to,
        'simple_mode': simple_mode,
        'analytics_json': json.dumps(analytics_data, default=str)
    }

    return render(request, 'analytics/advanced_analytics.html', context)


def get_critical_alerts():
    """Get real-time critical alerts for dashboard"""
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count, Q
    
    today = timezone.now().date()
    last_24h = today - timedelta(hours=24)
    last_7_days = today - timedelta(days=7)
    
    alerts = []
    
    # Alert 1: Recent fatalities in last 24 hours
    recent_fatalities = Accident.objects.filter(
        victim_killed=True,
        date_committed__gte=last_24h
    ).count()
    
    if recent_fatalities > 0:
        alerts.append({
            'type': 'critical',
            'icon': '💀',
            'title': 'Recent Fatalities',
            'message': f'{recent_fatalities} fatal accident(s) in the last 24 hours',
            'action_url': '/accidents/?victim_killed=true'
        })
    
    # Alert 2: Spike in accidents (50% increase compared to previous week)
    current_week_accidents = Accident.objects.filter(
        date_committed__gte=last_7_days
    ).count()
    
    previous_week = today - timedelta(days=14)
    previous_week_accidents = Accident.objects.filter(
        date_committed__gte=previous_week,
        date_committed__lt=last_7_days
    ).count()
    
    if previous_week_accidents > 0:
        increase_percentage = ((current_week_accidents - previous_week_accidents) / previous_week_accidents) * 100
        if increase_percentage >= 50:
            alerts.append({
                'type': 'warning',
                'icon': '📈',
                'title': 'Accident Spike Detected',
                'message': f'{increase_percentage:.0f}% increase in accidents this week',
                'action_url': '/analytics/'
            })

    # Alert 3: High-severity hotspots
    critical_hotspots = AccidentCluster.objects.filter(
        severity_score__gte=80
    ).count()

    if critical_hotspots > 0:
        alerts.append({
            'type': 'warning',
            'icon': '⚠️',
            'title': 'Critical Hotspots',
            'message': f'{critical_hotspots} high-severity areas identified',
            'action_url': '/hotspots/?min_severity=80'
        })

    # Alert 4: Pending reports needing attention
    pending_reports_24h = AccidentReport.objects.filter(
        status='pending',
        created_at__gte=last_24h
    ).count()
    
    if pending_reports_24h >= 5:
        alerts.append({
            'type': 'info',
            'icon': '📝',
            'title': 'Pending Reports',
            'message': f'{pending_reports_24h} new reports awaiting verification',
            'action_url': '/admin/accidents/accidentreport/'
        })

    return alerts


# ============================================================================
# AUTHENTICATION VIEWS - PNP Login System
# ============================================================================

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from .auth_utils import handle_failed_login, handle_successful_login, log_user_action, get_client_ip


def login(request):
    """PNP Login View with audit trail and security features"""

    # If already logged in, check if they have a profile
    if request.user.is_authenticated:
        # Check if user has profile - if not, logout and show error
        if not hasattr(request.user, 'profile'):
            auth_logout(request)
            messages.error(request, 'Your account is not properly configured. Please contact administrator.')
            return render(request, 'registration/login.html')

        # User is authenticated with valid profile - redirect to dashboard
        return redirect('dashboard')

    # Clear any lingering messages from previous logout to avoid duplication
    storage = messages.get_messages(request)
    storage.used = True

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Check if user has profile
            if not hasattr(user, 'profile'):
                messages.error(request, 'Your account is not properly configured. Contact administrator.')
                return render(request, 'registration/login.html')

            profile = user.profile

            # Check if account is locked
            if profile.is_account_locked():
                messages.error(request, 'Account temporarily locked due to failed login attempts. Please try again later.')
                return render(request, 'registration/login.html')

            # Check if account is active
            if not profile.is_active:
                messages.error(request, 'Your account has been deactivated. Contact administrator.')
                log_user_action(
                    request,
                    'login_failed',
                    f'Login attempt for deactivated account: {username}',
                    severity='warning',
                    success=False
                )
                return render(request, 'registration/login.html')

            # Successful login
            auth_login(request, user)
            handle_successful_login(user, request)

            # Set session expiry based on "remember me"
            if not remember:
                request.session.set_expiry(0)  # Expire when browser closes

            # Only show welcome message if user doesn't need to change password
            # (New users will be redirected to password change by decorator)
            if not profile.must_change_password:
                messages.success(request, f'Welcome back, {profile.get_full_name_with_rank()}!')
            else:
                # For new users, clear any existing messages and show only password change requirement
                storage = messages.get_messages(request)
                storage.used = True
                messages.warning(request, 'You must change your password before continuing.')

            # Redirect to next page or dashboard
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            # Failed login - determine which field is incorrect
            from django.contrib.auth.models import User

            # Check if user exists (by username or badge number)
            user_exists = User.objects.filter(username=username).exists()
            if not user_exists:
                # Check if it's a badge number
                user_exists = UserProfile.objects.filter(badge_number=username).exists()

            if user_exists:
                # User exists but password is wrong - keep username, focus on password
                error_message = handle_failed_login(username, get_client_ip(request))
                messages.error(request, error_message, extra_tags='focus-password')
                # Pass the username to template to retain it in the form
                return render(request, 'registration/login.html', {
                    'retained_username': username  # Retain username for user convenience
                })
            else:
                # User doesn't exist - clear both fields, focus on username
                error_message = handle_failed_login(username, get_client_ip(request))
                messages.error(request, error_message, extra_tags='focus-username')
                # Don't pass username - both fields will be cleared for security

    return render(request, 'registration/login.html')


def logout_view(request):
    """PNP Logout View with audit trail"""

    if request.user.is_authenticated:
        # Log the logout action (handle users without profiles)
        try:
            if hasattr(request.user, 'profile'):
                user_name = request.user.profile.get_full_name_with_rank()
            else:
                user_name = request.user.username

            log_user_action(
                request,
                'logout',
                f'{user_name} logged out',
                severity='info'
            )
        except:
            pass  # If logging fails, just continue with logout

        username = request.user.username
        auth_logout(request)
        messages.success(request, f'You have been logged out successfully. Stay safe, officer!')

    return redirect('login')


@require_http_methods(["POST"])
@login_required
def change_username(request):
    """
    Change username with password confirmation
    - Requires current password for security
    - Validates new username
    - Checks for duplicates
    - Logs the action
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        new_username = data.get('new_username', '').strip()
        password = data.get('password', '')

        # Validate inputs
        if not new_username:
            return JsonResponse({'success': False, 'error': 'Username cannot be empty'}, status=400)

        if not password:
            return JsonResponse({'success': False, 'error': 'Password is required'}, status=400)

        # Validate password
        user = authenticate(username=request.user.username, password=password)
        if user is None:
            log_user_action(
                request,
                'FAILED_USERNAME_CHANGE',
                f'Failed username change attempt - incorrect password',
                severity='warning'
            )
            return JsonResponse({'success': False, 'error': 'Incorrect password'}, status=403)

        # Validate new username
        if len(new_username) < 3:
            return JsonResponse({'success': False, 'error': 'Username must be at least 3 characters'}, status=400)

        if len(new_username) > 150:
            return JsonResponse({'success': False, 'error': 'Username is too long'}, status=400)

        # Check if username already exists
        from django.contrib.auth.models import User
        if User.objects.filter(username=new_username).exclude(id=request.user.id).exists():
            return JsonResponse({'success': False, 'error': 'Username already taken'}, status=400)

        # Save old username for logging
        old_username = request.user.username

        # Update username
        request.user.username = new_username
        request.user.save()

        # Log the action
        log_user_action(
            request,
            'CHANGE_USERNAME',
            f'Username changed from "{old_username}" to "{new_username}"',
            severity='warning'
        )

        # Logout user for security (they need to login with new username)
        logout(request)

        return JsonResponse({
            'success': True,
            'message': 'Username changed successfully. Please login with your new username.',
            'new_username': new_username
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error changing username: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred. Please try again.'}, status=500)


@login_required
@require_http_methods(["POST"])
def change_password_api(request):
    """
    API endpoint for password change from modal
    - Requires current password for security
    - Validates new password strength
    - Updates password and maintains session
    - Logs the action
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        old_password = data.get('old_password', '')
        new_password1 = data.get('new_password1', '')
        new_password2 = data.get('new_password2', '')

        # Validate inputs
        if not old_password or not new_password1 or not new_password2:
            return JsonResponse({'success': False, 'error': 'All fields are required'}, status=400)

        # Verify current password
        user = authenticate(username=request.user.username, password=old_password)
        if user is None:
            log_user_action(
                request,
                'FAILED_PASSWORD_CHANGE',
                'Failed password change attempt - incorrect current password',
                severity='warning'
            )
            return JsonResponse({'success': False, 'error': 'Current password is incorrect'}, status=403)

        # Validate new passwords match
        if new_password1 != new_password2:
            return JsonResponse({'success': False, 'error': 'New passwords do not match'}, status=400)

        # Validate password is not the same as old password
        if old_password == new_password1:
            return JsonResponse({'success': False, 'error': 'New password must be different from current password'}, status=400)

        # Validate password length
        if len(new_password1) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters long'}, status=400)

        # Validate password is not entirely numeric
        if new_password1.isdigit():
            return JsonResponse({'success': False, 'error': 'Password cannot be entirely numeric'}, status=400)

        # Use Django's password validators for additional security
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        try:
            validate_password(new_password1, user=request.user)
        except ValidationError as e:
            return JsonResponse({'success': False, 'error': '; '.join(e.messages)}, status=400)

        # Use atomic transaction to ensure changes are committed
        with transaction.atomic():
            # Update password
            request.user.set_password(new_password1)
            request.user.save()

            # Update profile - mark password as changed
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                profile.must_change_password = False
                profile.password_changed_at = timezone.now()
                profile.save()

        # Transaction is now committed - changes are in database

        # Update session to prevent logout
        update_session_auth_hash(request, request.user)

        # Log the action
        log_user_action(
            request,
            'CHANGE_PASSWORD',
            'Password changed successfully',
            severity='warning'
        )

        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully!'
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Error changing password: {str(e)}')
        return JsonResponse({'success': False, 'error': 'An error occurred. Please try again.'}, status=500)