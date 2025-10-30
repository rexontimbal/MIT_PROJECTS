# hotspot_detection/settings.py

import os
from pathlib import Path
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-this-in-production-12345')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    # 'leaflet',  # REMOVE THIS LINE
    
    # Local apps
    'accidents',
    'clustering',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hotspot_detection.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'hotspot_detection.wsgi.application'

# ==============================================================================
# DATABASE CONFIGURATION - PostgreSQL 14.x
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'accident_hotspot_db',
        'USER': 'postgres',
        'PASSWORD': 'irex@9911',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Use SQLite for testing
import sys
if 'test' in sys.argv or 'test_coverage' in sys.argv:
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }

# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Manila'  # Philippine timezone

USE_I18N = True

USE_L10N = True

USE_TZ = True

# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================================================

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Simplified static file serving for development
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ==============================================================================
# MEDIA FILES (User Uploads)
# ==============================================================================

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ==============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

# Session settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# ==============================================================================
# SESSION CONFIGURATION
# ==============================================================================

SESSION_COOKIE_AGE = 86400  # 24 hours in seconds
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG  # Use secure cookies in production

# ==============================================================================
# CACHE CONFIGURATION
# ==============================================================================

# Default: File-based caching (no Redis required for development)
# For production, switch to Redis backend (see Redis configuration below)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'cache',
        'TIMEOUT': 300,  # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

# Redis cache configuration (commented out - will be used with Celery)
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': 'redis://127.0.0.1:6379/1',
#         'OPTIONS': {
#             'CLIENT_CLASS': 'django_redis.client.DefaultClient',
#         },
#         'KEY_PREFIX': 'hotspot',
#         'TIMEOUT': 300,  # 5 minutes default
#     }
# }

# Cache keys for different data types
CACHE_TTL = {
    'dashboard': 60 * 5,        # 5 minutes
    'statistics': 60 * 15,      # 15 minutes
    'clusters': 60 * 10,        # 10 minutes
    'accidents_list': 60 * 5,   # 5 minutes
    'map_data': 60 * 30,        # 30 minutes
}

# ==============================================================================
# DJANGO REST FRAMEWORK
# ==============================================================================

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
}

# ==============================================================================
# CORS SETTINGS (for API access from frontend)
# ==============================================================================

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==============================================================================
# LEAFLET CONFIGURATION (GIS Mapping)
# ==============================================================================

# LEAFLET_CONFIG = {
#     'DEFAULT_CENTER': (9.0, 125.5),  # Caraga Region center coordinates
#     'DEFAULT_ZOOM': 9,
#     'MIN_ZOOM': 7,
#     'MAX_ZOOM': 18,
#     'DEFAULT_PRECISION': 6,
#     'SCALE': 'both',
#     'ATTRIBUTION_PREFIX': 'AGNES Hotspot Detection System',
#     'TILES': [
#         ('OpenStreetMap', 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
#             'attribution': '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
#             'maxZoom': 18,
#         }),
#         ('Satellite', 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
#             'attribution': 'Tiles &copy; Esri',
#             'maxZoom': 18,
#         }),
#     ],
# }

# ==============================================================================
# AGNES CLUSTERING CONFIGURATION
# ==============================================================================

CLUSTERING_CONFIG = {
    # Default parameters for AGNES algorithm
    'DEFAULT_LINKAGE': 'complete',  # Options: 'complete', 'single', 'average'
    'DEFAULT_DISTANCE_THRESHOLD': 0.05,  # ~5km in decimal degrees
    'MIN_CLUSTER_SIZE': 3,  # Minimum accidents to form a hotspot
    
    # Severity scoring weights
    'SEVERITY_WEIGHTS': {
        'killed': 10,      # Each fatality = 10 points
        'injured': 5,      # Each injury = 5 points
        'property_damage': 1,  # Property damage only = 1 point
    },
    
    # Distance calculation method
    'DISTANCE_METRIC': 'euclidean',  # Options: 'euclidean', 'haversine'
    
    # Auto-clustering settings
    'AUTO_RUN_ENABLED': False,  # Set to True to auto-run clustering
    'AUTO_RUN_SCHEDULE': 'daily',  # Options: 'daily', 'weekly', 'monthly'
}

# ==============================================================================
# CELERY CONFIGURATION (Async Task Queue)
# ==============================================================================

# Celery broker URL (Redis)
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')

# Celery result backend
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')

# Celery task settings
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Manila'  # Philippines timezone
CELERY_ENABLE_UTC = False

# Task execution settings
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes max
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit
CELERY_WORKER_MAX_TASKS_PER_CHILD = 50  # Restart worker after 50 tasks

# Result backend settings
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 3600  # Results expire after 1 hour

# Task routing
CELERY_TASK_ROUTES = {
    'accidents.tasks.run_clustering_task': {'queue': 'clustering'},
    'accidents.tasks.export_*': {'queue': 'exports'},
    'accidents.tasks.generate_*': {'queue': 'reports'},
}

# Beat schedule (periodic tasks configured in celery.py)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ==============================================================================
# FILE UPLOAD SETTINGS
# ==============================================================================

# Maximum upload size (10MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Allowed image file extensions
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif']

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'accidents': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'clustering': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# ==============================================================================
# EMAIL CONFIGURATION (Optional - for notifications)
# ==============================================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@pnp-caraga.gov.ph')

# ==============================================================================
# SECURITY SETTINGS FOR PRODUCTION
# ==============================================================================

if not DEBUG:
    # HTTPS settings
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # HSTS settings
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# ==============================================================================
# CUSTOM SETTINGS FOR THE PROJECT
# ==============================================================================

# Caraga Region bounds (for validation)
CARAGA_REGION_BOUNDS = {
    'min_latitude': 7.5,
    'max_latitude': 10.5,
    'min_longitude': 124.5,
    'max_longitude': 127.0,
}

# Provinces in Caraga Region
CARAGA_PROVINCES = [
    'AGUSAN DEL NORTE',
    'AGUSAN DEL SUR',
    'SURIGAO DEL NORTE',
    'SURIGAO DEL SUR',
    'DINAGAT ISLANDS',
]

# Report status choices
REPORT_STATUSES = [
    ('pending', 'Pending Verification'),
    ('verified', 'Verified'),
    ('investigating', 'Under Investigation'),
    ('resolved', 'Resolved'),
    ('rejected', 'Rejected'),
]

# Pagination settings
ITEMS_PER_PAGE = 25

# Map settings
MAP_DEFAULT_CENTER = [9.0, 125.5]  # Caraga Region center
MAP_DEFAULT_ZOOM = 9

# ==============================================================================
# MESSAGES FRAMEWORK
# ==============================================================================

from django.contrib.messages import constants as message_constants

MESSAGE_TAGS = {
    message_constants.DEBUG: 'debug',
    message_constants.INFO: 'info',
    message_constants.SUCCESS: 'success',
    message_constants.WARNING: 'warning',
    message_constants.ERROR: 'error',
}