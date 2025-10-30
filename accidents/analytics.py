"""
Advanced Analytics Module for Road Accident Hotspot Detection
Provides realistic, data-driven analytical insights aligned with actual data
"""

from django.db.models import Count, Q, Avg, Sum, Max, Min, StdDev, F
from django.db.models.functions import ExtractHour, ExtractWeekDay, TruncMonth
from datetime import datetime, timedelta
import numpy as np
from scipy import stats
from collections import defaultdict
import json


class AccidentAnalytics:
    """
    Advanced analytics engine for accident data analysis
    """

    def __init__(self, queryset):
        """
        Initialize with accident queryset

        Args:
            queryset: Accident queryset to analyze
        """
        self.queryset = queryset
        self.total_accidents = queryset.count()

    # ========================================================================
    # SPATIAL ANALYSIS
    # ========================================================================

    def hotspot_effectiveness_analysis(self):
        """
        Analyze effectiveness of hotspot detection

        Returns:
            dict: Hotspot effectiveness metrics
        """
        hotspot_accidents = self.queryset.filter(is_hotspot=True).count()
        non_hotspot_accidents = self.queryset.filter(is_hotspot=False).count()

        # Calculate concentration ratio
        hotspot_percentage = (hotspot_accidents / self.total_accidents * 100) if self.total_accidents > 0 else 0

        # Severity in hotspots vs non-hotspots
        hotspot_fatal = self.queryset.filter(is_hotspot=True, victim_killed=True).count()
        non_hotspot_fatal = self.queryset.filter(is_hotspot=False, victim_killed=True).count()

        hotspot_fatality_rate = (hotspot_fatal / hotspot_accidents * 100) if hotspot_accidents > 0 else 0
        non_hotspot_fatality_rate = (non_hotspot_fatal / non_hotspot_accidents * 100) if non_hotspot_accidents > 0 else 0

        return {
            'hotspot_accidents': hotspot_accidents,
            'non_hotspot_accidents': non_hotspot_accidents,
            'hotspot_percentage': round(hotspot_percentage, 1),
            'hotspot_concentration_ratio': round(hotspot_percentage / (100 - hotspot_percentage), 2) if hotspot_percentage < 100 else float('inf'),
            'hotspot_fatality_rate': round(hotspot_fatality_rate, 1),
            'non_hotspot_fatality_rate': round(non_hotspot_fatality_rate, 1),
            'severity_differential': round(hotspot_fatality_rate - non_hotspot_fatality_rate, 1),
            'high_risk_areas_identified': True if hotspot_percentage > 20 else False
        }

    def spatial_concentration_index(self):
        """
        Calculate spatial concentration using Gini coefficient approach

        Returns:
            dict: Spatial concentration metrics
        """
        # Group by municipality
        municipal_counts = self.queryset.values('municipal').annotate(
            count=Count('id')
        ).order_by('count')

        if not municipal_counts:
            return {'gini_coefficient': 0, 'concentration_level': 'LOW'}

        counts = [m['count'] for m in municipal_counts]

        # Calculate Gini coefficient
        n = len(counts)
        if n == 0:
            return {'gini_coefficient': 0, 'concentration_level': 'LOW'}

        sorted_counts = sorted(counts)
        cumsum = np.cumsum(sorted_counts)
        total = sum(sorted_counts)

        if total == 0:
            gini = 0
        else:
            gini = (2 * sum((i + 1) * count for i, count in enumerate(sorted_counts))) / (n * total) - (n + 1) / n

        # Interpret concentration level
        if gini >= 0.6:
            level = 'VERY HIGH'
        elif gini >= 0.4:
            level = 'HIGH'
        elif gini >= 0.25:
            level = 'MODERATE'
        else:
            level = 'LOW'

        return {
            'gini_coefficient': round(gini, 3),
            'concentration_level': level,
            'municipalities_analyzed': n,
            'top_10_percentage': round(sum(sorted(counts, reverse=True)[:10]) / total * 100, 1) if total > 0 else 0
        }

    # ========================================================================
    # TEMPORAL PATTERN ANALYSIS
    # ========================================================================

    def rush_hour_analysis(self):
        """
        Analyze accidents during rush hours vs non-rush hours

        Rush hours defined as: 7-9 AM, 5-7 PM on weekdays

        Returns:
            dict: Rush hour analysis metrics
        """
        from django.db.models.functions import ExtractHour, ExtractWeekDay

        # Define rush hour periods
        morning_rush = Q(time_committed__hour__gte=7, time_committed__hour__lt=9)
        evening_rush = Q(time_committed__hour__gte=17, time_committed__hour__lt=19)
        weekday = Q(date_committed__week_day__in=[2, 3, 4, 5, 6])  # Monday-Friday

        rush_hour_accidents = self.queryset.filter(
            weekday,
            morning_rush | evening_rush
        ).count()

        non_rush_accidents = self.total_accidents - rush_hour_accidents

        # Calculate severity during rush hours
        rush_fatal = self.queryset.filter(
            weekday,
            morning_rush | evening_rush,
            victim_killed=True
        ).count()

        rush_fatality_rate = (rush_fatal / rush_hour_accidents * 100) if rush_hour_accidents > 0 else 0
        overall_fatality_rate = (self.queryset.filter(victim_killed=True).count() / self.total_accidents * 100) if self.total_accidents > 0 else 0

        return {
            'rush_hour_accidents': rush_hour_accidents,
            'non_rush_accidents': non_rush_accidents,
            'rush_hour_percentage': round(rush_hour_accidents / self.total_accidents * 100, 1) if self.total_accidents > 0 else 0,
            'rush_hour_fatality_rate': round(rush_fatality_rate, 1),
            'overall_fatality_rate': round(overall_fatality_rate, 1),
            'rush_hour_risk_multiplier': round(rush_fatality_rate / overall_fatality_rate, 2) if overall_fatality_rate > 0 else 1.0,
            'is_rush_hour_high_risk': rush_fatality_rate > overall_fatality_rate
        }

    def weekend_vs_weekday_analysis(self):
        """
        Compare accident patterns between weekends and weekdays

        Returns:
            dict: Weekend vs weekday metrics
        """
        weekday_accidents = self.queryset.filter(
            date_committed__week_day__in=[2, 3, 4, 5, 6]  # Mon-Fri
        )
        weekend_accidents = self.queryset.filter(
            date_committed__week_day__in=[1, 7]  # Sun, Sat
        )

        weekday_count = weekday_accidents.count()
        weekend_count = weekend_accidents.count()

        weekday_fatal = weekday_accidents.filter(victim_killed=True).count()
        weekend_fatal = weekend_accidents.filter(victim_killed=True).count()

        # Normalize by number of days (5 weekdays vs 2 weekend days)
        weekday_daily_avg = weekday_count / 5 if weekday_count > 0 else 0
        weekend_daily_avg = weekend_count / 2 if weekend_count > 0 else 0

        return {
            'weekday_total': weekday_count,
            'weekend_total': weekend_count,
            'weekday_daily_average': round(weekday_daily_avg, 1),
            'weekend_daily_average': round(weekend_daily_avg, 1),
            'weekend_risk_ratio': round(weekend_daily_avg / weekday_daily_avg, 2) if weekday_daily_avg > 0 else 0,
            'weekday_fatality_rate': round(weekday_fatal / weekday_count * 100, 1) if weekday_count > 0 else 0,
            'weekend_fatality_rate': round(weekend_fatal / weekend_count * 100, 1) if weekend_count > 0 else 0,
            'higher_risk_period': 'Weekend' if weekend_daily_avg > weekday_daily_avg else 'Weekday'
        }

    def seasonal_analysis(self):
        """
        Analyze seasonal patterns in accidents

        Returns:
            dict: Seasonal analysis by quarter
        """
        from django.db.models.functions import TruncQuarter

        quarterly_data = self.queryset.annotate(
            quarter=TruncQuarter('date_committed')
        ).values('quarter').annotate(
            total=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True))
        ).order_by('quarter')

        quarters = []
        for q in quarterly_data:
            if q['quarter']:
                quarter_num = (q['quarter'].month - 1) // 3 + 1
                quarters.append({
                    'quarter': f"Q{quarter_num} {q['quarter'].year}",
                    'total': q['total'],
                    'fatal': q['fatal'],
                    'fatality_rate': round(q['fatal'] / q['total'] * 100, 1) if q['total'] > 0 else 0
                })

        # Find highest risk quarter
        if quarters:
            highest_risk = max(quarters, key=lambda x: x['total'])
            lowest_risk = min(quarters, key=lambda x: x['total'])
        else:
            highest_risk = {'quarter': 'N/A', 'total': 0}
            lowest_risk = {'quarter': 'N/A', 'total': 0}

        return {
            'quarterly_breakdown': quarters,
            'highest_risk_quarter': highest_risk['quarter'],
            'highest_risk_count': highest_risk['total'],
            'lowest_risk_quarter': lowest_risk['quarter'],
            'lowest_risk_count': lowest_risk['total'],
            'seasonal_variation': round((highest_risk['total'] - lowest_risk['total']) / lowest_risk['total'] * 100, 1) if lowest_risk['total'] > 0 else 0
        }

    # ========================================================================
    # SEVERITY ANALYSIS
    # ========================================================================

    def severity_index_analysis(self):
        """
        Calculate comprehensive severity index

        Severity Index = (Fatal * 10 + Injury * 5 + Property * 1) / Total

        Returns:
            dict: Severity metrics
        """
        fatal_count = self.queryset.filter(victim_killed=True).count()
        injury_count = self.queryset.filter(victim_injured=True, victim_killed=False).count()
        property_only = self.total_accidents - fatal_count - injury_count

        # Calculate weighted severity index
        severity_score = (fatal_count * 10 + injury_count * 5 + property_only * 1)
        severity_index = severity_score / self.total_accidents if self.total_accidents > 0 else 0

        # Calculate casualty statistics
        total_casualties = self.queryset.aggregate(Sum('victim_count'))['victim_count__sum'] or 0

        return {
            'fatal_accidents': fatal_count,
            'injury_accidents': injury_count,
            'property_only_accidents': property_only,
            'total_casualties': total_casualties,
            'severity_index': round(severity_index, 2),
            'severity_category': self._categorize_severity(severity_index),
            'average_casualties_per_accident': round(total_casualties / self.total_accidents, 2) if self.total_accidents > 0 else 0,
            'fatal_rate': round(fatal_count / self.total_accidents * 100, 1) if self.total_accidents > 0 else 0,
            'injury_rate': round(injury_count / self.total_accidents * 100, 1) if self.total_accidents > 0 else 0
        }

    def _categorize_severity(self, severity_index):
        """Categorize severity index"""
        if severity_index >= 7:
            return 'CRITICAL'
        elif severity_index >= 5:
            return 'HIGH'
        elif severity_index >= 3:
            return 'MODERATE'
        else:
            return 'LOW'

    def high_risk_combinations(self):
        """
        Identify high-risk combinations (time, location, vehicle type)

        Returns:
            dict: High-risk combinations
        """
        # Time-Location combinations
        time_location = self.queryset.annotate(
            hour=ExtractHour('time_committed')
        ).values('hour', 'municipal').annotate(
            count=Count('id'),
            fatal=Count('id', filter=Q(victim_killed=True))
        ).filter(count__gte=3).order_by('-fatal', '-count')[:5]

        high_risk_combos = []
        for combo in time_location:
            if combo['hour'] is not None:
                high_risk_combos.append({
                    'time_slot': f"{combo['hour']:02d}:00-{(combo['hour']+1):02d}:00",
                    'location': combo['municipal'] or 'Unknown',
                    'accidents': combo['count'],
                    'fatal': combo['fatal'],
                    'risk_score': combo['fatal'] * 10 + combo['count']
                })

        return {
            'high_risk_combinations': high_risk_combos,
            'total_combinations_analyzed': time_location.count()
        }

    # ========================================================================
    # PREDICTIVE ANALYTICS
    # ========================================================================

    def trend_analysis_with_confidence(self):
        """
        Perform trend analysis with statistical confidence

        Returns:
            dict: Trend metrics with confidence intervals
        """
        monthly_data = self.queryset.annotate(
            month=TruncMonth('date_committed')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        if len(monthly_data) < 3:
            return {
                'trend': 'INSUFFICIENT_DATA',
                'confidence': 0,
                'prediction': 0
            }

        counts = [m['count'] for m in monthly_data]
        x = np.arange(len(counts))

        # Linear regression
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, counts)

        # Predict next period
        next_x = len(counts)
        prediction = slope * next_x + intercept

        # Calculate confidence interval
        confidence = abs(r_value) * 100

        # Determine trend
        if slope > 1:
            trend = 'INCREASING'
        elif slope < -1:
            trend = 'DECREASING'
        else:
            trend = 'STABLE'

        return {
            'trend': trend,
            'slope': round(slope, 2),
            'r_squared': round(r_value ** 2, 3),
            'p_value': round(p_value, 4),
            'confidence_percentage': round(confidence, 1),
            'prediction_next_month': max(0, int(prediction)),
            'std_error': round(std_err, 2),
            'is_significant': p_value < 0.05
        }

    def anomaly_detection(self):
        """
        Detect anomalous spikes in accident data

        Returns:
            dict: Anomaly detection results
        """
        monthly_data = self.queryset.annotate(
            month=TruncMonth('date_committed')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')

        if len(monthly_data) < 6:
            return {'anomalies_detected': 0, 'anomalies': []}

        counts = [m['count'] for m in monthly_data]
        months = [m['month'] for m in monthly_data]

        # Calculate mean and standard deviation
        mean = np.mean(counts)
        std = np.std(counts)

        # Define anomaly threshold (2 standard deviations)
        threshold = mean + (2 * std)

        # Detect anomalies
        anomalies = []
        for i, count in enumerate(counts):
            if count > threshold:
                anomalies.append({
                    'month': months[i].strftime('%B %Y'),
                    'count': count,
                    'deviation': round((count - mean) / std, 2),
                    'percentage_above_normal': round((count - mean) / mean * 100, 1)
                })

        return {
            'anomalies_detected': len(anomalies),
            'anomalies': anomalies,
            'mean': round(mean, 1),
            'std_dev': round(std, 1),
            'threshold': round(threshold, 1)
        }

    # ========================================================================
    # STATISTICAL TESTS
    # ========================================================================

    def provincial_variance_test(self):
        """
        ANOVA test for significant differences between provinces

        Returns:
            dict: ANOVA test results
        """
        # Group by province and month
        provincial_monthly = {}

        provinces = self.queryset.values_list('province', flat=True).distinct()

        for province in provinces:
            if province:
                monthly_counts = self.queryset.filter(province=province).annotate(
                    month=TruncMonth('date_committed')
                ).values('month').annotate(
                    count=Count('id')
                ).order_by('month')

                provincial_monthly[province] = [m['count'] for m in monthly_counts]

        # Filter provinces with sufficient data
        valid_provinces = {k: v for k, v in provincial_monthly.items() if len(v) >= 3}

        if len(valid_provinces) < 2:
            return {
                'test_performed': False,
                'reason': 'Insufficient provinces or data points'
            }

        # Perform ANOVA
        groups = list(valid_provinces.values())

        try:
            f_statistic, p_value = stats.f_oneway(*groups)

            return {
                'test_performed': True,
                'f_statistic': round(f_statistic, 4),
                'p_value': round(p_value, 4),
                'is_significant': p_value < 0.05,
                'conclusion': 'Significant differences exist between provinces' if p_value < 0.05 else 'No significant differences between provinces',
                'provinces_tested': len(valid_provinces)
            }
        except:
            return {
                'test_performed': False,
                'reason': 'Statistical test could not be performed'
            }

    def correlation_analysis(self):
        """
        Analyze correlations between different factors

        Returns:
            dict: Correlation metrics
        """
        # Time of day vs severity
        hourly_severity = self.queryset.annotate(
            hour=ExtractHour('time_committed')
        ).values('hour').annotate(
            fatal_rate=Count('id', filter=Q(victim_killed=True)) * 100.0 / Count('id')
        ).order_by('hour')

        hours = []
        fatal_rates = []

        for h in hourly_severity:
            if h['hour'] is not None:
                hours.append(h['hour'])
                fatal_rates.append(h['fatal_rate'])

        # Calculate correlation
        if len(hours) >= 3:
            correlation, p_value = stats.pearsonr(hours, fatal_rates)
        else:
            correlation, p_value = 0, 1.0

        return {
            'time_severity_correlation': round(correlation, 3),
            'p_value': round(p_value, 4),
            'is_significant': p_value < 0.05,
            'interpretation': self._interpret_correlation(correlation)
        }

    def _interpret_correlation(self, r):
        """Interpret correlation coefficient"""
        abs_r = abs(r)
        if abs_r >= 0.7:
            strength = 'Strong'
        elif abs_r >= 0.4:
            strength = 'Moderate'
        elif abs_r >= 0.2:
            strength = 'Weak'
        else:
            strength = 'Very Weak'

        direction = 'positive' if r > 0 else 'negative'
        return f"{strength} {direction} correlation"

    # ========================================================================
    # COMPREHENSIVE REPORT
    # ========================================================================

    def generate_comprehensive_report(self):
        """
        Generate comprehensive analytics report

        Returns:
            dict: All analytics combined
        """
        return {
            'spatial_analysis': {
                'hotspot_effectiveness': self.hotspot_effectiveness_analysis(),
                'spatial_concentration': self.spatial_concentration_index()
            },
            'temporal_analysis': {
                'rush_hour': self.rush_hour_analysis(),
                'weekend_vs_weekday': self.weekend_vs_weekday_analysis(),
                'seasonal': self.seasonal_analysis()
            },
            'severity_analysis': {
                'severity_index': self.severity_index_analysis(),
                'high_risk_combinations': self.high_risk_combinations()
            },
            'predictive_analysis': {
                'trend': self.trend_analysis_with_confidence(),
                'anomalies': self.anomaly_detection()
            },
            'statistical_tests': {
                'provincial_variance': self.provincial_variance_test(),
                'correlations': self.correlation_analysis()
            }
        }
