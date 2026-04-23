# AGNES Final Defense — Speaker Script
### Rexon L. Timbal | Master in Information Technology | SNSU

---

## SLIDE 1 — TITLE SLIDE

> Good morning/afternoon, esteemed panel members, faculty, and guests. My name is Rexon L. Timbal, a candidate for the degree of Master in Information Technology at the Surigao del Norte State University.
>
> Today, I will present my capstone project entitled **"AI-Based Hotspot Detection and Reporting System for Road Accident Analysis: A Decision Support System."**
>
> This system leverages the AGNES — or Agglomerative Nesting — clustering algorithm to identify high-risk road accident zones in the Caraga Region, serving as a data-driven tool for the Philippine National Police.

---

## SLIDE 2 — PRESENTATION OUTLINE

> Before we begin, let me walk you through the flow of this presentation. We will cover ten key areas:
>
> First, the **Introduction and Background** to set the context. Then, the **Problem Statement** and **Research Gap** to establish what this study addresses. Next, the **Objectives**, followed by the **Methodology** and **System Architecture**. We will then look at the **Key Features**, the **AGNES Algorithm** in detail, the **Results and Validation**, and finally, the **Conclusion and Recommendations**.
>
> Let us begin.

---

## SLIDE 3 — INTRODUCTION & BACKGROUND

> Road traffic accidents are a global crisis. According to the World Health Organization, approximately **1.19 million lives** are lost every year due to road crashes. This costs nations up to **3% of their GDP**, and the most affected group is working-age males between **20 to 40 years old** — the breadwinners of families.
>
> Here in the Philippines, particularly in the **Caraga Region**, driver negligence remains the primary cause of vehicular collisions. High-risk areas such as Libertad in Butuan City experience frequent incidents, yet there is no systematic, data-driven approach to identify and prioritize these danger zones.
>
> The key insight here is that **current methods rely on manual reporting and generalized statistics**. There is no precision tool for targeted, evidence-based traffic safety interventions — and that is the gap this study aims to fill.

---

## SLIDE 4 — PROBLEM STATEMENT

> The core problems this study addresses are fourfold:
>
> **First**, there is a lack of systematic analysis. Traffic accident data in Caraga is collected manually, without any spatial clustering or pattern recognition — so recurring high-risk zones go unidentified.
>
> **Second**, there is no geospatial hotspot detection. Existing processes do not use geographic coordinates to pinpoint accident-prone areas. As a result, interventions are reactive — they happen after major incidents — rather than proactive and preventive.
>
> **Third**, reporting workflows are fragmented. Accident reports follow paper-based or unstructured formats, making the data inconsistent and difficult to aggregate or analyze at scale.
>
> And **fourth**, there is a complete absence of decision support tools. Law enforcement agencies have no centralized dashboard to visualize trends, assess severity, or make informed decisions on where to deploy resources.

---

## SLIDE 5 — RESEARCH GAP

> Now, let me highlight the research gap — the space between what existing studies have done and what this study uniquely contributes.
>
> On the left, you can see the **current state**. Most studies focus on national-level or metro-area analysis, overlooking regional patterns in areas like Caraga. Existing systems use only basic statistics — counts and averages — without applying clustering algorithms. There is no integration of AGNES with a web-based decision support system for Philippine law enforcement. Paper-based TARs are hard to digitize. And critically, there is no use of scientific validation metrics.
>
> On the right, **this study addresses every one of those gaps**. It focuses specifically on the Caraga Region's 5 provinces. It applies AGNES hierarchical clustering to geospatial coordinates. It integrates the clustering engine with a full-featured web-based DSS. It digitizes the TAR workflow with structured, verifiable data. And it validates results using three scientific metrics — Silhouette Score, Davies-Bouldin Index, and Calinski-Harabasz Score.

---

## SLIDE 6 — RESEARCH OBJECTIVES

> The **general objective** of this study is to develop an AI-based hotspot detection and reporting system that uses the AGNES clustering algorithm to identify high-risk road accident zones in the Caraga Region, providing a decision support tool for PNP traffic management.
>
> This is broken down into **five specific objectives**:
>
> 1. Design and implement a web-based TAR management system with structured data capture and multi-stage verification.
> 2. Apply AGNES hierarchical clustering to geospatial accident data for identifying and ranking hotspots by severity.
> 3. Develop an interactive analytics dashboard with real-time statistics, maps, and trend analysis.
> 4. Validate clustering results using Silhouette, Davies-Bouldin, and Calinski-Harabasz metrics.
> 5. Deploy as a responsive web platform with mobile app support for PNP field personnel.
>
> Each objective directly maps to a deliverable in the system.

---

## SLIDE 7 — METHODOLOGY & FRAMEWORK

> The methodology follows a six-phase approach:
>
> **Phase 1 — Data Collection**: We gathered traffic accident records from CY2019 to 2024 from PNP Caraga, covering five provinces.
>
> **Phase 2 — System Design**: We designed the TAR-based reporting workflow, the database schema, and the user interface following PNP standards.
>
> **Phase 3 — Development**: The system was built using Django 5.0.6 with PostgreSQL, REST APIs, and Leaflet.js for mapping.
>
> **Phase 4 — AGNES Clustering**: We implemented the hierarchical clustering algorithm on spatial coordinates using SciPy.
>
> **Phase 5 — Validation**: We applied three scientific metrics to assess clustering quality and reliability.
>
> **Phase 6 — Testing and Deployment**: User Acceptance Testing was conducted with PNP personnel, IT experts evaluated the system, and it was deployed on Railway cloud hosting.
>
> The research design is **applied research** with an **agile, iterative** development model.

---

## SLIDE 8 — SYSTEM ARCHITECTURE & TECHNOLOGY STACK

> The system follows a four-layer architecture:
>
> At the top, the **Presentation Layer** handles the user interface — responsive web design with Leaflet.js maps, Chart.js analytics, dark mode, and a mobile app built with Capacitor.
>
> The **Application Layer** runs Django 5.0.6 with REST APIs, role-based access control, the TAR report workflow, and Celery for asynchronous task processing.
>
> The **Intelligence Layer** is the core — this is where AGNES clustering runs via SciPy, severity scoring is calculated, and validation metrics are generated using scikit-learn.
>
> At the base, the **Data Layer** uses PostgreSQL 14 for the database, Cloudinary for media storage, and supports CSV import/export through Django's ORM.
>
> Deployment is on Railway with Gunicorn, SSL, and Philippine timezone configuration.

---

## SLIDE 9 — KEY FEATURES (Part 1)

> Let me walk you through the six core modules:
>
> **Hotspot Detection Engine** — the heart of the system. It runs AGNES clustering on GPS coordinates with configurable parameters like linkage method, distance threshold, and minimum cluster size.
>
> **Analytics Dashboard** — provides real-time statistics: today's, this week's, and this month's accident counts, 12-month trends, breakdown by province, and the top 5 hotspots by severity.
>
> **Interactive Map** — powered by Leaflet.js with marker clustering, fullscreen mode, satellite imagery, and visual hotspot zones that officers can explore geographically.
>
> **TAR Reporting** — a structured 8-section Traffic Accident Report form with sections from Officer Information through Action Taken, following PNP standards with multi-stage verification.
>
> **Role-Based Access Control** — four user roles: Officer, Admin, Supervisor, and Data Manager, each with specific permissions and full audit logging.
>
> **Mobile Application** — a Capacitor-based Android APK that allows PNP field personnel to access the system from their phones.

---

## SLIDE 10 — KEY FEATURES (Part 2)

> Continuing with additional modules:
>
> **Severity Scoring** uses a multi-factor formula on a 0 to 100 scale. Frequency contributes up to 40 points, and casualties contribute up to 60 — with 10 points per fatality, 5 per injury, and 1 for property damage only.
>
> **Clustering Validation** applies three scientific metrics to every clustering run, ensuring results are reliable and not arbitrary.
>
> **Report Workflow** follows a complete pipeline: from Submitted to Pending Verification, to Verified, Under Investigation, and finally Resolved — with officer assignments and evidence uploads at each stage.
>
> **Data Import/Export** supports CSV bulk import of the CY2019-2024 dataset, plus PDF and Excel exports with validation on ingest.
>
> At the bottom, you can see the workflow visualized — from submission all the way through to resolution.

---

## SLIDE 11 — AGNES CLUSTERING ALGORITHM

> Now let me explain how the AGNES algorithm works in detail.
>
> AGNES stands for **Agglomerative Nesting** — it is a bottom-up hierarchical clustering approach.
>
> **Step 1**: Each accident location — defined by its latitude and longitude — starts as its own individual cluster.
>
> **Step 2**: The algorithm computes pairwise distances between all clusters using Euclidean distance.
>
> **Step 3**: The two closest clusters are merged into one, using the selected linkage method. We use **Complete linkage** by default, which considers the farthest neighbor distance — this produces more compact, evenly-sized clusters.
>
> **Step 4**: This merging process repeats iteratively.
>
> **Step 5**: We cut the resulting dendrogram at a distance threshold of approximately 0.05 degrees — roughly 5 kilometers — to form flat clusters.
>
> **Step 6**: Clusters with fewer than 3 accidents are filtered out, and severity scores are calculated for the remaining hotspots.
>
> On the right, you can see the default configuration and the severity scoring breakdown. This scoring system ensures that areas with fatalities are prioritized over those with only property damage.

---

## SLIDE 12 — RESULTS & VALIDATION

> For validation, we use three scientifically established clustering quality metrics:
>
> **Silhouette Score** ranges from -1 to +1. Higher values indicate well-separated, cohesive clusters. It measures how similar each point is to its own cluster compared to neighboring clusters.
>
> **Davies-Bouldin Index** ranges from 0 to infinity, where lower is better. It measures the average similarity between clusters — values close to 0 mean compact, well-separated groupings.
>
> **Calinski-Harabasz Score** also ranges from 0 to infinity, where higher is better. It is the ratio of between-cluster dispersion to within-cluster dispersion — higher values mean denser, better-defined clusters.
>
> These three metrics together provide a comprehensive assessment of clustering quality from multiple angles.
>
> The evaluation also included **User Acceptance Testing** with actual PNP Caraga personnel and **IT Expert Evaluation** by domain specialists, both of which validated the system's usability and technical soundness.

---

## SLIDE 13 — SYSTEM DEMONSTRATION

> *[At this point, either switch to a live demo of the system or walk through the screenshots on this slide.]*
>
> Here you can see the key interfaces:
>
> The **Dashboard** shows real-time accident statistics with trend charts and key performance indicators.
>
> The **Hotspot Map** displays identified clusters geographically, with color-coded severity indicators that officers can click for detailed information.
>
> The **TAR Report Form** demonstrates the structured, section-by-section data entry following PNP standards.
>
> The **Clustering Results** panel shows detected hotspots with their severity scores and validation metrics.
>
> And the **Mobile App** interface shows how field officers can access the system on Android devices.
>
> *[If doing a live demo, navigate through: Dashboard → Map → Submit a Report → Run Clustering → View Results]*

---

## SLIDE 14 — CONCLUSION

> To conclude, this study has achieved the following:
>
> **First**, we successfully developed an AI-based decision support system that applies AGNES hierarchical clustering to identify road accident hotspots across the Caraga Region.
>
> **Second**, the system digitizes the entire Traffic Accident Report workflow, replacing paper-based processes with a structured, verifiable digital pipeline — improving data quality and accessibility.
>
> **Third**, scientific validation through three established metrics confirms the reliability and quality of the clustering results — this is not just a tool, it produces scientifically defensible outputs.
>
> **Fourth**, the interactive dashboard and map visualization give law enforcement actionable, data-driven insights — enabling them to allocate resources where they are needed most.
>
> And **fifth**, successful deployment as both a web platform and mobile application demonstrates that the system is ready for practical use by PNP Caraga in the field.

---

## SLIDE 15 — RECOMMENDATIONS

> For future work, I recommend five directions:
>
> **Predictive Analytics** — integrating time-series forecasting to predict where future hotspots may emerge based on historical trends and seasonal patterns.
>
> **Advanced AI Models** — exploring other algorithms like DBSCAN and OPTICS for comparison, and adding natural language processing for automated report analysis.
>
> **Regional Expansion** — extending the system beyond Caraga to other Philippine regions, potentially creating a nationwide platform.
>
> **Real-Time Data Integration** — connecting with CCTV feeds, IoT sensors, and traffic management systems for immediate accident detection.
>
> **Inter-Agency Integration** — enabling data sharing with DPWH, DOTr, LTO, and hospital systems for a comprehensive road safety ecosystem.
>
> These enhancements would significantly amplify the system's impact on public safety.

---

## SLIDE 16 — THANK YOU / Q&A

> That concludes my presentation. I would like to express my sincere gratitude to my adviser, the panel members, the PNP Caraga Region for their cooperation, and the faculty of the Graduate School at SNSU for their guidance throughout this journey.
>
> I am now open for questions and discussions. Thank you.

---

### TIPS FOR THE DEFENSE:

1. **Pace yourself** — speak slowly and clearly, especially during the algorithm and validation slides.
2. **Make eye contact** with the panel, not the screen.
3. **For the demo slide** — if possible, do a live demo. If not, insert actual screenshots before the presentation.
4. **Anticipate questions** about: why AGNES over DBSCAN, how you validated accuracy, what the actual clustering results showed (have specific numbers ready), and scalability.
5. **Keep answers concise** — answer what was asked, then stop. Don't over-explain.
6. **Bring printed copies** of your manuscript for the panel.
7. **Time target**: Aim for 20-25 minutes for the presentation, leaving 15-20 minutes for Q&A.
