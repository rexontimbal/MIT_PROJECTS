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
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth import authenticate, logout
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
import json
from datetime import timedelta
from datetime import time as dt_time
from django.contrib.auth.models import User
from .models import Accident, AccidentCluster, AccidentReport, UserProfile, Notification, ReportActivityLog, ClusteringJob
from datetime import datetime
from django.contrib.auth.views import LoginView
from .auth_utils import pnp_login_required, log_user_action

@pnp_login_required
def dashboard(request):
    """Optimized dashboard with better performance and caching - Enhanced for PNP Operations"""

    # Check if it's an AJAX request for partial updates
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Get current date in local timezone (Asia/Manila) for calculations
    today = timezone.localdate()
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
        # Hybrid approach for the operational summary:
        #   - CSV-imported records (no linked report): filter by date_committed (incident date)
        #   - Report-approved records (linked report): filter by created_at (approval date)
        # This ensures newly approved reports immediately appear in Today/This Week/This Month
        # while bulk-imported historical data uses the actual incident date.

        # TODAY's accidents
        today_q = (
            Q(report__isnull=True, date_committed=today) |
            Q(report__isnull=False, created_at__date=today)
        )
        today_accidents = Accident.objects.filter(today_q).aggregate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True)),
            injury=Count('id', filter=Q(victim_injured=True))
        )

        # THIS WEEK's accidents (Monday to today)
        week_start = today - timedelta(days=today.weekday())
        week_q = (
            Q(report__isnull=True, date_committed__gte=week_start, date_committed__lte=today) |
            Q(report__isnull=False, created_at__date__gte=week_start, created_at__date__lte=today)
        )
        week_accidents = Accident.objects.filter(week_q).aggregate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True)),
            injury=Count('id', filter=Q(victim_injured=True))
        )

        # THIS MONTH's accidents
        month_start = today.replace(day=1)
        month_q = (
            Q(report__isnull=True, date_committed__gte=month_start, date_committed__lte=today) |
            Q(report__isnull=False, created_at__date__gte=month_start, created_at__date__lte=today)
        )
        month_accidents = Accident.objects.filter(month_q).aggregate(
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

        # Gender statistics
        gender_stats = Accident.objects.aggregate(
            male_drivers=Count('id', filter=Q(driver_gender='MALE')),
            female_drivers=Count('id', filter=Q(driver_gender='FEMALE')),
            unknown_drivers=Count('id', filter=Q(driver_gender='UNKNOWN')),
            male_victims=Count('id', filter=Q(victim_gender='MALE')),
            female_victims=Count('id', filter=Q(victim_gender='FEMALE')),
            unknown_victims=Count('id', filter=Q(victim_gender='UNKNOWN'))
        )

        # Calculate gender percentages
        total_with_driver_gender = gender_stats['male_drivers'] + gender_stats['female_drivers']
        male_driver_pct = (gender_stats['male_drivers'] / total_with_driver_gender * 100) if total_with_driver_gender > 0 else 0
        female_driver_pct = (gender_stats['female_drivers'] / total_with_driver_gender * 100) if total_with_driver_gender > 0 else 0

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

            # Gender statistics
            'male_drivers': gender_stats['male_drivers'] or 0,
            'female_drivers': gender_stats['female_drivers'] or 0,
            'unknown_drivers': gender_stats['unknown_drivers'] or 0,
            'male_victims': gender_stats['male_victims'] or 0,
            'female_victims': gender_stats['female_victims'] or 0,
            'male_driver_pct': round(male_driver_pct, 1),
            'female_driver_pct': round(female_driver_pct, 1),
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

    # Per-user reporter stats (not cached - user-specific)
    if request.user.is_authenticated:
        user_reports = AccidentReport.objects.filter(reported_by=request.user)
        context['my_total'] = user_reports.count()
        context['my_approved'] = user_reports.filter(status='verified').count()
        context['my_pending'] = user_reports.filter(status='pending').count()
        context['my_rejected'] = user_reports.filter(status='rejected').count()

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
    accidents = Accident.objects.select_related('report').all().order_by('-date_committed', '-created_at')

    # Role-based data scoping: traffic_officer sees only their station's data
    accidents = _apply_role_scoping(accidents, request.user)

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
    no_hotspot = request.GET.get('no_hotspot')
    case_status = request.GET.get('case_status')

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
    if no_hotspot:
        accidents = accidents.filter(is_hotspot=False)
    if case_status:
        accidents = accidents.filter(case_status=case_status)
    
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
    hotspot_count = AccidentCluster.objects.count()
    
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
        'is_standalone_view': no_hotspot,
        'case_status_filter': case_status or '',
    }

    return render(request, 'accidents/accident_list.html', context)

@pnp_login_required
def accident_detail(request, pk):
    """Display detailed information about a specific accident"""
    from math import radians, cos, sin, asin, sqrt
    from decimal import Decimal
    
    accident = get_object_or_404(Accident.objects.select_related('report'), pk=pk)

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

    # Determine if user can edit/update this accident (role + jurisdiction)
    can_edit_accident = False
    if hasattr(request.user, 'profile'):
        role = request.user.profile.role
        if role in ['super_admin', 'regional_director']:
            can_edit_accident = True
        elif role == 'provincial_chief' and (accident.province or '').upper() == (request.user.profile.province or '').upper():
            can_edit_accident = True
        elif role == 'station_commander' and accident.station == request.user.profile.station:
            can_edit_accident = True

    context = {
        'accident': accident,
        'nearby_accidents': nearby_accidents,
        'formatted_narrative': format_narrative(accident.narrative),
        'can_edit_accident': can_edit_accident,
    }

    return render(request, 'accidents/accident_detail.html', context)


def format_narrative(text):
    """Format narrative text for better readability with proper punctuation."""
    if not text or text == 'nan':
        return ''

    import re

    # Convert to string and strip
    text = str(text).strip()

    # Fix time patterns: "08 30 PM" → "08:30 PM", "0830H" → "08:30H"
    text = re.sub(r'(\d{2})\s?(\d{2})\s*(AM|PM|H)\b', r'\1:\2 \3', text, flags=re.IGNORECASE)
    text = re.sub(r'(\d{2})(\d{2})H\b', r'\1:\2H', text)

    # Add periods after common police report abbreviations at start
    text = re.sub(r'^(RIR)\s+(PI)\s+(DOP)\s+', r'\1 \2 \3. ', text)
    text = re.sub(r'^(RIR)\s+', r'\1. ', text)

    # Add comma after date patterns: "December 31 2024" → "December 31, 2024,"
    months = r'(January|February|March|April|May|June|July|August|September|October|November|December)'
    text = re.sub(rf'{months}\s+(\d{{1,2}})\s+(\d{{4}})\s+at', r'\1 \2, \3, at', text, flags=re.IGNORECASE)

    # Add comma after time expressions
    text = re.sub(r'(\d{1,2}:\d{2}\s*(?:AM|PM|H))\s+([A-Z])', r'\1, \2', text, flags=re.IGNORECASE)

    # Add comma before common transition words/phrases
    transitions = [
        r'\s+(Involved in the said incident)',
        r'\s+(bearing a plate)',
        r'\s+(with certificate of registration)',
        r'\s+(and official receipt)',
        r'\s+(driven by)',
        r'\s+(owned by)',
        r'\s+(registered under)',
        r'\s+(who was)',
        r'\s+(which resulted)',
        r'\s+(causing)',
    ]
    for pattern in transitions:
        text = re.sub(pattern, r', \1', text, flags=re.IGNORECASE)

    # Add period before "We received" or similar starts
    text = re.sub(r',?\s+(We received|Police received|This office received)', r'. \1', text, flags=re.IGNORECASE)

    # Add period at the end if missing
    text = text.strip()
    if text and text[-1] not in '.!?':
        text += '.'

    # Clean up multiple spaces
    text = re.sub(r'\s+', ' ', text)

    # Clean up punctuation issues
    text = re.sub(r'\s+,', ',', text)
    text = re.sub(r'\s+\.', '.', text)
    text = re.sub(r',,+', ',', text)
    text = re.sub(r'\.\.+', '.', text)
    text = re.sub(r',\.', '.', text)

    # Capitalize after periods
    def capitalize_after_period(match):
        return match.group(1) + match.group(2).upper()
    text = re.sub(r'(\.\s+)([a-z])', capitalize_after_period, text)

    return text


@pnp_login_required
def accident_details_json(request, pk):
    """Return accident details as JSON for the print report modal."""
    accident = get_object_or_404(Accident, pk=pk)

    data = {
        'narrative': format_narrative(accident.narrative),
        'victim_details': accident.victim_details or '',
        'suspect_details': accident.suspect_details or '',
        'case_status': accident.case_status or '',
        'offense': accident.offense or '',
        # Additional fields for PNP Caraga report format
        'offense_type': accident.offense_type or '',
        'stage_of_felony': accident.stage_of_felony or '',
        'date_reported': accident.date_reported.strftime('%B %d, %Y') if accident.date_reported else '',
        'time_reported': accident.time_reported.strftime('%I:%M %p') if accident.time_reported else '',
        'ppo': accident.ppo or '',
        'pro': accident.pro or '',
        'vehicle_make': accident.vehicle_make or '',
        'vehicle_model': accident.vehicle_model or '',
        'vehicle_plate_no': accident.vehicle_plate_no or '',
        'vehicle_chassis_no': accident.vehicle_chassis_no or '',
        'vehicle_colorum': accident.vehicle_colorum,
        'drug_involved': accident.drug_involved,
        'driver_gender': accident.get_driver_gender_display() if accident.driver_gender != 'UNKNOWN' else '',
        'driver_age': accident.driver_age,
        'victim_gender': accident.get_victim_gender_display() if accident.victim_gender != 'UNKNOWN' else '',
        'victim_age': accident.victim_age,
        'suspect_count': accident.suspect_count or 0,
        'victim_unharmed': accident.victim_unharmed,
    }

    return JsonResponse(data)


# ============================================================================
# SUPER ADMIN ONLY: CSV UPLOAD & EDIT FUNCTIONALITY (ON ACCIDENT PAGE)
# ============================================================================

@pnp_login_required
def accident_csv_upload(request):
    """Import accident data from CSV or Excel files (super_admin only).

    Supports .csv, .xlsx, and .xls files. Returns JSON when called via AJAX,
    otherwise redirects with Django messages.
    """
    from django.http import JsonResponse

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Permission check
    if not (hasattr(request.user, 'profile') and request.user.profile.role == 'super_admin'):
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Permission denied. Only super admins can import data.'}, status=403)
        messages.error(request, 'Permission denied. Only super admins can import data.')
        return redirect('accident_list')

    if request.method != 'POST':
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)
        return redirect('accident_list')

    if 'csv_file' not in request.FILES:
        if is_ajax:
            return JsonResponse({'success': False, 'error': 'No file uploaded.'}, status=400)
        messages.error(request, 'No file uploaded.')
        return redirect('accident_list')

    uploaded_file = request.FILES['csv_file']
    file_name = uploaded_file.name.lower()

    # Validate file type
    allowed_extensions = ('.csv', '.xlsx', '.xls')
    if not file_name.endswith(allowed_extensions):
        err = 'Invalid file type. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file.'
        if is_ajax:
            return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return redirect('accident_list')

    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024
    if uploaded_file.size > max_size:
        err = 'File too large. Maximum size is 50MB.'
        if is_ajax:
            return JsonResponse({'success': False, 'error': err}, status=400)
        messages.error(request, err)
        return redirect('accident_list')

    try:
        import pandas as pd
        import numpy as np
        from datetime import datetime
        from decimal import Decimal
        from .management.commands.import_accidents import Command as ImportCommand

        import_cmd = ImportCommand()

        # Read the entire file into memory first (Django UploadedFile streams
        # don't always support multiple seek/read cycles with pandas)
        import io
        raw_bytes = uploaded_file.read()

        # Read file based on extension
        if file_name.endswith('.csv'):
            # Try multiple encodings - cp1252/latin-1 handles ñ and other
            # special characters common in Filipino place names
            df = None
            for enc in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    df = pd.read_csv(io.BytesIO(raw_bytes), encoding=enc, comment='#', skip_blank_lines=True)
                    break
                except (UnicodeDecodeError, Exception):
                    continue
            if df is None:
                raise ValueError('Could not read CSV file. Please check the file encoding.')
        else:
            # Excel file (.xlsx or .xls)
            engine = 'openpyxl' if file_name.endswith('.xlsx') else None
            df = pd.read_excel(io.BytesIO(raw_bytes), engine=engine)

        total_rows = len(df)
        if total_rows == 0:
            err = 'The uploaded file contains no data rows.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return redirect('accident_list')

        # Normalize column names: strip whitespace
        df.columns = [str(c).strip() for c in df.columns]

        # Validate that the file contains accident data columns
        # These are accident-specific column names that would NOT appear in other files
        ACCIDENT_COLUMNS = {
            'dateCommitted', 'timeCommitted', 'incidentType', 'offense',
            'offenseType', 'stageoffelony', 'victimKilled', 'victimInjured',
            'victimUnharmed', 'victimCount', 'suspectCount', 'vehicleKind',
            'vehicleMake', 'vehicleModel', 'vehiclePlateNo', 'casestatus',
            'caseSolveType', 'dateReported', 'timeReported', 'typeofPlace',
            'narrative', 'suspect', 'victim',
        }
        # Also accept columns from system-exported files (CSV and Excel exports)
        EXPORTED_COLUMNS = {
            'date_committed', 'time_committed', 'incident_type',
            'victim_killed', 'victim_injured', 'victim_unharmed',
            'victim_count', 'vehicle_kind', 'vehicle_make', 'vehicle_model',
            'driver_gender', 'victim_gender', 'driver_age', 'victim_age',
            'is_hotspot', 'cluster_id',
        }
        # CSV export uses these human-readable column names
        CSV_EXPORT_COLUMNS = {
            'Incident Type', 'Casualties', 'Fatal', 'Injured',
            'Hotspot', 'Cluster ID',
        }
        file_columns = set(df.columns)
        matched_original = file_columns & ACCIDENT_COLUMNS
        matched_exported = file_columns & EXPORTED_COLUMNS
        matched_csv_export = file_columns & CSV_EXPORT_COLUMNS
        total_matched = len(matched_original) + len(matched_exported) + len(matched_csv_export)
        if total_matched < 5:
            err = 'The uploaded file does not appear to contain accident data. Please upload a valid accident dataset file.'
            if is_ajax:
                return JsonResponse({'success': False, 'error': err}, status=400)
            messages.error(request, err)
            return redirect('accident_list')

        # Map system-exported column names back to import column names
        # so exported files can be re-imported seamlessly
        EXPORT_TO_IMPORT_MAP = {
            # Excel export → import columns
            'date_committed': 'dateCommitted',
            'time_committed': 'timeCommitted',
            'incident_type': 'incidentType',
            'victim_killed': 'victimKilled',
            'victim_injured': 'victimInjured',
            'victim_unharmed': 'victimUnharmed',
            'victim_count': 'victimCount',
            'vehicle_kind': 'vehicleKind',
            'vehicle_make': 'vehicleMake',
            'vehicle_model': 'vehicleModel',
            'vehicle_plate_no': 'vehiclePlateNo',
            'type_of_place': 'typeofPlace',
            'date_reported': 'dateReported',
            'time_reported': 'timeReported',
            'offense_type': 'offenseType',
            'stage_of_felony': 'stageoffelony',
            'case_status': 'casestatus',
            'case_solve_type': 'caseSolveType',
            'suspect_count': 'suspectCount',
            # CSV export → import columns
            'Date': 'dateCommitted',
            'Time': 'timeCommitted',
            'Municipality': 'municipal',
            'Incident Type': 'incidentType',
            'Casualties': 'victimCount',
            'Fatal': 'victimKilled',
            'Injured': 'victimInjured',
            'Latitude': 'lat',
            'Longitude': 'lng',
            'Province': 'province',
            'Barangay': 'barangay',
            'Street': 'street',
        }
        # Rename exported columns to import-expected names
        rename_map = {k: v for k, v in EXPORT_TO_IMPORT_MAP.items() if k in df.columns and v not in df.columns}
        if rename_map:
            df = df.rename(columns=rename_map)

        # Replace NaN with None
        df = df.replace({np.nan: None})

        # Handle import mode: 'replace' clears ALL existing accident data first
        # Report-linked accidents are also deleted (SET_NULL keeps the reports).
        # Users can re-sync verified reports via the Re-sync button on Manage Reports.
        import_mode = request.POST.get('import_mode', 'add')
        deleted_count = 0
        unsynced_count = 0
        if import_mode == 'replace':
            # Count how many verified reports will lose their link
            unsynced_count = AccidentReport.objects.filter(accident__isnull=False).count()
            # Delete ALL accidents — SET_NULL on FK keeps reports safe
            deleted_count = Accident.objects.count()
            Accident.objects.all().delete()
            # Also clear clustering data (depends on accidents)
            AccidentCluster.objects.all().delete()
            ClusteringJob.objects.all().delete()
            from .models import ClusterValidationMetrics
            ClusterValidationMetrics.objects.all().delete()

        # ── Vectorized pre-processing (much faster than row-by-row) ──

        # Helper: safe string column — strip, truncate, fill default
        def _col_str(col_name, default=''):
            if col_name not in df.columns:
                return pd.Series([default] * len(df), index=df.index)
            s = df[col_name].fillna('').astype(str).str.strip().str[:500]
            if default:
                s = s.replace('', default)
            return s

        # Helper: safe boolean column
        def _col_bool(col_name):
            if col_name not in df.columns:
                return pd.Series([False] * len(df), index=df.index)
            return df[col_name].fillna('').astype(str).str.strip().str.upper().isin(['YES', 'TRUE', '1', 'Y', 'T'])

        # Helper: safe int column
        def _col_int(col_name, default=None):
            if col_name not in df.columns:
                return pd.Series([default] * len(df), index=df.index)
            return pd.to_numeric(df[col_name], errors='coerce').apply(
                lambda v: int(v) if pd.notna(v) else default
            )

        # Parse dates using pandas (vectorized, much faster)
        def _col_date(col_name):
            if col_name not in df.columns:
                return pd.Series([None] * len(df), index=df.index)
            return pd.to_datetime(df[col_name], errors='coerce', infer_datetime_format=True).apply(
                lambda v: v.date() if pd.notna(v) else None
            )

        # Parse times
        def _col_time(col_name):
            if col_name not in df.columns:
                return pd.Series([None] * len(df), index=df.index)
            def _parse_time(v):
                if pd.isna(v) or str(v).strip() == '':
                    return None
                time_str = str(v).strip()
                for fmt in ['%H:%M:%S', '%H:%M', '%I:%M:%S %p', '%I:%M %p']:
                    try:
                        return datetime.strptime(time_str, fmt).time()
                    except (ValueError, TypeError):
                        continue
                return None
            return df[col_name].apply(_parse_time)

        # Parse coordinates
        if 'lat' in df.columns:
            lat_series = pd.to_numeric(df['lat'], errors='coerce')
        elif 'latitude' in df.columns:
            lat_series = pd.to_numeric(df['latitude'], errors='coerce')
        else:
            lat_series = pd.Series([np.nan] * len(df), index=df.index)

        if 'lng' in df.columns:
            lng_series = pd.to_numeric(df['lng'], errors='coerce')
        elif 'longitude' in df.columns:
            lng_series = pd.to_numeric(df['longitude'], errors='coerce')
        else:
            lng_series = pd.Series([np.nan] * len(df), index=df.index)

        # Invalidate out-of-range coordinates
        lat_series = lat_series.where(lat_series.between(7.0, 11.0))
        lng_series = lng_series.where(lng_series.between(124.0, 128.0))

        # Pre-process all columns
        col_pro = _col_str('pro')
        col_ppo = _col_str('ppo')
        col_stn = _col_str('stn')
        col_region = _col_str('region', 'CARAGA')
        col_province = _col_str('province', 'UNKNOWN')
        col_municipal = _col_str('municipal', 'UNKNOWN')
        col_barangay = _col_str('barangay', 'UNKNOWN')
        col_street = _col_str('street')
        col_type_of_place = _col_str('typeofPlace')
        col_date_reported = _col_date('dateReported')
        col_time_reported = _col_time('timeReported')
        col_date_committed = _col_date('dateCommitted')
        col_time_committed = _col_time('timeCommitted')
        col_year = _col_int('Year')
        col_incident_type = _col_str('incidentType', 'UNKNOWN')
        col_offense = _col_str('offense')
        col_offense_type = _col_str('offenseType')
        col_stage_of_felony = _col_str('stageoffelony')
        col_victim_killed = _col_bool('victimKilled')
        col_victim_injured = _col_bool('victimInjured')
        col_victim_unharmed = _col_bool('victimUnharmed')
        col_victim_count = _col_int('victimCount', 0)
        col_suspect_count = _col_int('suspectCount', 0)
        col_vehicle_kind = _col_str('vehicleKind')
        col_vehicle_make = _col_str('vehicleMake')
        col_vehicle_model = _col_str('vehicleModel')
        col_vehicle_plate_no = _col_str('vehiclePlateNo')
        col_victim_details = _col_str('victim')
        col_suspect_details = _col_str('suspect')
        col_narrative = _col_str('narrative', 'No details available')
        col_case_status = _col_str('casestatus', 'UNKNOWN')
        col_case_solve_type = _col_str('caseSolveType')

        # Fallback date: use Year column, else 2020-01-01
        for i in col_date_committed.index:
            if col_date_committed[i] is None:
                yr = col_year[i]
                col_date_committed[i] = datetime(yr, 1, 1).date() if yr else datetime(2020, 1, 1).date()

        # Fix missing coordinates using approximate lookup
        for i in df.index:
            lat_val = lat_series.get(i)
            lng_val = lng_series.get(i)
            if pd.isna(lat_val) or pd.isna(lng_val):
                approx = import_cmd.get_approximate_coordinates(
                    col_province[i], col_municipal[i], col_barangay[i]
                )
                if approx:
                    lat_series.at[i] = approx[0]
                    lng_series.at[i] = approx[1]
                else:
                    lat_series.at[i] = 9.0
                    lng_series.at[i] = 125.5

        # ── Build fingerprints of existing accidents to avoid duplicates ──
        # Uses many fields to precisely identify the same accident record.
        # Coordinates are excluded because they can change between export/import
        # cycles (approximate lookup, rounding, etc.) which would cause false mismatches.
        # A duplicate is only detected when ALL these fields match exactly.
        existing_accidents = Accident.objects.all().values_list(
            'date_committed', 'time_committed', 'province', 'municipal',
            'barangay', 'street', 'incident_type', 'offense', 'vehicle_kind',
            'victim_count', 'suspect_count'
        )
        existing_fingerprints = set()
        for acc in existing_accidents:
            fp = (
                str(acc[0]) if acc[0] else '',
                str(acc[1]) if acc[1] else '',
                str(acc[2] or '').strip().upper(),
                str(acc[3] or '').strip().upper(),
                str(acc[4] or '').strip().upper(),
                str(acc[5] or '').strip().upper(),
                str(acc[6] or '').strip().upper(),
                str(acc[7] or '').strip().upper(),
                str(acc[8] or '').strip().upper(),
                str(acc[9]) if acc[9] is not None else '0',
                str(acc[10]) if acc[10] is not None else '0',
            )
            existing_fingerprints.add(fp)

        # ── Build Accident objects and bulk insert ──
        imported = 0
        skipped_duplicates = 0
        errors = 0
        error_samples = []
        batch = []
        batch_size = 2000

        for i in df.index:
            try:
                accident = Accident(
                    pro=col_pro[i],
                    ppo=col_ppo[i],
                    station=col_stn[i],
                    region=col_region[i],
                    province=col_province[i],
                    municipal=col_municipal[i],
                    barangay=col_barangay[i],
                    street=col_street[i],
                    type_of_place=col_type_of_place[i],
                    latitude=Decimal(str(lat_series[i])),
                    longitude=Decimal(str(lng_series[i])),
                    date_reported=col_date_reported[i],
                    time_reported=col_time_reported[i],
                    date_committed=col_date_committed[i],
                    time_committed=col_time_committed[i],
                    year=col_year[i],
                    incident_type=col_incident_type[i],
                    offense=col_offense[i],
                    offense_type=col_offense_type[i],
                    stage_of_felony=col_stage_of_felony[i],
                    victim_killed=col_victim_killed[i],
                    victim_injured=col_victim_injured[i],
                    victim_unharmed=col_victim_unharmed[i],
                    victim_count=col_victim_count[i],
                    suspect_count=col_suspect_count[i],
                    vehicle_kind=col_vehicle_kind[i],
                    vehicle_make=col_vehicle_make[i],
                    vehicle_model=col_vehicle_model[i],
                    vehicle_plate_no=col_vehicle_plate_no[i],
                    victim_details=col_victim_details[i],
                    suspect_details=col_suspect_details[i],
                    narrative=col_narrative[i],
                    case_status=col_case_status[i],
                    case_solve_type=col_case_solve_type[i],
                )

                # Skip if this row already exists (avoid duplicates)
                # All 11 fields must match exactly for a row to be considered duplicate
                row_fp = (
                    str(col_date_committed[i]) if col_date_committed[i] else '',
                    str(col_time_committed[i]) if col_time_committed[i] else '',
                    str(col_province[i] or '').strip().upper(),
                    str(col_municipal[i] or '').strip().upper(),
                    str(col_barangay[i] or '').strip().upper(),
                    str(col_street[i] or '').strip().upper(),
                    str(col_incident_type[i] or '').strip().upper(),
                    str(col_offense[i] or '').strip().upper(),
                    str(col_vehicle_kind[i] or '').strip().upper(),
                    str(col_victim_count[i]) if col_victim_count[i] is not None else '0',
                    str(col_suspect_count[i]) if col_suspect_count[i] is not None else '0',
                )
                if row_fp in existing_fingerprints:
                    skipped_duplicates += 1
                    continue

                # Add fingerprint so we also skip duplicates within the file itself
                existing_fingerprints.add(row_fp)
                batch.append(accident)

                if len(batch) >= batch_size:
                    Accident.objects.bulk_create(batch)
                    imported += len(batch)
                    batch = []

            except Exception as e:
                errors += 1
                if len(error_samples) < 5:
                    error_samples.append(f'Row {i + 2}: {str(e)[:120]}')

        # Insert remaining
        if batch:
            Accident.objects.bulk_create(batch)
            imported += len(batch)

        # Auto-extract gender & age from victim_details and suspect_details
        gender_extracted = 0
        try:
            import re
            extract_pattern = re.compile(r'\((\d+)/(Male|Female|male|female)')
            gender_updates = []
            for acc in Accident.objects.filter(
                Q(driver_gender='UNKNOWN') | Q(victim_gender='UNKNOWN')
            ).only('id', 'suspect_details', 'victim_details', 'driver_gender', 'victim_gender', 'driver_age', 'victim_age').iterator():
                updated = False
                # Extract driver/suspect gender & age
                if acc.suspect_details and acc.driver_gender == 'UNKNOWN':
                    match = extract_pattern.search(str(acc.suspect_details))
                    if match:
                        acc.driver_age = int(match.group(1))
                        acc.driver_gender = match.group(2).upper()
                        updated = True
                # Extract victim gender & age
                if acc.victim_details and acc.victim_gender == 'UNKNOWN':
                    match = extract_pattern.search(str(acc.victim_details))
                    if match:
                        acc.victim_age = int(match.group(1))
                        acc.victim_gender = match.group(2).upper()
                        updated = True
                if updated:
                    gender_updates.append(acc)
                    gender_extracted += 1
                if len(gender_updates) >= 500:
                    Accident.objects.bulk_update(
                        gender_updates,
                        ['driver_gender', 'driver_age', 'victim_gender', 'victim_age'],
                        batch_size=500
                    )
                    gender_updates = []
            if gender_updates:
                Accident.objects.bulk_update(
                    gender_updates,
                    ['driver_gender', 'driver_age', 'victim_gender', 'victim_age'],
                    batch_size=500
                )
        except Exception:
            pass  # Gender extraction is best-effort, don't fail the import

        # Clear dashboard cache so fresh data shows immediately
        from django.core.cache import cache
        cache.clear()

        # Build response
        success_rate = round((imported / total_rows * 100), 1) if total_rows > 0 else 0

        if is_ajax:
            return JsonResponse({
                'success': True,
                'imported': imported,
                'errors': errors,
                'total_rows': total_rows,
                'success_rate': success_rate,
                'file_name': uploaded_file.name,
                'error_samples': error_samples,
                'import_mode': import_mode,
                'deleted_count': deleted_count,
                'unsynced_count': unsynced_count,
                'skipped_duplicates': skipped_duplicates,
                'gender_extracted': gender_extracted,
            })
        else:
            mode_msg = f' (replaced {deleted_count} records)' if import_mode == 'replace' else ''
            dup_msg = f', {skipped_duplicates} duplicates skipped' if skipped_duplicates > 0 else ''
            resync_msg = f' — {unsynced_count} approved report(s) need re-sync via Manage Reports.' if import_mode == 'replace' and unsynced_count > 0 else ''
            if errors > 0:
                messages.warning(request, f'Import completed{mode_msg}: {imported} records imported, {errors} errors encountered{dup_msg}.{resync_msg}')
            else:
                messages.success(request, f'Successfully imported {imported} accident records from {uploaded_file.name}{mode_msg}{dup_msg}!{resync_msg}')
            return redirect('accident_list')

    except Exception as e:
        if is_ajax:
            return JsonResponse({'success': False, 'error': f'Import failed: {str(e)}'}, status=500)
        messages.error(request, f'Import failed: {str(e)}')
        return redirect('accident_list')


@pnp_login_required
def update_case_status(request, pk):
    """Update the case status of an accident record - admins only"""
    import json as json_module

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # Check admin permissions
    if not hasattr(request.user, 'profile') or request.user.profile.role not in [
        'super_admin', 'regional_director', 'provincial_chief', 'station_commander'
    ]:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    accident = get_object_or_404(Accident, pk=pk)

    # Jurisdiction check: users can only update cases in their area
    profile = request.user.profile
    if profile.role == 'provincial_chief' and (accident.province or '').upper() != (profile.province or '').upper():
        return JsonResponse({'error': 'You can only update cases within your province'}, status=403)
    elif profile.role == 'station_commander' and accident.station != profile.station:
        return JsonResponse({'error': 'You can only update cases within your station'}, status=403)

    try:
        data = json_module.loads(request.body)
    except (json_module.JSONDecodeError, TypeError):
        data = request.POST

    new_status = data.get('case_status', '').strip()
    solve_type = data.get('case_solve_type', '').strip()

    valid_statuses = [c[0] for c in Accident.CASE_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid case status'}, status=400)

    if new_status == 'Solved' and not solve_type:
        return JsonResponse({'error': 'Solve type is required when status is Solved'}, status=400)

    if new_status != 'Solved':
        solve_type = ''

    accident.case_status = new_status
    accident.case_solve_type = solve_type
    accident.case_status_updated_by = request.user
    accident.case_status_updated_at = timezone.now()
    accident.save()

    # Audit log
    log_user_action(request, 'case_status_update',
        f'Updated case status for accident #{pk} to "{new_status}"' + (f' ({solve_type})' if solve_type else ''),
        object_type='Accident', object_id=pk)

    updater_name = request.user.get_full_name() or request.user.username
    return JsonResponse({
        'success': True,
        'case_status': new_status,
        'case_solve_type': solve_type,
        'updated_by': updater_name,
        'updated_at': accident.case_status_updated_at.strftime('%b %d, %Y %I:%M %p'),
    })


@pnp_login_required
def accident_edit(request, pk):
    """Edit accident - admins and data encoders with jurisdiction"""

    # Check if user has an editing role
    if not hasattr(request.user, 'profile') or request.user.profile.role not in [
        'super_admin', 'regional_director', 'provincial_chief', 'station_commander', 'data_encoder'
    ]:
        messages.error(request, 'Permission denied. You do not have permission to edit accidents.')
        return redirect('accident_list')

    accident = get_object_or_404(Accident, pk=pk)

    # Jurisdiction check: users can only edit accidents in their area
    profile = request.user.profile
    if profile.role == 'provincial_chief' and (accident.province or '').upper() != (profile.province or '').upper():
        messages.error(request, 'Permission denied. You can only edit accidents within your province.')
        return redirect('accident_list')
    elif profile.role == 'station_commander' and accident.station != profile.station:
        messages.error(request, 'Permission denied. You can only edit accidents within your station.')

    if request.method == 'POST':
        try:
            from decimal import Decimal

            # Police/Administrative Info
            accident.pro = request.POST.get('pro', accident.pro)
            accident.ppo = request.POST.get('ppo', accident.ppo)
            accident.station = request.POST.get('station', accident.station)

            # Location fields
            accident.province = request.POST.get('province', accident.province)
            accident.municipal = request.POST.get('municipal', accident.municipal)
            accident.barangay = request.POST.get('barangay', accident.barangay)
            accident.street = request.POST.get('street', accident.street)
            accident.type_of_place = request.POST.get('type_of_place', accident.type_of_place)

            # Coordinates
            lat_str = request.POST.get('latitude')
            lng_str = request.POST.get('longitude')
            if lat_str:
                accident.latitude = Decimal(lat_str)
            if lng_str:
                accident.longitude = Decimal(lng_str)

            # Incident details
            accident.incident_type = request.POST.get('incident_type', accident.incident_type)
            accident.offense = request.POST.get('offense', accident.offense)
            accident.offense_type = request.POST.get('offense_type', accident.offense_type)
            accident.stage_of_felony = request.POST.get('stage_of_felony', accident.stage_of_felony)

            # Casualties
            accident.victim_killed = request.POST.get('victim_killed') == 'true'
            accident.victim_injured = request.POST.get('victim_injured') == 'true'
            accident.victim_unharmed = request.POST.get('victim_unharmed') == 'true'

            victim_count_str = request.POST.get('victim_count')
            if victim_count_str:
                accident.victim_count = int(victim_count_str)

            suspect_count_str = request.POST.get('suspect_count')
            if suspect_count_str:
                accident.suspect_count = int(suspect_count_str)

            # Vehicle information
            accident.vehicle_kind = request.POST.get('vehicle_kind', accident.vehicle_kind)
            accident.vehicle_make = request.POST.get('vehicle_make', accident.vehicle_make)
            accident.vehicle_model = request.POST.get('vehicle_model', accident.vehicle_model)
            accident.vehicle_plate_no = request.POST.get('vehicle_plate_no', accident.vehicle_plate_no)

            # Detailed information
            accident.victim_details = request.POST.get('victim_details', accident.victim_details)
            accident.suspect_details = request.POST.get('suspect_details', accident.suspect_details)
            accident.narrative = request.POST.get('narrative', accident.narrative)

            # Gender and demographic information
            accident.driver_gender = request.POST.get('driver_gender', accident.driver_gender)
            accident.victim_gender = request.POST.get('victim_gender', accident.victim_gender)

            driver_age_str = request.POST.get('driver_age')
            if driver_age_str:
                accident.driver_age = int(driver_age_str) if driver_age_str else None

            victim_age_str = request.POST.get('victim_age')
            if victim_age_str:
                accident.victim_age = int(victim_age_str) if victim_age_str else None

            # Case status
            accident.case_status = request.POST.get('case_status', accident.case_status)
            accident.case_solve_type = request.POST.get('case_solve_type', accident.case_solve_type)

            accident.save()

            # Audit log
            log_user_action(request, 'accident_edit',
                f'Edited accident #{pk} at {accident.municipal}, {accident.province}',
                object_type='Accident', object_id=pk)

            messages.success(request, f'Accident #{pk} updated successfully!')

        except Exception as e:
            messages.error(request, f'Failed to update accident: {str(e)}')

        return redirect('accident_list')

    # GET request - return accident data as JSON for modal
    from django.http import JsonResponse
    data = {
        'id': accident.pk,
        # Police/Administrative Info
        'pro': accident.pro or '',
        'ppo': accident.ppo or '',
        'station': accident.station or '',
        # Location
        'province': accident.province or '',
        'municipal': accident.municipal or '',
        'barangay': accident.barangay or '',
        'street': accident.street or '',
        'type_of_place': accident.type_of_place or '',
        # Coordinates
        'latitude': str(accident.latitude) if accident.latitude else '',
        'longitude': str(accident.longitude) if accident.longitude else '',
        # Incident details
        'incident_type': accident.incident_type or '',
        'offense': accident.offense or '',
        'offense_type': accident.offense_type or '',
        'stage_of_felony': accident.stage_of_felony or '',
        # Casualties
        'victim_killed': accident.victim_killed,
        'victim_injured': accident.victim_injured,
        'victim_unharmed': accident.victim_unharmed,
        'victim_count': accident.victim_count or 0,
        'suspect_count': accident.suspect_count or 0,
        # Vehicle information
        'vehicle_kind': accident.vehicle_kind or '',
        'vehicle_make': accident.vehicle_make or '',
        'vehicle_model': accident.vehicle_model or '',
        'vehicle_plate_no': accident.vehicle_plate_no or '',
        # Detailed information
        'victim_details': accident.victim_details or '',
        'suspect_details': accident.suspect_details or '',
        'narrative': accident.narrative or '',
        # Gender and demographic information
        'driver_gender': accident.driver_gender or 'UNKNOWN',
        'victim_gender': accident.victim_gender or 'UNKNOWN',
        'driver_age': accident.driver_age or '',
        'victim_age': accident.victim_age or '',
        # Case status
        'case_status': accident.case_status or '',
        'case_solve_type': accident.case_solve_type or '',
        # Temporal (read-only in modal)
        'date_committed': accident.date_committed.strftime('%Y-%m-%d') if accident.date_committed else '',
        'time_committed': accident.time_committed.strftime('%H:%M') if accident.time_committed else '',
    }
    return JsonResponse(data)


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
    
    # Get all accidents in this cluster
    accidents = Accident.objects.filter(cluster_id=cluster_id).order_by('-date_committed')
    total_count = accidents.count()
    accidents_display = list(accidents)
    
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
    
    # Prepare ALL accidents data for map - WITH DECIMAL TO FLOAT CONVERSION
    accidents_for_map = accidents.values(
        'id', 'latitude', 'longitude', 'incident_type',
        'date_committed', 'barangay', 'municipal',
        'victim_count', 'victim_killed', 'victim_injured'
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

    # ============================================
    # DPWH-ALIGNED RECOMMENDATION ENGINE
    # Analyze accident patterns to generate data-driven recommendations
    # Based on DPWH Highway Safety Design Standards (DO 041-S2012),
    # Road Safety Audit Manual, and iRAP framework
    # ============================================
    recommendations = []
    if total_count > 0:
        fatal_ratio = total_killed / total_count
        injury_ratio = total_injured / total_count

        # --- Pattern Analysis ---
        # Incident type keywords (free-text field)
        incident_types_raw = list(accidents.values_list('incident_type', flat=True))
        incident_text = ' '.join([t.lower() for t in incident_types_raw if t])

        hit_and_run_count = sum(1 for t in incident_types_raw if t and 'hit and run' in t.lower())
        pedestrian_count = sum(1 for t in incident_types_raw if t and 'pedestrian' in t.lower())
        reckless_count = sum(1 for t in incident_types_raw if t and 'reckless' in t.lower())
        collision_count = sum(1 for t in incident_types_raw if t and ('collision' in t.lower() or 'crash' in t.lower()))

        # Vehicle kind keywords
        vehicle_kinds_raw = list(accidents.values_list('vehicle_kind', flat=True))
        vehicle_text = ' '.join([v.lower() for v in vehicle_kinds_raw if v])

        motorcycle_count = sum(1 for v in vehicle_kinds_raw if v and ('motorcycle' in v.lower() or 'motor cycle' in v.lower() or 'mc' in v.lower().split()))
        truck_bus_count = sum(1 for v in vehicle_kinds_raw if v and ('truck' in v.lower() or 'bus' in v.lower() or 'trailer' in v.lower()))
        bicycle_count = sum(1 for v in vehicle_kinds_raw if v and 'bicycle' in v.lower())

        # Place type keywords
        place_types_raw = list(accidents.values_list('type_of_place', flat=True))
        place_text = ' '.join([p.lower() for p in place_types_raw if p])

        intersection_count = sum(1 for p in place_types_raw if p and ('intersection' in p.lower() or 'junction' in p.lower()))
        curve_count = sum(1 for p in place_types_raw if p and ('curve' in p.lower() or 'bend' in p.lower()))
        highway_count = sum(1 for p in place_types_raw if p and ('highway' in p.lower() or 'national road' in p.lower()))

        # Time analysis (night: 6PM-6AM)
        night_accidents = accidents.filter(
            Q(time_committed__hour__gte=18) | Q(time_committed__hour__lt=6)
        ).exclude(time_committed__isnull=True).count()
        timed_accidents = accidents.exclude(time_committed__isnull=True).count()
        night_ratio = night_accidents / max(timed_accidents, 1)

        # Drug & colorum
        drug_count = accidents.filter(drug_involved=True).count()
        colorum_count = accidents.filter(vehicle_colorum=True).count()

        # --- Generate Recommendations ---

        # 1. CRITICAL: High fatality rate → Geometric Improvements
        if fatal_ratio >= 0.3:
            recommendations.append({
                'category': 'Geometric / Road Design Improvements',
                'icon': 'fa-road',
                'title': 'Road Realignment & Safety Zone Establishment',
                'description': 'Conduct road safety audit for horizontal/vertical alignment deficiencies. Establish clear zones, widen shoulders, and improve sight distance. Consider road realignment at high-risk segments.',
                'priority': 'CRITICAL',
                'basis': f'{int(fatal_ratio * 100)}% fatality rate ({total_killed} of {total_count} accidents are fatal)',
                'dpwh_ref': 'DPWH DO 041-S2012 Part 1 — Road Safety Design Manual',
            })
        elif fatal_ratio >= 0.1:
            recommendations.append({
                'category': 'Geometric / Road Design Improvements',
                'icon': 'fa-road',
                'title': 'Road Safety Assessment & Shoulder Improvement',
                'description': 'Assess road cross-section adequacy. Improve paved shoulders and sight distance. Review vertical curve design for headlight visibility and drainage.',
                'priority': 'HIGH',
                'basis': f'{int(fatal_ratio * 100)}% fatality rate ({total_killed} fatal out of {total_count} accidents)',
                'dpwh_ref': 'DPWH DO 041-S2012 Part 1 — Road Safety Design Manual',
            })

        # 2. Motorcycle-heavy hotspot → Roadside Safety
        motorcycle_ratio = motorcycle_count / total_count
        if motorcycle_ratio >= 0.4:
            priority = 'CRITICAL' if fatal_ratio >= 0.2 else 'HIGH'
            recommendations.append({
                'category': 'Roadside Safety',
                'icon': 'fa-motorcycle',
                'title': 'Motorcycle Safety Barriers & Lane Separation',
                'description': 'Install motorcycle-friendly guard rails and crash barriers. Assess need for motorcycle lanes or lane separation. Remove roadside hazards within the clear zone.',
                'priority': priority,
                'basis': f'{int(motorcycle_ratio * 100)}% of accidents involve motorcycles ({motorcycle_count} of {total_count})',
                'dpwh_ref': 'DPWH DO 041-S2012 — Roadside Safety / iRAP Safety Barriers',
            })

        # 3. Truck/Bus involvement → Speed Management
        truck_ratio = truck_bus_count / total_count
        if truck_ratio >= 0.15:
            priority = 'HIGH' if fatal_ratio >= 0.1 else 'MEDIUM'
            recommendations.append({
                'category': 'Speed Management',
                'icon': 'fa-tachometer-alt',
                'title': 'Heavy Vehicle Speed Control & Restriction',
                'description': 'Install speed limit signs for heavy vehicles. Consider speed calming devices (rumble strips, raised crossings). Assess need for truck/bus restrictions during peak hours.',
                'priority': priority,
                'basis': f'{int(truck_ratio * 100)}% of accidents involve trucks/buses ({truck_bus_count} of {total_count})',
                'dpwh_ref': 'DPWH DO 041-S2012 — Speed Management / RA 4136',
            })

        # 4. Pedestrian accidents → Pedestrian Facilities
        if pedestrian_count > 0 or bicycle_count > 0:
            ped_total = pedestrian_count + bicycle_count
            has_fatal_ped = pedestrian_count > 0 and fatal_ratio > 0
            priority = 'CRITICAL' if has_fatal_ped else 'HIGH'
            recommendations.append({
                'category': 'Pedestrian & Cyclist Facilities',
                'icon': 'fa-walking',
                'title': 'Pedestrian Crossings, Sidewalks & Refuge Islands',
                'description': 'Install marked pedestrian crossings with warning signs. Provide sidewalks/footpaths and pedestrian refuge islands. Consider pedestrian fencing near high-traffic areas. Add bicycle lanes if cyclist involvement is detected.',
                'priority': priority,
                'basis': f'{ped_total} accident(s) involving pedestrians/cyclists',
                'dpwh_ref': 'DPWH DO 041-S2012 — Pedestrian & Vulnerable Road User Facilities',
            })

        # 5. Night accidents → Lighting
        if night_ratio >= 0.3:
            recommendations.append({
                'category': 'Lighting & Road Surface',
                'icon': 'fa-lightbulb',
                'title': 'Street Lighting Installation',
                'description': 'Install or upgrade street lighting along this corridor. Prioritize lighting at curves, intersections, and pedestrian crossing areas. Improve reflective pavement markings for night visibility.',
                'priority': 'HIGH',
                'basis': f'{int(night_ratio * 100)}% of accidents occur at night ({night_accidents} of {timed_accidents} with recorded time)',
                'dpwh_ref': 'DPWH DO 041-S2012 — Lighting & Surface / iRAP Street Lighting',
            })

        # 6. Intersection hotspot → Intersection Improvements
        intersection_ratio = intersection_count / total_count
        if intersection_ratio >= 0.2 or intersection_count >= 3:
            priority = 'HIGH' if fatal_ratio >= 0.1 else 'MEDIUM'
            recommendations.append({
                'category': 'Intersection Improvements',
                'icon': 'fa-project-diagram',
                'title': 'Intersection Channelization & Traffic Signals',
                'description': 'Assess intersection geometry for channelization improvements. Evaluate need for traffic signal installation, turn lanes, or roundabout conversion. Improve intersection delineation and warning signs.',
                'priority': priority,
                'basis': f'{intersection_count} accidents at intersections/junctions ({int(intersection_ratio * 100)}%)',
                'dpwh_ref': 'DPWH DO 041-S2012 — Intersection Design / iRAP Intersection Treatment',
            })

        # 7. Curve/bend accidents → Signs & Delineation
        curve_ratio = curve_count / total_count
        if curve_ratio >= 0.15 or curve_count >= 2:
            recommendations.append({
                'category': 'Road Signs & Pavement Markings',
                'icon': 'fa-exclamation-triangle',
                'title': 'Curve Warning Signs & Chevron Delineation',
                'description': 'Install advance curve warning signs and advisory speed plates. Provide chevron alignment signs (CAS) at appropriate spacing. Improve centerline and edge line markings through curves.',
                'priority': 'HIGH',
                'basis': f'{curve_count} accidents at curves/bends ({int(curve_ratio * 100)}%)',
                'dpwh_ref': 'DPWH DO 041-S2012 Part 2 — Road Signs & Pavement Markings Manual / DO 013-08',
            })

        # 8. Hit and run → Traffic Management
        hitrun_ratio = hit_and_run_count / total_count
        if hitrun_ratio >= 0.15 or hit_and_run_count >= 3:
            recommendations.append({
                'category': 'Traffic Management',
                'icon': 'fa-video',
                'title': 'CCTV Surveillance & Monitoring System',
                'description': 'Install CCTV cameras at critical points for incident documentation and deterrence. Consider automated plate recognition for hit-and-run prevention. Coordinate with LGU for traffic monitoring center integration.',
                'priority': 'MEDIUM',
                'basis': f'{hit_and_run_count} hit-and-run incidents ({int(hitrun_ratio * 100)}%)',
                'dpwh_ref': 'Traffic Management — LGU/PNP-HPG Coordination',
            })

        # 9. Drug/alcohol involvement → Enforcement
        drug_ratio = drug_count / total_count
        if drug_ratio >= 0.05 or drug_count >= 2:
            recommendations.append({
                'category': 'Enforcement',
                'icon': 'fa-ban',
                'title': 'Anti-Drunk & Drugged Driving Checkpoints',
                'description': 'Establish regular sobriety checkpoints in this area. Coordinate with PNP-HPG for enforcement of RA 10586 (Anti-Drunk and Drugged Driving Act of 2013). Deploy alcohol breath testing equipment.',
                'priority': 'HIGH',
                'basis': f'{drug_count} accident(s) with drug/alcohol involvement ({int(drug_ratio * 100)}%)',
                'dpwh_ref': 'RA 10586 — Anti-Drunk and Drugged Driving Act of 2013',
            })

        # 10. Colorum vehicles → Enforcement
        colorum_ratio = colorum_count / total_count
        if colorum_ratio >= 0.05 or colorum_count >= 2:
            recommendations.append({
                'category': 'Enforcement',
                'icon': 'fa-id-card',
                'title': 'Vehicle Registration & Franchise Checkpoints',
                'description': 'Conduct regular anti-colorum operations. Verify vehicle registration and franchise compliance. Coordinate with LTFRB for enforcement against unauthorized public transport.',
                'priority': 'MEDIUM',
                'basis': f'{colorum_count} accident(s) involving colorum (unfranchised) vehicles ({int(colorum_ratio * 100)}%)',
                'dpwh_ref': 'RA 4136 — Land Transportation and Traffic Code',
            })

        # 11. Reckless driving dominant → Speed Management
        reckless_ratio = reckless_count / total_count
        if reckless_ratio >= 0.3:
            recommendations.append({
                'category': 'Speed Management',
                'icon': 'fa-tachometer-alt',
                'title': 'Speed Enforcement & Traffic Calming',
                'description': 'Install speed limit regulatory signs. Deploy speed detection equipment. Consider traffic calming devices: rumble strips, raised pedestrian crossings, and central hatching.',
                'priority': 'HIGH' if fatal_ratio >= 0.1 else 'MEDIUM',
                'basis': f'{int(reckless_ratio * 100)}% of incidents involve reckless driving ({reckless_count} of {total_count})',
                'dpwh_ref': 'DPWH DO 041-S2012 — Speed Management / RA 4136',
            })

        # 12. Highway corridor → Roadside Safety (always relevant for highways)
        if highway_count >= 3 or highway_count / max(total_count, 1) >= 0.3:
            if not any(r['category'] == 'Roadside Safety' for r in recommendations):
                recommendations.append({
                    'category': 'Roadside Safety',
                    'icon': 'fa-shield-alt',
                    'title': 'Guard Rails & Roadside Hazard Removal',
                    'description': 'Install guard rails and crash barriers at hazardous sections. Remove or relocate fixed roadside hazards (poles, trees, structures) from the clear zone. Improve shoulder rumble strips.',
                    'priority': 'HIGH',
                    'basis': f'{highway_count} accidents on highway/national road segments',
                    'dpwh_ref': 'DPWH DO 041-S2012 — Roadside Safety / iRAP Safety Barriers',
                })

        # ALWAYS INCLUDED: Road Signs & Pavement Markings assessment
        if not any(r['category'] == 'Road Signs & Pavement Markings' for r in recommendations):
            recommendations.append({
                'category': 'Road Signs & Pavement Markings',
                'icon': 'fa-sign',
                'title': 'Signage Adequacy Assessment & Pavement Marking Renewal',
                'description': 'Conduct comprehensive assessment of regulatory, warning, and guide signs. Renew faded pavement markings (centerline, edge lines, crosswalks). Install hazard markers and delineation posts at critical points.',
                'priority': 'MEDIUM',
                'basis': f'Standard assessment for hotspot with {total_count} recorded accidents',
                'dpwh_ref': 'DPWH DO 041-S2012 Part 2 — Road Signs & Pavement Markings Manual / DO 013-08',
            })

        # ALWAYS INCLUDED: Multi-Agency Coordination (3E Approach)
        municipalities_text = ', '.join(hotspot.municipalities) if hotspot.municipalities else 'local LGU'
        recommendations.append({
            'category': 'Multi-Agency Coordination',
            'icon': 'fa-handshake',
            'title': '3E Approach: Engineering, Enforcement & Education',
            'description': f'Coordinate with {municipalities_text} LGU, DPWH District Engineering Office, PNP-HPG, and LTFRB for joint road safety action plan. Implement public awareness campaigns for motorists about this high-risk location.',
            'priority': 'MEDIUM',
            'basis': f'Multi-stakeholder approach for hotspot spanning {municipalities_text}',
            'dpwh_ref': 'Philippine Road Safety Action Plan — 3E Framework',
        })

        # Sort by priority: CRITICAL first, then HIGH, then MEDIUM
        priority_order = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2}
        recommendations.sort(key=lambda r: priority_order.get(r['priority'], 3))

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
        'recommendations': recommendations,
    }

    return render(request, 'hotspots/hotspot_detail.html', context)


@pnp_login_required
def report_accident(request):
    """Form for reporting new accidents"""
    from .forms import AccidentReportForm

    # Check if user has report submission access
    profile = getattr(request.user, 'profile', None)
    if profile and not profile.can_submit_reports:
        messages.error(request, 'You do not have permission to submit reports. Please contact your administrator.')
        return redirect('dashboard')

    # Auto-fill reporter info from logged-in user's profile
    reporter_name = request.user.get_full_name() or request.user.username
    reporter_contact = ''
    if hasattr(request.user, 'profile'):
        reporter_contact = request.user.profile.mobile_number or request.user.profile.phone_number or request.user.email or ''
    if not reporter_contact:
        reporter_contact = request.user.email or ''

    if request.method == 'POST':
        form = AccidentReportForm(request.POST, request.FILES)

        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            # Always use profile data for reporter fields
            report.reporter_name = reporter_name
            report.reporter_contact = reporter_contact

            # Parse multi-victim/suspect JSON from dynamic form rows
            import json as json_module
            try:
                report.victims_data = json_module.loads(request.POST.get('victims_json', '[]'))
            except (json_module.JSONDecodeError, TypeError):
                report.victims_data = []
            try:
                report.suspects_data = json_module.loads(request.POST.get('suspects_json', '[]'))
            except (json_module.JSONDecodeError, TypeError):
                report.suspects_data = []

            # Auto-compute counts from victim/suspect data
            report.suspect_count = len(report.suspects_data) or 1
            report.casualties_killed = int(request.POST.get('casualties_killed', 0) or 0)
            report.casualties_injured = int(request.POST.get('casualties_injured', 0) or 0)

            report.save()

            # Handle dynamic photo uploads
            from .models import ReportPhoto
            photo_files = request.FILES.getlist('report_photos')
            for idx, photo_file in enumerate(photo_files):
                ReportPhoto.objects.create(
                    report=report,
                    image=photo_file,
                    order=idx,
                )

            # Log activity
            log_report_activity(report, 'submitted', request.user)

            # Notify admins/commanders about the new report (only those with jurisdiction)
            admin_roles = ['super_admin', 'regional_director', 'provincial_chief', 'station_commander']
            admin_users = User.objects.filter(
                profile__role__in=admin_roles,
                is_active=True
            ).select_related('profile').exclude(pk=request.user.pk)

            notifications = []
            for admin_user in admin_users:
                # Only notify if report is within their jurisdiction
                if can_user_approve_report(admin_user, report):
                    notifications.append(Notification(
                        recipient=admin_user,
                        notification_type='report_submitted',
                        title='New Accident Report',
                        message=f'{reporter_name} submitted a new accident report at {report.barangay}, {report.municipal}.',
                        url=f'/manage/report/{report.pk}/go/',
                        related_report=report,
                    ))
            if notifications:
                Notification.objects.bulk_create(notifications)

            messages.success(request, 'Accident report submitted successfully!')
            return redirect('report_success', pk=report.pk)
    else:
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


@pnp_login_required
def my_reports(request):
    """View submitted reports for the current user"""
    from django.core.paginator import Paginator
    from django.utils import timezone
    from datetime import timedelta

    # Get filters
    status_filter = request.GET.get('status', 'all')
    period_filter = request.GET.get('period', 'all')

    all_user_reports = AccidentReport.objects.filter(reported_by=request.user)

    # Status counts (always based on all time, unaffected by period filter)
    total_count = all_user_reports.count()
    approved_count = all_user_reports.filter(status='verified').count()
    pending_count = all_user_reports.filter(status='pending').count()
    rejected_count = all_user_reports.filter(status='rejected').count()
    cancelled_count = all_user_reports.filter(status='cancelled').count()

    reports = all_user_reports

    # Apply status filter
    if status_filter != 'all':
        reports = reports.filter(status=status_filter)

    # Apply time period filter
    now = timezone.now()
    if period_filter == 'week':
        reports = reports.filter(created_at__gte=now - timedelta(days=7))
    elif period_filter == 'month':
        reports = reports.filter(created_at__gte=now - timedelta(days=30))
    elif period_filter == '3months':
        reports = reports.filter(created_at__gte=now - timedelta(days=90))
    elif period_filter == 'year':
        reports = reports.filter(created_at__year=now.year)

    # Sort: latest activity first
    reports = reports.order_by('-updated_at')

    # Pagination with configurable per-page (system default from settings)
    from .models import SystemSetting
    sys_default = SystemSetting.get('default_per_page')
    per_page = request.GET.get('per_page', sys_default)
    try:
        per_page_int = int(per_page)
        if per_page_int not in (5, 10, 15, 20, 50):
            per_page_int = int(sys_default)
    except (ValueError, TypeError):
        per_page_int = 15
    paginator = Paginator(reports, per_page_int)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'reports': page_obj,
        'status_filter': status_filter,
        'period_filter': period_filter,
        'status_choices': AccidentReport.STATUS_CHOICES,
        'page_obj': page_obj,
        'paginator': paginator,
        'per_page': str(per_page_int),
        'total_count': total_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'rejected_count': rejected_count,
        'cancelled_count': cancelled_count,
    }

    return render(request, 'reports/my_reports.html', context)


def can_approve_reports(user):
    """Check if user has permission to approve reports based on role hierarchy"""
    if not hasattr(user, 'profile'):
        return False
    return user.profile.role in ['super_admin', 'regional_director', 'provincial_chief', 'station_commander']


def get_reports_for_jurisdiction(user, queryset):
    """Filter reports based on user's role and jurisdiction"""
    if not hasattr(user, 'profile'):
        return queryset.none()

    profile = user.profile
    role = profile.role

    # Super admin and regional director can see all reports in the region
    if role in ['super_admin', 'regional_director']:
        return queryset

    # Provincial chief can see reports from their province
    if role == 'provincial_chief':
        if profile.province:
            return queryset.filter(province__icontains=profile.province)
        return queryset.none()

    # Station commander can see reports from their station/municipality
    if role == 'station_commander':
        if profile.station:
            # Extract key location words from station name (e.g., "Cabadbaran City PS" -> "Cabadbaran")
            station_clean = profile.station.lower()
            # Remove common suffixes/words (PS = Police Station, MPS = Municipal Police Station, CPS = City Police Station)
            for remove_word in ['city', 'police', 'office', 'station', 'municipal', ' ps', ' mps', ' cps', 'ppo', 'pro']:
                station_clean = station_clean.replace(remove_word, '')
            station_words = station_clean.split()
            station_words = [w.strip() for w in station_words if len(w.strip()) > 2]

            # Build query to match any of the key words
            if station_words:
                q_filter = Q()
                for word in station_words:
                    q_filter |= Q(municipal__icontains=word) | Q(barangay__icontains=word)

                # Also filter by province if set (for more accurate matching)
                if profile.province:
                    q_filter &= Q(province__icontains=profile.province)

                return queryset.filter(q_filter)

            # Fallback: match by province if station extraction failed but province is set
            if profile.province:
                return queryset.filter(province__icontains=profile.province)

            return queryset.filter(
                Q(municipal__icontains=profile.station) |
                Q(barangay__icontains=profile.station)
            )
        # If no station set but province is set, use province
        elif profile.province:
            return queryset.filter(province__icontains=profile.province)
        return queryset.none()

    return queryset.none()


def can_user_approve_report(user, report):
    """Check if a specific user can approve a specific report based on jurisdiction"""
    if not hasattr(user, 'profile'):
        return False

    profile = user.profile
    role = profile.role

    # Super admin and regional director can approve any report
    if role in ['super_admin', 'regional_director']:
        return True

    # Provincial chief can approve reports from their province
    if role == 'provincial_chief':
        if profile.province:
            # Check both ways
            if (profile.province.lower() in report.province.lower() or
                report.province.lower() in profile.province.lower()):
                return True
        return False

    # Station commander can approve reports from their station/municipality
    if role == 'station_commander':
        if profile.station:
            # Extract key location words from station name (e.g., "Cabadbaran City PS" -> "Cabadbaran")
            station_clean = profile.station.lower()
            for remove_word in ['city', 'police', 'office', 'station', 'municipal', ' ps', ' mps', ' cps', 'ppo', 'pro']:
                station_clean = station_clean.replace(remove_word, '')
            station_words = station_clean.split()
            station_words = [w.strip() for w in station_words if len(w.strip()) > 2]

            municipal_lower = report.municipal.lower()
            barangay_lower = report.barangay.lower()
            province_lower = report.province.lower()

            # Check if any key word matches the municipal or barangay
            for word in station_words:
                if word in municipal_lower or word in barangay_lower:
                    # Also verify province matches if set
                    if profile.province:
                        if profile.province.lower() in province_lower or province_lower in profile.province.lower():
                            return True
                    else:
                        return True

            # Fallback: direct comparison
            station_lower = profile.station.lower()
            if (station_lower in municipal_lower or station_lower in barangay_lower):
                return True

        # If no station but province is set, allow by province
        elif profile.province:
            if profile.province.lower() in report.province.lower():
                return True

        return False

    return False


# Mapping: form municipal names → dataset format (UPPERCASE with suffixes)
# Key: (PROVINCE, MUNICIPAL) or just MUNICIPAL for province-independent mappings
MUNICIPAL_NAME_MAP = {
    'CABADBARAN CITY': 'CABADBARAN',
    'BAYUGAN CITY': 'BAYUGAN',
    'SURIGAO CITY': 'SURIGAO CITY (CAPITAL)',
    'TANDAG CITY': 'TANDAG (CAPITAL)',
    'BISLIG CITY': 'CITY OF BISLIG',
    'PROSPERIDAD': 'PROSPERIDAD (CAPITAL)',
    'BASILISA': 'BASILISA (RIZAL)',
    'LIBJO': 'LIBJO (ALBOR)',
    'SANTA MONICA': 'SANTA MONICA (SAPAO)',
}

# Province-specific municipal mappings (when same name exists in multiple provinces)
MUNICIPAL_NAME_MAP_BY_PROVINCE = {
    ('SURIGAO DEL NORTE', 'SAN FRANCISCO'): 'SAN FRANCISCO (ANAO-AON)',
    ('DINAGAT ISLANDS', 'SAN JOSE'): 'SAN JOSE (CAPITAL)',
}


def normalize_municipal(municipal_name, province_name=''):
    """Normalize municipal name from form format to dataset format"""
    if not municipal_name:
        return ''
    upper_muni = municipal_name.upper()
    upper_prov = province_name.upper() if province_name else ''

    # Check province-specific mapping first
    key = (upper_prov, upper_muni)
    if key in MUNICIPAL_NAME_MAP_BY_PROVINCE:
        return MUNICIPAL_NAME_MAP_BY_PROVINCE[key]

    # Then check general mapping
    return MUNICIPAL_NAME_MAP.get(upper_muni, upper_muni)


def log_report_activity(report, action, actor, details=''):
    """Log an activity event for a report"""
    actor_name = actor.get_full_name() or actor.username
    actor_role = actor.profile.get_role_display() if hasattr(actor, 'profile') else ''
    ReportActivityLog.objects.create(
        report=report, action=action, actor=actor,
        actor_name=actor_name, actor_role=actor_role, details=details
    )


def notify_hierarchy_on_action(actor, report, action):
    """
    Notify relevant officers in the hierarchy when a report is approved/rejected.

    - Station Commander acts → notify Provincial Chief (same province) + Regional Director + Super Admin
    - Provincial Chief acts → notify Station Commander (same municipality) + Regional Director + Super Admin
    - Regional Director acts → notify Station Commander + Provincial Chief of that area
    - Super Admin acts → notify Station Commander + Provincial Chief of that area + Regional Director

    'action' is 'approved' or 'rejected'
    """
    actor_name = actor.get_full_name() or actor.username
    actor_role = actor.profile.get_role_display() if hasattr(actor, 'profile') else ''
    actor_role_key = actor.profile.role if hasattr(actor, 'profile') else ''

    report_location = f'{report.barangay}, {report.municipal}'
    incident_label = report.incident_type_other if (report.incident_type == 'OTHER' and report.incident_type_other) else report.get_incident_type_display()

    if action == 'approved':
        notif_type = 'report_approved'
        title = 'Report Approved'
        verb = 'approved'
    else:
        notif_type = 'report_rejected'
        title = 'Report Rejected'
        verb = 'rejected'

    notifications = []
    notified_ids = {actor.pk, report.reported_by.pk}  # Don't notify actor or reporter (reporter gets separate notif)

    # Determine which roles to notify based on who acted
    profiles_to_notify = []

    if actor_role_key == 'station_commander':
        # Notify: provincial chief of same province, regional director, super admin
        profiles_to_notify = UserProfile.objects.filter(
            role__in=['provincial_chief', 'regional_director', 'super_admin'],
            is_active=True
        ).select_related('user')

    elif actor_role_key == 'provincial_chief':
        # Notify: station commanders in that municipality, regional director, super admin
        profiles_to_notify = UserProfile.objects.filter(
            role__in=['station_commander', 'regional_director', 'super_admin'],
            is_active=True
        ).select_related('user')

    elif actor_role_key == 'regional_director':
        # Notify: station commanders + provincial chiefs of that area, super admin
        profiles_to_notify = UserProfile.objects.filter(
            role__in=['station_commander', 'provincial_chief', 'super_admin'],
            is_active=True
        ).select_related('user')

    elif actor_role_key == 'super_admin':
        # Notify: station commanders + provincial chiefs of that area + regional director
        profiles_to_notify = UserProfile.objects.filter(
            role__in=['station_commander', 'provincial_chief', 'regional_director'],
            is_active=True
        ).select_related('user')

    for profile in profiles_to_notify:
        if profile.user.pk in notified_ids:
            continue

        # Filter by jurisdiction relevance
        should_notify = False

        if profile.role in ['super_admin', 'regional_director']:
            # Always notify - they oversee everything
            should_notify = True

        elif profile.role == 'provincial_chief':
            # Only notify if report is in their province
            if profile.province and report.province:
                if (profile.province.lower() in report.province.lower() or
                    report.province.lower() in profile.province.lower()):
                    should_notify = True

        elif profile.role == 'station_commander':
            # Only notify if report is in their municipality/station area
            if profile.station and report.municipal:
                station_clean = profile.station.lower()
                for remove_word in ['city', 'police', 'office', 'station', 'municipal', ' ps', ' mps', ' cps', 'ppo', 'pro']:
                    station_clean = station_clean.replace(remove_word, '')
                station_words = [w.strip() for w in station_clean.split() if len(w.strip()) > 2]

                municipal_lower = report.municipal.lower()
                for word in station_words:
                    if word in municipal_lower:
                        should_notify = True
                        break

        if should_notify:
            notified_ids.add(profile.user.pk)
            notifications.append(Notification(
                recipient=profile.user,
                notification_type=notif_type,
                title=title,
                message=f'{actor_name} ({actor_role}) has {verb} the report "{incident_label}" at {report_location}.',
                url=f'/manage/report/{report.pk}/go/',
                related_report=report,
            ))

    if notifications:
        Notification.objects.bulk_create(notifications)


@pnp_login_required
def pending_reports(request):
    """Admin view to manage pending accident reports - filtered by role hierarchy"""
    # Check if user has approval privileges based on role
    if not can_approve_reports(request.user):
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')

    # Get status filter - default to 'all' (processed reports)
    status_filter = request.GET.get('status', 'all')

    # Get base queryset
    if status_filter == 'all':
        # "All" shows only processed reports (verified + rejected), not pending/cancelled
        base_queryset = AccidentReport.objects.exclude(status__in=['pending', 'cancelled'])
    else:
        base_queryset = AccidentReport.objects.filter(status=status_filter)

    # Filter by user's jurisdiction, sort by latest activity first
    reports = get_reports_for_jurisdiction(request.user, base_queryset).select_related('reported_by__profile', 'verified_by__profile').order_by('-updated_at')

    # Annotate reports with submission/rejection counts from activity logs
    from django.db.models import Count, Q
    report_ids = [r.pk for r in reports]
    if report_ids:
        log_counts = ReportActivityLog.objects.filter(
            report_id__in=report_ids
        ).values('report_id').annotate(
            submit_count=Count('id', filter=Q(action__in=['submitted', 'resubmitted'])),
            reject_count=Count('id', filter=Q(action='rejected')),
        )
        counts_map = {lc['report_id']: lc for lc in log_counts}
        for report in reports:
            c = counts_map.get(report.pk, {})
            report.submit_count = c.get('submit_count', 0)
            report.reject_count = c.get('reject_count', 0)

    # Get pending count for user's jurisdiction
    pending_queryset = AccidentReport.objects.filter(status='pending')
    pending_count = get_reports_for_jurisdiction(request.user, pending_queryset).count()

    # Pagination with configurable per-page (system default from settings)
    from .models import SystemSetting
    sys_default = SystemSetting.get('default_per_page')
    total_report_count = len(reports) if isinstance(reports, list) else reports.count()
    per_page = request.GET.get('per_page', sys_default)
    try:
        per_page_int = int(per_page)
        if per_page_int not in (5, 10, 15, 20, 50):
            per_page_int = int(sys_default)
    except (ValueError, TypeError):
        per_page_int = 15
    paginator = Paginator(reports, per_page_int)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Count verified reports that lost their Accident link (unsynced)
    unsynced_reports = AccidentReport.objects.filter(status='verified', accident__isnull=True)
    unsynced_count = get_reports_for_jurisdiction(request.user, unsynced_reports).count()

    context = {
        'reports': page_obj,
        'status_filter': status_filter,
        'status_choices': AccidentReport.STATUS_CHOICES,
        'pending_count': pending_count,
        'unsynced_count': unsynced_count,
        'page_obj': page_obj,
        'per_page': str(per_page_int),
        'total_report_count': total_report_count,
        'user_role': request.user.profile.get_role_display() if hasattr(request.user, 'profile') else '',
    }

    _role = getattr(getattr(request.user, 'profile', None), 'role', '')
    context['base_tpl'] = 'admin_panel/base.html' if _role in ['super_admin', 'regional_director'] else 'base.html'

    return render(request, 'admin_panel/pending_reports.html', context)


@pnp_login_required
def approve_report(request, pk):
    """Approve a pending report and create official accident record"""
    # Check if user has approval privileges
    if not can_approve_reports(request.user):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')

    report = get_object_or_404(AccidentReport, pk=pk)

    # Check if user can approve this specific report based on jurisdiction
    if not can_user_approve_report(request.user, report):
        messages.error(request, 'This report is outside your jurisdiction.')
        return redirect('pending_reports')

    if report.status != 'pending':
        messages.warning(request, 'This report has already been processed.')
        return redirect('pending_reports')

    if request.method == 'POST':
        # Create official Accident record from the report
        # Normalize location fields to UPPERCASE to match dataset format
        norm_province = report.province.upper() if report.province else ''
        norm_municipal = normalize_municipal(report.municipal, report.province)
        norm_barangay = report.barangay.upper() if report.barangay else ''
        accident = Accident.objects.create(
            # Location
            province=norm_province,
            municipal=norm_municipal,
            barangay=norm_barangay,
            street=report.street_address,
            type_of_place=report.type_of_place_other if (report.type_of_place == 'OTHER' and report.type_of_place_other) else (report.get_type_of_place_display() if report.type_of_place else ''),
            latitude=report.latitude,
            longitude=report.longitude,

            # Temporal
            date_committed=report.incident_date,
            time_committed=report.incident_time,
            date_reported=report.created_at.date(),
            time_reported=report.created_at.time(),
            year=report.incident_date.year,

            # Incident Details
            narrative=report.incident_description,
            incident_type=report.incident_type_other if (report.incident_type == 'OTHER' and report.incident_type_other) else (report.get_incident_type_display() if report.incident_type else 'Traffic Accident'),
            offense=report.offense or '',
            offense_type=report.offense_type or '',
            stage_of_felony=report.get_stage_of_felony_display() if report.stage_of_felony else '',

            # Casualties
            victim_killed=report.casualties_killed > 0,
            victim_injured=report.casualties_injured > 0,
            victim_unharmed=(report.casualties_killed == 0 and report.casualties_injured == 0),
            victim_count=report.casualties_killed + report.casualties_injured,

            # Victim/Suspect Details (from JSON arrays → CARAGA text format)
            victim_details=", ".join(
                f"{v.get('name','')} ({v.get('age','')}/{v.get('gender','')}/{v.get('status','')}/{v.get('nationality','FILIPINO')}/{v.get('occupation','')})"
                for v in (report.victims_data or [])
            ) or (f"{report.victim_name or ''} ({report.victim_age or ''}/{report.get_victim_gender_display()}/{report.get_victim_status_display() if report.victim_status else ''})".strip(' (/)') if report.victim_name else ''),
            victim_gender=(report.victims_data[0].get('gender', '').upper() if report.victims_data else report.victim_gender) or 'UNKNOWN',
            victim_age=int(report.victims_data[0].get('age', 0) or 0) if report.victims_data else report.victim_age,
            suspect_details=", ".join(
                f"{s.get('name','')} ({s.get('age','')}/{s.get('gender','')}/{s.get('status','')}/{s.get('nationality','FILIPINO')}/{s.get('occupation','')})"
                for s in (report.suspects_data or [])
            ) or (f"{report.suspect_name or ''} ({report.driver_age or ''}/{report.get_driver_gender_display()})".strip(' (/)') if report.suspect_name else ''),
            suspect_count=len(report.suspects_data) if report.suspects_data else (report.suspect_count or 0),
            driver_gender=(report.suspects_data[0].get('gender', '').upper() if report.suspects_data else report.driver_gender) or 'UNKNOWN',
            driver_age=int(report.suspects_data[0].get('age', 0) or 0) if report.suspects_data else report.driver_age,

            # Vehicle Info (structured)
            vehicle_kind=report.vehicle_kind_other if (report.vehicle_kind == 'OTHER' and report.vehicle_kind_other) else (report.get_vehicle_kind_display() if report.vehicle_kind else None),
            vehicle_make=report.vehicle_make_other if (report.vehicle_make == 'OTHER' and report.vehicle_make_other) else (report.vehicle_make or None),
            vehicle_model=report.vehicle_model_other if (report.vehicle_model == 'OTHER' and report.vehicle_model_other) else (report.vehicle_model or None),
            vehicle_plate_no=report.vehicle_plate_no or None,
            vehicle_chassis_no=report.vehicle_chassis_no or None,
            vehicle_colorum=report.vehicle_colorum,
            drug_involved=report.drug_involved,

            # Police Information (auto-filled from reporter's profile)
            pro='PRO 13' if (hasattr(report.reported_by, 'profile') and report.reported_by.profile.region == 'CARAGA') else (report.reported_by.profile.region if hasattr(report.reported_by, 'profile') else ''),
            ppo=report.reported_by.profile.province if hasattr(report.reported_by, 'profile') and report.reported_by.profile.province else '',
            station=report.reported_by.profile.station if hasattr(report.reported_by, 'profile') and report.reported_by.profile.station else '',

            # Case Status (auto-set on approval)
            case_status='Under Investigation',

            # System fields
            created_by=report.reported_by,
        )

        # Update report status
        report.status = 'verified'
        report.verified_by = request.user
        report.verified_at = timezone.now()
        report.accident = accident
        report.save()

        # Log activity
        log_report_activity(report, 'approved', request.user)

        # Audit log
        log_user_action(request, 'accident_create',
            f'Accident #{accident.pk} created from approved report #{report.pk}',
            object_type='Accident', object_id=accident.pk)

        # Notify the reporter that their report was approved
        approver_name = request.user.get_full_name() or request.user.username
        approver_role = request.user.profile.get_role_display() if hasattr(request.user, 'profile') else ''
        Notification.objects.create(
            recipient=report.reported_by,
            notification_type='report_approved',
            title='Report Approved',
            message=f'Your accident report #{report.pk} at {report.barangay}, {report.municipal} has been approved by {approver_name} ({approver_role}).',
            url=f'/manage/report/{report.pk}/go/',
            related_report=report,
        )

        # Notify hierarchy (up and down) about the approval
        notify_hierarchy_on_action(request.user, report, 'approved')

        # Clear dashboard cache so stats update immediately
        cache.delete('dashboard_data')

        messages.success(request, f'Report #{report.pk} has been approved and added to official records.')
        return redirect('pending_reports')

    # GET request — redirect to detail page (approve only via POST)
    return redirect('report_detail', pk=pk)


@pnp_login_required
def resync_reports(request):
    """Re-create Accident records for verified reports that lost their link.
    Only super_admin and regional_director can perform this action."""
    if not hasattr(request.user, 'profile') or request.user.profile.role not in ['super_admin', 'regional_director']:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('pending_reports')

    if request.method != 'POST':
        return redirect('pending_reports')

    # Get unsynced verified reports within user's jurisdiction
    unsynced_qs = AccidentReport.objects.filter(status='verified', accident__isnull=True)
    unsynced_reports = get_reports_for_jurisdiction(request.user, unsynced_qs)

    if not unsynced_reports.exists():
        messages.info(request, 'All verified reports are already synced. Nothing to do.')
        return redirect('pending_reports')

    synced_count = 0
    for report in unsynced_reports.select_related('reported_by__profile'):
        norm_province = report.province.upper() if report.province else ''
        norm_municipal = normalize_municipal(report.municipal, report.province)
        norm_barangay = report.barangay.upper() if report.barangay else ''

        accident = Accident.objects.create(
            province=norm_province,
            municipal=norm_municipal,
            barangay=norm_barangay,
            street=report.street_address,
            type_of_place=report.type_of_place_other if (report.type_of_place == 'OTHER' and report.type_of_place_other) else (report.get_type_of_place_display() if report.type_of_place else ''),
            latitude=report.latitude,
            longitude=report.longitude,
            date_committed=report.incident_date,
            time_committed=report.incident_time,
            date_reported=report.created_at.date(),
            time_reported=report.created_at.time(),
            year=report.incident_date.year,
            narrative=report.incident_description,
            incident_type=report.incident_type_other if (report.incident_type == 'OTHER' and report.incident_type_other) else (report.get_incident_type_display() if report.incident_type else 'Traffic Accident'),
            offense=report.offense or '',
            offense_type=report.offense_type or '',
            stage_of_felony=report.get_stage_of_felony_display() if report.stage_of_felony else '',
            victim_killed=report.casualties_killed > 0,
            victim_injured=report.casualties_injured > 0,
            victim_unharmed=(report.casualties_killed == 0 and report.casualties_injured == 0),
            victim_count=report.casualties_killed + report.casualties_injured,
            victim_details=", ".join(
                f"{v.get('name','')} ({v.get('age','')}/{v.get('gender','')}/{v.get('status','')}/{v.get('nationality','FILIPINO')}/{v.get('occupation','')})"
                for v in (report.victims_data or [])
            ) or (f"{report.victim_name or ''} ({report.victim_age or ''}/{report.get_victim_gender_display()}/{report.get_victim_status_display() if report.victim_status else ''})".strip(' (/)') if report.victim_name else ''),
            victim_gender=(report.victims_data[0].get('gender', '').upper() if report.victims_data else report.victim_gender) or 'UNKNOWN',
            victim_age=int(report.victims_data[0].get('age', 0) or 0) if report.victims_data else report.victim_age,
            suspect_details=", ".join(
                f"{s.get('name','')} ({s.get('age','')}/{s.get('gender','')}/{s.get('status','')}/{s.get('nationality','FILIPINO')}/{s.get('occupation','')})"
                for s in (report.suspects_data or [])
            ) or (f"{report.suspect_name or ''} ({report.driver_age or ''}/{report.get_driver_gender_display()})".strip(' (/)') if report.suspect_name else ''),
            suspect_count=len(report.suspects_data) if report.suspects_data else (report.suspect_count or 0),
            driver_gender=(report.suspects_data[0].get('gender', '').upper() if report.suspects_data else report.driver_gender) or 'UNKNOWN',
            driver_age=int(report.suspects_data[0].get('age', 0) or 0) if report.suspects_data else report.driver_age,
            vehicle_kind=report.vehicle_kind_other if (report.vehicle_kind == 'OTHER' and report.vehicle_kind_other) else (report.get_vehicle_kind_display() if report.vehicle_kind else None),
            vehicle_make=report.vehicle_make_other if (report.vehicle_make == 'OTHER' and report.vehicle_make_other) else (report.vehicle_make or None),
            vehicle_model=report.vehicle_model_other if (report.vehicle_model == 'OTHER' and report.vehicle_model_other) else (report.vehicle_model or None),
            vehicle_plate_no=report.vehicle_plate_no or None,
            vehicle_chassis_no=report.vehicle_chassis_no or None,
            vehicle_colorum=report.vehicle_colorum,
            drug_involved=report.drug_involved,
            pro='PRO 13' if (hasattr(report.reported_by, 'profile') and report.reported_by.profile.region == 'CARAGA') else (report.reported_by.profile.region if hasattr(report.reported_by, 'profile') else ''),
            ppo=report.reported_by.profile.province if hasattr(report.reported_by, 'profile') and report.reported_by.profile.province else '',
            station=report.reported_by.profile.station if hasattr(report.reported_by, 'profile') and report.reported_by.profile.station else '',
            case_status='Under Investigation',
            created_by=report.reported_by,
        )

        report.accident = accident
        report.save(update_fields=['accident'])
        synced_count += 1

    log_user_action(request, 'report_resync',
        f'Re-synced {synced_count} verified report(s) to Accident records',
        object_type='AccidentReport')

    messages.success(request, f'Successfully re-synced {synced_count} verified report{"s" if synced_count != 1 else ""} to accident records.')
    return redirect('pending_reports')


@pnp_login_required
def reject_report(request, pk):
    """Reject a pending report"""
    # Check if user has approval privileges
    if not can_approve_reports(request.user):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')

    report = get_object_or_404(AccidentReport, pk=pk)

    # Check if user can reject this specific report based on jurisdiction
    if not can_user_approve_report(request.user, report):
        messages.error(request, 'This report is outside your jurisdiction.')
        return redirect('pending_reports')

    if report.status != 'pending':
        messages.warning(request, 'This report has already been processed.')
        return redirect('pending_reports')

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            reason = 'No reason provided'

        # Update report status
        report.status = 'rejected'
        report.verified_by = request.user
        report.verified_at = timezone.now()
        report.rejection_reason = reason
        report.save()

        # Log activity
        log_report_activity(report, 'rejected', request.user, details=reason)

        # Notify the reporter that their report was rejected
        rejector_name = request.user.get_full_name() or request.user.username
        rejector_role = request.user.profile.get_role_display() if hasattr(request.user, 'profile') else ''
        Notification.objects.create(
            recipient=report.reported_by,
            notification_type='report_rejected',
            title='Report Rejected',
            message=f'Your accident report #{report.pk} has been rejected by {rejector_name} ({rejector_role}). Reason: {reason}',
            url=f'/manage/report/{report.pk}/go/',
            related_report=report,
        )

        # Notify hierarchy (up and down) about the rejection
        notify_hierarchy_on_action(request.user, report, 'rejected')

        # Clear dashboard cache so pending count updates immediately
        cache.delete('dashboard_data')

        if is_ajax:
            return JsonResponse({'success': True, 'message': f'Report #{report.pk} has been rejected.'})

        messages.success(request, f'Report #{report.pk} has been rejected.')
        return redirect('pending_reports')

    context = {
        'report': report,
    }
    _role = getattr(getattr(request.user, 'profile', None), 'role', '')
    context['base_tpl'] = 'admin_panel/base.html' if _role in ['super_admin', 'regional_director'] else 'base.html'
    return render(request, 'admin_panel/reject_report.html', context)


@pnp_login_required
def admin_cancel_report(request, pk):
    """Allow approvers to cancel (withdraw) a pending report on behalf of management"""
    if not can_approve_reports(request.user):
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('dashboard')

    report = get_object_or_404(AccidentReport, pk=pk)

    if not can_user_approve_report(request.user, report):
        messages.error(request, 'This report is outside your jurisdiction.')
        return redirect('pending_reports')

    if report.status != 'pending':
        messages.warning(request, 'Only pending reports can be cancelled.')
        return redirect('pending_reports')

    if request.method == 'POST':
        report.status = 'cancelled'
        report.verified_by = request.user
        report.verified_at = timezone.now()
        report.save()

        log_report_activity(report, 'cancelled', request.user)

        # Notify the reporter
        canceller_name = request.user.get_full_name() or request.user.username
        canceller_role = request.user.profile.get_role_display() if hasattr(request.user, 'profile') else ''
        Notification.objects.create(
            recipient=report.reported_by,
            notification_type='report_cancelled',
            title='Report Cancelled',
            message=f'Your accident report #{report.pk} at {report.barangay}, {report.municipal} has been cancelled by {canceller_name} ({canceller_role}).',
            url=f'/manage/report/{report.pk}/go/',
            related_report=report,
        )

        cache.delete('dashboard_data')
        messages.success(request, f'Report #{report.pk} has been cancelled.')
        return redirect('pending_reports')

    return redirect('pending_reports')


@pnp_login_required
def bulk_action_reports(request):
    """Bulk approve or reject multiple pending reports at once"""
    if not can_approve_reports(request.user):
        return JsonResponse({'error': 'Permission denied'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    import json as json_module
    try:
        body = json_module.loads(request.body)
    except (json_module.JSONDecodeError, TypeError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    action = body.get('action')  # 'approve' or 'reject'
    report_ids = body.get('report_ids', [])
    reason = body.get('reason', '').strip() or 'Bulk action — no reason provided'

    if action not in ('approve', 'reject'):
        return JsonResponse({'error': 'Invalid action'}, status=400)

    if not report_ids:
        return JsonResponse({'error': 'No reports selected'}, status=400)

    reports = AccidentReport.objects.filter(pk__in=report_ids, status='pending')
    approved = 0
    rejected = 0
    skipped = 0

    for report in reports:
        # Check jurisdiction for each report
        if not can_user_approve_report(request.user, report):
            skipped += 1
            continue

        if action == 'approve':
            # Create official Accident record (same logic as approve_report)
            # Normalize location fields to UPPERCASE to match dataset format
            norm_province = report.province.upper() if report.province else ''
            norm_municipal = normalize_municipal(report.municipal, report.province)
            norm_barangay = report.barangay.upper() if report.barangay else ''
            accident = Accident.objects.create(
                province=norm_province,
                municipal=norm_municipal,
                barangay=norm_barangay,
                street=report.street_address,
                type_of_place=report.type_of_place_other if (report.type_of_place == 'OTHER' and report.type_of_place_other) else (report.get_type_of_place_display() if report.type_of_place else ''),
                latitude=report.latitude,
                longitude=report.longitude,
                date_committed=report.incident_date,
                time_committed=report.incident_time,
                date_reported=report.created_at.date(),
                time_reported=report.created_at.time(),
                year=report.incident_date.year,
                narrative=report.incident_description,
                incident_type=report.incident_type_other if (report.incident_type == 'OTHER' and report.incident_type_other) else (report.get_incident_type_display() if report.incident_type else 'Traffic Accident'),
                offense=report.offense or '',
                offense_type=report.offense_type or '',
                stage_of_felony=report.get_stage_of_felony_display() if report.stage_of_felony else '',
                victim_killed=report.casualties_killed > 0,
                victim_injured=report.casualties_injured > 0,
                victim_unharmed=(report.casualties_killed == 0 and report.casualties_injured == 0),
                victim_count=report.casualties_killed + report.casualties_injured,
                victim_details=", ".join(
                    f"{v.get('name','')} ({v.get('age','')}/{v.get('gender','')}/{v.get('status','')}/{v.get('nationality','FILIPINO')}/{v.get('occupation','')})"
                    for v in (report.victims_data or [])
                ) or '',
                victim_gender=(report.victims_data[0].get('gender', '').upper() if report.victims_data else report.victim_gender) or 'UNKNOWN',
                victim_age=int(report.victims_data[0].get('age', 0) or 0) if report.victims_data else report.victim_age,
                suspect_details=", ".join(
                    f"{s.get('name','')} ({s.get('age','')}/{s.get('gender','')}/{s.get('status','')}/{s.get('nationality','FILIPINO')}/{s.get('occupation','')})"
                    for s in (report.suspects_data or [])
                ) or '',
                suspect_count=len(report.suspects_data) if report.suspects_data else (report.suspect_count or 0),
                driver_gender=(report.suspects_data[0].get('gender', '').upper() if report.suspects_data else report.driver_gender) or 'UNKNOWN',
                driver_age=int(report.suspects_data[0].get('age', 0) or 0) if report.suspects_data else report.driver_age,
                vehicle_kind=report.vehicle_kind_other if (report.vehicle_kind == 'OTHER' and report.vehicle_kind_other) else (report.get_vehicle_kind_display() if report.vehicle_kind else None),
                vehicle_make=report.vehicle_make_other if (report.vehicle_make == 'OTHER' and report.vehicle_make_other) else (report.vehicle_make or None),
                vehicle_model=report.vehicle_model_other if (report.vehicle_model == 'OTHER' and report.vehicle_model_other) else (report.vehicle_model or None),
                vehicle_plate_no=report.vehicle_plate_no or None,
                pro='PRO 13' if (hasattr(report.reported_by, 'profile') and report.reported_by.profile.region == 'CARAGA') else (report.reported_by.profile.region if hasattr(report.reported_by, 'profile') else ''),
                ppo=report.reported_by.profile.province if hasattr(report.reported_by, 'profile') and report.reported_by.profile.province else '',
                station=report.reported_by.profile.station if hasattr(report.reported_by, 'profile') and report.reported_by.profile.station else '',
                case_status='Under Investigation',
                created_by=report.reported_by,
            )

            report.status = 'verified'
            report.verified_by = request.user
            report.verified_at = timezone.now()
            report.accident = accident
            report.save()

            log_report_activity(report, 'approved', request.user)

            # Audit log
            log_user_action(request, 'accident_create',
                f'Accident #{accident.pk} created from bulk-approved report #{report.pk}',
                object_type='Accident', object_id=accident.pk)

            approver_name = request.user.get_full_name() or request.user.username
            approver_role = request.user.profile.get_role_display() if hasattr(request.user, 'profile') else ''
            Notification.objects.create(
                recipient=report.reported_by,
                notification_type='report_approved',
                title='Report Approved',
                message=f'Your accident report #{report.pk} at {report.barangay}, {report.municipal} has been approved by {approver_name} ({approver_role}).',
                url=f'/manage/report/{report.pk}/go/',
                related_report=report,
            )
            notify_hierarchy_on_action(request.user, report, 'approved')
            approved += 1

        elif action == 'reject':
            report.status = 'rejected'
            report.verified_by = request.user
            report.verified_at = timezone.now()
            report.rejection_reason = reason
            report.save()

            log_report_activity(report, 'rejected', request.user, details=reason)

            rejector_name = request.user.get_full_name() or request.user.username
            rejector_role = request.user.profile.get_role_display() if hasattr(request.user, 'profile') else ''
            Notification.objects.create(
                recipient=report.reported_by,
                notification_type='report_rejected',
                title='Report Rejected',
                message=f'Your accident report #{report.pk} has been rejected by {rejector_name} ({rejector_role}). Reason: {reason}',
                url=f'/manage/report/{report.pk}/go/',
                related_report=report,
            )
            notify_hierarchy_on_action(request.user, report, 'rejected')
            rejected += 1

    cache.delete('dashboard_data')

    return JsonResponse({
        'success': True,
        'approved': approved,
        'rejected': rejected,
        'skipped': skipped,
    })


@pnp_login_required
def check_duplicate_report(request):
    """Check if a similar report already exists (same date + nearby location)"""
    incident_date = request.GET.get('date', '')
    lat = request.GET.get('lat', '')
    lng = request.GET.get('lng', '')
    barangay = request.GET.get('barangay', '')
    municipal = request.GET.get('municipal', '')

    if not incident_date:
        return JsonResponse({'duplicates': []})

    from datetime import timedelta
    try:
        from django.utils.dateparse import parse_date
        target_date = parse_date(incident_date)
        if not target_date:
            return JsonResponse({'duplicates': []})
    except (ValueError, TypeError):
        return JsonResponse({'duplicates': []})

    # Look for reports within ±1 day with same location
    date_range_start = target_date - timedelta(days=1)
    date_range_end = target_date + timedelta(days=1)

    existing = AccidentReport.objects.filter(
        incident_date__range=(date_range_start, date_range_end),
    ).exclude(status='rejected')

    # Also check approved accidents
    existing_accidents = Accident.objects.filter(
        date_committed__range=(date_range_start, date_range_end),
    )

    # Filter by location: same barangay+municipal OR nearby coordinates
    matches = []

    # Check reports
    for report in existing:
        score = 0
        if barangay and report.barangay and barangay.lower() == report.barangay.lower():
            score += 2
        if municipal and report.municipal and municipal.lower() == report.municipal.lower():
            score += 1

        # Coordinate proximity (within ~500m)
        if lat and lng and report.latitude and report.longitude:
            try:
                dlat = abs(float(lat) - float(report.latitude))
                dlng = abs(float(lng) - float(report.longitude))
                if dlat < 0.005 and dlng < 0.005:
                    score += 3
            except (ValueError, TypeError):
                pass

        if score >= 2:
            matches.append({
                'type': 'report',
                'id': report.pk,
                'date': report.incident_date.strftime('%b %d, %Y'),
                'time': report.incident_time.strftime('%I:%M %p') if report.incident_time else '',
                'location': f'{report.barangay}, {report.municipal}',
                'incident_type': report.incident_type_other if (report.incident_type == 'OTHER' and report.incident_type_other) else (report.get_incident_type_display() or ''),
                'status': report.get_status_display(),
                'reporter': report.reporter_name,
            })

    # Check official accidents
    for acc in existing_accidents:
        score = 0
        if barangay and acc.barangay and barangay.lower() == acc.barangay.lower():
            score += 2
        if municipal and acc.municipal and municipal.lower() == acc.municipal.lower():
            score += 1

        if lat and lng and acc.latitude and acc.longitude:
            try:
                dlat = abs(float(lat) - float(acc.latitude))
                dlng = abs(float(lng) - float(acc.longitude))
                if dlat < 0.005 and dlng < 0.005:
                    score += 3
            except (ValueError, TypeError):
                pass

        if score >= 2:
            matches.append({
                'type': 'accident',
                'id': acc.pk,
                'date': acc.date_committed.strftime('%b %d, %Y') if acc.date_committed else '',
                'time': acc.time_committed.strftime('%I:%M %p') if acc.time_committed else '',
                'location': f'{acc.barangay}, {acc.municipal}',
                'incident_type': acc.incident_type or '',
                'status': 'Official Record',
                'reporter': '',
            })

    return JsonResponse({'duplicates': matches[:5]})  # Limit to 5 matches


@pnp_login_required
def view_report_detail(request, pk):
    """View detailed information about a report"""
    report = get_object_or_404(AccidentReport, pk=pk)

    # Check access:
    # 1. User can view their own reports
    # 2. Users with approval roles can view reports in their jurisdiction
    is_own_report = report.reported_by == request.user
    can_approve = can_approve_reports(request.user)
    in_jurisdiction = can_user_approve_report(request.user, report) if can_approve else False

    if not is_own_report and not in_jurisdiction:
        messages.error(request, 'You do not have permission to view this report.')
        return redirect('my_reports')

    # Determine if user can approve/reject this report
    can_take_action = can_approve and in_jurisdiction and report.status == 'pending'

    # Determine if user can edit (own report + cancelled or rejected)
    can_edit = is_own_report and report.status in ('cancelled', 'rejected')

    # Determine if user can cancel (own report + pending)
    can_cancel = is_own_report and report.status == 'pending'

    context = {
        'report': report,
        'is_admin': can_approve and in_jurisdiction,
        'can_take_action': can_take_action,
        'is_own_report': is_own_report,
        'can_edit': can_edit,
        'can_cancel': can_cancel,
        'activity_logs': report.activity_logs.select_related('actor__profile').all(),
    }
    return render(request, 'reports/report_detail.html', context)


@pnp_login_required
def edit_report(request, pk):
    """Edit a pending report - only the reporter can edit their own pending reports"""
    report = get_object_or_404(AccidentReport, pk=pk)

    # Check if user owns this report
    if report.reported_by != request.user:
        messages.error(request, 'You do not have permission to edit this report.')
        return redirect('my_reports')

    # Check if report is editable (cancelled or rejected only - pending must be cancelled first)
    if report.status not in ('cancelled', 'rejected'):
        if report.status == 'pending':
            messages.warning(request, 'You must cancel a pending report before editing it.')
        else:
            messages.warning(request, 'You cannot edit a report that has already been verified.')
        return redirect('my_reports')

    is_resubmit = True  # Editing a cancelled/rejected report always resubmits

    if request.method == 'POST':
        from .forms import AccidentReportForm
        form = AccidentReportForm(request.POST, request.FILES, instance=report)

        if form.is_valid():
            updated_report = form.save(commit=False)

            # Parse multi-victim/suspect JSON from dynamic form rows
            import json as json_module
            try:
                updated_report.victims_data = json_module.loads(request.POST.get('victims_json', '[]'))
            except (json_module.JSONDecodeError, TypeError):
                updated_report.victims_data = []
            try:
                updated_report.suspects_data = json_module.loads(request.POST.get('suspects_json', '[]'))
            except (json_module.JSONDecodeError, TypeError):
                updated_report.suspects_data = []

            # Auto-compute counts
            updated_report.suspect_count = len(updated_report.suspects_data) or 1
            updated_report.casualties_killed = int(request.POST.get('casualties_killed', 0) or 0)
            updated_report.casualties_injured = int(request.POST.get('casualties_injured', 0) or 0)

            # Handle legacy photo removal (clear photos marked for deletion)
            for photo_field in ['photo_1', 'photo_2', 'photo_3']:
                if request.POST.get(f'{photo_field}-clear') == 'on':
                    photo = getattr(updated_report, photo_field)
                    if photo:
                        photo.delete(save=False)
                    setattr(updated_report, photo_field, None)

            # If resubmitting a rejected report, reset status to pending
            if is_resubmit:
                updated_report.status = 'pending'
                updated_report.rejection_reason = ''
                updated_report.verified_by = None
                updated_report.verified_at = None

            updated_report.save()

            # Handle dynamic photo uploads (new ReportPhoto model)
            from .models import ReportPhoto

            # Remove photos marked for deletion
            delete_photo_ids = request.POST.getlist('delete_photos')
            if delete_photo_ids:
                photos_to_delete = ReportPhoto.objects.filter(
                    report=updated_report, pk__in=delete_photo_ids
                )
                for photo in photos_to_delete:
                    if photo.image:
                        photo.image.delete(save=False)
                    photo.delete()

            # Add new uploaded photos
            photo_files = request.FILES.getlist('report_photos')
            next_order = updated_report.photos.count()
            for photo_file in photo_files:
                ReportPhoto.objects.create(
                    report=updated_report,
                    image=photo_file,
                    order=next_order,
                )
                next_order += 1

            # Log activity
            if is_resubmit:
                log_report_activity(updated_report, 'resubmitted', request.user)
            else:
                log_report_activity(updated_report, 'edited', request.user)

            if is_resubmit:
                # Notify admin roles about the resubmitted report (only those with jurisdiction)
                admin_roles = ['super_admin', 'regional_director', 'provincial_chief', 'station_commander']
                admin_users = User.objects.filter(
                    profile__role__in=admin_roles,
                    is_active=True
                ).select_related('profile').exclude(pk=request.user.pk)

                notifications = []
                for admin_user in admin_users:
                    if can_user_approve_report(admin_user, updated_report):
                        notifications.append(Notification(
                            recipient=admin_user,
                            notification_type='report_submitted',
                            title='Report Resubmitted',
                            message=f'{updated_report.reporter_name} resubmitted accident report #{updated_report.pk} at {updated_report.barangay}, {updated_report.municipal}.',
                            url=f'/manage/report/{updated_report.pk}/go/',
                            related_report=updated_report,
                        ))
                if notifications:
                    Notification.objects.bulk_create(notifications)

                messages.success(request, 'Report resubmitted successfully! It will be reviewed again.')
            else:
                messages.success(request, 'Report updated successfully!')
            return redirect('report_detail', pk=pk)
    else:
        from .forms import AccidentReportForm
        form = AccidentReportForm(instance=report)

    import json as json_module
    context = {
        'form': form,
        'report': report,
        'is_edit': True,
        'is_resubmit': is_resubmit,
        'victims_data_json': json_module.dumps(report.victims_data or []),
        'suspects_data_json': json_module.dumps(report.suspects_data or []),
    }

    return render(request, 'reports/report_form.html', context)


@pnp_login_required
def cancel_report(request, pk):
    """Cancel a pending report - withdraws submission"""
    report = get_object_or_404(AccidentReport, pk=pk)

    if report.reported_by != request.user:
        messages.error(request, 'You do not have permission to cancel this report.')
        return redirect('my_reports')

    if report.status != 'pending':
        messages.warning(request, 'Only pending reports can be cancelled.')
        return redirect('my_reports')

    if request.method == 'POST':
        report.status = 'cancelled'
        report.save()

        # Log activity
        log_report_activity(report, 'cancelled', request.user)

        # Notify admins/commanders about the cancellation
        admin_roles = ['super_admin', 'regional_director', 'provincial_chief', 'station_commander']
        admin_users = User.objects.filter(
            profile__role__in=admin_roles,
            is_active=True
        ).select_related('profile').exclude(pk=request.user.pk)

        reporter_name = request.user.get_full_name() or request.user.username
        notifications = []
        for admin_user in admin_users:
            if can_user_approve_report(admin_user, report):
                notifications.append(Notification(
                    recipient=admin_user,
                    notification_type='report_cancelled',
                    title='Report Cancelled',
                    message=f'{reporter_name} cancelled their accident report #{report.pk} at {report.barangay}, {report.municipal}.',
                    url=f'/my-reports/',
                    related_report=report,
                ))
        if notifications:
            Notification.objects.bulk_create(notifications)

        messages.success(request, 'Report has been cancelled successfully.')
        return redirect('my_reports')

    return redirect('my_reports')


@pnp_login_required
def delete_report(request, pk):
    """Delete a cancelled or rejected report permanently"""
    report = get_object_or_404(AccidentReport, pk=pk)

    if report.reported_by != request.user:
        messages.error(request, 'You do not have permission to delete this report.')
        return redirect('my_reports')

    if report.status not in ('cancelled', 'rejected'):
        messages.warning(request, 'Only cancelled or rejected reports can be deleted.')
        return redirect('my_reports')

    if request.method == 'POST':
        # Delete all notifications related to this report (clean up for higher ranks)
        Notification.objects.filter(related_report=report).delete()

        # Delete activity logs
        report.activity_logs.all().delete()

        # Delete photo files (legacy fields)
        for photo_field in ['photo_1', 'photo_2', 'photo_3']:
            photo = getattr(report, photo_field)
            if photo:
                photo.delete(save=False)

        # Delete ReportPhoto files
        for rp in report.photos.all():
            if rp.image:
                rp.image.delete(save=False)

        report.delete()

        messages.success(request, 'Report has been permanently deleted.')
        return redirect('my_reports')

    return redirect('my_reports')


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
    """Change password page - required for new users and password resets"""
    from .auth_utils import log_user_action, validate_password_strength

    is_forced = hasattr(request.user, 'profile') and request.user.profile.must_change_password
    error = None

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        # Validate current password
        if not request.user.check_password(current_password):
            error = 'Current password is incorrect.'
        # Validate new passwords match
        elif new_password != confirm_password:
            error = 'New passwords do not match.'
        # Validate new password is different from current
        elif current_password == new_password:
            error = 'New password must be different from your current password.'
        else:
            # Validate password strength using PNP requirements
            strength_errors = validate_password_strength(new_password)
            if strength_errors:
                error = strength_errors[0]

        if error:
            return render(request, 'accounts/change_password.html', {
                'error': error,
                'is_forced': is_forced,
            })

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

    return render(request, 'accounts/change_password.html', {
        'is_forced': is_forced,
    })

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

    # Get available years from accidents
    years_raw = Accident.objects.filter(
        date_committed__isnull=False
    ).dates('date_committed', 'year', order='DESC')
    years = [date.year for date in years_raw]
    
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
        'years': years,  # Available years for filter dropdown
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
    
    # ============================================================================
    # MULTI-FACTOR RISK ASSESSMENT
    # Considers: Total volume, Fatality rate, and Trend direction
    # ============================================================================
    risk_score = 0

    # Factor 1: Total Accident Volume (0-40 points)
    # High volume = higher risk regardless of fatality rate
    if total_accidents >= 10000:
        risk_score += 40  # Very high volume
    elif total_accidents >= 5000:
        risk_score += 35  # High volume
    elif total_accidents >= 2000:
        risk_score += 25  # Moderate volume
    elif total_accidents >= 1000:
        risk_score += 15  # Low-moderate volume
    elif total_accidents >= 500:
        risk_score += 10  # Low volume
    else:
        risk_score += 5   # Very low volume

    # Factor 2: Fatality Rate (0-40 points)
    # Higher death rate = higher risk
    if fatality_rate >= 15:
        risk_score += 40  # Very high fatality rate
    elif fatality_rate >= 10:
        risk_score += 30  # High fatality rate
    elif fatality_rate >= 5:
        risk_score += 20  # Moderate fatality rate
    elif fatality_rate >= 2:
        risk_score += 10  # Low fatality rate
    else:
        risk_score += 5   # Very low fatality rate

    # Factor 3: Trend Direction (0-20 points)
    # Increasing trend = higher risk
    if trend_direction == "increasing":
        if trend_percentage >= 20:
            risk_score += 20  # Rapidly increasing
        elif trend_percentage >= 10:
            risk_score += 15  # Moderately increasing
        else:
            risk_score += 10  # Slowly increasing
    elif trend_direction == "decreasing":
        risk_score += 0   # Decreasing trend = no added risk
    else:
        risk_score += 5   # Stable

    # Convert risk score to risk level
    # Total possible: 100 points
    if risk_score >= 80:
        risk_level = "CRITICAL"  # 80-100 points
    elif risk_score >= 60:
        risk_level = "HIGH"      # 60-79 points
    elif risk_score >= 40:
        risk_level = "MEDIUM"    # 40-59 points
    else:
        risk_level = "LOW"       # 0-39 points

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

    # Add context about what drove the risk score
    risk_factors_breakdown = f"Volume: {total_accidents:,} | Fatality Rate: {fatality_rate:.1f}% | Trend: {trend_direction}"

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
    # GENDER ANALYTICS
    # ============================================================================
    # Gender Distribution Statistics
    gender_stats = accidents.aggregate(
        male_drivers=Count('id', filter=Q(driver_gender='MALE')),
        female_drivers=Count('id', filter=Q(driver_gender='FEMALE')),
        unknown_drivers=Count('id', filter=Q(driver_gender='UNKNOWN')),
        male_victims=Count('id', filter=Q(victim_gender='MALE')),
        female_victims=Count('id', filter=Q(victim_gender='FEMALE')),
    )

    # Calculate percentages
    total_with_gender = gender_stats['male_drivers'] + gender_stats['female_drivers']
    male_driver_pct = (gender_stats['male_drivers'] / total_with_gender * 100) if total_with_gender > 0 else 0
    female_driver_pct = (gender_stats['female_drivers'] / total_with_gender * 100) if total_with_gender > 0 else 0

    # Gender distribution labels and data (for pie chart)
    gender_labels = ['Male Drivers', 'Female Drivers']
    gender_data = [gender_stats['male_drivers'], gender_stats['female_drivers']]

    # Gender over time (monthly trends)
    gender_trends = accidents.annotate(
        period=trunc_func('date_committed')
    ).values('period').annotate(
        male=Count('id', filter=Q(driver_gender='MALE')),
        female=Count('id', filter=Q(driver_gender='FEMALE'))
    ).order_by('period')

    gender_trend_labels = []
    for item in gender_trends:
        if time_granularity == 'quarterly':
            quarter = (item['period'].month - 1) // 3 + 1
            gender_trend_labels.append(f"Q{quarter} {item['period'].year}")
        else:
            gender_trend_labels.append(item['period'].strftime(date_format))

    gender_trend_male = [item['male'] for item in gender_trends]
    gender_trend_female = [item['female'] for item in gender_trends]

    # Gender by hour of day
    gender_hourly = accidents.annotate(
        hour=ExtractHour('time_committed')
    ).values('hour').annotate(
        male=Count('id', filter=Q(driver_gender='MALE')),
        female=Count('id', filter=Q(driver_gender='FEMALE'))
    ).order_by('hour')

    gender_hourly_male = [0] * 24
    gender_hourly_female = [0] * 24
    for item in gender_hourly:
        if item['hour'] is not None:
            gender_hourly_male[item['hour']] = item['male']
            gender_hourly_female[item['hour']] = item['female']

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
        'risk_score': risk_score,
        'risk_factors_breakdown': risk_factors_breakdown,

        # Gender Analytics
        'male_drivers': gender_stats['male_drivers'],
        'female_drivers': gender_stats['female_drivers'],
        'unknown_drivers': gender_stats['unknown_drivers'],
        'male_driver_pct': round(male_driver_pct, 1),
        'female_driver_pct': round(female_driver_pct, 1),
        'gender_labels': json.dumps(gender_labels),
        'gender_data': json.dumps(gender_data),
        'gender_trend_labels': json.dumps(gender_trend_labels),
        'gender_trend_male': json.dumps(gender_trend_male),
        'gender_trend_female': json.dumps(gender_trend_female),
        'gender_hourly_male': json.dumps(gender_hourly_male),
        'gender_hourly_female': json.dumps(gender_hourly_female),
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
        username_or_badge = request.POST.get('username', '').strip()
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        # Resolve badge number to username if needed
        username = username_or_badge
        try:
            badge_profile = UserProfile.objects.select_related('user').get(badge_number=username_or_badge)
            username = badge_profile.user.username
        except UserProfile.DoesNotExist:
            pass  # Not a badge number — treat as username

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

            # Check if account is active (user.is_active is what admin toggles)
            if not user.is_active:
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
            found_user = User.objects.filter(username=username).first()
            if not found_user:
                # Check if it's a badge number
                try:
                    found_user = UserProfile.objects.select_related('user').get(badge_number=username).user
                except UserProfile.DoesNotExist:
                    pass

            # Check if the account is inactive (deactivated by admin)
            if found_user and not found_user.is_active:
                messages.error(request, 'Your account has been deactivated. Contact administrator.')
                return render(request, 'registration/login.html')

            if found_user:
                # User exists but password is wrong - keep input, focus on password
                error_message = handle_failed_login(username, get_client_ip(request))
                messages.error(request, error_message, extra_tags='focus-password')
                # Pass the original input to template to retain it in the form
                return render(request, 'registration/login.html', {
                    'retained_username': username_or_badge
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


@login_required
def display_settings(request):
    """User-facing page to manage personal display preferences."""
    from .models import SystemSetting

    profile = request.user.profile

    if request.method == 'POST':
        accident_val = request.POST.get('pref_accident_view', '')
        hotspot_val = request.POST.get('pref_hotspot_view', '')

        if accident_val in ('', 'cards', 'table'):
            profile.pref_accident_view = accident_val
        if hotspot_val in ('', 'grid', 'list'):
            profile.pref_hotspot_view = hotspot_val

        profile.save(update_fields=['pref_accident_view', 'pref_hotspot_view'])
        messages.success(request, 'Display settings saved successfully.')
        return redirect('display_settings')

    # Get system defaults for display
    sys_accident = SystemSetting.get('accident_default_view')
    sys_hotspot = SystemSetting.get('hotspot_default_view')

    return render(request, 'pages/display_settings.html', {
        'profile': profile,
        'sys_accident_default': sys_accident,
        'sys_hotspot_default': sys_hotspot,
    })


@pnp_login_required
@require_http_methods(["POST"])
def run_clustering_view(request):
    """Run AGNES clustering synchronously from the UI (no Celery needed)."""
    profile = getattr(request.user, 'profile', None)
    if not (profile and (profile.role in ('super_admin', 'regional_director') or profile.can_run_clustering)):
        return JsonResponse({'success': False, 'error': 'Permission denied. You do not have permission to run clustering.'}, status=403)

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        data = {}

    linkage_method = data.get('linkage_method', 'complete')
    distance_threshold = float(data.get('distance_threshold', 0.05))
    min_cluster_size = int(data.get('min_cluster_size', 3))

    from .models import ClusteringJob, ClusterValidationMetrics
    from clustering.agnes_algorithm import AGNESClusterer
    import time

    start_time = time.time()

    # Create job record
    earliest = Accident.objects.filter(date_committed__isnull=False).order_by('date_committed').first()
    date_from = earliest.date_committed if earliest else timezone.now().date()

    job = ClusteringJob.objects.create(
        linkage_method=linkage_method,
        distance_threshold=distance_threshold,
        min_cluster_size=min_cluster_size,
        date_from=date_from,
        date_to=timezone.now().date(),
        status='running',
        started_by=request.user
    )

    # Audit log - clustering started
    log_user_action(request, 'clustering_run',
        f'Started clustering job #{job.pk} (method={linkage_method}, threshold={distance_threshold}, min_size={min_cluster_size})',
        object_type='ClusteringJob', object_id=job.pk)

    try:
        accidents = list(Accident.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        ).values(
            'id', 'latitude', 'longitude', 'victim_count',
            'victim_killed', 'victim_injured', 'municipal',
            'date_committed'
        ))

        total_accidents = len(accidents)
        if total_accidents < min_cluster_size:
            raise ValueError(f'Not enough accidents with coordinates ({total_accidents} found, need at least {min_cluster_size})')

        # Run AGNES
        clusterer = AGNESClusterer(
            linkage_method=linkage_method,
            distance_threshold=distance_threshold,
            min_cluster_size=min_cluster_size
        )
        result = clusterer.fit(accidents)

        if not result['success']:
            raise Exception(result.get('message', 'Clustering failed'))

        # Clear old clusters
        AccidentCluster.objects.all().delete()
        Accident.objects.all().update(cluster_id=None, is_hotspot=False)

        # Save new clusters
        clusters_created = 0
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
                date_range_start=cluster_data['date_range_start'],
                date_range_end=cluster_data['date_range_end'],
                linkage_method=linkage_method,
                distance_threshold=distance_threshold
            )
            Accident.objects.filter(
                id__in=cluster_data['accident_ids']
            ).update(cluster_id=cluster_data['cluster_id'], is_hotspot=True)
            clusters_created += 1

        # Save validation metrics
        validation_quality = None
        if 'validation_metrics' in result and result['validation_metrics']:
            metrics = result['validation_metrics']
            val = ClusterValidationMetrics.objects.create(
                clustering_job=job,
                num_clusters=result['clusters_found'],
                total_accidents=total_accidents,
                silhouette_score=metrics.get('silhouette_score'),
                davies_bouldin_index=metrics.get('davies_bouldin_index'),
                calinski_harabasz_score=metrics.get('calinski_harabasz_score'),
                linkage_method=linkage_method,
                distance_threshold=distance_threshold
            )
            validation_quality = val.interpret_quality()

        # Update job
        duration = round(time.time() - start_time, 1)
        job.status = 'completed'
        job.completed_at = timezone.now()
        job.total_accidents = total_accidents
        job.clusters_found = clusters_created
        job.save()

        # Audit log - clustering completed
        log_user_action(request, 'clustering_complete',
            f'Clustering job #{job.pk} completed: {clusters_created} clusters found from {total_accidents} accidents in {duration}s',
            object_type='ClusteringJob', object_id=job.pk)

        return JsonResponse({
            'success': True,
            'clusters_found': clusters_created,
            'total_accidents': total_accidents,
            'duration': duration,
            'linkage_method': linkage_method,
            'distance_threshold': distance_threshold,
            'validation_quality': validation_quality,
        })

    except Exception as e:
        job.status = 'failed'
        job.error_message = str(e)
        job.completed_at = timezone.now()
        job.save()

        # Audit log - clustering failed
        log_user_action(request, 'clustering_failed',
            f'Clustering job #{job.pk} failed: {str(e)}',
            object_type='ClusteringJob', object_id=job.pk, severity='critical', success=False)

        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# ========================================
# EXPORT FUNCTIONALITY
# ========================================

from django.http import FileResponse
from .exports import AccidentExporter, ClusterPDFExporter


def _apply_role_scoping(queryset, user):
    """Apply role-based data scoping to an accident queryset.
    Currently all roles can view all accident records for situational awareness."""
    return queryset


@pnp_login_required
def export_accidents_csv(request):
    """Export accidents to CSV file"""
    # Get filter parameters from request
    province = request.GET.get('province', '')
    year = request.GET.get('year', '')
    incident_type = request.GET.get('incident_type', '')

    # Build queryset with filters
    queryset = Accident.objects.all()

    # Role-based data scoping
    queryset = _apply_role_scoping(queryset, request.user)

    if province:
        queryset = queryset.filter(province__icontains=province)
    if year:
        queryset = queryset.filter(year=year)
    if incident_type:
        queryset = queryset.filter(incident_type__icontains=incident_type)

    queryset = queryset.order_by('-date_committed')

    # Generate CSV
    exporter = AccidentExporter()
    filepath = exporter.export_to_csv(queryset)

    # Audit log
    log_user_action(request, 'export_data',
        f'Exported {queryset.count()} accident records to CSV',
        object_type='Accident')

    # Return file response
    response = FileResponse(
        open(filepath, 'rb'),
        content_type='text/csv'
    )
    response['Content-Disposition'] = f'attachment; filename="accidents_export.csv"'
    return response


@pnp_login_required
def export_accidents_excel(request):
    """Export accidents to Excel file"""
    # Get filter parameters from request
    province = request.GET.get('province', '')
    year = request.GET.get('year', '')
    incident_type = request.GET.get('incident_type', '')

    # Build queryset with filters
    queryset = Accident.objects.all()

    # Role-based data scoping
    queryset = _apply_role_scoping(queryset, request.user)

    if province:
        queryset = queryset.filter(province__icontains=province)
    if year:
        queryset = queryset.filter(year=year)
    if incident_type:
        queryset = queryset.filter(incident_type__icontains=incident_type)

    queryset = queryset.order_by('-date_committed')

    # Generate Excel
    exporter = AccidentExporter()
    filepath = exporter.export_to_excel(queryset)

    # Audit log
    log_user_action(request, 'export_data',
        f'Exported {queryset.count()} accident records to Excel',
        object_type='Accident')

    # Return file response
    response = FileResponse(
        open(filepath, 'rb'),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="accidents_export.xlsx"'
    return response


@pnp_login_required
def export_hotspots_pdf(request):
    """Export hotspots to PDF report"""
    # Get filter parameters
    province = request.GET.get('province', '')
    min_severity = request.GET.get('min_severity', '')

    # Build queryset
    queryset = AccidentCluster.objects.all().order_by('-severity_score')

    if province:
        queryset = queryset.filter(primary_location__icontains=province)
    if min_severity:
        queryset = queryset.filter(severity_score__gte=float(min_severity))

    # Generate PDF
    exporter = ClusterPDFExporter()
    filepath = exporter.generate_report(queryset)

    # Audit log
    log_user_action(request, 'export_data',
        f'Exported {queryset.count()} hotspot clusters to PDF',
        object_type='AccidentCluster')

    # Return file response
    response = FileResponse(
        open(filepath, 'rb'),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="hotspots_report.pdf"'
    return response


@pnp_login_required
def export_analytics_pdf(request):
    """Export analytics summary to PDF"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_CENTER
    import os

    # Create exports directory if not exists
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
    os.makedirs(exports_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(exports_dir, f'analytics_report_{timestamp}.pdf')

    # Create PDF
    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)

    elements = []
    styles = getSampleStyleSheet()

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#003087'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    title = Paragraph("Traffic Accident Analytics Report", title_style)
    elements.append(title)

    # Subtitle
    subtitle = Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal'])
    elements.append(subtitle)
    elements.append(Spacer(1, 20))

    # Statistics
    total_accidents = Accident.objects.count()
    total_hotspots = AccidentCluster.objects.count()
    fatal_count = Accident.objects.filter(victim_killed=True).count()
    injury_count = Accident.objects.filter(victim_injured=True).count()

    stats_data = [
        ['Metric', 'Value'],
        ['Total Accidents', str(total_accidents)],
        ['Total Hotspots', str(total_hotspots)],
        ['Fatal Accidents', str(fatal_count)],
        ['Injury Accidents', str(injury_count)],
        ['Fatality Rate', f'{(fatal_count / max(total_accidents, 1) * 100):.1f}%'],
    ]

    stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))

    elements.append(stats_table)
    elements.append(Spacer(1, 30))

    # Province breakdown
    province_stats = Accident.objects.values('province').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    province_data = [['Province', 'Accidents']]
    for stat in province_stats:
        province_data.append([stat['province'], str(stat['count'])])

    if len(province_data) > 1:
        heading = Paragraph("<b>Top 10 Provinces by Accident Count</b>", styles['Heading2'])
        elements.append(heading)
        elements.append(Spacer(1, 10))

        province_table = Table(province_data, colWidths=[3*inch, 2*inch])
        province_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003087')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        elements.append(province_table)

    # Build PDF
    doc.build(elements)

    # Return file
    response = FileResponse(
        open(filepath, 'rb'),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="analytics_report.pdf"'

    # Audit log
    log_user_action(request, 'export_data',
        'Exported analytics summary to PDF',
        object_type='Analytics')

    return response


# =============================================================================
# NARRATIVE ACCIDENT REPORT (PDF) — Weekly / Monthly / Yearly
# =============================================================================

@login_required
def export_monthly_narrative_pdf(request):
    """Generate a Narrative Accident Report PDF (weekly, monthly, or yearly)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
        HRFlowable, KeepTogether, Image
    )
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
    from django.http import FileResponse
    import calendar
    import os

    period = request.GET.get('period', 'monthly')
    year = int(request.GET.get('year', datetime.now().year))

    if year < 2000 or year > 2100:
        return JsonResponse({'error': 'Invalid year'}, status=400)

    # ── Determine date range, labels, and previous-period comparison ──
    if period == 'weekly':
        week = int(request.GET.get('week', 1))
        if week < 1 or week > 53:
            return JsonResponse({'error': 'Invalid week number'}, status=400)
        # ISO week → Monday-based start
        from datetime import date as _date
        start_date = _date.fromisocalendar(year, week, 1)
        end_date = _date.fromisocalendar(year, week, 7)
        period_label = f"Week {week} ({start_date.strftime('%b %d')} – {end_date.strftime('%b %d, %Y')})"
        report_title = "WEEKLY ACCIDENT NARRATIVE REPORT"
        file_prefix = f"weekly_narrative_{year}_W{week:02d}"
        file_label = f"Weekly_Accident_Narrative_Report_W{week}_{year}"
        # Narrative opening
        period_phrase = f"the week of {start_date.strftime('%B %d')} to {end_date.strftime('%B %d, %Y')}"
        # Previous period
        prev_start = start_date - timedelta(days=7)
        prev_end = end_date - timedelta(days=7)
        prev_label = f"the previous week ({prev_start.strftime('%b %d')} – {prev_end.strftime('%b %d')})"

    elif period == 'yearly':
        start_date = datetime(year, 1, 1).date()
        end_date = datetime(year, 12, 31).date()
        period_label = f"Year {year}"
        report_title = "ANNUAL ACCIDENT NARRATIVE REPORT"
        file_prefix = f"annual_narrative_{year}"
        file_label = f"Annual_Accident_Narrative_Report_{year}"
        period_phrase = f"the year {year}"
        prev_start = datetime(year - 1, 1, 1).date()
        prev_end = datetime(year - 1, 12, 31).date()
        prev_label = f"the previous year ({year - 1})"

    else:  # monthly (default)
        month = int(request.GET.get('month', datetime.now().month))
        if month < 1 or month > 12:
            return JsonResponse({'error': 'Invalid month'}, status=400)
        month_name = calendar.month_name[month]
        _, last_day = calendar.monthrange(year, month)
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, last_day).date()
        period_label = f"{month_name} {year}"
        report_title = "MONTHLY ACCIDENT NARRATIVE REPORT"
        file_prefix = f"monthly_narrative_{year}_{month:02d}"
        file_label = f"Monthly_Accident_Narrative_Report_{month_name}_{year}"
        period_phrase = f"the month of {month_name} {year}"
        if month == 1:
            prev_m, prev_y = 12, year - 1
        else:
            prev_m, prev_y = month - 1, year
        _, prev_last_day = calendar.monthrange(prev_y, prev_m)
        prev_start = datetime(prev_y, prev_m, 1).date()
        prev_end = datetime(prev_y, prev_m, prev_last_day).date()
        prev_label = f"{calendar.month_name[prev_m]} {prev_y}"

    # ── Query data ──
    accidents = Accident.objects.filter(
        date_committed__gte=start_date,
        date_committed__lte=end_date
    )
    total = accidents.count()
    fatal = accidents.filter(victim_killed=True).count()
    injury = accidents.filter(victim_injured=True).count()
    property_damage = total - fatal - injury
    total_casualties = accidents.aggregate(s=Sum('victim_count'))['s'] or 0
    hotspot_count = accidents.filter(is_hotspot=True).count()

    province_stats = accidents.values('province').annotate(
        count=Count('id'),
        fatal_count=Count('id', filter=Q(victim_killed=True)),
        injury_count=Count('id', filter=Q(victim_injured=True)),
    ).order_by('-count')

    incident_types = accidents.exclude(
        incident_type__isnull=True
    ).exclude(incident_type='').values('incident_type').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    top_municipalities = accidents.values('municipal', 'province').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    male_drivers = accidents.filter(driver_gender='MALE').count()
    female_drivers = accidents.filter(driver_gender='FEMALE').count()

    prev_total = Accident.objects.filter(
        date_committed__gte=prev_start, date_committed__lte=prev_end
    ).count()

    # ── Build PDF ──
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
    os.makedirs(exports_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filepath = os.path.join(exports_dir, f'{file_prefix}_{timestamp}.pdf')

    doc = SimpleDocTemplate(
        filepath, pagesize=letter,
        rightMargin=60, leftMargin=60,
        topMargin=50, bottomMargin=40
    )

    elements = []
    styles = getSampleStyleSheet()
    W = doc.width  # usable width

    PRIMARY = colors.HexColor('#003087')
    LIGHT_BG = colors.HexColor('#F0F4FA')
    BORDER = colors.HexColor('#CCCCCC')

    s_hdr = ParagraphStyle('HdrSm', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', alignment=TA_CENTER, leading=10, textColor=colors.HexColor('#444444'))
    s_hdr_bold = ParagraphStyle('HdrBold', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=13)
    style_title = ParagraphStyle('ReportTitle', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER, textColor=PRIMARY,
        spaceAfter=2, spaceBefore=4)
    style_subtitle = ParagraphStyle('ReportSubtitle', parent=styles['Normal'],
        fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor('#333333'), spaceAfter=8)
    style_section = ParagraphStyle('SectionHead', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', textColor=colors.white, leading=13)
    style_body = ParagraphStyle('BodyText2', parent=styles['Normal'],
        fontSize=9, leading=13, alignment=TA_JUSTIFY, spaceAfter=6)
    style_footer = ParagraphStyle('Footer', parent=styles['Normal'],
        fontSize=7, fontName='Helvetica-Oblique', alignment=TA_CENTER, textColor=colors.HexColor('#888888'), spaceBefore=12)

    # ===================== HEADER (3-column: logo | text | logo) =====================
    static_dir = settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT or ''
    pnp_logo_path = os.path.join(static_dir, 'images', 'pnp-logo1.png')
    if not os.path.exists(pnp_logo_path):
        pnp_logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'pnp-logo1.png')
    agnes_logo_path = os.path.join(static_dir, 'images', 'pnp-logo.png')
    if not os.path.exists(agnes_logo_path):
        agnes_logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'pnp-logo.png')

    header_left = Image(pnp_logo_path, width=50, height=60) if os.path.exists(pnp_logo_path) else ''
    header_right = Image(agnes_logo_path, width=50, height=55) if os.path.exists(agnes_logo_path) else ''

    header_center = [
        Paragraph('Republic of the Philippines', s_hdr),
        Paragraph('<b>PHILIPPINE NATIONAL POLICE</b>', s_hdr_bold),
        Paragraph('POLICE REGIONAL OFFICE 13', ParagraphStyle('PRO', parent=s_hdr_bold, fontSize=9, leading=11)),
        Paragraph('Camp Col. Rafael C. Rodriguez, Libertad, Butuan City', s_hdr),
    ]

    header_tbl = Table(
        [[header_left, header_center, header_right]],
        colWidths=[0.9 * inch, W - 1.8 * inch, 0.9 * inch],
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_tbl)
    elements.append(HRFlowable(width="100%", thickness=2, color=PRIMARY, spaceBefore=2, spaceAfter=2))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=PRIMARY, spaceBefore=0, spaceAfter=6))

    # ===================== TITLE =====================
    elements.append(Paragraph(f"<b>{report_title}</b>", style_title))
    elements.append(Paragraph(period_label, style_subtitle))
    elements.append(HRFlowable(width="40%", thickness=0.5, color=BORDER, spaceAfter=10))

    # ── Section header builder (blue banner, matching report page) ──
    def section_banner(title):
        tbl = Table([[Paragraph(title, style_section)]], colWidths=[W])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('ROUNDEDCORNERS', [3, 3, 0, 0]),
        ]))
        return tbl

    # ── Standard table style ──
    def std_table_style():
        return TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ])

    # ===================== I. SUMMARY STATISTICS =====================
    elements.append(section_banner('I. SUMMARY STATISTICS'))

    if prev_total > 0:
        trend_word = 'Increase' if total > prev_total else ('Decrease' if total < prev_total else 'Same as')
        remarks_trend = f"{trend_word} from {prev_total} in {prev_label}"
    else:
        remarks_trend = f"No data for {prev_label}"

    stats_data = [
        ['Metric', 'Count', 'Remarks'],
        ['Total Accidents Recorded', str(total), remarks_trend],
        ['Fatal Accidents', str(fatal), f'{(fatal / max(total, 1) * 100):.1f}% of total'],
        ['Injury Accidents', str(injury), f'{(injury / max(total, 1) * 100):.1f}% of total'],
        ['Property Damage Only', str(property_damage), f'{(property_damage / max(total, 1) * 100):.1f}% of total'],
        ['Total Casualties', str(total_casualties), 'Victims involved'],
        ['Hotspot-Area Accidents', str(hotspot_count), f'{(hotspot_count / max(total, 1) * 100):.1f}% in identified hotspots'],
    ]

    stats_table = Table(stats_data, colWidths=[2.2 * inch, 0.8 * inch, W - 3.0 * inch])
    stats_table.setStyle(std_table_style())
    elements.append(stats_table)
    elements.append(Spacer(1, 10))

    # ===================== II. NARRATIVE SUMMARY =====================
    elements.append(section_banner('II. NARRATIVE SUMMARY'))

    if prev_total > 0:
        change = total - prev_total
        change_pct = abs(change) / prev_total * 100
        if change > 0:
            trend_text = f"an increase of {change} ({change_pct:.1f}%) compared to {prev_total} accidents in {prev_label}"
        elif change < 0:
            trend_text = f"a decrease of {abs(change)} ({change_pct:.1f}%) compared to {prev_total} accidents in {prev_label}"
        else:
            trend_text = f"the same number as {prev_label}"
    else:
        trend_text = f"with no records available for comparison from {prev_label}"

    top_province = province_stats.first()
    top_province_text = f"{top_province['province']} with {top_province['count']} recorded incidents" if top_province else "N/A"
    top_muni = top_municipalities.first()
    top_muni_text = f"{top_muni['municipal']}, {top_muni['province']}" if top_muni else "N/A"
    top_type = incident_types.first()
    top_type_text = f"{top_type['incident_type']} ({top_type['count']} incidents)" if top_type else "N/A"

    total_gendered = male_drivers + female_drivers
    male_pct = (male_drivers / max(total_gendered, 1) * 100)
    female_pct = (female_drivers / max(total_gendered, 1) * 100)

    narrative = (
        f"For {period_phrase}, a total of <b>{total}</b> traffic accidents were "
        f"recorded within the CARAGA region, representing {trend_text}. "
        f"Of these, <b>{fatal}</b> were classified as fatal accidents, <b>{injury}</b> resulted in physical injuries, "
        f"and <b>{property_damage}</b> involved property damage only. "
        f"A total of <b>{total_casualties}</b> casualties (killed and injured combined) were reported during the period."
    )
    elements.append(Paragraph(narrative, style_body))

    narrative2 = (
        f"The highest concentration of accidents was observed in <b>{top_province_text}</b>, "
        f"with <b>{top_muni_text}</b> recording the most incidents at the municipal level. "
        f"The most prevalent type of incident was <b>{top_type_text}</b>. "
        f"Among identified drivers/suspects, <b>{male_pct:.1f}%</b> were male and "
        f"<b>{female_pct:.1f}%</b> were female."
    )
    elements.append(Paragraph(narrative2, style_body))

    if hotspot_count > 0:
        elements.append(Paragraph(
            f"Notably, <b>{hotspot_count}</b> of the period's accidents ({(hotspot_count / max(total, 1) * 100):.1f}%) "
            f"occurred within previously identified hotspot areas, underscoring the need for continued "
            f"enforcement and preventive measures in these high-risk zones.",
            style_body
        ))

    elements.append(Spacer(1, 8))

    # ===================== III. BREAKDOWN BY PROVINCE =====================
    if province_stats.exists():
        elements.append(section_banner('III. BREAKDOWN BY PROVINCE'))
        prov_data = [['Province', 'Total', 'Fatal', 'Injury', 'Property Damage']]
        for p in province_stats:
            pd_count = p['count'] - p['fatal_count'] - p['injury_count']
            prov_data.append([p['province'] or 'Unknown', str(p['count']), str(p['fatal_count']), str(p['injury_count']), str(pd_count)])

        cw = W / 5
        prov_table = Table(prov_data, colWidths=[cw * 1.6, cw * 0.85, cw * 0.85, cw * 0.85, cw * 0.85])
        prov_table.setStyle(std_table_style())
        elements.append(prov_table)
        elements.append(Spacer(1, 10))

    # ===================== IV. TOP INCIDENT TYPES =====================
    if incident_types.exists():
        elements.append(section_banner('IV. TOP INCIDENT TYPES'))
        type_data = [['Incident Type', 'Count', '% of Total']]
        for t in incident_types:
            type_data.append([t['incident_type'][:60], str(t['count']), f'{(t["count"] / max(total, 1) * 100):.1f}%'])

        type_table = Table(type_data, colWidths=[W - 2.0 * inch, 1.0 * inch, 1.0 * inch])
        type_table.setStyle(std_table_style())
        elements.append(type_table)
        elements.append(Spacer(1, 10))

    # ===================== V. NARRATIVE REPORT OF ACCIDENTS =====================
    elements.append(section_banner('V. NARRATIVE REPORT OF ACCIDENTS'))
    elements.append(Paragraph(
        f"The following are the individual narrative accounts of traffic accidents recorded "
        f"during {period_phrase} in the CARAGA region, presented in chronological order "
        f"following the standard PNP incident reporting format.",
        style_body
    ))

    style_entry_no = ParagraphStyle('EntryNumber', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', leading=13, textColor=colors.white)

    accident_list = accidents.order_by('date_committed', 'time_committed')[:100]

    for i, acc in enumerate(accident_list, 1):
        entry_elements = []

        # Severity classification
        if acc.victim_killed:
            severity = 'FATAL'
            severity_color = '#DC2626'
        elif acc.victim_injured:
            severity = 'NON-FATAL (INJURY)'
            severity_color = '#D97706'
        else:
            severity = 'DAMAGE TO PROPERTY'
            severity_color = '#2563EB'

        # ── Entry Number Header with severity badge ──
        num_badge_data = [[
            Paragraph(f"Entry No. {i}", style_entry_no),
            Paragraph(f"<font color='white'><b>{severity}</b></font>",
                ParagraphStyle('SevBadge', parent=styles['Normal'],
                    fontSize=8, fontName='Helvetica-Bold', alignment=TA_CENTER,
                    textColor=colors.white, leading=10))
        ]]
        num_badge = Table(num_badge_data, colWidths=[4.8 * inch, 1.6 * inch])
        num_badge.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#003087')),
            ('BACKGROUND', (1, 0), (1, 0), colors.HexColor(severity_color)),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (0, 0), 8),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        entry_elements.append(num_badge)

        # ── Detail rows as structured table ──
        detail_rows = []

        # 1. Date/Time of Incident
        date_str = acc.date_committed.strftime('%B %d, %Y') if acc.date_committed else 'N/A'
        time_str = acc.time_committed.strftime('%I:%M %p') if acc.time_committed else 'N/A'
        detail_rows.append(['Date/Time of Incident:', f"{date_str} at {time_str}"])

        # 2. Date/Time Reported
        rpt_date = acc.date_reported.strftime('%B %d, %Y') if acc.date_reported else 'N/A'
        rpt_time = acc.time_reported.strftime('%I:%M %p') if acc.time_reported else 'N/A'
        detail_rows.append(['Date/Time Reported:', f"{rpt_date} at {rpt_time}"])

        # 3. Place of Incident
        place_parts = []
        if acc.street:
            place_parts.append(acc.street)
        if acc.barangay:
            place_parts.append(f"Brgy. {acc.barangay}")
        if acc.municipal:
            place_parts.append(acc.municipal)
        if acc.province:
            place_parts.append(acc.province)
        place_str = ', '.join(place_parts) if place_parts else 'N/A'
        if acc.type_of_place:
            place_str += f" ({acc.type_of_place})"
        detail_rows.append(['Place of Incident:', place_str])

        # 4. Reporting Unit/Station
        station_parts = []
        if acc.station:
            station_parts.append(acc.station)
        if acc.ppo:
            station_parts.append(acc.ppo)
        station_str = ', '.join(station_parts) if station_parts else 'N/A'
        detail_rows.append(['Reporting Unit:', station_str])

        # 5. Type of Incident / Offense
        incident_str = acc.incident_type or 'N/A'
        if acc.offense:
            offense_text = str(acc.offense)[:80]
            incident_str += f" / {offense_text}"
        detail_rows.append(['Type of Incident:', incident_str])

        # 6. Suspect/Driver Information
        driver_info_parts = []
        if acc.suspect_details and acc.suspect_details != 'nan':
            # Clean up suspect details - take first 120 chars
            suspect_text = str(acc.suspect_details).strip()[:120]
            driver_info_parts.append(suspect_text)
        else:
            gender_str = acc.get_driver_gender_display() if acc.driver_gender != 'UNKNOWN' else 'Unidentified'
            age_str = f", {acc.driver_age} years old" if acc.driver_age else ''
            driver_info_parts.append(f"{gender_str}{age_str}")
        detail_rows.append(['Suspect/Driver:', ' '.join(driver_info_parts)])

        # 7. Victim Information
        victim_info_parts = []
        if acc.victim_details and acc.victim_details != 'nan':
            victim_text = str(acc.victim_details).strip()[:120]
            victim_info_parts.append(victim_text)
        else:
            v_gender = acc.get_victim_gender_display() if acc.victim_gender != 'UNKNOWN' else 'Unidentified'
            v_age = f", {acc.victim_age} years old" if acc.victim_age else ''
            victim_info_parts.append(f"{v_gender}{v_age}")
        casualty_summary = []
        if acc.victim_killed:
            casualty_summary.append(f"Killed: {acc.victim_count}")
        if acc.victim_injured:
            casualty_summary.append(f"Injured: {acc.victim_count}")
        if casualty_summary:
            victim_info_parts.append(f"[{', '.join(casualty_summary)}]")
        detail_rows.append(['Victim(s):', ' '.join(victim_info_parts)])

        # 8. Vehicle Information
        vehicle_parts = []
        if acc.vehicle_kind:
            vehicle_parts.append(str(acc.vehicle_kind))
        if acc.vehicle_make:
            vehicle_parts.append(str(acc.vehicle_make))
        if acc.vehicle_model:
            vehicle_parts.append(str(acc.vehicle_model))
        vehicle_str = ' / '.join(vehicle_parts) if vehicle_parts else 'N/A'
        if acc.vehicle_plate_no:
            vehicle_str += f" (Plate: {acc.vehicle_plate_no})"
        if acc.vehicle_colorum:
            vehicle_str += " [COLORUM]"
        detail_rows.append(['Vehicle Involved:', vehicle_str])

        # 9. Drug/Alcohol Involvement
        if acc.drug_involved:
            detail_rows.append(['Drug/Alcohol:', 'YES - Drug/Alcohol involvement reported'])

        # Build the detail table
        # Convert detail_rows to Paragraph objects for word wrapping
        detail_table_data = []
        for label, value in detail_rows:
            detail_table_data.append([
                Paragraph(f"<b>{label}</b>", ParagraphStyle('DL', parent=styles['Normal'],
                    fontSize=8, fontName='Helvetica-Bold', leading=10, textColor=colors.HexColor('#374151'))),
                Paragraph(str(value), ParagraphStyle('DV', parent=styles['Normal'],
                    fontSize=8, fontName='Helvetica', leading=10, textColor=colors.HexColor('#1a1a1a')))
            ])

        detail_table = Table(detail_table_data, colWidths=[1.4 * inch, 5.0 * inch])
        detail_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (0, -1), 8),
            ('LEFTPADDING', (1, 0), (1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.HexColor('#E5E7EB')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFBFC')),
        ]))
        entry_elements.append(detail_table)

        # 10. Narrative paragraph (if available)
        if acc.narrative and str(acc.narrative).strip() and str(acc.narrative).strip() != 'nan':
            narr_text = str(acc.narrative).strip()[:500]
            narr_header_data = [[
                Paragraph("<b>NARRATIVE:</b>", ParagraphStyle('NH', parent=styles['Normal'],
                    fontSize=8, fontName='Helvetica-Bold', leading=10, textColor=colors.HexColor('#003087')))
            ]]
            narr_header_tbl = Table(narr_header_data, colWidths=[6.4 * inch])
            narr_header_tbl.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFBFC')),
            ]))
            entry_elements.append(narr_header_tbl)

            narr_body_data = [[
                Paragraph(f"&ldquo;{narr_text}&rdquo;", ParagraphStyle('NB', parent=styles['Normal'],
                    fontSize=8, fontName='Helvetica-Oblique', leading=11, textColor=colors.HexColor('#374151'),
                    alignment=TA_JUSTIFY))
            ]]
            narr_body_tbl = Table(narr_body_data, colWidths=[6.4 * inch])
            narr_body_tbl.setStyle(TableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 20),
                ('RIGHTPADDING', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFBFC')),
            ]))
            entry_elements.append(narr_body_tbl)

        # Wrap entire entry in KeepTogether to avoid page breaks mid-entry
        elements.append(KeepTogether(entry_elements))
        elements.append(Spacer(1, 8))

    if total > 100:
        elements.append(Paragraph(
            f"<i>Note: This report displays the first 100 entries out of {total} total recorded accidents "
            f"for {period_phrase}. A complete listing may be obtained from the AGNES system database.</i>",
            ParagraphStyle('TruncNote', parent=styles['Normal'],
                fontSize=8, fontName='Helvetica-Oblique', leading=10,
                textColor=colors.HexColor('#6B7280'), alignment=TA_CENTER, spaceBefore=4)
        ))
    elif total == 0:
        elements.append(Paragraph(
            f"<i>No traffic accident records were found for {period_phrase}.</i>",
            ParagraphStyle('NoData', parent=styles['Normal'],
                fontSize=9, fontName='Helvetica-Oblique', leading=12,
                textColor=colors.HexColor('#6B7280'), alignment=TA_CENTER, spaceBefore=8)
        ))

    elements.append(Spacer(1, 14))

    # ===================== PREPARED / NOTED BY =====================
    s_sig_label = ParagraphStyle('SigLabel', parent=styles['Normal'],
        fontSize=7.5, fontName='Helvetica', alignment=TA_CENTER, textColor=colors.HexColor('#666666'))
    s_sig_line = ParagraphStyle('SigLine', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', alignment=TA_CENTER)

    sig_line = '_' * 32
    sig_data = [
        ['', '', ''],
        [Paragraph(sig_line, s_sig_line), '', Paragraph(sig_line, s_sig_line)],
        [Paragraph('Prepared by', s_sig_label), '', Paragraph('Noted by', s_sig_label)],
        [Paragraph('AGNES System / Investigating Officer', s_sig_label), '',
         Paragraph('Chief of Police / OIC', s_sig_label)],
    ]
    sig_tbl = Table(sig_data, colWidths=[W * 0.4, W * 0.2, W * 0.4])
    sig_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, 0), 20),
        ('TOPPADDING', (0, 1), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 12))

    # ===================== FOOTER =====================
    elements.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY, spaceAfter=6))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        style_footer
    ))
    elements.append(Paragraph(
        f"AGNES Hotspot Detection System &nbsp;|&nbsp; PNP Police Regional Office 13",
        style_footer
    ))

    doc.build(elements)

    response = FileResponse(open(filepath, 'rb'), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{file_label}.pdf"'

    log_user_action(request, 'export_data',
        f'Generated {period.capitalize()} Narrative Report for {period_label}',
        object_type='NarrativeReport')

    return response


# =============================================================================
# ACCIDENT REPORT PDF DOWNLOAD
# =============================================================================

@login_required
def download_report_pdf(request, pk):
    """Generate a PDF of an approved accident report matching the official PNP form."""
    from django.http import HttpResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
    )
    from io import BytesIO
    import os

    report = get_object_or_404(AccidentReport, pk=pk)

    # Permission check: own report or approver with jurisdiction
    is_own = report.reported_by == request.user
    can_approve = can_approve_reports(request.user)
    in_jurisdiction = can_user_approve_report(request.user, report) if can_approve else False

    if not (is_own or (can_approve and in_jurisdiction)):
        return JsonResponse({'error': 'Permission denied.'}, status=403)

    # Only approved (verified) reports can be downloaded
    if report.status != 'verified':
        return JsonResponse({'error': 'Only approved reports can be downloaded as PDF.'}, status=403)

    # ---------- helpers ----------
    def _v(val, default='-'):
        """Return val or default if empty/None."""
        if val is None or val == '' or val == 'None':
            return default
        return str(val)

    def _choice(val, choices, default='-'):
        """Display label for a choice value."""
        if not val:
            return default
        for k, label in choices:
            if k == val:
                return label
        return _v(val, default)

    def _bool(val):
        return 'Yes' if val else 'No'

    # ---------- build PDF in memory ----------
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
    )

    elements = []
    styles = getSampleStyleSheet()
    W = doc.width  # usable width

    # Style definitions
    s_title = ParagraphStyle('PNPTitle', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER, leading=13)
    s_subtitle = ParagraphStyle('PNPSub', parent=styles['Normal'], fontSize=8, fontName='Helvetica', alignment=TA_CENTER, leading=10)
    s_section = ParagraphStyle('Section', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', leading=12, textColor=colors.white)
    s_label = ParagraphStyle('Label', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica-Bold', leading=9, textColor=colors.HexColor('#333333'))
    s_value = ParagraphStyle('Value', parent=styles['Normal'], fontSize=8, fontName='Helvetica', leading=10)
    s_value_sm = ParagraphStyle('ValueSm', parent=styles['Normal'], fontSize=7.5, fontName='Helvetica', leading=9)
    s_narrative = ParagraphStyle('Narrative', parent=styles['Normal'], fontSize=8, fontName='Helvetica', leading=11, spaceBefore=2, spaceAfter=2)
    s_footer = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, fontName='Helvetica-Oblique', alignment=TA_CENTER, textColor=colors.HexColor('#888888'))

    PRIMARY = colors.HexColor('#003087')
    LIGHT_BG = colors.HexColor('#F0F4FA')
    BORDER = colors.HexColor('#CCCCCC')

    # ==================== HEADER ====================
    logo_path = os.path.join(settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT or '', 'images', 'pnp-logo1.png')

    header_data = []
    header_left = ''
    if os.path.exists(logo_path):
        header_left = Image(logo_path, width=50, height=60)

    header_center = [
        Paragraph('Republic of the Philippines', s_subtitle),
        Paragraph('<b>NATIONAL POLICE COMMISSION</b>', ParagraphStyle('H0', parent=s_subtitle, fontSize=7.5, leading=9)),
        Paragraph('<b>PHILIPPINE NATIONAL POLICE</b>', ParagraphStyle('H', parent=s_title, fontSize=10, leading=12)),
        Paragraph('POLICE REGIONAL OFFICE 13', ParagraphStyle('H2', parent=s_title, fontSize=9, leading=11)),
        Paragraph('Camp Col. Rafael C. Rodriguez, Libertad, Butuan City', s_subtitle),
        Spacer(1, 4),
        Paragraph('<b>TRAFFIC ACCIDENT REPORT</b>', ParagraphStyle('H3', parent=s_title, fontSize=11, leading=13, textColor=PRIMARY)),
    ]

    logo2_path = os.path.join(settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else settings.STATIC_ROOT or '', 'images', 'pnp-logo.png')
    header_right = ''
    if os.path.exists(logo2_path):
        header_right = Image(logo2_path, width=50, height=55)

    header_tbl = Table(
        [[header_left, header_center, header_right]],
        colWidths=[0.9 * inch, W - 1.8 * inch, 0.9 * inch],
    )
    header_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_tbl)

    # Report reference line
    ref_data = [
        [Paragraph(f'<b>Report No:</b> AR-{report.pk:05d}', s_value),
         Paragraph(f'<b>Date Filed:</b> {report.created_at.strftime("%B %d, %Y")}', s_value),
         Paragraph(f'<b>Status:</b> APPROVED', ParagraphStyle('S', parent=s_value, textColor=colors.HexColor('#059669')))]
    ]
    ref_tbl = Table(ref_data, colWidths=[W / 3] * 3)
    ref_tbl.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, PRIMARY),
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    elements.append(ref_tbl)
    elements.append(Spacer(1, 6))

    # ==================== SECTION BUILDER ====================
    def section_header(title):
        tbl = Table(
            [[Paragraph(title, s_section)]],
            colWidths=[W],
        )
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('ROUNDEDCORNERS', [3, 3, 0, 0]),
        ]))
        return tbl

    def field_row(pairs, col_widths=None):
        """Build a row of label-value pairs. pairs = [(label, value), ...]"""
        cells = []
        for lbl, val in pairs:
            cells.append(Paragraph(f'<b>{lbl}:</b>', s_label))
            cells.append(Paragraph(_v(val), s_value))
        n = len(pairs)
        if col_widths is None:
            lw = 1.3 * inch
            vw = (W - n * lw) / n
            col_widths = []
            for _ in range(n):
                col_widths.extend([lw, vw])
        tbl = Table([cells], colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.25, colors.HexColor('#E5E7EB')),
        ]))
        return tbl

    # ==================== 1. INCIDENT INFORMATION ====================
    elements.append(section_header('I. INCIDENT INFORMATION'))

    incident_type_display = _choice(report.incident_type, AccidentReport.INCIDENT_TYPE_CHOICES)
    if report.incident_type == 'OTHER' and report.incident_type_other:
        incident_type_display = f'Other: {report.incident_type_other}'

    place_type_display = _choice(report.type_of_place, AccidentReport.PLACE_TYPE_CHOICES)
    if report.type_of_place == 'OTHER' and report.type_of_place_other:
        place_type_display = f'Other: {report.type_of_place_other}'

    elements.append(field_row([
        ('Date of Incident', report.incident_date.strftime('%B %d, %Y') if report.incident_date else '-'),
        ('Time of Incident', report.incident_time.strftime('%I:%M %p') if report.incident_time else '-'),
    ]))
    elements.append(field_row([
        ('Type of Incident', incident_type_display),
        ('Type of Place', place_type_display),
    ]))
    elements.append(Spacer(1, 6))

    # ==================== 2. LOCATION ====================
    elements.append(section_header('II. LOCATION OF INCIDENT'))

    elements.append(field_row([
        ('Province', _v(report.province)),
        ('Municipality', _v(report.municipal)),
    ]))
    elements.append(field_row([
        ('Barangay', _v(report.barangay)),
        ('Street Address', _v(report.street_address)),
    ]))
    elements.append(field_row([
        ('Latitude', str(report.latitude) if report.latitude else '-'),
        ('Longitude', str(report.longitude) if report.longitude else '-'),
    ]))
    elements.append(Spacer(1, 6))

    # ==================== 3. OFFENSE / LEGAL ====================
    elements.append(section_header('III. OFFENSE / LEGAL CLASSIFICATION'))

    offense_display = _choice(report.offense, AccidentReport.OFFENSE_CHOICES)
    if report.offense == 'OTHER' and report.offense_other:
        offense_display = f'Other: {report.offense_other}'

    offense_type_display = _choice(report.offense_type, AccidentReport.OFFENSE_TYPE_CHOICES)
    if report.offense_type == 'OTHER' and report.offense_type_other:
        offense_type_display = f'Other: {report.offense_type_other}'

    elements.append(field_row([('Offense', offense_display)],
        col_widths=[1.3 * inch, W - 1.3 * inch]))
    elements.append(field_row([
        ('Offense Type', offense_type_display),
        ('Stage of Felony', _choice(report.stage_of_felony, AccidentReport.STAGE_OF_FELONY_CHOICES)),
    ]))
    elements.append(field_row([
        ('Drug/Alcohol Involved', _bool(report.drug_involved)),
        ('Casualties Killed', str(report.casualties_killed)),
    ]))
    elements.append(field_row([
        ('Casualties Injured', str(report.casualties_injured)),
        ('', ''),
    ]))
    elements.append(Spacer(1, 6))

    # ==================== 4. VICTIM INFORMATION ====================
    elements.append(section_header('IV. VICTIM INFORMATION'))

    victims = report.victims_data if report.victims_data else []
    if not victims and report.victim_name:
        victims = [{
            'name': report.victim_name or '-',
            'age': report.victim_age or '-',
            'gender': _choice(report.victim_gender, AccidentReport.GENDER_CHOICES),
            'status': _choice(report.victim_status, AccidentReport.VICTIM_STATUS_CHOICES),
        }]

    if victims:
        v_header = [
            Paragraph('<b>No.</b>', s_label),
            Paragraph('<b>Name</b>', s_label),
            Paragraph('<b>Age</b>', s_label),
            Paragraph('<b>Gender</b>', s_label),
            Paragraph('<b>Status</b>', s_label),
        ]
        v_rows = [v_header]
        for i, v in enumerate(victims, 1):
            gender_val = v.get('gender', '-')
            if gender_val in ('MALE', 'FEMALE', 'UNKNOWN'):
                gender_val = _choice(gender_val, AccidentReport.GENDER_CHOICES)
            status_val = v.get('status', '-')
            if status_val in ('KILLED', 'INJURED', 'UNHARMED'):
                status_val = _choice(status_val, AccidentReport.VICTIM_STATUS_CHOICES)
            v_rows.append([
                Paragraph(str(i), s_value_sm),
                Paragraph(_v(v.get('name')), s_value_sm),
                Paragraph(_v(v.get('age')), s_value_sm),
                Paragraph(_v(gender_val), s_value_sm),
                Paragraph(_v(status_val), s_value_sm),
            ])
        v_tbl = Table(v_rows, colWidths=[0.4 * inch, 2.2 * inch, 0.6 * inch, 0.9 * inch, W - 4.1 * inch])
        v_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(v_tbl)
    else:
        elements.append(Paragraph('No victim information recorded.', s_value))
    elements.append(Spacer(1, 6))

    # ==================== 5. SUSPECT / DRIVER ====================
    elements.append(section_header('V. SUSPECT / DRIVER INFORMATION'))

    suspects = report.suspects_data if report.suspects_data else []
    if not suspects and report.suspect_name:
        suspects = [{
            'name': report.suspect_name or '-',
            'age': report.driver_age or '-',
            'gender': _choice(report.driver_gender, AccidentReport.GENDER_CHOICES),
        }]

    if suspects:
        sp_header = [
            Paragraph('<b>No.</b>', s_label),
            Paragraph('<b>Name</b>', s_label),
            Paragraph('<b>Age</b>', s_label),
            Paragraph('<b>Gender</b>', s_label),
        ]
        sp_rows = [sp_header]
        for i, s in enumerate(suspects, 1):
            gender_val = s.get('gender', '-')
            if gender_val in ('MALE', 'FEMALE', 'UNKNOWN'):
                gender_val = _choice(gender_val, AccidentReport.GENDER_CHOICES)
            sp_rows.append([
                Paragraph(str(i), s_value_sm),
                Paragraph(_v(s.get('name')), s_value_sm),
                Paragraph(_v(s.get('age')), s_value_sm),
                Paragraph(_v(gender_val), s_value_sm),
            ])
        sp_tbl = Table(sp_rows, colWidths=[0.4 * inch, 2.8 * inch, 0.6 * inch, W - 3.8 * inch])
        sp_tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), LIGHT_BG),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sp_tbl)
    else:
        elements.append(field_row([
            ('Suspect Name', _v(report.suspect_name)),
            ('Suspect Count', str(report.suspect_count)),
        ]))
        elements.append(field_row([
            ('Driver Gender', _choice(report.driver_gender, AccidentReport.GENDER_CHOICES)),
            ('Driver Age', _v(report.driver_age)),
        ]))
    elements.append(Spacer(1, 6))

    # ==================== 6. VEHICLE INFORMATION ====================
    elements.append(section_header('VI. VEHICLE INFORMATION'))

    vk_display = _choice(report.vehicle_kind, AccidentReport.VEHICLE_KIND_CHOICES)
    if report.vehicle_kind == 'OTHER' and report.vehicle_kind_other:
        vk_display = f'Other: {report.vehicle_kind_other}'

    make_display = _v(report.vehicle_make)
    if report.vehicle_make == 'Other' and report.vehicle_make_other:
        make_display = report.vehicle_make_other

    model_display = _v(report.vehicle_model)
    if report.vehicle_model == 'Other' and report.vehicle_model_other:
        model_display = report.vehicle_model_other

    elements.append(field_row([
        ('Vehicle Type', vk_display),
        ('Make/Brand', make_display),
    ]))
    elements.append(field_row([
        ('Model', model_display),
        ('Plate Number', _v(report.vehicle_plate_no)),
    ]))
    elements.append(field_row([
        ('Chassis No.', _v(report.vehicle_chassis_no)),
        ('Colorum (No Franchise)', _bool(report.vehicle_colorum)),
    ]))
    elements.append(Spacer(1, 6))

    # ==================== 7. NARRATIVE ====================
    elements.append(section_header('VII. INCIDENT NARRATIVE'))

    narrative_text = report.incident_description or 'No narrative provided.'
    # Wrap in a bordered box
    nar_tbl = Table(
        [[Paragraph(narrative_text.replace('\n', '<br/>'), s_narrative)]],
        colWidths=[W],
    )
    nar_tbl.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFBFC')),
    ]))
    elements.append(nar_tbl)
    elements.append(Spacer(1, 6))

    # ==================== 8. REPORTER & VERIFICATION ====================
    elements.append(section_header('VIII. REPORTER & VERIFICATION'))

    elements.append(field_row([
        ('Reported By', _v(report.reporter_name)),
        ('Contact', _v(report.reporter_contact)),
    ]))

    verifier_name = '-'
    verifier_rank = ''
    if report.verified_by:
        verifier_name = report.verified_by.get_full_name() or report.verified_by.username
        if hasattr(report.verified_by, 'profile') and report.verified_by.profile.rank:
            verifier_rank = f' ({report.verified_by.profile.get_rank_display()})'
        verifier_name += verifier_rank

    elements.append(field_row([
        ('Approved By', verifier_name),
        ('Date Approved', report.verified_at.strftime('%B %d, %Y') if report.verified_at else '-'),
    ]))
    elements.append(Spacer(1, 16))

    # ==================== SIGNATURE BLOCK ====================
    sig_line = '_' * 35
    sig_data = [
        ['', '', ''],
        [Paragraph(sig_line, ParagraphStyle('SL', parent=s_value, alignment=TA_CENTER)),
         '',
         Paragraph(sig_line, ParagraphStyle('SL', parent=s_value, alignment=TA_CENTER))],
        [Paragraph(f'<b>{_v(report.reporter_name).upper()}</b>', ParagraphStyle('SN', parent=s_label, alignment=TA_CENTER)),
         '',
         Paragraph(f'<b>{verifier_name.upper()}</b>', ParagraphStyle('SN', parent=s_label, alignment=TA_CENTER))],
        [Paragraph('Reporter / Complainant', ParagraphStyle('SR', parent=s_value_sm, alignment=TA_CENTER, textColor=colors.HexColor('#666666'))),
         '',
         Paragraph('Approving Officer', ParagraphStyle('SR', parent=s_value_sm, alignment=TA_CENTER, textColor=colors.HexColor('#666666')))],
    ]
    sig_tbl = Table(sig_data, colWidths=[W * 0.4, W * 0.2, W * 0.4])
    sig_tbl.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]))
    elements.append(sig_tbl)
    elements.append(Spacer(1, 16))

    # ==================== FOOTER ====================
    elements.append(Paragraph(
        f'Generated from AGNES Hotspot Detection System on {datetime.now().strftime("%B %d, %Y at %I:%M %p")}',
        s_footer,
    ))
    elements.append(Paragraph(
        'This document is a system-generated copy of an approved accident report.',
        s_footer,
    ))

    # ---------- build & return ----------
    doc.build(elements)
    buf.seek(0)

    response = HttpResponse(buf.read(), content_type='application/pdf')
    filename = f'Accident_Report_AR-{report.pk:05d}.pdf'
    # Inline for browser preview / print, attachment for download
    disposition = request.GET.get('dl', '0')
    if disposition == '1':
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
    else:
        response['Content-Disposition'] = f'inline; filename="{filename}"'

    return response


# =============================================================================
# NOTIFICATIONS PAGE
# =============================================================================

@pnp_login_required
def notifications_page(request):
    """Dedicated page to view all notifications"""
    from django.core.paginator import Paginator
    from datetime import timedelta

    # Auto-cleanup: delete read notifications older than 30 days,
    # unread older than 90 days
    now = timezone.now()
    Notification.objects.filter(
        recipient=request.user, is_read=True,
        created_at__lt=now - timedelta(days=30)
    ).delete()
    Notification.objects.filter(
        recipient=request.user, is_read=False,
        created_at__lt=now - timedelta(days=90)
    ).delete()

    filter_type = request.GET.get('type', 'all')
    filter_read = request.GET.get('read', 'all')

    notifications = Notification.objects.filter(recipient=request.user)

    if filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    if filter_read == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_read == 'read':
        notifications = notifications.filter(is_read=True)

    notifications = notifications.select_related('related_report').order_by('-created_at')

    unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()

    paginator = Paginator(notifications, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'filter_type': filter_type,
        'filter_read': filter_read,
        'unread_count': unread_count,
        'total_count': Notification.objects.filter(recipient=request.user).count(),
        'type_choices': Notification.TYPE_CHOICES,
    }
    return render(request, 'notifications/notifications.html', context)


# =============================================================================
# NOTIFICATION API ENDPOINTS
# =============================================================================

@ensure_csrf_cookie
@pnp_login_required
def get_notifications(request):
    """API endpoint to get notifications for the current user"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]

    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()

    # Include pending report counts
    pending_count = 0
    pending_count_total = AccidentReport.objects.filter(status='pending').count()
    if can_approve_reports(request.user):
        pending_queryset = AccidentReport.objects.filter(status='pending')
        pending_count = get_reports_for_jurisdiction(request.user, pending_queryset).count()

    # Count new accidents since last clustering (for roles that can run clustering)
    unclustered_count = 0
    if hasattr(request.user, 'profile') and request.user.profile.role in ('super_admin', 'regional_director', 'data_encoder'):
        from .models import ClusteringJob
        last_job = ClusteringJob.objects.filter(status='completed').order_by('-completed_at').first()
        if last_job and last_job.completed_at:
            unclustered_count = Accident.objects.filter(created_at__gt=last_job.completed_at).count()
        else:
            unclustered_count = Accident.objects.count()

    def get_notification_url(n):
        """Always use smart redirect for report-related notifications"""
        if n.related_report_id and n.notification_type in ('report_submitted', 'report_approved', 'report_rejected', 'report_cancelled'):
            return f'/manage/report/{n.related_report_id}/go/'
        return n.url

    data = {
        'unread_count': unread_count,
        'pending_count': pending_count,
        'pending_count_total': pending_count_total,
        'unclustered_count': unclustered_count,
        'notifications': [
            {
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'url': get_notification_url(n),
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
                'time_ago': _time_ago(n.created_at),
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@pnp_login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    notification = get_object_or_404(
        Notification, pk=notification_id, recipient=request.user
    )
    notification.is_read = True
    notification.save()
    return JsonResponse({'success': True})


@pnp_login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read for current user"""
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'success': True})


@pnp_login_required
def report_notification_redirect(request, pk):
    """Redirect to the correct page based on report's current status"""
    report = get_object_or_404(AccidentReport, pk=pk)

    # If user is an admin role, go to manage reports with the correct tab + highlight
    if can_approve_reports(request.user):
        status_tab = report.status if report.status in ('pending', 'verified', 'rejected') else 'all'
        return redirect(f'/manage/pending-reports/?status={status_tab}&highlight={pk}')

    # For regular users (reporter), go to my reports with correct tab + highlight
    status_tab = report.status if report.status in ('pending', 'verified', 'rejected') else 'all'
    return redirect(f'/my-reports/?status={status_tab}&highlight={pk}')


def _time_ago(dt):
    """Helper to return human-readable time ago string"""
    now = timezone.now()
    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return 'Just now'
    elif seconds < 3600:
        minutes = int(seconds // 60)
        return f'{minutes}m ago'
    elif seconds < 86400:
        hours = int(seconds // 3600)
        return f'{hours}h ago'
    elif seconds < 604800:
        days = int(seconds // 86400)
        return f'{days}d ago'
    else:
        return dt.strftime('%b %d')