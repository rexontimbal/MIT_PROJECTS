# Caching and Performance Optimization Guide

This guide covers caching strategies and performance optimizations for the PNP Caraga Accident Hotspot Detection System.

## Table of Contents
1. [Redis Caching Setup](#redis-caching-setup)
2. [Cache Strategy](#cache-strategy)
3. [Performance Monitoring](#performance-monitoring)
4. [Database Optimization](#database-optimization)
5. [Frontend Optimization](#frontend-optimization)

---

## Redis Caching Setup

### Prerequisites
- Redis server 5.0 or higher
- Python redis client
- django-redis

### Installation

1. **Install Redis Server** (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

2. **Verify Redis is running**:
```bash
redis-cli ping
# Should return: PONG
```

3. **Install Python packages** (already in requirements.txt):
```bash
pip install redis==5.2.0
pip install django-redis==5.4.0
```

### Configuration

#### 1. Update `settings.py` Cache Configuration

Replace the file-based cache with Redis cache:

```python
# hotspot_detection/settings.py

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
                'retry_on_timeout': True,
            },
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
            'IGNORE_EXCEPTIONS': True,  # Fallback to DB if Redis fails
        },
        'KEY_PREFIX': 'pnp_hotspot',
        'TIMEOUT': 300,  # 5 minutes default
        'VERSION': 1,
    },
    # Separate cache for sessions
    'session': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://127.0.0.1:6379/2'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'pnp_session',
        'TIMEOUT': 86400,  # 24 hours
    },
}

# Use Redis for Django sessions
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'session'
```

#### 2. Add to `.env` file:
```bash
# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1
REDIS_SESSION_URL=redis://127.0.0.1:6379/2
```

#### 3. Update Celery Configuration

In `hotspot_detection/celery.py`:
```python
# Use Redis from environment
app.conf.broker_url = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
app.conf.result_backend = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
```

---

## Cache Strategy

### Cache TTL (Time To Live) Settings

```python
# Recommended TTL values by data type
CACHE_TTL = {
    'dashboard': 300,        # 5 minutes - Dashboard statistics
    'statistics': 900,       # 15 minutes - Aggregate statistics
    'clusters': 600,         # 10 minutes - Hotspot clusters
    'accidents_list': 300,   # 5 minutes - Accident lists
    'accident_detail': 1800, # 30 minutes - Individual accident details
    'map_data': 1800,        # 30 minutes - Map markers
    'analytics': 3600,       # 1 hour - Analytics reports
    'reports_pending': 60,   # 1 minute - Pending reports count
}
```

### Caching Patterns

#### 1. View-level Caching
```python
from django.views.decorators.cache import cache_page
from django.core.cache import cache

# Cache entire view for 5 minutes
@cache_page(60 * 5)
def accident_list(request):
    # View logic
    pass
```

#### 2. Template Fragment Caching
```django
{% load cache %}

{% cache 600 sidebar %}
    <!-- Sidebar content that doesn't change often -->
    <div class="sidebar">
        {{ recent_accidents }}
    </div>
{% endcache %}
```

#### 3. Manual Caching
```python
from django.core.cache import cache

def get_accident_statistics():
    cache_key = 'accident_stats_today'
    stats = cache.get(cache_key)

    if stats is None:
        # Calculate statistics
        stats = calculate_statistics()
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)

    return stats
```

#### 4. Query Result Caching
```python
from django.core.cache import cache

def get_hotspots():
    cache_key = 'hotspot_clusters_all'
    hotspots = cache.get(cache_key)

    if hotspots is None:
        hotspots = list(AccidentCluster.objects.all().values())
        cache.set(cache_key, hotspots, 600)  # 10 minutes

    return hotspots
```

### Cache Invalidation

#### Automatic Invalidation
```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

@receiver(post_save, sender=Accident)
@receiver(post_delete, sender=Accident)
def invalidate_accident_cache(sender, instance, **kwargs):
    """Invalidate caches when accidents are modified"""
    cache.delete('accident_stats_today')
    cache.delete('dashboard_data')
    cache.delete_pattern('accident_list_*')
```

#### Manual Invalidation
```python
from django.core.cache import cache

# Clear specific key
cache.delete('dashboard_data')

# Clear by pattern (requires django-redis)
from django_redis import get_redis_connection
redis_conn = get_redis_connection('default')
redis_conn.delete_pattern('accident_*')

# Clear all cache
cache.clear()
```

---

## Performance Monitoring

### 1. Django Debug Toolbar (Development)

Install and configure:
```bash
pip install django-debug-toolbar
```

In `settings.py`:
```python
if DEBUG:
    INSTALLED_APPS += ['debug_toolbar']
    MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = ['127.0.0.1']
```

### 2. Query Count Monitoring

Add middleware to track query counts:
```python
# accidents/performance.py

class QueryCountDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.db import connection
        from django.db import reset_queries

        reset_queries()

        response = self.get_response(request)

        if settings.DEBUG:
            queries = connection.queries
            print(f'Total Queries: {len(queries)}')
            if len(queries) > 50:
                print('⚠️  WARNING: High query count!')

        return response
```

### 3. Response Time Logging

```python
import time
import logging

logger = logging.getLogger(__name__)

class ResponseTimeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time
        if duration > 1.0:  # Slow request
            logger.warning(
                f'Slow request: {request.path} took {duration:.2f}s'
            )

        response['X-Response-Time'] = f'{duration:.3f}s'
        return response
```

---

## Database Optimization

### 1. Index Coverage

Current indexes (already implemented):
```python
class Meta:
    indexes = [
        models.Index(fields=['latitude', 'longitude']),  # Spatial queries
        models.Index(fields=['date_committed']),         # Date filtering
        models.Index(fields=['province', 'municipal']),  # Location filtering
        models.Index(fields=['cluster_id']),             # Hotspot queries
        models.Index(fields=['is_hotspot']),             # Hotspot filtering
        models.Index(fields=['year']),                   # Year filtering
    ]
```

### 2. Query Optimization

#### Use select_related() for foreign keys:
```python
# BAD: N+1 queries
accidents = Accident.objects.all()
for accident in accidents:
    print(accident.created_by.username)  # Separate query each time

# GOOD: Single JOIN query
accidents = Accident.objects.select_related('created_by').all()
for accident in accidents:
    print(accident.created_by.username)  # No additional query
```

#### Use prefetch_related() for reverse relations:
```python
# BAD: N+1 queries
clusters = AccidentCluster.objects.all()
for cluster in clusters:
    print(cluster.accident_set.count())  # Separate query each time

# GOOD: Two queries total
clusters = AccidentCluster.objects.prefetch_related('accident_set').all()
for cluster in clusters:
    print(cluster.accident_set.count())  # No additional query
```

#### Use only() to limit fields:
```python
# BAD: Loads all fields
accidents = Accident.objects.all()

# GOOD: Only loads needed fields
accidents = Accident.objects.only('id', 'province', 'date_committed')
```

#### Use defer() to exclude heavy fields:
```python
# Exclude text fields if not needed
accidents = Accident.objects.defer('narrative', 'victim_details', 'suspect_details')
```

#### Use aggregate() for statistics:
```python
from django.db.models import Count, Sum, Avg

# Single query with aggregation
stats = Accident.objects.aggregate(
    total=Count('id'),
    total_casualties=Sum('victim_count'),
    avg_casualties=Avg('victim_count')
)
```

### 3. Connection Pooling

For production, use connection pooling:
```python
# settings.py

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000'  # 30 seconds
        }
    }
}
```

---

## Frontend Optimization

### 1. Static File Compression

Already configured with WhiteNoise:
```python
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

### 2. Browser Caching

Add cache headers:
```python
# For static files (already handled by WhiteNoise)

# For dynamic content
from django.views.decorators.cache import cache_control

@cache_control(max_age=3600, public=True)
def public_view(request):
    # Cached by browser for 1 hour
    pass
```

### 3. Lazy Loading Images

In templates:
```html
<img src="{{ accident.photo.url }}"
     loading="lazy"
     alt="Accident photo">
```

### 4. Minimize JavaScript/CSS

Use Django Compressor:
```bash
pip install django-compressor
```

```python
INSTALLED_APPS += ['compressor']

COMPRESS_ENABLED = not DEBUG
COMPRESS_OFFLINE = True
```

---

## Redis Monitoring

### Check Redis Status
```bash
# Connect to Redis CLI
redis-cli

# Check memory usage
INFO memory

# Check key count
DBSIZE

# Monitor commands in real-time
MONITOR

# Check slow queries
SLOWLOG GET 10
```

### Redis Performance Tuning

In `/etc/redis/redis.conf`:
```
# Maximum memory
maxmemory 256mb

# Eviction policy
maxmemory-policy allkeys-lru

# Persistence (optional for cache)
save ""  # Disable RDB persistence for cache-only

# Performance
tcp-backlog 511
timeout 300
tcp-keepalive 300
```

---

## Performance Checklist

- [ ] Redis caching enabled
- [ ] Database indexes optimized
- [ ] Query optimization (select_related, prefetch_related)
- [ ] Static files compressed
- [ ] Browser caching configured
- [ ] Celery for async tasks
- [ ] Connection pooling enabled
- [ ] Slow query logging enabled
- [ ] Performance monitoring in place
- [ ] Cache invalidation strategy implemented

---

## Benchmarking

### Run load tests:
```bash
# Install locust
pip install locust

# Create locustfile.py
# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Monitor performance:
```bash
# Django command
python manage.py runserver --noreload

# Monitor queries
python manage.py shell
>>> from django.db import connection
>>> connection.queries
```

---

## Troubleshooting

### Redis Connection Issues
```bash
# Check Redis is running
sudo systemctl status redis-server

# Check network connectivity
redis-cli ping

# Check logs
sudo tail -f /var/log/redis/redis-server.log
```

### High Memory Usage
```python
# Clear old cache entries
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()
```

### Slow Queries
```python
# Enable query logging in settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
```

---

## Support

For performance issues:
- Check logs: `logs/django.log`
- Monitor Redis: `redis-cli MONITOR`
- Profile queries: Django Debug Toolbar
- Contact: it@pnp-caraga.gov.ph
