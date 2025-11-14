# Error Monitoring and Logging Guide

Comprehensive guide for error monitoring, logging, and debugging in the PNP Caraga Accident Hotspot Detection System.

## Table of Contents
1. [Logging Configuration](#logging-configuration)
2. [Error Tracking with Sentry](#error-tracking-with-sentry)
3. [Custom Error Handlers](#custom-error-handlers)
4. [Monitoring Dashboard](#monitoring-dashboard)
5. [Alert Configuration](#alert-configuration)

---

## Logging Configuration

### Current Logging Setup

The system uses Python's built-in logging with Django integration:

```python
# hotspot_detection/settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'error.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'maxBytes': 10485760,  # 10 MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        }
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file', 'mail_admins'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accidents': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'clustering': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file', 'error_file'],
        'level': 'INFO',
    }
}
```

### Usage in Code

```python
import logging

logger = logging.getLogger(__name__)

# Different log levels
logger.debug('Detailed information for debugging')
logger.info('General information')
logger.warning('Warning message')
logger.error('Error occurred')
logger.critical('Critical error')

# With context
logger.info('User %s accessed dashboard', user.username)

# With exception
try:
    dangerous_operation()
except Exception as e:
    logger.exception('Failed to perform operation: %s', e)
```

---

## Error Tracking with Sentry

### Setup Sentry

1. **Create Sentry account**:
   - Visit https://sentry.io/
   - Create free account (includes 5,000 errors/month)
   - Create new project for Django

2. **Install Sentry SDK**:
```bash
pip install sentry-sdk
```

Add to `requirements.txt`:
```
sentry-sdk==1.40.0
```

3. **Configure Sentry** in `settings.py`:

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

# Sentry Configuration
SENTRY_DSN = config('SENTRY_DSN', default='')

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        # Performance monitoring
        traces_sample_rate=0.1,  # 10% of transactions

        # Error sampling
        sample_rate=1.0,

        # Environment
        environment=config('ENVIRONMENT', default='production'),

        # Release tracking
        release=config('APP_VERSION', default='1.0.0'),

        # Send PII (Personally Identifiable Information)
        send_default_pii=False,  # Set False for privacy

        # Before send hook
        before_send=before_send_sentry,
    )

def before_send_sentry(event, hint):
    """Filter or modify events before sending to Sentry"""

    # Don't send 404 errors
    if event.get('logger') == 'django.request' and \
       event.get('level') == 'error':
        if '404' in str(hint.get('exc_info', '')):
            return None

    # Add custom context
    event['tags'] = event.get('tags', {})
    event['tags']['server'] = 'pnp-caraga-01'

    return event
```

4. **Add to `.env`**:
```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
ENVIRONMENT=production
APP_VERSION=1.0.0
```

### Sentry Usage

#### Capture exceptions manually:
```python
from sentry_sdk import capture_exception, capture_message

try:
    process_data()
except Exception as e:
    capture_exception(e)
    logger.error('Data processing failed: %s', e)
```

#### Add context:
```python
from sentry_sdk import configure_scope

with configure_scope() as scope:
    scope.user = {'id': user.id, 'username': user.username}
    scope.set_tag('feature', 'clustering')
    scope.set_extra('cluster_count', len(clusters))

    # Your code here
    perform_clustering()
```

#### Capture messages:
```python
from sentry_sdk import capture_message

capture_message('High memory usage detected', level='warning')
```

### Sentry Best Practices

1. **Group related errors** using fingerprints:
```python
from sentry_sdk import configure_scope

with configure_scope() as scope:
    scope.fingerprint = ['clustering', 'invalid-coordinates']
```

2. **Add breadcrumbs** for debugging:
```python
from sentry_sdk import add_breadcrumb

add_breadcrumb(
    category='clustering',
    message='Started AGNES algorithm',
    level='info',
)
```

3. **Performance monitoring**:
```python
from sentry_sdk import start_transaction

with start_transaction(op='task', name='cluster_accidents'):
    # Your code
    run_clustering()
```

---

## Custom Error Handlers

### Create Error View Handlers

```python
# accidents/error_handlers.py

from django.shortcuts import render
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

def handler404(request, exception):
    """Custom 404 error handler"""
    logger.warning(
        '404 Error: %s requested by %s',
        request.path,
        request.user if request.user.is_authenticated else 'Anonymous'
    )

    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Not Found',
            'status': 404,
            'path': request.path
        }, status=404)

    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """Custom 500 error handler"""
    logger.error(
        '500 Error on %s by %s',
        request.path,
        request.user if request.user.is_authenticated else 'Anonymous'
    )

    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Internal Server Error',
            'status': 500,
            'message': 'An unexpected error occurred. Please try again later.'
        }, status=500)

    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """Custom 403 error handler"""
    logger.warning(
        '403 Forbidden: %s attempted by %s',
        request.path,
        request.user
    )

    if request.path.startswith('/api/'):
        return JsonResponse({
            'error': 'Forbidden',
            'status': 403,
            'message': 'You do not have permission to access this resource.'
        }, status=403)

    return render(request, 'errors/403.html', status=403)
```

### Register Handlers in `urls.py`:
```python
# hotspot_detection/urls.py

handler404 = 'accidents.error_handlers.handler404'
handler500 = 'accidents.error_handlers.handler500'
handler403 = 'accidents.error_handlers.handler403'
```

---

## Monitoring Dashboard

### Health Check Endpoint

```python
# accidents/views.py

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import redis

def health_check(request):
    """System health check endpoint"""
    health = {
        'status': 'healthy',
        'checks': {}
    }

    # Database check
    try:
        connection.ensure_connection()
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'

    # Cache check
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = 'ok'
        else:
            health['checks']['cache'] = 'error'
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['cache'] = f'error: {str(e)}'
        health['status'] = 'degraded'

    # Celery check
    try:
        from celery import current_app
        stats = current_app.control.inspect().stats()
        if stats:
            health['checks']['celery'] = 'ok'
        else:
            health['checks']['celery'] = 'no workers'
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['celery'] = f'error: {str(e)}'
        health['status'] = 'degraded'

    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)
```

### System Status Page

```python
# accidents/views.py

@staff_member_required
def system_status(request):
    """System status dashboard (admin only)"""
    from django.db import connection
    import psutil
    import os

    # Database stats
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM accidents")
        total_accidents = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM accident_clusters")
        total_clusters = cursor.fetchone()[0]

    # System stats
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # Cache stats
    from django.core.cache import cache
    cache_stats = cache._cache.get_stats() if hasattr(cache, '_cache') else {}

    context = {
        'database': {
            'accidents': total_accidents,
            'clusters': total_clusters,
        },
        'system': {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'disk_percent': disk.percent,
        },
        'cache': cache_stats,
    }

    return render(request, 'admin/system_status.html', context)
```

---

## Alert Configuration

### Email Alerts for Critical Errors

Already configured in `settings.py`:
```python
# Email admins on errors
ADMINS = [
    ('Admin Name', 'admin@pnp-caraga.gov.ph'),
]

# Email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@pnp-caraga.gov.ph')
```

### Slack Notifications

```python
# accidents/notifications.py

import requests
import logging

logger = logging.getLogger(__name__)

def send_slack_alert(message, level='info'):
    """Send alert to Slack channel"""
    webhook_url = config('SLACK_WEBHOOK_URL', default='')

    if not webhook_url:
        return

    color = {
        'info': '#36a64f',
        'warning': '#ff9900',
        'error': '#ff0000',
        'critical': '#9b0000',
    }.get(level, '#cccccc')

    payload = {
        'attachments': [{
            'color': color,
            'title': f'PNP Hotspot System Alert ({level.upper()})',
            'text': message,
            'footer': 'PNP Caraga Monitoring',
            'ts': int(time.time())
        }]
    }

    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        response.raise_for_status()
    except Exception as e:
        logger.error('Failed to send Slack alert: %s', e)

# Usage
def clustering_failed_alert(error):
    send_slack_alert(
        f'❌ Clustering job failed: {error}',
        level='error'
    )
```

### Custom Alert Thresholds

```python
# accidents/monitoring.py

from django.core.mail import mail_admins

def check_system_health():
    """Check system health and send alerts"""

    # Check accident report backlog
    pending_reports = AccidentReport.objects.filter(status='pending').count()

    if pending_reports > 50:
        mail_admins(
            subject='High Pending Report Count',
            message=f'There are {pending_reports} pending accident reports.'
        )

    # Check clustering job failures
    failed_jobs = ClusteringJob.objects.filter(
        status='failed',
        created_at__gte=timezone.now() - timedelta(days=1)
    ).count()

    if failed_jobs > 3:
        mail_admins(
            subject='Multiple Clustering Failures',
            message=f'{failed_jobs} clustering jobs failed in the last 24 hours.'
        )

    # Check disk space
    import psutil
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        mail_admins(
            subject='Low Disk Space Warning',
            message=f'Disk usage is at {disk.percent}%'
        )
```

---

## Log Analysis

### Useful Commands

```bash
# View recent errors
tail -f logs/error.log

# Count errors by type
grep "ERROR" logs/django.log | cut -d' ' -f5 | sort | uniq -c

# Find slow requests
grep "took" logs/django.log | awk '$NF > 1.0'

# View security warnings
tail -f logs/security.log

# Search for specific user activity
grep "user_id=123" logs/django.log
```

### Log Rotation

System uses `RotatingFileHandler` with:
- Max file size: 10 MB
- Backup count: 5 files
- Total max storage: 50 MB per log type

---

## Production Checklist

- [ ] Sentry configured and tested
- [ ] Email alerts configured
- [ ] Slack webhooks set up (optional)
- [ ] Health check endpoint enabled
- [ ] Log rotation configured
- [ ] Error pages customized
- [ ] DEBUG = False in production
- [ ] ALLOWED_HOSTS configured
- [ ] Monitoring dashboard accessible
- [ ] Alert thresholds defined
- [ ] On-call rotation established

---

## Support

For monitoring setup:
- Sentry documentation: https://docs.sentry.io/platforms/python/guides/django/
- Django logging: https://docs.djangoproject.com/en/5.0/topics/logging/
- Contact: it@pnp-caraga.gov.ph
