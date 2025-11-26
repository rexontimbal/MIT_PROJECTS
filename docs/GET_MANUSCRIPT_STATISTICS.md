# HOW TO GET STATISTICS FOR YOUR MANUSCRIPT

## Quick Statistics You Can Add to Chapter 1 and 4

Run these commands in your Django shell to get real numbers for your paper:

```bash
# Open Django shell
python manage.py shell
```

Then run these Python commands:

---

## 1. TOTAL ACCIDENTS IN DATASET

```python
from accidents.models import Accident, AccidentCluster
from django.db.models import Count, Sum, Q

# Total accidents
total = Accident.objects.count()
print(f"Total accidents in database: {total}")

# By year
by_year = Accident.objects.values('year').annotate(count=Count('id')).order_by('year')
for item in by_year:
    print(f"Year {item['year']}: {item['count']} accidents")
```

**Use in manuscript:** "From 2020 to 2024, the system recorded a total of [X] traffic accidents across the Caraga Region."

---

## 2. ACCIDENTS BY PROVINCE

```python
# Province distribution
by_province = Accident.objects.values('province').annotate(
    count=Count('id')
).order_by('-count')

for item in by_province:
    print(f"{item['province']}: {item['count']} accidents")
```

**Use in manuscript:** "[Province name] recorded the highest number of accidents at [X] incidents, followed by [Province 2] with [Y] incidents."

---

## 3. CASUALTY STATISTICS

```python
# Fatal accidents
fatal = Accident.objects.filter(victim_killed=True).count()
injured = Accident.objects.filter(victim_injured=True).count()
no_harm = Accident.objects.filter(victim_unharmed=True).count()

total_casualties = Accident.objects.aggregate(Sum('victim_count'))['victim_count__sum']

print(f"Fatal accidents: {fatal}")
print(f"Injury accidents: {injured}")
print(f"Property damage only: {no_harm}")
print(f"Total casualties: {total_casualties}")

# Percentage
fatal_pct = (fatal / total * 100) if total > 0 else 0
print(f"Fatal accidents: {fatal_pct:.1f}%")
```

**Use in manuscript:** "Fatal accidents accounted for [X]% of total incidents, with [Y] casualties recorded throughout the study period."

---

## 4. HOTSPOT CLUSTERS

```python
# Total clusters
clusters = AccidentCluster.objects.count()
print(f"Total hotspot clusters identified: {clusters}")

# Cluster statistics
cluster_stats = AccidentCluster.objects.aggregate(
    total_accidents=Sum('accident_count'),
    total_casualties=Sum('total_casualties'),
    avg_severity=Avg('severity_score')
)

print(f"Accidents in hotspots: {cluster_stats['total_accidents']}")
print(f"Average severity score: {cluster_stats['avg_severity']:.2f}")
```

**Use in manuscript:** "The AGNES algorithm identified [X] accident hotspot clusters, containing a total of [Y] accidents."

---

## 5. TOP 5 HOTSPOTS

```python
# Top hotspots by severity
top_hotspots = AccidentCluster.objects.order_by('-severity_score')[:5]

print("\nTop 5 Hotspots:")
for i, cluster in enumerate(top_hotspots, 1):
    print(f"{i}. {cluster.primary_location}")
    print(f"   Accidents: {cluster.accident_count}")
    print(f"   Severity: {cluster.severity_score:.1f}")
    print(f"   Casualties: {cluster.total_casualties}")
```

**Use in manuscript (in Chapter 4 Results):**
"Table X shows the top five hotspots identified by the system, with [Location] ranking highest at a severity score of [X]."

---

## 6. MOST COMMON INCIDENT TYPES

```python
# Top incident types
incident_types = Accident.objects.values('incident_type').annotate(
    count=Count('id')
).order_by('-count')[:10]

print("\nTop 10 Incident Types:")
for item in incident_types:
    if item['incident_type']:
        print(f"{item['incident_type']}: {item['count']}")
```

**Use in manuscript:** "[Incident type] was the most common type of accident, accounting for [X] cases."

---

## 7. TEMPORAL PATTERNS

```python
from django.db.models.functions import ExtractMonth, ExtractHour

# By month
by_month = Accident.objects.annotate(
    month=ExtractMonth('date_committed')
).values('month').annotate(count=Count('id')).order_by('month')

months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

print("\nAccidents by Month:")
for item in by_month:
    month_name = months[item['month']-1] if item['month'] else 'Unknown'
    print(f"{month_name}: {item['count']}")
```

**Use in manuscript:** "Temporal analysis revealed that [Month] recorded the highest number of accidents at [X] incidents."

---

## 8. VALIDATION METRICS (If you ran clustering)

```python
from clustering.agnes_algorithm import AGNESClusterer
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
import numpy as np

# Get accidents with cluster assignments
clustered = Accident.objects.filter(cluster_id__isnull=False)

if clustered.exists():
    # Extract coordinates and labels
    coords = np.array([[float(a.latitude), float(a.longitude)] for a in clustered])
    labels = np.array([a.cluster_id for a in clustered])

    # Calculate metrics
    sil = silhouette_score(coords, labels)
    db = davies_bouldin_score(coords, labels)
    ch = calinski_harabasz_score(coords, labels)

    print(f"\nCluster Validation Metrics:")
    print(f"Silhouette Score: {sil:.3f} (higher is better, range: -1 to 1)")
    print(f"Davies-Bouldin Index: {db:.3f} (lower is better)")
    print(f"Calinski-Harabasz Index: {ch:.1f} (higher is better)")
else:
    print("No clustered accidents found. Run clustering first.")
```

**Use in manuscript (Chapter 4):**
"The clustering quality was evaluated using three validation metrics. The Silhouette Score of [X] indicates well-separated clusters, while the Davies-Bouldin Index of [Y] confirms minimal inter-cluster overlap."

---

## 9. SYSTEM USAGE STATISTICS (If you have users)

```python
from django.contrib.auth.models import User
from accidents.models import UserProfile, AuditLog

# User statistics
total_users = User.objects.count()
active_users = UserProfile.objects.filter(is_active=True).count()

# By role
by_role = UserProfile.objects.values('role').annotate(count=Count('id'))
print(f"\nTotal users: {total_users}")
print(f"Active users: {active_users}")
print("\nUsers by role:")
for item in by_role:
    print(f"{item['role']}: {item['count']}")

# Audit logs
total_actions = AuditLog.objects.count()
print(f"\nTotal logged actions: {total_actions}")
```

**Use in manuscript (Chapter 4 or 5):**
"During the testing phase, [X] users from various PNP ranks utilized the system, generating [Y] logged actions."

---

## 10. COMPLETE SUMMARY FOR ABSTRACT

```python
# Generate complete summary
print("\n" + "="*50)
print("COMPLETE DATASET SUMMARY")
print("="*50)

summary = {
    'Total Accidents': Accident.objects.count(),
    'Date Range': f"{Accident.objects.earliest('date_committed').date_committed} to {Accident.objects.latest('date_committed').date_committed}",
    'Provinces Covered': Accident.objects.values('province').distinct().count(),
    'Municipalities': Accident.objects.values('municipal').distinct().count(),
    'Fatal Accidents': Accident.objects.filter(victim_killed=True).count(),
    'Injury Accidents': Accident.objects.filter(victim_injured=True).count(),
    'Total Casualties': Accident.objects.aggregate(Sum('victim_count'))['victim_count__sum'] or 0,
    'Hotspots Identified': AccidentCluster.objects.count(),
    'Accidents in Hotspots': Accident.objects.filter(is_hotspot=True).count(),
}

for key, value in summary.items():
    print(f"{key:25}: {value}")

print("="*50)
```

---

## HOW TO EXPORT THIS DATA TO EXCEL (For Reference)

```python
import csv
from datetime import datetime

# Create CSV file
filename = f'manuscript_stats_{datetime.now().strftime("%Y%m%d")}.csv'

with open(filename, 'w', newline='') as f:
    writer = csv.writer(f)

    # Write province statistics
    writer.writerow(['Province', 'Accident Count'])
    by_province = Accident.objects.values('province').annotate(count=Count('id'))
    for item in by_province:
        writer.writerow([item['province'], item['count']])

    print(f"Exported to {filename}")
```

---

## QUICK ONE-LINER FOR COMMON STATS

Add these to a file `get_stats.py` in your project root:

```python
# get_stats.py
from accidents.models import Accident, AccidentCluster
from django.db.models import Count, Sum, Avg

def print_stats():
    print(f"Accidents: {Accident.objects.count()}")
    print(f"Clusters: {AccidentCluster.objects.count()}")
    print(f"Fatal: {Accident.objects.filter(victim_killed=True).count()}")
    print(f"Provinces: {Accident.objects.values('province').distinct().count()}")

    top = AccidentCluster.objects.order_by('-severity_score').first()
    if top:
        print(f"Top hotspot: {top.primary_location} (severity: {top.severity_score:.1f})")

if __name__ == '__main__':
    print_stats()
```

Then run: `python get_stats.py`

---

## FOR YOUR ABSTRACT (250 words max)

Use this template with your real numbers:

```
This study developed an AGNES-based hotspot detection and reporting system
for road accident analysis in the Caraga Region. Using [X] accident records
from [year] to [year] provided by PNP-HPG, the system identified [Y] accident
hotspots through hierarchical clustering. The AGNES algorithm, configured with
a distance threshold of 0.05 degrees and minimum cluster size of 3, successfully
grouped accidents based on spatial proximity. Severity scoring weighted fatal
accidents at 10 points and injuries at 5 points, enabling prioritization of
high-risk zones. The web-based system features interactive mapping, real-time
reporting, and analytics dashboard. Validation using Silhouette Score ([value])
and Davies-Bouldin Index ([value]) confirmed cluster quality. The top hotspot,
located in [location], recorded [X] accidents with a severity score of [Y].
Results demonstrate that AGNES effectively identifies accident-prone areas,
providing traffic authorities with data-driven insights for intervention planning.
```

---

**Save these queries for when you need to update your manuscript with real data!**
