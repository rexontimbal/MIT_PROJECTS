# AGNES Role-Based Permissions Guide

## Overview

AGNES implements a hierarchical role-based access control (RBAC) system that aligns with the Philippine National Police (PNP) organizational structure. This guide documents all roles, their permissions, and use cases.

---

## Role Hierarchy

```
Super Admin (System Administrator)
    ↓
Regional Director (PRO 13 Caraga)
    ↓
Provincial Chief (Provincial/City Directors)
    ↓
Station Commander (Municipal/City Police Stations)
    ↓
Traffic Officer / Data Encoder (Field Personnel)
```

---

## Complete Permission Matrix

| Permission | Super Admin | Regional Director | Provincial Chief | Station Commander | Traffic Officer | Data Encoder |
|-----------|-------------|-------------------|------------------|-------------------|-----------------|--------------|
| **Accident Data** |
| view | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| add | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| edit | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| delete | ✅ | ❌ | ✅ (province) | ❌ | ❌ | ❌ |
| **User Management** |
| manage_users | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| delete_users | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| assign_jurisdiction | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Analytics** |
| run_clustering | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| generate_reports | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| **Data Scope** |
| view_all_data | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| view_province_data | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| view_station_data | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| view_own_data | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **System** |
| view_audit_logs | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| system_config | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| verify_reports | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |

---

## Role Details

### 1. Super Admin (System Administrator)

**Purpose**: Technical system management and oversight

**Who Gets This Role**:
- System administrators
- IT personnel managing AGNES
- Executive officers overseeing the system
- **Recommended: 1-2 accounts only**

**Full Permissions**:
- ✅ View all data (entire region)
- ✅ Add/edit/delete accidents
- ✅ Create, edit, activate/deactivate users
- ✅ Delete user accounts permanently
- ✅ Assign users to provinces/stations
- ✅ Run clustering algorithms
- ✅ Generate and export all reports
- ✅ View complete audit logs
- ✅ Change system configuration
- ✅ Verify citizen reports
- ✅ Access Django admin panel
- ✅ Access admin panel features

**Use Cases**:
- System maintenance and configuration
- Creating initial user accounts
- Troubleshooting technical issues
- Generating region-wide reports for PNP HQ
- Managing system settings

---

### 2. Regional Director (PRO 13 Caraga)

**Purpose**: Overall command and supervision of Caraga region

**Who Gets This Role**:
- Regional Director of PRO 13
- Deputy Regional Director for Operations
- Deputy Regional Director for Administration
- **Recommended: 2-3 accounts**

**Current Position**: PBGen Marcial Mariano P. Magistrado IV (as of 2025)

**Full Permissions**:
- ✅ View all data (entire Caraga region)
- ✅ Add/edit accidents (no delete - requires super_admin)
- ✅ Create, edit, activate/deactivate users region-wide
- ✅ Assign users to provinces/stations
- ✅ Run clustering algorithms
- ✅ Generate and export reports
- ✅ View audit logs
- ✅ Verify citizen reports
- ✅ Access admin panel

**Restrictions**:
- ❌ Cannot delete accidents (requires super_admin approval)
- ❌ Cannot delete users permanently
- ❌ Cannot change system configuration

**Use Cases**:
- Monitor accident trends across entire region
- Create accounts for new provincial directors
- Generate monthly/quarterly reports for PNP National HQ
- Run clustering to identify regional hotspots
- Allocate resources across provinces
- Review audit logs for security
- Oversee all provincial operations

---

### 3. Provincial Chief (Provincial/City Director)

**Purpose**: Command and manage provincial/city police operations

**Who Gets This Role**:
- Provincial Directors (Agusan del Norte, Agusan del Sur, Surigao del Norte, Surigao del Sur, Dinagat Islands)
- City Directors (Butuan City)
- **Recommended: 5-6 accounts for Caraga**

**Full Permissions**:
- ✅ View data within assigned province
- ✅ Add/edit accidents in province
- ✅ Delete accidents in province (with approval process)
- ✅ Create, edit, activate/deactivate users in province
- ✅ Run clustering for province
- ✅ Generate provincial reports
- ✅ View provincial audit logs
- ✅ Verify citizen reports
- ✅ Access admin panel

**Restrictions**:
- ❌ Cannot view other provinces' data
- ❌ Cannot delete users permanently
- ❌ Cannot assign jurisdiction
- ❌ Cannot change system configuration

**Use Cases**:
- Monitor accidents within their province
- Create accounts for station commanders
- Coordinate with municipal stations
- Allocate resources to identified hotspots
- Generate provincial reports for Regional Director
- Manage provincial-level clustering
- Supervise station-level operations

---

### 4. Station Commander (Chief of Police)

**Purpose**: Direct command of municipal/city police station

**Who Gets This Role**:
- Chiefs of Police (Municipal Stations)
- Chiefs of Police (City Stations)
- Precinct Commanders
- **Recommended: ~50-100 accounts across Caraga**

**Full Permissions**:
- ✅ View data within assigned station
- ✅ Add/edit accidents in station
- ✅ Create, edit, activate/deactivate officers at station
- ✅ Generate station reports
- ✅ Verify citizen reports
- ✅ Access admin panel

**Restrictions**:
- ❌ Cannot delete accidents (requires provincial approval)
- ❌ Cannot run clustering
- ❌ Cannot view other stations' data
- ❌ Cannot view audit logs
- ❌ Cannot assign jurisdiction

**Use Cases**:
- Log accidents in their jurisdiction
- Create accounts for traffic officers
- Monitor hotspots within station area
- Coordinate patrols based on data
- Submit reports to Provincial Director
- Verify citizen-submitted accident reports
- Manage station-level personnel

---

### 5. Traffic Officer (Field Personnel)

**Purpose**: Frontline officers handling accident reports at the scene

**Who Gets This Role**:
- Traffic Enforcers
- Patrolmen assigned to accident investigation
- Highway Patrol personnel
- Field officers
- **Recommended: ~200-500 accounts across Caraga**

**Full Permissions**:
- ✅ View own created reports
- ✅ Add new accident reports (primary job)

**Restrictions**:
- ❌ Cannot edit accidents (requires approval)
- ❌ Cannot delete accidents
- ❌ Cannot manage users
- ❌ Cannot run clustering
- ❌ Cannot generate reports
- ❌ Cannot view other officers' data

**Use Cases**:
- Log accidents immediately at the scene
- Fill in accident details (location, casualties, vehicles)
- Upload photos from the scene
- Input basic data for later analysis
- Submit reports to station commander
- View their own submitted reports

**Typical Workflow**:
1. Respond to accident scene
2. Log accident in AGNES via mobile device
3. Upload photos (up to 3)
4. Submit report to station commander
5. Station commander reviews and approves

---

### 6. Data Encoder (Civilian/Administrative Personnel)

**Purpose**: Input and verify accident data from paper reports

**Who Gets This Role**:
- Civilian employees at stations/headquarters
- Administrative staff
- Records management personnel
- Non-uniformed personnel
- **Recommended: ~20-50 accounts across Caraga**

**Full Permissions**:
- ✅ View all data (read-only, for verification)
- ✅ Add accidents from paper forms

**Restrictions**:
- ❌ Cannot edit accidents (limited)
- ❌ Cannot delete accidents
- ❌ Cannot manage users
- ❌ Cannot run clustering
- ❌ Cannot generate reports
- ❌ Cannot verify reports

**Use Cases**:
- Encode handwritten accident reports into AGNES
- Backlog data entry from paper forms
- Verify and clean historical data
- Support officers with data entry
- Input data from other sources

**Typical Workflow**:
1. Receive paper accident report
2. Input data into AGNES
3. Verify accuracy with original document
4. Flag any discrepancies to supervisor

---

## Permission Definitions

### Accident Data Permissions

- **view**: Can view accident records
- **add**: Can create new accident reports
- **edit**: Can modify existing accident data
- **delete**: Can delete accident records (with approval workflow)

### User Management Permissions

- **manage_users**: Can create, edit, activate/deactivate user accounts within jurisdiction
- **delete_users**: Can permanently delete user accounts (super_admin only)
- **assign_jurisdiction**: Can assign users to provinces/stations (super_admin, regional_director)

### Analytics Permissions

- **run_clustering**: Can execute AGNES clustering algorithm to identify hotspots
- **generate_reports**: Can generate and export reports (Excel, PDF, CSV)

### Data Scope Permissions

- **view_all_data**: Can view data across entire Caraga region
- **view_province_data**: Can view data within assigned province only
- **view_station_data**: Can view data within assigned station only
- **view_own_data**: Can only view own created records

### System Permissions

- **view_audit_logs**: Can view system audit trail
- **system_config**: Can change system configuration settings
- **verify_reports**: Can verify citizen-submitted accident reports

---

## Jurisdiction-Based Access Control

In addition to role permissions, AGNES implements jurisdiction-based data filtering:

### Super Admin
- **Scope**: Entire system
- **Can view**: All provinces, all stations, all data

### Regional Director
- **Scope**: Caraga Region (PRO 13)
- **Can view**: All provinces within Caraga
  - Agusan del Norte
  - Agusan del Sur
  - Surigao del Norte
  - Surigao del Sur
  - Dinagat Islands
  - Butuan City

### Provincial Chief
- **Scope**: Assigned province only
- **Example**: Director of Agusan del Norte can only view Agusan del Norte data
- **Cannot view**: Other provinces

### Station Commander
- **Scope**: Assigned station only
- **Example**: Chief of Butuan City Station 1 can only view Station 1 data
- **Cannot view**: Other stations, even within same province

### Traffic Officer
- **Scope**: Own created records only
- **Cannot view**: Records created by other officers

### Data Encoder
- **Scope**: All data (for verification purposes)
- **Special**: Read-only access to all data for accurate data entry

---

## Real-World Workflow Example

**Scenario**: Vehicular accident in Butuan City

```
1. Traffic Officer Juan responds to scene
   ↓
   • Logs accident in AGNES via mobile app
   • Uploads 3 photos
   • Submits report

2. Station Commander (Butuan Station 1) reviews
   ↓
   • Receives notification
   • Reviews report for accuracy
   • Approves report (or sends back for correction)

3. City Director (Butuan) monitors
   ↓
   • Sees accident added to city statistics
   • Notes increase in accidents at that intersection
   • Requests clustering analysis

4. Provincial Director (Agusan del Norte) analyzes
   ↓
   • Runs clustering for the province
   • Identifies hotspot at intersection
   • Allocates additional traffic enforcers

5. Regional Director reviews monthly
   ↓
   • Runs region-wide clustering
   • Generates report for PNP National HQ
   • Identifies budget needs for hotspot areas

6. Data Encoder backfills historical data
   ↓
   • Encodes 2024 paper reports
   • Adds missing data for trend analysis
```

---

## Account Distribution (Recommended for PRO 13 Caraga)

| Role | Recommended Accounts | Rationale |
|------|---------------------|-----------|
| Super Admin | 1-2 | IT/System administrators only |
| Regional Director | 2-3 | Regional Director + 2 Deputy Directors |
| Provincial Chief | 5-6 | 5 provinces + 1 city |
| Station Commander | 50-100 | All municipal/city stations |
| Traffic Officer | 200-500 | Field personnel |
| Data Encoder | 20-50 | Administrative staff |
| **TOTAL** | **~280-660** | For entire Caraga region |

---

## Security Notes

1. **Principle of Least Privilege**: Users are assigned the minimum permissions needed for their job
2. **Hierarchical Access**: Higher roles can view subordinate data
3. **Audit Trail**: All actions are logged with user, timestamp, IP address
4. **Account Locking**: 5 failed login attempts = 30-minute lockout
5. **Password Requirements**: Minimum 8 characters, must include uppercase, lowercase, number, special character
6. **Session Management**: 24-hour session timeout, can be extended with "Remember Me"

---

## Implementation Details

### Code Location
- **Permission Model**: `accidents/models.py` (UserProfile.has_permission)
- **Template Restriction**: `templates/admin_panel/base.html`
- **View Decorators**: `accidents/auth_utils.py` (role_required, permission_required)

### Checking Permissions in Code

```python
# Check if user has permission
if request.user.profile.has_permission('manage_users'):
    # Allow user management

# Check jurisdiction-based access
if request.user.profile.can_view_accident(accident):
    # Allow viewing accident

# Role-based view restriction
@role_required('super_admin', 'regional_director')
def admin_dashboard(request):
    # Only super_admin and regional_director can access
```

---

## Future Enhancements

### Planned Improvements
1. **Deputy Regional Director** role (separate from Regional Director)
2. **Investigation Officer** role (between Traffic Officer and Station Commander)
3. **Granular edit permissions** (e.g., can edit basic info but not casualties)
4. **Time-based permissions** (e.g., clustering only during business hours)
5. **Approval workflows** for sensitive operations (delete, user creation)

---

## Support

For questions about role assignments or permissions, contact:
- **System Administrator**: AGNES Super Admin
- **Technical Support**: PRO 13 IT Division
- **Policy Questions**: PRO 13 Regional Director's Office

---

*Last Updated: January 2025*
*AGNES Version: 1.0*
*PNP Police Regional Office 13 (PRO 13) - Caraga*
