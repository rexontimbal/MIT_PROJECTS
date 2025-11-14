# API Documentation Setup

This document describes how to set up and use the API documentation for the PNP Caraga Accident Hotspot Detection System.

## Overview

The API is documented using **OpenAPI 3.0** specification with **drf-spectacular**. This provides:

- Interactive API documentation (Swagger UI)
- Redoc documentation
- OpenAPI schema (JSON/YAML)
- Auto-generated client code support

## Installation

1. Install drf-spectacular:
```bash
pip install drf-spectacular==0.27.2
```

2. Add to `INSTALLED_APPS` in `settings.py`:
```python
INSTALLED_APPS = [
    # ... other apps
    'drf_spectacular',
    'rest_framework',
]
```

3. Configure REST Framework to use drf-spectacular:
```python
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

4. Add drf-spectacular settings:
```python
SPECTACULAR_SETTINGS = {
    'TITLE': 'PNP Caraga Accident Hotspot Detection API',
    'DESCRIPTION': '''
    RESTful API for the PNP Caraga Region Accident Hotspot Detection System.

    This API provides access to:
    - Accident records and statistics
    - Hotspot clusters (AGNES algorithm results)
    - Accident reports (citizen submissions)
    - Geographic and temporal analytics

    ## Authentication
    API requires authentication using Django session or token authentication.

    ## Rate Limiting
    API requests are limited to prevent abuse.

    ## Data Privacy
    All data is handled in accordance with Philippine Data Privacy Act of 2012 (RA 10173).
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'PNP Caraga IT Division',
        'email': 'it@pnp-caraga.gov.ph',
    },
    'LICENSE': {
        'name': 'Proprietary',
    },
    'TAGS': [
        {'name': 'accidents', 'description': 'Accident records operations'},
        {'name': 'clusters', 'description': 'Hotspot cluster operations'},
        {'name': 'reports', 'description': 'Citizen report operations'},
        {'name': 'analytics', 'description': 'Analytics and statistics'},
    ],
    'COMPONENT_SPLIT_REQUEST': True,
}
```

5. Add URL patterns in `hotspot_detection/urls.py`:
```python
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView
)

urlpatterns = [
    # ... other patterns

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

## Accessing Documentation

After setup, access the documentation at:

- **Swagger UI (Interactive)**: `http://localhost:8000/api/docs/`
- **ReDoc (Clean Reading)**: `http://localhost:8000/api/redoc/`
- **OpenAPI Schema (JSON)**: `http://localhost:8000/api/schema/`

## API Endpoints

### Accidents API
- `GET /api/accidents/` - List all accidents (paginated)
- `GET /api/accidents/{id}/` - Get accident details
- `GET /api/accidents/statistics/` - Get accident statistics

**Filters:**
- `province` - Filter by province
- `municipal` - Filter by municipality
- `year` - Filter by year
- `is_hotspot` - Filter hotspot accidents
- `search` - Search by location or incident type
- `ordering` - Order by field (e.g., `-date_committed`)

**Example:**
```bash
curl -X GET "http://localhost:8000/api/accidents/?province=Agusan+del+Norte&year=2024"
```

### Clusters API
- `GET /api/clusters/` - List all hotspot clusters
- `GET /api/clusters/{id}/` - Get cluster details

**Filters:**
- `ordering` - Order by severity_score, accident_count

**Example:**
```bash
curl -X GET "http://localhost:8000/api/clusters/?ordering=-severity_score"
```

### Reports API
- `GET /api/reports/` - List accident reports
- `POST /api/reports/` - Submit new report
- `GET /api/reports/{id}/` - Get report details
- `PATCH /api/reports/{id}/` - Update report status

**Example:**
```bash
curl -X POST "http://localhost:8000/api/reports/" \
  -H "Content-Type: application/json" \
  -d '{
    "reporter_name": "Juan dela Cruz",
    "reporter_contact": "09171234567",
    "incident_date": "2024-03-15",
    "incident_time": "14:30:00",
    "latitude": "8.9475",
    "longitude": "125.5406",
    "province": "Agusan del Norte",
    "municipal": "Butuan City",
    "barangay": "Libertad",
    "incident_description": "Two vehicles collided at intersection"
  }'
```

### Analytics API
- `GET /api/analytics/temporal/` - Temporal pattern analysis
- `GET /api/analytics/geographic/` - Geographic distribution
- `GET /api/analytics/severity/` - Severity metrics
- `GET /api/analytics/hotspot-effectiveness/` - Hotspot effectiveness

## Response Format

All API responses follow this format:

**List Endpoints (Paginated):**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/accidents/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "province": "Agusan del Norte",
      "municipal": "Butuan City",
      "latitude": "8.9475",
      "longitude": "125.5406",
      "date_committed": "2024-01-15",
      "incident_type": "Vehicular Accident",
      "victim_killed": true,
      "is_hotspot": true
    }
  ]
}
```

**Detail Endpoints:**
```json
{
  "id": 1,
  "province": "Agusan del Norte",
  "municipal": "Butuan City",
  "barangay": "Libertad",
  "latitude": "8.9475",
  "longitude": "125.5406",
  "date_committed": "2024-01-15",
  "time_committed": "14:30:00",
  "incident_type": "Vehicular Accident",
  "victim_killed": true,
  "victim_injured": false,
  "victim_count": 1,
  "cluster_id": 5,
  "is_hotspot": true,
  "created_at": "2024-01-15T14:35:00Z"
}
```

**Error Responses:**
```json
{
  "detail": "Error message here",
  "errors": {
    "field_name": ["Error for this field"]
  }
}
```

## Authentication

### Session Authentication
Use Django session authentication for web browsers:
```python
# Login required
from django.contrib.auth import authenticate, login

user = authenticate(username='username', password='password')
login(request, user)
```

### Token Authentication (Optional)
To add token authentication:

1. Install `djangorestframework-simplejwt`:
```bash
pip install djangorestframework-simplejwt
```

2. Add to settings:
```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

3. Get token:
```bash
curl -X POST "http://localhost:8000/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'
```

4. Use token in requests:
```bash
curl -X GET "http://localhost:8000/api/accidents/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Pagination

All list endpoints are paginated:
- Default page size: 50 items
- Max page size: 1000 items
- Page parameter: `?page=2`
- Page size parameter: `?page_size=100`

## Filtering

Use query parameters for filtering:
```
GET /api/accidents/?province=Agusan+del+Norte&year=2024&is_hotspot=true
```

## Ordering

Use the `ordering` parameter:
```
GET /api/accidents/?ordering=-date_committed
GET /api/clusters/?ordering=-severity_score,accident_count
```

Use `-` prefix for descending order.

## Field Selection (Optional)

To optimize performance, request only needed fields:
```
GET /api/accidents/?fields=id,province,municipal,date_committed
```

## Rate Limiting

To protect the API, implement rate limiting:

1. Install django-ratelimit:
```bash
pip install django-ratelimit
```

2. Apply to views:
```python
from ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h')
def api_view(request):
    # ...
```

## CORS Configuration

CORS is configured in settings.py:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]
```

## Testing API

### Using curl
```bash
# Get accidents
curl -X GET "http://localhost:8000/api/accidents/"

# Get specific accident
curl -X GET "http://localhost:8000/api/accidents/1/"

# Create report
curl -X POST "http://localhost:8000/api/reports/" \
  -H "Content-Type: application/json" \
  -d @report_data.json
```

### Using Python requests
```python
import requests

# Get accidents
response = requests.get('http://localhost:8000/api/accidents/')
accidents = response.json()

# Filter by province
response = requests.get(
    'http://localhost:8000/api/accidents/',
    params={'province': 'Agusan del Norte', 'year': 2024}
)
```

### Using JavaScript fetch
```javascript
// Get accidents
fetch('http://localhost:8000/api/accidents/')
  .then(response => response.json())
  .then(data => console.log(data));

// Post report
fetch('http://localhost:8000/api/reports/', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    reporter_name: 'Juan dela Cruz',
    incident_date: '2024-03-15',
    // ... other fields
  })
})
.then(response => response.json())
.then(data => console.log(data));
```

## API Schema Generation

Generate OpenAPI schema file:
```bash
python manage.py spectacular --color --file schema.yml
```

Generate as JSON:
```bash
python manage.py spectacular --format openapi-json --file schema.json
```

## Client Code Generation

Use the OpenAPI schema to generate client code:

### Python Client
```bash
openapi-generator generate -i schema.yml -g python -o python-client/
```

### JavaScript Client
```bash
openapi-generator generate -i schema.yml -g javascript -o js-client/
```

### TypeScript Client
```bash
openapi-generator generate -i schema.yml -g typescript-fetch -o ts-client/
```

## Best Practices

1. **Always authenticate** - Use proper authentication for all API requests
2. **Handle pagination** - Don't assume all results fit in one page
3. **Use filtering** - Filter server-side rather than client-side when possible
4. **Cache responses** - Cache GET responses when appropriate
5. **Handle errors** - Always check response status and handle errors gracefully
6. **Respect rate limits** - Don't make excessive requests
7. **Use HTTPS** - Always use HTTPS in production
8. **Validate input** - Validate all user input before sending to API

## Troubleshooting

### Documentation not loading
- Check that drf-spectacular is installed
- Verify URL patterns are configured
- Check INSTALLED_APPS includes 'drf_spectacular'

### Authentication errors
- Verify user is logged in
- Check session/token is valid
- Verify permissions for the endpoint

### CORS errors
- Check CORS_ALLOWED_ORIGINS in settings
- Verify request origin matches allowed origins
- Check CORS middleware is enabled

## Support

For API issues or questions:
- Email: it@pnp-caraga.gov.ph
- Internal ticket system: https://helpdesk.pnp-caraga.local

## Change Log

### Version 1.0.0 (2024)
- Initial API release
- Accidents, Clusters, and Reports endpoints
- Analytics endpoints
- OpenAPI documentation
