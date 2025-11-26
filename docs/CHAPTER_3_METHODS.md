CHAPTER 3
METHODS

Research Design

This study utilized a descriptive-developmental research design to develop an AGNES-based hotspot detection and reporting system for road accident analysis in the Caraga Region. The descriptive component involved analyzing historical accident data to identify spatial and temporal patterns, while the developmental aspect focused on building a functional web-based system that integrates clustering algorithms with reporting capabilities.

The research followed an iterative development approach, allowing continuous refinement of both the clustering algorithm parameters and system features based on testing results and stakeholder feedback.

**[INSERT FIGURE 1: Conceptual Framework - showing Input→Process→Output flow]**


Data Collection and Sources

Accident data was collected from the Philippine National Police - Highway Patrol Group (PNP-HPG) Caraga Regional Office. The dataset covered traffic accident incidents recorded from 2020 to 2024 across the five provinces of the Caraga Region: Agusan del Norte, Agusan del Sur, Surigao del Norte, Surigao del Sur, and Dinagat Islands.

Each accident record contained the following key attributes:
- Geographic coordinates (latitude and longitude)
- Administrative location (province, municipality, barangay, street)
- Temporal information (date and time of occurrence)
- Incident details (type of offense, vehicle involved)
- Casualty information (number of victims killed, injured, or unharmed)
- Case status and investigation details

The data was provided in CSV format and underwent preprocessing before being imported into the system database.


Data Preprocessing

Before applying the clustering algorithm, the raw accident data went through several preprocessing steps to ensure quality and consistency:

1. **Coordinate Validation** - All latitude and longitude values were validated to fall within Philippine boundaries (4.0° to 22.0° N, 115.0° to 128.0° E). Records with invalid coordinates were flagged for manual verification.

2. **Caraga Region Filtering** - Only accidents within the Caraga Region's geographic bounds (8.0° to 10.5° N, 125.0° to 126.5° E) were included in the analysis.

3. **Missing Value Handling** - Records with missing critical fields (coordinates, date, location) were excluded from clustering but retained in the database for reference purposes.

4. **Duplicate Removal** - Duplicate entries based on matching coordinates, date, and time were identified and removed.

5. **Date Normalization** - All timestamps were converted to Philippine Standard Time (Asia/Manila timezone) to ensure temporal consistency.

After preprocessing, the cleaned dataset was stored in a PostgreSQL database for efficient querying and analysis.


AGNES Clustering Algorithm Implementation

The core of the hotspot detection system is based on the AGNES (Agglomerative Nesting) algorithm, a hierarchical clustering method that builds clusters from the bottom up by iteratively merging the closest pairs of accidents.

**Algorithm Parameters:**
The following parameters were used based on preliminary testing and consultation with traffic management experts:

- **Linkage Method:** Complete linkage (considers maximum distance between cluster pairs)
- **Distance Metric:** Euclidean distance calculated from geographic coordinates
- **Distance Threshold:** 0.05 decimal degrees (approximately 5.5 kilometers)
- **Minimum Cluster Size:** 3 accidents (minimum required to be classified as a hotspot)

**Clustering Process:**
The AGNES algorithm was implemented using Python's SciPy library (scipy.cluster.hierarchy) following these steps:

1. Extract latitude and longitude coordinates from all accident records
2. Compute pairwise distances between all accident locations using Euclidean metric
3. Perform hierarchical clustering with complete linkage method
4. Form flat clusters using the distance threshold criterion
5. Filter out clusters with fewer than 3 accidents
6. Calculate cluster statistics (centroid, bounds, severity score)

**[INSERT FIGURE 2: AGNES Clustering Algorithm Flowchart]**

For each identified cluster, the system computes:
- **Center coordinates (centroid):** Mean latitude and longitude of all accidents in the cluster
- **Cluster bounds:** Minimum and maximum latitude/longitude values
- **Accident count:** Total number of accidents in the cluster
- **Casualty statistics:** Number of fatalities and injuries
- **Severity score:** Weighted score based on casualty impact


Severity Scoring Method

To prioritize hotspots based on risk level, a severity scoring formula was developed that considers both accident frequency and casualty impact:

**Severity Score = Frequency Score + Casualty Score**

Where:
- **Frequency Score** = min(accident_count × 2, 40) [Maximum 40 points]
- **Casualty Score** = (killed_count × 10) + (injured_count × 5) [Maximum 60 points]

The weights (10 for fatalities, 5 for injuries) reflect the relative severity of accident outcomes. The total severity score ranges from 0 to 100, with higher scores indicating more critical hotspots requiring immediate intervention.

This scoring approach ensures that both high-frequency accident areas and high-impact casualty zones are appropriately prioritized.


System Architecture and Design

The system was developed as a web-based application using Django 5.0.6 framework to ensure scalability, maintainability, and ease of deployment. The architecture follows a three-tier model:

**[INSERT FIGURE 3: System Architecture Diagram - 3-tier architecture showing Presentation, Application, Data layers]**

**1. Presentation Layer (Frontend)**
- HTML5 templates with Bootstrap CSS framework for responsive design
- Leaflet.js library for interactive map visualization
- Chart.js for statistical graphs and analytics
- JavaScript for asynchronous data loading and user interactions

**2. Application Layer (Backend)**
- Django web framework for business logic and request handling
- Django REST Framework for API endpoints
- Celery task queue for asynchronous clustering operations
- Custom AGNES clustering module implemented in Python

**3. Data Layer**
- PostgreSQL 14.x database for persistent storage
- Redis cache for session management and task queue
- File storage for exported reports and uploaded images

**Communication Flow:**
User requests are processed through Django views, which interact with the database through Django ORM (Object-Relational Mapping). Clustering operations are executed as background tasks using Celery to prevent blocking the web interface. Results are cached in Redis to improve response times for subsequent requests.


Database Design

The system database consists of six main tables to manage accidents, clusters, reports, users, and system operations:

**[INSERT FIGURE 4: Entity-Relationship Diagram showing 6 models and their relationships]**

**Key Models:**

1. **Accident** - Stores complete accident records with location, temporal, casualty, and vehicle information. Contains foreign key reference to cluster assignment.

2. **AccidentCluster** - Stores AGNES clustering results including centroid coordinates, cluster bounds, accident count, severity score, and affected municipalities.

3. **AccidentReport** - Manages citizen-submitted accident reports with verification workflow (pending, verified, investigating, resolved, rejected statuses).

4. **UserProfile** - Extends Django's User model with PNP-specific fields (badge number, rank, role, assigned station).

5. **ClusteringJob** - Audit trail for clustering operations, recording parameters used, execution time, and results.

6. **AuditLog** - Comprehensive activity logging for security and compliance tracking.

The database uses spatial indexing on latitude/longitude fields to optimize geographic queries required for clustering and map-based searches.


System Features and Modules

The developed system integrates four main functional modules:

**3.7.1 Hotspot Detection Module**
This module executes the AGNES clustering algorithm on demand or through scheduled tasks. It processes all accident records in the database, identifies clusters, calculates severity scores, and updates the AccidentCluster table. The clustering can be triggered manually by authorized users or runs automatically every 24 hours to incorporate new accident data.

**3.7.2 Interactive Map Visualization**
The system provides an interactive map interface built with Leaflet.js that displays:
- Individual accident markers color-coded by severity
- Cluster circles sized proportionally to severity score
- Heatmap overlay showing accident density
- Province and municipality boundaries
- Clickable markers that show detailed accident information

**[INSERT FIGURE 5: Screenshot of Interactive Map showing hotspot clusters]**

**3.7.3 Incident Reporting Module**
This module allows PNP personnel and authorized users to submit new accident reports through a web form. The reporting interface includes:
- Location picker using map click or coordinate entry
- Date and time selectors
- Casualty information inputs
- Vehicle details section
- Photo upload capability (up to 3 images, max 5MB each)
- Narrative text area for incident description

Submitted reports enter a verification workflow where authorized personnel review and approve them before integration into the main accident database.

**3.7.4 Analytics Dashboard**
The dashboard provides statistical summaries and visualizations:
- Total accidents by time period (day, week, month, year)
- Accidents by province and municipality
- Incident type distribution
- Casualty trends over time
- Top 10 hotspots by severity score
- Interactive charts using Chart.js library

**[INSERT FIGURE 6: Dashboard Screenshot showing key statistics and charts]**


Cluster Validation

To evaluate the quality of the clusters identified by AGNES, two validation approaches were employed:

**3.8.1 Statistical Validation Metrics**
The following internal validation indices were calculated:

- **Silhouette Score** - Measures how similar an accident is to its own cluster compared to other clusters. Values range from -1 to 1, with higher values indicating better-defined clusters.

- **Davies-Bouldin Index** - Evaluates cluster separation by comparing within-cluster scatter to between-cluster distance. Lower values indicate better clustering.

- **Calinski-Harabasz Index** - Ratio of between-cluster variance to within-cluster variance. Higher values indicate better-defined clusters.

These metrics were computed using scikit-learn library functions to assess clustering performance objectively.

**3.8.2 Ground-Truth Validation**
The identified hotspots were compared against known high-risk areas documented in PNP-HPG traffic reports and local government traffic management plans. Traffic officers familiar with the region validated whether the detected clusters correspond to locations recognized as accident-prone based on their field experience.

Validation results were used to fine-tune the distance threshold and minimum cluster size parameters to optimize detection accuracy.


User Access Control and Security

The system implements role-based access control with six user roles, each with specific permissions:

1. **Super Admin** - Full system access including user management and configuration
2. **Regional Director** - Region-wide data access and reporting
3. **Provincial Chief** - Province-level data and operations
4. **Station Commander** - Station-assigned data management
5. **Traffic Officer** - Accident data entry and basic reporting
6. **Data Encoder** - Batch data import and entry

**Security Features:**
- Custom authentication backend supporting both username and PNP badge number login
- Account lockout after 5 failed login attempts (30-minute duration)
- Session timeout after 24 hours of inactivity
- Comprehensive audit logging of all user actions with IP address tracking
- Password complexity requirements (minimum 8 characters with uppercase, lowercase, digit, and special character)

**[INSERT FIGURE 7: User Role Hierarchy Diagram]**


Development Tools and Environment

**Programming Languages and Frameworks:**
- Python 3.11 for backend development
- JavaScript ES6 for frontend interactivity
- HTML5 and CSS3 for user interface

**Libraries and Dependencies:**
- Django 5.0.6 - Web framework
- SciPy 1.13.1 - Hierarchical clustering implementation
- NumPy 1.26.4 - Numerical computations
- PostgreSQL 14.x - Database management system
- Redis 5.2.0 - Caching and task queue backend
- Celery 5.4.0 - Asynchronous task processing
- Leaflet.js - Interactive maps
- Chart.js - Data visualization

**Development Environment:**
- Operating System: Linux/Ubuntu
- IDE: Visual Studio Code
- Version Control: Git
- Database Tool: pgAdmin 4
- API Testing: Postman

**Deployment Configuration:**
- WSGI Server: Gunicorn
- Static File Serving: WhiteNoise middleware
- Process Management: Systemd (for production)


Testing and Evaluation

The system underwent three levels of testing:

**3.11.1 Unit Testing**
Individual components (clustering algorithm, severity calculation, validation functions) were tested using Django's TestCase framework to ensure correct functionality under various input conditions.

**3.11.2 Integration Testing**
Module interactions were tested, particularly:
- Database operations with clustering workflow
- API endpoints with frontend map interface
- Report submission with verification workflow
- Export functionality with data formatting

**3.11.3 User Acceptance Testing**
A pilot deployment was conducted with PNP-HPG Caraga personnel who evaluated:
- System usability and interface design
- Accuracy of detected hotspots against their field knowledge
- Report submission workflow efficiency
- Usefulness of visualization and analytics features

Feedback from these testing phases guided final refinements before system completion.
