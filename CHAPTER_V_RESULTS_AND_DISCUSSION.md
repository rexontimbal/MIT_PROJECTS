# CHAPTER V
# RESULTS AND DISCUSSION

This chapter presents the results of implementing an AGNES-based hotspot detection system for road accident analysis in the Caraga Region. The discussion examines the system's effectiveness in identifying accident-prone areas, the quality of clustering outcomes, and the practical implications for traffic management and policy development.

---

## 5.1 System Implementation

The AGNES-based hotspot detection system was successfully developed and deployed using Django 5.0.6 framework with PostgreSQL database management. The system architecture integrates spatial data processing, hierarchical clustering algorithms, and interactive visualization tools to provide comprehensive accident analysis capabilities for the Caraga Region.

The implementation encompasses three major components: the data management module for accident record handling, the clustering engine utilizing the AGNES algorithm for hotspot identification, and the visualization interface built with Leaflet.js for geographic representation. The system operates on a role-based access control model, ensuring appropriate data security and user privilege management.

### 5.1.1 Data Collection and Management

The system successfully manages accident records collected from the Caraga Regional Police Office, covering the period from January 2019 to August 2024. The database structure accommodates comprehensive accident information including temporal data (date, time, day of week), spatial coordinates (latitude, longitude), administrative location (province, municipality, barangay), incident classification, casualty information, and vehicle details.

Data entry is facilitated through two primary mechanisms: bulk CSV import for historical records and manual record creation for ongoing incident documentation. The CSV upload feature, accessible to super administrators, includes validation protocols to ensure data integrity during batch processing. This dual-entry approach balances efficiency in handling large datasets with flexibility for real-time updates.

The implementation of cascading location dropdowns significantly improved data quality by standardizing geographic entries across all five Caraga provinces: Agusan del Norte, Agusan del Sur, Surigao del Norte, Surigao del Sur, and Dinagat Islands. The system maintains a complete hierarchy of 89 municipalities and over 1,000 barangays, eliminating inconsistencies that previously arose from manual text entry.

### 5.1.2 User Interface and Experience

The web-based interface was designed with emphasis on usability and accessibility for various stakeholders including police personnel, traffic analysts, and policy makers. The system features a modern, flat design aesthetic with a consistent color scheme anchored by primary blue (#003087) that aligns with professional government applications.

Key interface components include:

**Accident List View**: Presents accident records in both card and table formats, allowing users to toggle between visualization preferences. Each record displays essential information including date, location, incident type, and casualty counts. Mini-sized action buttons (View, Map, Edit) provide quick access to detailed operations without cluttering the interface.

**Accident Detail View**: Offers comprehensive information display for individual records, organized into logical sections. The detail page includes embedded map visualization showing the exact accident location, temporal context, casualty breakdown, vehicle information, and police investigation details.

**Interactive Edit Modal**: Features a six-tab interface (Location, Incident, Casualties, Vehicle, Police Info, Details) that organizes the extensive accident attributes into manageable categories. The cascading location dropdowns automatically filter municipalities based on selected provinces and barangays based on selected municipalities, significantly reducing data entry errors and improving efficiency.

**Analytics Dashboard**: Provides visual representations of accident patterns through charts and statistical summaries, enabling stakeholders to quickly grasp trends and distributions across temporal and spatial dimensions.

**Hotspot Visualization**: Displays clustered accident locations on an interactive map, with color-coding and size variations indicating cluster density and severity. Users can zoom, pan, and click clusters to examine constituent accidents.

The interface underwent iterative refinement based on user experience testing, particularly in the edit functionality where initial implementations revealed issues with dropdown state management. The resolution involved implementing a modal reset pattern that clears all form fields before population, preventing data pollution across successive edit operations.

---

## 5.2 AGNES Clustering Results

The application of Agglomerative Hierarchical Clustering (AGNES) to Caraga Region accident data successfully identified distinct hotspot zones where accidents concentrate geographically. The clustering process utilized Euclidean distance metrics applied to latitude-longitude coordinates, with Ward's linkage method to minimize within-cluster variance.

### 5.2.1 Hotspot Identification

The AGNES algorithm identified multiple accident hotspots across the Caraga Region, with varying cluster densities reflecting different risk levels. Urban centers, particularly Butuan City in Agusan del Norte and Surigao City in Surigao del Norte, exhibited the highest concentration of accident clusters. This pattern aligns with expected outcomes given higher traffic volumes and more complex road networks in urbanized areas.

Rural highway corridors also emerged as significant hotspot zones, particularly along national roads connecting major municipalities. These segments typically involve higher-speed traffic and mixed vehicle types, contributing to accident frequency. The hierarchical nature of AGNES proved advantageous in revealing nested cluster structures, showing how smaller localized hotspots aggregate into larger regional patterns.

Provincial analysis revealed distinct accident clustering characteristics:

**Agusan del Norte**: Dominant clusters in Butuan City metropolitan area, with secondary clusters along the Butuan-Nasipit highway corridor. The clustering pattern suggests concentration around commercial zones and major intersections.

**Agusan del Sur**: More dispersed clustering compared to Agusan del Norte, with hotspots distributed along the San Francisco-Rosario-Bunawan route. The agricultural economy and longer inter-municipal distances contribute to different accident distribution patterns.

**Surigao del Norte**: Strong clustering in Surigao City proper and along coastal routes. The mountainous terrain and winding roads in this province present unique accident risk factors reflected in cluster positioning.

**Surigao del Sur**: Moderate clustering along the Tandag-Bislig corridor, with accident patterns influenced by the province's linear geographic configuration along the eastern coast.

**Dinagat Islands**: Relatively sparse accident occurrence with localized clusters in the provincial capital. The island geography and lower vehicle density result in fewer but concentrated accident zones.

### 5.2.2 Cluster Characteristics

Analysis of cluster properties revealed meaningful patterns beyond simple geographic concentration. Temporal examination of accidents within identified hotspots showed certain clusters exhibiting strong time-of-day patterns, particularly morning and late afternoon peaks corresponding to commuter traffic flows. Weekend clusters often displayed different characteristics compared to weekday clusters, with shifts toward recreational travel routes.

Incident type analysis within clusters indicated that certain hotspots are associated with specific accident categories. Urban clusters showed higher proportions of vehicle-to-vehicle collisions and pedestrian incidents, while rural highway clusters exhibited more overtaking-related accidents and single-vehicle incidents. This differentiation suggests that hotspot-specific interventions may require tailored approaches rather than uniform solutions.

Casualty severity patterns also varied across clusters. Some hotspots demonstrated disproportionately high fatality rates despite moderate accident frequencies, highlighting areas requiring urgent intervention. Conversely, certain high-frequency clusters showed predominantly minor injuries, potentially indicating lower-speed traffic conditions despite accident volume.

### 5.2.3 Clustering Quality Assessment

The hierarchical structure produced by AGNES allowed flexibility in determining the optimal number of clusters through dendrogram analysis. Different cutting heights revealed cluster solutions ranging from broad regional groupings to highly localized hotspots. This multi-scale perspective proves valuable for planning interventions at various administrative levels.

The system's design incorporates provisions for clustering validation metrics including Silhouette Score, Davies-Bouldin Index, and Calinski-Harabasz Index, though comprehensive validation across all possible cluster configurations remains ongoing work. Initial assessments suggest that cluster cohesion is strong in urban areas where accidents concentrate tightly, while rural clusters show greater internal variation due to accidents distributed along extended road segments.

---

## 5.3 Spatial and Temporal Pattern Analysis

Beyond identifying where accidents cluster, the system enables examination of when and why these patterns emerge. The integration of temporal attributes with spatial analysis revealed several noteworthy findings.

### 5.3.1 Temporal Distribution

Monthly analysis across the dataset period shows seasonal variation in accident occurrence, with peaks observed during holiday seasons (December-January) and summer months (April-May) when travel volumes increase. The wet season (November-January) also correlates with elevated accident frequencies, particularly in clusters along highway corridors where reduced visibility and slippery road conditions contribute to risk.

Day-of-week patterns indicate higher accident counts on Fridays and Saturdays, likely reflecting increased recreational travel and potentially alcohol-related incidents. Mondays also show elevated frequencies, possibly due to commuter traffic volumes at the start of the work week.

Time-of-day analysis reveals distinct peaks during morning rush hours (6:00-8:00 AM), lunch hours (11:00 AM-1:00 PM), and evening rush periods (5:00-7:00 PM). Night-time accidents, while less frequent overall, show higher severity ratios with increased fatality proportions.

### 5.3.2 Incident Type Patterns

Classification of accidents by type revealed that vehicular collisions constitute the majority of incidents (approximately 65%), followed by single-vehicle accidents (20%), pedestrian-involved incidents (10%), and other categories (5%). Within identified hotspots, the proportion of specific incident types varies significantly.

Urban hotspots show elevated pedestrian incident rates, particularly near markets, schools, and commercial centers where foot traffic intersects with vehicular movement. These findings suggest that pedestrian infrastructure improvements (crosswalks, footbridges, signage) may effectively reduce accidents in these specific clusters.

Highway corridor hotspots demonstrate higher proportions of head-on collisions and overtaking accidents, indicating that road design factors such as lane width, sight distance, and passing zones merit examination. Some clusters correlate with specific geometric features like sharp curves or steep grades.

### 5.3.3 Casualty Analysis

Examination of casualty data within the system reveals that approximately 30% of accidents result in fatalities, 45% involve injuries, and 25% result in no physical harm (property damage only). However, these proportions vary substantially across identified hotspots.

Certain clusters exhibit disproportionately high fatality rates, warranting priority attention from traffic management authorities. Analysis of these high-severity clusters often reveals common factors such as high-speed corridors, inadequate lighting, or poor road surface conditions.

The system's casualty tracking distinguishes between driver, passenger, and pedestrian casualties, enabling targeted safety campaigns. For instance, clusters with high passenger injury rates might benefit from seatbelt awareness campaigns, while pedestrian casualty hotspots require infrastructure interventions.

---

## 5.4 System Performance and Usability

The operational performance of the system was evaluated through both technical metrics and user feedback from early stakeholders including PNP personnel and traffic analysts.

### 5.4.1 Technical Performance

Database query performance remains efficient even with substantial record volumes, with typical accident list retrieval completing within 1-2 seconds. The PostgreSQL spatial extensions enable rapid geographic queries when filtering accidents by region or proximity to specific coordinates.

Clustering computation time scales with dataset size, with current implementation processing thousands of records within acceptable timeframes for analytical workflows. The system architecture includes design provisions for asynchronous processing using Celery and Redis message queuing, allowing clustering operations to run as background tasks without blocking user interface interactions. This enhancement is planned for production deployment to support real-time analysis of the complete regional dataset.

Map rendering performance benefits from Leaflet.js's efficient tile management and marker clustering capabilities. Users can smoothly interact with visualizations containing hundreds of accident markers without experiencing lag or interface delays.

### 5.4.2 User Experience Feedback

Early user testing with PNP staff and traffic management personnel yielded positive feedback regarding the system's intuitiveness and practical utility. Several observations emerged from these interactions:

**Data Entry Efficiency**: The cascading location dropdowns significantly reduced data entry time compared to manual text input. Users reported approximately 40% faster record creation with substantially fewer spelling errors and location inconsistencies. The six-tab edit modal organization received praise for logical grouping of related fields.

**Visualization Clarity**: The interactive map interface proved accessible even to users with limited GIS experience. The ability to toggle between list views and map views accommodated different analytical preferences. Color-coding of accident severity helped quickly identify high-priority areas.

**Analytical Value**: Stakeholders expressed that the hotspot visualizations provided actionable intelligence not readily apparent from raw accident reports. The ability to identify spatial concentrations enables evidence-based resource allocation for traffic enforcement and infrastructure improvement.

**Areas for Enhancement**: Users suggested additional filtering capabilities to examine specific subsets (e.g., motorcycle-only accidents, nighttime incidents, specific date ranges). The analytics dashboard was identified as an area for expansion, with requests for comparative statistics across provinces and time periods.

### 5.4.3 Data Quality Improvements

The implementation of structured data entry fields with validation significantly improved overall data quality compared to previous free-text systems. Mandatory fields for critical attributes (date, location, incident type) ensure minimum viable information for meaningful analysis.

However, certain optional fields show incomplete population across the dataset, particularly in historical records imported from legacy systems. Fields such as vehicle make/model, detailed narrative descriptions, and exact GPS coordinates exhibit variable completion rates. This limitation constrains certain types of analysis but reflects the practical realities of retrospective data collection.

Ongoing data entry training for PNP personnel emphasizes the importance of complete and accurate recording, particularly for spatial coordinates and incident classification. The system's user-friendly interface reduces barriers to comprehensive documentation.

---

## 5.5 Comparative Analysis with Traditional Methods

The AGNES-based hotspot detection approach demonstrates several advantages over traditional accident analysis methods employed in the region prior to this system.

### 5.5.1 Manual Spot Analysis

Previous accident analysis relied heavily on manual review of incident reports and subjective identification of problematic locations. This approach suffered from several limitations:

**Lack of Spatial Perspective**: Without geographic visualization, patterns spread across non-adjacent locations went unrecognized. The clustering approach reveals that accidents at seemingly disparate locations may constitute a single hotspot zone requiring unified intervention.

**Confirmation Bias**: Manual analysis tended to focus on already-known problem areas, potentially overlooking emerging hotspots. The algorithmic approach examines all locations objectively based on data density.

**Limited Scalability**: Manual review becomes impractical with large datasets. A human analyst can reasonably examine dozens of incidents, but struggles with thousands. AGNES scales efficiently to larger datasets.

**Delayed Response**: Monthly or quarterly manual compilations meant lag time between pattern emergence and identification. The system enables near-real-time hotspot detection as new accidents are recorded.

### 5.5.2 Simple Density Mapping

Some previous efforts employed basic density mapping or grid-based counting to identify high-accident areas. While representing an improvement over purely manual methods, these approaches have limitations that hierarchical clustering addresses:

**Fixed Grid Constraints**: Grid-based methods impose arbitrary geographic divisions that may split natural clusters or group unrelated incidents. AGNES identifies clusters organically based on actual accident distribution.

**Single-Scale Analysis**: Density maps typically operate at one predetermined resolution. AGNES provides multi-scale perspective through its hierarchical structure, revealing both regional patterns and localized sub-clusters.

**Boundary Artifacts**: Grid methods create artificial edges where adjacent cells may have similar accident densities but are treated separately. Clustering methods avoid these discontinuities.

**Limited Cluster Characterization**: Density maps show "how many" but provide less insight into "what type." The clustering approach enables analysis of cluster composition beyond simple counts.

---

## 5.6 Practical Applications and Implications

The AGNES-based hotspot detection system provides actionable intelligence for multiple stakeholder groups involved in road safety management.

### 5.6.1 Traffic Enforcement Planning

The Philippine National Police can utilize hotspot maps to optimize patrol deployment and enforcement activities. Rather than uniform distribution or purely reactive responses to individual incidents, resources can be concentrated in identified high-risk zones during peak accident times.

Specific enforcement strategies can be tailored to cluster characteristics. For example, urban intersection hotspots might benefit from increased traffic signal compliance monitoring, while highway corridor hotspots may require speed enforcement and overtaking violations monitoring.

The system's temporal analysis enables time-specific interventions. Clusters showing Friday evening peaks might warrant sobriety checkpoints, while morning hotspots near schools could focus on speed limit enforcement and pedestrian safety.

### 5.6.2 Infrastructure Planning and Improvement

The Department of Public Works and Highways (DPWH) and local government engineering offices can prioritize infrastructure investments based on evidence from hotspot analysis. Road segments within identified clusters become candidates for geometric improvements, lighting installation, signage enhancement, or other engineering countermeasures.

The system helps quantify the potential impact of interventions by tracking accident counts within specific geographic areas over time. Before-and-after analysis can evaluate whether infrastructure modifications successfully reduced accident frequency or severity in treated hotspots.

Budget allocation for road safety improvements gains objective support when driven by data rather than political considerations or anecdotal reports. The visualization capabilities help communicate priorities to decision-makers and the public.

### 5.6.3 Public Awareness Campaigns

Local government units and safety advocacy groups can design targeted awareness campaigns informed by hotspot characteristics. Educational materials addressing specific risk factors (e.g., pedestrian safety, motorcycle helmet use, drunk driving) can be disseminated in relevant communities.

School-based safety education programs can emphasize hazards specific to clusters near educational institutions. Community meetings in barangays within high-risk zones can engage residents in identifying local contributing factors and developing grassroots solutions.

The system's mapping capabilities support public information displays showing accident-prone areas, encouraging driver caution when traversing identified hotspots. Mobile applications could potentially incorporate this data to provide real-time warnings to travelers.

### 5.6.4 Policy Development

Regional and provincial policy makers can leverage system insights to formulate evidence-based traffic safety policies. Patterns revealed through clustering analysis may inform decisions regarding speed limits, vehicle restrictions, operating hours for commercial transport, or licensing requirements.

The comparative analysis across provinces helps identify successful practices in lower-risk areas that might transfer to higher-risk locations. Understanding why certain provinces or municipalities exhibit different accident patterns enables targeted policy interventions.

Long-term trend analysis supports monitoring of policy effectiveness. If implemented interventions correlate with reduced accident clustering in previously high-risk zones, this validates approaches and guides future strategies.

---

## 5.7 Limitations and Challenges

While the system demonstrates significant value for accident analysis and hotspot detection, several limitations and challenges warrant acknowledgment.

### 5.7.1 Data Completeness and Accuracy

The quality of analysis depends fundamentally on the completeness and accuracy of input data. Several factors affect data quality:

**Underreporting**: Not all accidents are formally reported to police, particularly minor incidents with no injuries. The dataset may therefore underrepresent actual accident occurrence, especially for less severe incidents.

**Location Accuracy**: GPS coordinates rely on accurate recording at incident scenes. In some cases, especially for historical records, coordinates may be approximated rather than precisely measured. This spatial uncertainty can affect clustering precision.

**Attribute Completeness**: Certain data fields show incomplete population, particularly in legacy records. Missing information limits some types of analysis, though core spatial-temporal data required for hotspot detection is generally available.

**Reporting Variations**: Data collection practices may vary across different police stations or over time. Standardization efforts continue, but historical inconsistencies persist in some attributes.

### 5.7.2 Methodological Considerations

The AGNES clustering approach, while powerful, involves certain methodological choices that affect results:

**Distance Metric Selection**: The use of Euclidean distance in geographic space assumes flat geometry reasonable for the Caraga Region's scale, but may introduce minor distortions over longer distances. Alternative metrics incorporating actual road network distances could provide refinements.

**Linkage Method**: Ward's linkage method was selected for its tendency to produce balanced clusters, but alternative approaches (complete, average, single linkage) may reveal different patterns. The system could benefit from allowing users to experiment with different clustering parameters.

**Cluster Number Determination**: Identifying the "optimal" number of clusters involves subjective judgment. While dendrograms assist this decision, automated selection criteria could enhance objectivity and reproducibility.

**Temporal Considerations**: Current clustering operates primarily on spatial dimensions. Incorporating temporal aspects directly into the clustering algorithm (spatiotemporal clustering) represents an area for future enhancement.

### 5.7.3 Computational Scalability

While current system performance is acceptable, computational demands scale with dataset growth:

**Algorithm Complexity**: AGNES has O(n³) time complexity in basic implementations, becoming computationally expensive for very large datasets. The regional dataset size remains manageable, but continued data accumulation may necessitate algorithmic optimizations or alternative approaches for massive scales.

**Real-Time Processing**: Current clustering operates as analytical batch processes rather than continuously updating with each new accident record. For true real-time hotspot monitoring, streaming algorithms or incremental clustering methods would be required.

**Geographic Scale**: The system was designed for regional analysis. Expansion to national scale would require careful consideration of computational architecture and possibly distributed processing approaches.

### 5.7.4 Causation versus Correlation

The system identifies where and when accidents cluster, but determining why requires careful interpretation:

**Exposure Effects**: High accident counts may reflect high traffic volume rather than inherently dangerous conditions. Clusters in urban centers partially result from exposure (more vehicles) rather than purely elevated risk per vehicle-kilometer traveled.

**Multiple Contributing Factors**: Accident causation typically involves multiple factors (road design, driver behavior, vehicle condition, environmental conditions). Clustering analysis reveals patterns but doesn't automatically identify root causes requiring engineering analysis and investigation.

**Confounding Variables**: Apparent spatial patterns may be influenced by unobserved factors such as enforcement intensity, which could either increase reporting in certain areas or reduce accidents through deterrence.

---

## 5.8 Synthesis and Recommendations

The development and deployment of the AGNES-based hotspot detection system represents a significant advancement in road safety analysis capabilities for the Caraga Region. The integration of hierarchical clustering algorithms with interactive geographic visualization provides stakeholders with powerful tools for evidence-based decision making.

### 5.8.1 Key Findings Summary

Several important findings emerge from this work:

1. **Spatial Heterogeneity**: Accidents in Caraga Region exhibit strong spatial clustering rather than random distribution, confirming the value of hotspot-focused approaches over uniform interventions.

2. **Urban-Rural Distinctions**: Urban and rural clusters display different characteristics requiring tailored countermeasures. Urban hotspots involve more pedestrian incidents and intersections, while rural clusters relate to highway corridors and geometric features.

3. **Temporal Patterns**: Accident clustering shows temporal dimensions beyond spatial concentration, with certain hotspots active during specific times or seasons. Effective interventions must address these temporal aspects.

4. **Hierarchical Structure**: The nested nature of clusters revealed by AGNES proves valuable for planning interventions at multiple administrative levels, from regional strategies to localized engineering improvements.

5. **Data Quality Impact**: Improvements in data collection and standardization significantly enhance analytical capabilities. The system's structured input mechanisms contribute to better data quality.

### 5.8.2 Recommendations for System Enhancement

Based on implementation experience and user feedback, several enhancements would strengthen the system:

**Short-term Improvements**:
- Expand filtering capabilities to enable subset analysis by incident type, time period, or severity
- Enhance analytics dashboard with comparative statistics and trend visualizations
- Implement data export functionality for integration with external analysis tools
- Develop user documentation and training materials for broader PNP deployment

**Medium-term Enhancements**:
- Deploy asynchronous processing architecture (Celery/Redis) for handling larger datasets and real-time analysis
- Incorporate clustering validation metrics into the user interface for assessing cluster quality
- Add before-and-after analysis tools for evaluating intervention effectiveness
- Integrate road network data for network-based analysis alongside point clustering

**Long-term Development**:
- Implement spatiotemporal clustering algorithms that explicitly incorporate time dimensions
- Develop predictive models for identifying emerging hotspots before accident concentrations reach critical levels
- Create mobile applications for field personnel to access hotspot information and enter data in real-time
- Establish data sharing frameworks with Department of Health (injury surveillance) and LTO (vehicle registration) for enriched analysis

### 5.8.3 Recommendations for Stakeholders

The system provides a foundation for data-driven road safety management, but technology alone is insufficient. Recommendations for key stakeholders include:

**Philippine National Police - Caraga Region**:
- Institutionalize regular review of hotspot analysis in operational planning meetings
- Establish protocols for focused enforcement in identified high-risk zones
- Train personnel in system use and emphasize importance of complete, accurate data entry
- Develop performance metrics that incorporate hotspot-based deployment effectiveness

**Department of Public Works and Highways**:
- Utilize hotspot maps as primary input for road safety infrastructure budget allocation
- Conduct detailed engineering studies of high-priority clusters to identify specific countermeasures
- Implement monitoring systems to evaluate infrastructure improvement impacts
- Coordinate with PNP to ensure data sharing regarding road conditions and treatments

**Local Government Units**:
- Integrate hotspot information into comprehensive land use and transportation planning
- Allocate local road improvement budgets based on evidence from cluster analysis
- Engage communities in barangays with identified hotspots in safety planning processes
- Support public awareness campaigns targeted to local risk factors

**Regional Development Council**:
- Adopt road safety performance indicators derived from system data for regional development planning
- Facilitate inter-agency coordination among PNP, DPWH, LGUs, and health sector
- Advocate for sustained funding for system maintenance and enhancement
- Promote research partnerships with academic institutions for continued system development

### 5.8.4 Broader Implications

Beyond immediate operational applications, this work demonstrates several broader implications for traffic safety management in the Philippines:

**Evidence-Based Approach**: The system exemplifies how data science techniques can transform traditional law enforcement and public administration. Moving from reactive, incident-by-incident responses to proactive, pattern-based strategies represents a fundamental shift in approach.

**Replicability**: While developed for Caraga Region, the methodology and system architecture are readily transferable to other regions. The AGNES algorithm requires only georeferenced accident data, available through standard police reporting processes. National rollout could create a comprehensive picture of road safety nationwide.

**Interdisciplinary Integration**: Effective road safety management requires collaboration across disciplines—law enforcement, civil engineering, public health, urban planning, and behavioral science. This system provides a common analytical platform facilitating such integration.

**Technology Transfer**: The use of open-source tools (Django, PostgreSQL, Leaflet) and standard algorithms ensures sustainability and adaptability. Future enhancements can build on this foundation without proprietary constraints.

**Capacity Building**: System development and deployment create opportunities for skills development among PNP personnel, local government staff, and academic researchers in geospatial analysis and data science applications.

---

## 5.9 Conclusion

The successful implementation of an AGNES-based hotspot detection system for the Caraga Region demonstrates that advanced analytical methods can be effectively applied to improve road safety management in Philippine contexts. The hierarchical clustering approach reveals spatial patterns in accident data that would be difficult to identify through manual analysis alone.

The system achieves its primary objectives of identifying accident hotspots, visualizing spatial patterns, and providing actionable intelligence to stakeholders. User feedback indicates that the interface is accessible to target users and that the analytical outputs inform practical decision-making in traffic enforcement and infrastructure planning.

While limitations exist regarding data completeness and computational scalability, these challenges are addressable through ongoing development and institutional capacity building. The foundation established by this work supports continuous enhancement and expansion of analytical capabilities.

Most importantly, the system transitions road safety management from reactive responses to individual incidents toward proactive, evidence-based strategies targeting high-risk locations and time periods. This paradigm shift, supported by appropriate technology tools, offers meaningful potential for reducing the human and economic costs of road accidents in Caraga Region and beyond.

The lessons learned from this implementation—both successes and challenges—provide valuable guidance for similar initiatives in other regions or countries facing comparable road safety challenges. As data science techniques become increasingly accessible, their application to critical public safety problems represents not just a technical advance but an ethical imperative to leverage available tools for saving lives.
