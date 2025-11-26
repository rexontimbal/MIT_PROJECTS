# FIGURES AND DIAGRAMS NEEDED FOR MANUSCRIPT

## List of Required Figures (7 total)

### FIGURE 1: Conceptual Framework
**Location:** After Research Design section (page ~11)
**Type:** Input-Process-Output (IPO) Diagram
**Content:**
```
INPUT                    PROCESS                         OUTPUT
┌─────────────┐         ┌──────────────────┐          ┌─────────────────┐
│ PNP-HPG     │         │ Data Collection  │          │ Hotspot         │
│ Accident    │────────>│ & Preprocessing  │────────> │ Detection       │
│ Records     │         └──────────────────┘          │ System          │
│             │                  │                     │                 │
│ - Location  │         ┌──────────────────┐          │ - Interactive   │
│ - Date/Time │         │ AGNES Clustering │          │   Map           │
│ - Casualties│────────>│ Algorithm        │────────> │                 │
│ - Vehicles  │         └──────────────────┘          │ - Hotspot       │
│             │                  │                     │   Reports       │
└─────────────┘         ┌──────────────────┐          │                 │
                        │ Severity Scoring │          │ - Analytics     │
                        │ & Validation     │────────> │   Dashboard     │
                        └──────────────────┘          │                 │
                                 │                     │ - Incident      │
                        ┌──────────────────┐          │   Reporting     │
                        │ System           │          │   Module        │
                        │ Development      │────────> │                 │
                        └──────────────────┘          └─────────────────┘
```
**Tools to create:** Microsoft Visio, Draw.io, or PowerPoint

---

### FIGURE 2: AGNES Clustering Algorithm Flowchart
**Location:** After AGNES Implementation section (page ~14)
**Type:** Process Flowchart
**Content:**
```
START
  │
  ▼
[Load Accident Data from Database]
  │
  ▼
[Extract Latitude & Longitude Coordinates]
  │
  ▼
[Initialize AGNES Parameters]
(linkage=complete, threshold=0.05, min_size=3)
  │
  ▼
[Compute Pairwise Euclidean Distances]
  │
  ▼
[Perform Hierarchical Clustering]
(scipy.cluster.hierarchy.linkage)
  │
  ▼
[Form Flat Clusters using Distance Threshold]
(scipy.cluster.hierarchy.fcluster)
  │
  ▼
[Filter: cluster_size >= min_size?]────NO──> [Discard cluster]
  │ YES                                            │
  ▼                                                │
[For each valid cluster:]                         │
  - Calculate centroid (mean lat/lng)             │
  - Calculate bounds (min/max lat/lng)            │
  - Count accidents                               │
  - Count casualties (killed, injured)            │
  - Calculate severity score                      │
  │                                                │
  ▼                                                │
[Store cluster in AccidentCluster table]          │
  │                                                │
  ▼                                                │
[Update Accident records with cluster_id]         │
  │                                                │
  ▼                                                │
[Sort clusters by severity score (descending)]    │
  │<───────────────────────────────────────────────┘
  ▼
[Return clustering results]
  │
  ▼
END
```
**Tools to create:** Draw.io, Lucidchart, or Microsoft Visio

---

### FIGURE 3: System Architecture Diagram
**Location:** After System Architecture section (page ~16)
**Type:** 3-Tier Architecture Diagram
**Content:**
```
┌─────────────────────────────────────────────────────────────┐
│                    PRESENTATION LAYER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   HTML/CSS   │  │  Leaflet.js  │  │   Chart.js   │      │
│  │  Templates   │  │  (Map View)  │  │  (Analytics) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│           │                 │                 │              │
└───────────┼─────────────────┼─────────────────┼──────────────┘
            │                 │                 │
            └─────────────────┴─────────────────┘
                              │
                 HTTP Requests/JSON Responses
                              │
┌─────────────────────────────┼─────────────────────────────────┐
│                    APPLICATION LAYER                          │
│                             │                                 │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │              Django Web Framework                     │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │    │
│  │  │   Views &   │  │  Django REST │  │   Celery    │ │    │
│  │  │   URL       │  │   Framework  │  │   Tasks     │ │    │
│  │  │   Routing   │  │   (API)      │  │   (Async)   │ │    │
│  │  └─────────────┘  └──────────────┘  └─────────────┘ │    │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │         AGNES Clustering Module (Python)              │    │
│  │         - scipy.cluster.hierarchy                     │    │
│  │         - Severity calculation                        │    │
│  │         - Cluster validation                          │    │
│  └────────────────────────────────────────────────────────┘  │
│                             │                                 │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                    Database Queries (SQL)
                              │
┌─────────────────────────────┼─────────────────────────────────┐
│                        DATA LAYER                             │
│  ┌──────────────────────────▼───────────────────────────┐    │
│  │           PostgreSQL 14.x Database                    │    │
│  │  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │    │
│  │  │Accident │  │Accident  │  │ UserProfile/Audit  │  │    │
│  │  │  Table  │  │ Cluster  │  │      Tables        │  │    │
│  │  │         │  │  Table   │  │                    │  │    │
│  │  └─────────┘  └──────────┘  └────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │          Redis Cache & Task Queue                      │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```
**Tools to create:** Draw.io, Lucidchart, or PowerPoint

---

### FIGURE 4: Entity-Relationship Diagram
**Location:** After Database Design section (page ~17)
**Type:** ERD showing relationships
**Content:**
```
┌─────────────────┐
│      User       │
│ (Django Auth)   │
└────────┬────────┘
         │ 1
         │ creates
         │ *
┌────────▼────────┐         ┌──────────────────┐
│    Accident     │    *    │ AccidentCluster  │
│─────────────────│◄────────│──────────────────│
│ PK: id          │ belongs │ PK: id           │
│ latitude        │   to    │ cluster_id (UK)  │
│ longitude       │    1    │ center_latitude  │
│ date_committed  │         │ center_longitude │
│ incident_type   │         │ accident_count   │
│ victim_killed   │         │ severity_score   │
│ victim_injured  │         │                  │
│ FK: cluster_id  │         │                  │
│ FK: created_by  │         └──────────────────┘
└────────┬────────┘
         │ verified as
         │ *
         │ 0..1
┌────────▼──────────┐
│  AccidentReport   │       ┌──────────────────┐
│───────────────────│       │  ClusteringJob   │
│ PK: id            │       │──────────────────│
│ latitude          │       │ PK: id           │
│ longitude         │       │ started_at       │
│ incident_date     │       │ completed_at     │
│ status            │       │ status           │
│ FK: reported_by   │       │ clusters_found   │
│ FK: verified_by   │       │ total_accidents  │
│ FK: accident      │       │ FK: started_by   │
└───────────────────┘       └──────────────────┘
         │
         │ reported by
         │ *
         │ 1
┌────────▼────────┐         ┌──────────────────┐
│  UserProfile    │         │    AuditLog      │
│─────────────────│         │──────────────────│
│ PK: id          │    1    │ PK: id           │
│ FK: user (1-1)  │◄────────│ timestamp        │
│ badge_number    │   logs  │ action           │
│ rank            │    *    │ FK: user         │
│ role            │         │ ip_address       │
│ station         │         │ changes (JSON)   │
└─────────────────┘         └──────────────────┘
```
**Tools to create:** MySQL Workbench, dbdiagram.io, or Draw.io

---

### FIGURE 5: Interactive Map Screenshot
**Location:** After Map Visualization section (page ~19)
**Type:** Screenshot from actual system
**How to capture:**
1. Login to system at http://localhost:8000
2. Navigate to Map View (/map/)
3. Zoom to show Caraga Region with visible clusters
4. Take screenshot showing:
   - Accident markers (different colors)
   - Cluster circles
   - Legend
   - Province boundaries
5. Annotate screenshot with labels pointing to key features

---

### FIGURE 6: Analytics Dashboard Screenshot
**Location:** After Analytics Dashboard section (page ~20)
**Type:** Screenshot from actual system
**How to capture:**
1. Login to system
2. Navigate to Dashboard (/)
3. Ensure charts are loaded:
   - Monthly accident trends chart
   - Province distribution bar chart
   - Incident type pie chart
   - Key statistics cards at top
4. Take full-page screenshot
5. Optionally crop to show most important elements

---

### FIGURE 7: User Role Hierarchy Diagram
**Location:** After User Access Control section (page ~21)
**Type:** Organizational hierarchy chart
**Content:**
```
                    ┌──────────────────┐
                    │   Super Admin    │
                    │  (Full Access)   │
                    └────────┬─────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
    ┌─────▼─────┐    ┌──────▼──────┐    ┌─────▼──────┐
    │ Regional  │    │ Provincial  │    │  Station   │
    │ Director  │    │   Chief     │    │ Commander  │
    └───────────┘    └─────────────┘    └────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                  ┌──────────┴──────────┐
                  │                     │
           ┌──────▼──────┐      ┌──────▼──────┐
           │   Traffic   │      │    Data     │
           │   Officer   │      │   Encoder   │
           └─────────────┘      └─────────────┘

Permissions Legend:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Super Admin:      All permissions
Regional Director: View region data, run clustering
Provincial Chief: View/edit province data
Station Commander: Manage station assignments
Traffic Officer:  Add/edit accidents, submit reports
Data Encoder:     Batch data import
```
**Tools to create:** PowerPoint, Draw.io, or Visio

---

## LIST OF TABLES NEEDED

### TABLE 1: Comparison of Clustering Algorithms
**Location:** In Literature Review (Chapter 2, add as enhancement)
**Content:**
| Algorithm | Type | Distance Metric | Cluster Shape | Parameters | Advantages | Disadvantages |
|-----------|------|-----------------|---------------|------------|------------|---------------|
| AGNES | Hierarchical | Euclidean, Manhattan | Any | Linkage, threshold | No predefined k, dendrogram visualization | O(n³) complexity |
| K-Means | Partitional | Euclidean | Spherical | k (number of clusters) | Fast, simple | Requires k, sensitive to outliers |
| DBSCAN | Density-based | Euclidean | Arbitrary | eps, minPts | Handles noise, any shape | Sensitive to parameters |

### TABLE 2: AGNES Parameters Used in Study
**Location:** In Methods (after algorithm description)
| Parameter | Value | Justification |
|-----------|-------|---------------|
| Linkage Method | Complete | Considers maximum distance, creates compact clusters |
| Distance Metric | Euclidean | Straight-line geographic distance |
| Distance Threshold | 0.05° (~5.5 km) | Typical jurisdiction radius for traffic enforcement |
| Minimum Cluster Size | 3 accidents | Statistical significance threshold |

### TABLE 3: Severity Score Weights
**Location:** In Methods (severity scoring section)
| Outcome Type | Weight | Maximum Points | Rationale |
|--------------|--------|----------------|-----------|
| Fatal (killed) | 10 | 60 | Highest severity, irreversible |
| Injury | 5 | 60 | Significant harm, medical attention |
| Property damage only | 1 | 40 | Frequency indicator |

### TABLE 4: System Development Tools
**Location:** In Methods (development tools section)
| Category | Tool/Technology | Version | Purpose |
|----------|-----------------|---------|---------|
| Backend Framework | Django | 5.0.6 | Web application framework |
| Database | PostgreSQL | 14.x | Data persistence |
| Clustering | SciPy | 1.13.1 | Hierarchical clustering |
| Task Queue | Celery | 5.4.0 | Asynchronous processing |
| Frontend | Leaflet.js | 1.9.x | Interactive maps |
| Charts | Chart.js | 4.x | Data visualization |

### TABLE 5: User Roles and Permissions
**Location:** In Methods (security section)
| Role | View Data | Add/Edit | Delete | Run Clustering | Manage Users | Scope |
|------|-----------|----------|--------|----------------|--------------|-------|
| Super Admin | ✓ | ✓ | ✓ | ✓ | ✓ | All regions |
| Regional Director | ✓ | ✓ | ✗ | ✓ | ✗ | Caraga Region |
| Provincial Chief | ✓ | ✓ | ✗ | ✗ | ✗ | Assigned province |
| Station Commander | ✓ | ✓ | ✗ | ✗ | ✗ | Assigned station |
| Traffic Officer | ✓ | ✓ | ✗ | ✗ | ✗ | Own reports |
| Data Encoder | ✓ | ✓ | ✗ | ✗ | ✗ | Batch import |

---

## NOTES FOR CREATING FIGURES

1. **Use consistent styling:**
   - Color scheme: Blue (#003087) for PNP theme
   - Font: Arial 10-11pt for diagram text
   - White background

2. **Screenshots quality:**
   - Minimum 1920x1080 resolution
   - PNG format (better for diagrams)
   - Annotate with arrows/labels if needed

3. **File naming:**
   - Figure_1_Conceptual_Framework.png
   - Figure_2_AGNES_Flowchart.png
   - Figure_3_System_Architecture.png
   - etc.

4. **Placement in document:**
   - Insert after first mention in text
   - Center-align
   - Add caption below: "Figure X: [Title]"

5. **Update List of Figures section:**
   - After creating all figures, list them with page numbers
   - Format: "Figure 1  Conceptual Framework  Page 11"
