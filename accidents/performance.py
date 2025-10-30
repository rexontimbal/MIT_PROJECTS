"""
Performance Optimization Utilities
Provides caching decorators and query optimization helpers
"""

from functools import wraps
from django.core.cache import cache
from django.conf import settings
import hashlib
import json


def cache_query_result(cache_key_prefix, timeout=None):
    """
    Decorator to cache query results

    Usage:
        @cache_query_result('accidents_by_province', timeout=300)
        def get_accidents_by_province(province):
            return Accident.objects.filter(province=province)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [cache_key_prefix]
            if args:
                key_parts.extend([str(arg) for arg in args])
            if kwargs:
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])

            cache_key = '_'.join(key_parts)
            # Hash long keys
            if len(cache_key) > 200:
                cache_key = hashlib.md5(cache_key.encode()).hexdigest()

            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_timeout = timeout or settings.CACHES['default']['TIMEOUT']
            cache.set(cache_key, result, cache_timeout)

            return result
        return wrapper
    return decorator


def invalidate_cache(cache_key_pattern):
    """
    Invalidate cache entries matching a pattern

    Usage:
        invalidate_cache('accidents_*')
    """
    # Note: This is a simple implementation
    # For production, use Redis with pattern matching
    if hasattr(cache, 'delete_pattern'):
        cache.delete_pattern(cache_key_pattern)
    else:
        # For file-based cache, just delete specific keys
        cache.delete(cache_key_pattern)


def bulk_cache_set(data_dict, timeout=None):
    """
    Set multiple cache entries at once

    Usage:
        bulk_cache_set({
            'total_accidents': 1000,
            'total_hotspots': 50,
            'recent_increase': 5.2
        }, timeout=300)
    """
    cache_timeout = timeout or settings.CACHES['default']['TIMEOUT']
    cache.set_many(data_dict, cache_timeout)


def get_or_set_cache(cache_key, callable_func, timeout=None):
    """
    Get value from cache or execute function and cache result

    Usage:
        result = get_or_set_cache(
            'expensive_query',
            lambda: Accident.objects.all().count(),
            timeout=600
        )
    """
    result = cache.get(cache_key)
    if result is not None:
        return result

    result = callable_func()
    cache_timeout = timeout or settings.CACHES['default']['TIMEOUT']
    cache.set(cache_key, result, cache_timeout)

    return result


class QueryOptimizer:
    """
    Helper class for query optimization
    """

    @staticmethod
    def optimize_accident_queryset(queryset, for_list=True):
        """
        Optimize accident queryset with selective field loading

        Args:
            queryset: Base queryset
            for_list: If True, load only fields needed for list views

        Returns:
            Optimized queryset
        """
        if for_list:
            return queryset.only(
                'id', 'latitude', 'longitude', 'date_committed',
                'incident_type', 'victim_count', 'province', 'municipal',
                'is_hotspot', 'victim_killed', 'victim_injured'
            ).select_related()
        return queryset.select_related()

    @staticmethod
    def optimize_cluster_queryset(queryset, for_list=True):
        """
        Optimize cluster queryset with selective field loading

        Args:
            queryset: Base queryset
            for_list: If True, load only fields needed for list views

        Returns:
            Optimized queryset
        """
        if for_list:
            return queryset.only(
                'cluster_id', 'center_latitude', 'center_longitude',
                'accident_count', 'severity_score', 'primary_location',
                'total_casualties'
            )
        return queryset

    @staticmethod
    def paginate_queryset(queryset, page=1, page_size=50):
        """
        Manually paginate a queryset

        Args:
            queryset: Queryset to paginate
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (items, total_count, has_next, has_previous)
        """
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        items = list(queryset[start:end])

        has_next = end < total_count
        has_previous = page > 1

        return items, total_count, has_next, has_previous


def cache_page_conditional(timeout, condition_func):
    """
    Cache page only if condition is met

    Usage:
        @cache_page_conditional(300, lambda request: not request.user.is_staff)
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Check condition
            if condition_func(request):
                # Generate cache key
                cache_key = f'view_{request.path}_{request.GET.urlencode()}'
                cached_response = cache.get(cache_key)

                if cached_response is not None:
                    return cached_response

                response = view_func(request, *args, **kwargs)
                cache.set(cache_key, response, timeout)
                return response

            # Don't cache if condition not met
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def warm_cache():
    """
    Pre-warm frequently accessed cache entries
    Call this after clustering or data updates
    """
    from .models import Accident, AccidentCluster

    # Cache statistics
    stats_data = {
        'total_accidents': Accident.objects.count(),
        'total_hotspots': AccidentCluster.objects.count(),
        'fatal_accidents': Accident.objects.filter(victim_killed=True).count(),
    }
    bulk_cache_set(stats_data, timeout=settings.CACHE_TTL['statistics'])

    # Cache top hotspots
    top_hotspots = list(
        AccidentCluster.objects.order_by('-severity_score')[:10]
        .values('cluster_id', 'primary_location', 'accident_count', 'severity_score')
    )
    cache.set('top_hotspots', top_hotspots, settings.CACHE_TTL['clusters'])


def clear_all_cache():
    """
    Clear all cache entries
    Use after major data updates or clustering
    """
    cache.clear()


# Performance monitoring decorator
def monitor_query_performance(func):
    """
    Decorator to log query performance

    Usage:
        @monitor_query_performance
        def expensive_query():
            return Accident.objects.all()
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.db import connection
        from django.db import reset_queries
        import time

        reset_queries()
        start_time = time.time()

        result = func(*args, **kwargs)

        end_time = time.time()
        query_count = len(connection.queries)
        duration = end_time - start_time

        # Log performance metrics
        print(f"Function: {func.__name__}")
        print(f"Queries: {query_count}")
        print(f"Duration: {duration:.3f}s")

        if settings.DEBUG and query_count > 10:
            print(f"WARNING: {func.__name__} executed {query_count} queries")

        return result
    return wrapper
