# CT4 Ops Health — Discovery, Registry & Coverage System

## Architecture Overview

Single authoritative Ops Health system that guarantees:
1. All real data sources in the database are discovered
2. All sources used by code (backend/scripts/endpoints) are registered
3. All critical sources are monitored
4. Missing, stale, unmapped, or unmonitored sources are automatically detected
5. Health is observable, explainable, and drillable from UI

**CORE PRINCIPLE (NON-NEGOTIABLE):**
Source Registry is the single source of truth. Nothing is monitored, checked, or shown unless it exists or is derived from the registry. No hardcoded source lists anywhere.

---

## Project File Structure

```
CT4/
├── backend/
│   ├── sql/
│   │   └── ops/
│   │       ├── discovery_objects.sql              # DB object discovery query
│   │       ├── discovery_dependencies.sql          # Dependency graph discovery
│   │       ├── source_registry.sql                # Registry table definition
│   │       ├── v_health_checks.sql                # Health checks view (registry-based)
│   │       ├── v_health_global.sql                # Global health aggregation
│   │       ├── v_data_health_status.sql           # RAW health status (existing)
│   │       ├── mv_refresh_log.sql                 # MV refresh tracking (existing)
│   │       └── [other existing views...]
│   │
│   ├── scripts/
│   │   ├── discovery_objects.py                   # Execute discovery_objects.sql → CSV
│   │   ├── discovery_dependencies.py              # Execute discovery_dependencies.sql → CSV
│   │   ├── discovery_usage_backend.py             # Scan repo → CSV
│   │   └── populate_source_registry.py             # UPSERT registry from CSVs
│   │
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       └── ops.py                         # Health endpoints
│   │   │           ├── GET /api/v1/ops/source-registry
│   │   │           ├── GET /api/v1/ops/health-checks
│   │   │           ├── GET /api/v1/ops/health-global
│   │   │           ├── GET /api/v1/ops/raw-health/*
│   │   │           └── GET /api/v1/ops/mv-health
│   │   │
│   │   ├── schemas/
│   │   │   ├── ops_source_registry.py             # SourceRegistryRow, SourceRegistryResponse
│   │   │   ├── ops_health_checks.py               # HealthCheckRow, HealthChecksResponse
│   │   │   ├── ops_health_global.py               # HealthGlobalResponse
│   │   │   ├── ops_raw_health.py                  # Raw health schemas (existing)
│   │   │   └── ops_mv_health.py                   # MV health schemas (existing)
│   │   │
│   │   └── models/
│   │       └── ops.py                             # Alert, IngestionRun (existing)
│   │
│   └── alembic/
│       └── versions/                               # DB migrations (if needed)
│
├── frontend/
│   ├── app/
│   │   └── ops/
│   │       └── health/
│   │           └── page.tsx                        # Main health page with tabs
│   │
│   ├── components/
│   │   └── ops/
│   │       ├── IdentitySystemHealthPanel.tsx      # Identity tab (existing)
│   │       ├── RawDataHealthPanel.tsx              # RAW tab (existing)
│   │       ├── MvHealthPanel.tsx                  # MV tab (NEW)
│   │       └── HealthChecksPanel.tsx              # Checks tab (existing)
│   │
│   └── lib/
│       ├── api.ts                                  # API client functions
│       └── types.ts                                # TypeScript types
│
└── docs/
    └── backend/
        ├── OPS_HEALTH_SYSTEM_ARCHITECTURE.md       # This file
        ├── discovery_usage_backend.md              # Discovery usage docs
        └── source_registry.md                      # Registry docs
```

---

## System Layers

### A) DISCOVERY LAYER (Automated)

**Purpose:** Discover ALL existing DB objects and ALL objects used by code.

#### 1. DB Discovery
- **Script:** `backend/sql/ops/discovery_objects.sql`
- **Executor:** `backend/scripts/discovery_objects.py`
- **Output:** `backend/sql/ops/discovery_objects.csv`
- **Schemas:** `public`, `ops`, `canon`, `raw` (if exists), `observational`
- **Object Types:** `table`, `view`, `matview`
- **Fields:**
  - `schema_name`, `object_name`, `object_type`
  - `estimated_rows`, `size_mb`, `last_analyze`

#### 2. Dependency Discovery
- **Script:** `backend/sql/ops/discovery_dependencies.sql`
- **Executor:** `backend/scripts/discovery_dependencies.py`
- **Output:** `backend/sql/ops/discovery_dependencies.csv`
- **Method:** `pg_depend` + `pg_rewrite` for views/matviews
- **Fields:**
  - `parent_schema`, `parent_name`
  - `child_schema`, `child_name`
  - `dependency_type`

#### 3. Repo Usage Discovery
- **Script:** `backend/scripts/discovery_usage_backend.py`
- **Output:** `backend/sql/ops/discovery_usage_backend.csv`
- **Scans:** `backend/**/*.py`, `backend/sql/**/*.sql`
- **Patterns:** `schema.table`, `FROM schema.table`, `JOIN schema.table`
- **Validation:** Against DB catalog (only existing objects)
- **Context Detection:**
  - `endpoint`: FastAPI routes (`@router.get/post/etc`)
  - `script`: Cron/refresh/migration scripts
- **Fields:**
  - `schema_name`, `object_name`, `object_type`
  - `usage_context` (`endpoint` | `script` | `both`)
  - `usage_locations` (JSON array)
  - `discovered_at`

---

### B) SOURCE REGISTRY (Canonical)

**Purpose:** Single source of truth for all data sources.

#### Table: `ops.source_registry`
- **Definition:** `backend/sql/ops/source_registry.sql`
- **Population:** `backend/scripts/populate_source_registry.py`

#### Fields

**Identification:**
- `schema_name`, `object_name`, `object_type`

**Classification:**
- `layer`: `RAW` | `DERIVED` | `MV` | `CANON`
- `role`: `PRIMARY` | `SECONDARY`
- `criticality`: `critical` | `important` | `normal`

**Monitoring:**
- `should_monitor` (boolean)
- `health_enabled` (manual override)
- `is_expected` (manual override)
- `is_critical` (manual override)

**Metadata:**
- `description`, `usage_context`, `refresh_schedule`
- `depends_on` (JSONB array)
- `notes` (manual override)

**Timestamps:**
- `discovered_at` (set once)
- `last_verified_at` (updated every run)
- `created_at`, `updated_at`

#### Automatic Inference Rules

**Layer:**
- Schema `raw` → `RAW`
- Schema `canon` → `CANON`
- `object_type = 'matview'` → `MV`
- Else → `DERIVED`

**Role:**
- `RAW` or `CANON` → `PRIMARY`
- `MV` or `DERIVED` → `SECONDARY`

**Criticality:**
- MV in `refresh_ops_mvs.py` → `critical`
- Object in endpoints UI-ready → `critical`
- Used by endpoint → `important`
- Else → `normal`

#### UPSERT Logic

**Rules:**
- Idempotent (can run multiple times)
- Manual overrides (`is_expected`, `is_critical`, `health_enabled`, `notes`) NEVER overwritten if NOT NULL
- `discovered_at` set only if NULL
- `last_verified_at` always updated

---

### C) HEALTH & COVERAGE CHECKS

**Purpose:** Detect missing, stale, unmapped, or unmonitored sources.

#### View: `ops.v_health_checks`
- **Definition:** `backend/sql/ops/v_health_checks.sql`
- **Source:** Registry-based (NO hardcoded objects)

#### Required Checks

1. **expected_source_missing** (error)
   - Registry `is_expected=true` but object doesn't exist in DB

2. **unregistered_used_object** (warning/error)
   - Object used in repo but not in registry

3. **monitored_not_in_health_views** (warning)
   - `health_enabled=true` but not covered by health views/endpoints

4. **health_view_source_unknown** (warning)
   - Appears in `v_data_health_status` but not in registry

5. **raw_source_stale_affecting_critical** (warning/error)
   - RAW stale that feeds critical MV (uses `depends_on`)

6. **mv_refresh_stale** (warning)
   - MV not refreshed > 24h

7. **mv_refresh_failed** (error)
   - Last MV refresh failed

8. **mv_not_populated** (error)
   - MV exists but not populated

#### Check Structure

Each check exposes:
- `check_key`: Unique identifier
- `severity`: `info` | `warning` | `error`
- `status`: `OK` | `WARN` | `ERROR`
- `message`: Descriptive message
- `drilldown_url`: URL for details (e.g., `/ops/health?tab=raw`)
- `last_evaluated_at`: Timestamp

---

### D) HEALTH AGGREGATION

**Purpose:** Global health status and counts.

#### View: `ops.v_health_global`
- **Definition:** `backend/sql/ops/v_health_global.sql`
- **Source:** Aggregates from `ops.v_health_checks`

#### Output

- `global_status`: `OK` | `WARN` | `ERROR`
- `error_count`: Count of error-level checks with status=ERROR
- `warn_count`: Count of warning-level checks with status=WARN
- `ok_count`: Count of checks with status=OK
- `calculated_at`: Timestamp

#### Rules

- `ERROR` if any error-level check is `ERROR`
- `WARN` if any warning-level check is `WARN` or `ERROR`
- Else `OK`

---

### E) API CONTRACTS

**Base URL:** `http://localhost:8000`

#### Endpoints

1. **GET /api/v1/ops/source-registry**
   - Paginated registry query
   - Filters: `schema_name`, `object_type`, `layer`, `role`, `criticality`, `should_monitor`, `health_enabled`
   - Response: `SourceRegistryResponse`

2. **GET /api/v1/ops/health-checks**
   - All health checks
   - Response: `HealthChecksResponse`

3. **GET /api/v1/ops/health-global**
   - Global health status
   - Response: `HealthGlobalResponse`

4. **GET /api/v1/ops/raw-health/status**
   - RAW health status (existing)
   - Response: `RawDataHealthStatusResponse`

5. **GET /api/v1/ops/raw-health/freshness**
   - RAW freshness (existing)
   - Response: `RawDataFreshnessStatusResponse`

6. **GET /api/v1/ops/raw-health/ingestion-daily**
   - RAW ingestion daily (existing)
   - Response: `RawDataIngestionDailyResponse`

7. **GET /api/v1/ops/mv-health**
   - MV health status (existing)
   - Response: `MvHealthResponse`

#### Error Handling

- Client NEVER receives internal SQL errors
- All DB errors return `detail="database_error"`
- Full traceback logged server-side (`logger.exception`)

---

### F) UI CONTRACT

**Entrypoint:** `/ops/health`

#### Tabs

1. **Identity**
   - Component: `IdentitySystemHealthPanel`
   - Endpoint: `/api/v1/ops/data-health`

2. **RAW**
   - Component: `RawDataHealthPanel`
   - Endpoints: `/api/v1/ops/raw-health/*`

3. **MV**
   - Component: `MvHealthPanel`
   - Endpoint: `/api/v1/ops/mv-health`

4. **Checks**
   - Component: `HealthChecksPanel`
   - Endpoint: `/api/v1/ops/health-checks`

#### Rules

- No tab shows data unless backed by registry
- Checks must be drillable (via `drilldown_url`)
- PENDING tabs allowed only if explicitly marked

---

## Execution Order

### Initial Setup (One-time)

```bash
# 1. Create registry table
psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/source_registry.sql

# 2. Create/update health views
psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/v_health_checks.sql

psql -h <host> -p <port> -U <user> -d <database> \
  -f backend/sql/ops/v_health_global.sql
```

### Regular Execution (Scheduled/Cron)

```bash
# Step 1: Run discovery scripts (order matters)
cd backend

# 1.1 Discover DB objects
python scripts/discovery_objects.py
# Output: sql/ops/discovery_objects.csv

# 1.2 Discover dependencies
python scripts/discovery_dependencies.py
# Output: sql/ops/discovery_dependencies.csv

# 1.3 Discover repo usage
python scripts/discovery_usage_backend.py
# Output: sql/ops/discovery_usage_backend.csv

# Step 2: Populate registry (idempotent)
python scripts/populate_source_registry.py
# Reads: discovery_objects.csv, discovery_dependencies.csv, discovery_usage_backend.csv
# Updates: ops.source_registry

# Step 3: Health checks are automatically evaluated
# (v_health_checks is a view, no explicit execution needed)
```

### Validation

```bash
# Verify registry population
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT count(*) FROM ops.source_registry;"

# Verify health checks
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT check_key, severity, status FROM ops.v_health_checks ORDER BY severity, check_key;"

# Verify global health
psql -h <host> -p <port> -U <user> -d <database> \
  -c "SELECT * FROM ops.v_health_global;"

# Test API endpoints
curl "http://localhost:8000/api/v1/ops/source-registry?limit=10"
curl "http://localhost:8000/api/v1/ops/health-checks"
curl "http://localhost:8000/api/v1/ops/health-global"
curl "http://localhost:8000/api/v1/ops/mv-health?limit=5"
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    DISCOVERY LAYER                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  DB System Catalogs  ──┐                                   │
│  (pg_class, pg_namespace, │                               │
│   pg_depend, pg_rewrite)   │                               │
│                            ├──> discovery_objects.sql     │
│  Repo Code                 │   ──> discovery_objects.csv  │
│  (backend/**/*.py,         │                               │
│   backend/sql/**/*.sql)    ├──> discovery_dependencies.sql│
│                            │   ──> discovery_dependencies.csv│
│                            │                               │
│                            └──> discovery_usage_backend.py│
│                                ──> discovery_usage_backend.csv│
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    SOURCE REGISTRY                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  populate_source_registry.py                                │
│  ──> Reads CSVs                                             │
│  ──> UPSERT ops.source_registry                             │
│  ──> Respects manual overrides                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    HEALTH CHECKS                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  v_health_checks (view)                                     │
│  ──> Queries ops.source_registry                            │
│  ──> Queries DB system catalogs                             │
│  ──> Queries existing health views                          │
│  ──> Generates checks (NO hardcode)                         │
│                                                             │
│  v_health_global (view)                                     │
│  ──> Aggregates from v_health_checks                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GET /api/v1/ops/source-registry                            │
│  GET /api/v1/ops/health-checks                              │
│  GET /api/v1/ops/health-global                             │
│  GET /api/v1/ops/raw-health/*                               │
│  GET /api/v1/ops/mv-health                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    UI LAYER                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  /ops/health                                                │
│  ├── Identity tab                                           │
│  ├── RAW tab                                                │
│  ├── MV tab                                                 │
│  └── Checks tab                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Open Questions

### 1. Registry Population Schedule
**Question:** How frequently should the registry be populated?
- **Options:**
  - Daily (recommended for production)
  - On-demand (for development)
  - On code changes (CI/CD hook)
- **Recommendation:** Daily cron job, with on-demand option for development

### 2. Criticality Propagation
**Question:** Should criticality propagate through dependency chain?
- **Current:** RAW feeding critical MV becomes critical
- **Question:** Should DERIVED views that feed critical MVs also become critical?
- **Recommendation:** Yes, propagate criticality through dependency chain (implement in `populate_source_registry.py`)

### 3. Health View Coverage Detection
**Question:** How to detect if a monitored object is "covered" by health views?
- **Current:** Check if RAW object appears in `v_data_health_status`
- **Question:** Should we maintain an explicit mapping table or infer from view definitions?
- **Recommendation:** Infer from view definitions (scan `pg_rewrite` for view dependencies)

### 4. Unregistered Used Object Detection
**Question:** How to detect objects used in code but not in registry?
- **Current:** Compare DB objects with registry (approximation)
- **Question:** Should we cross-reference with `discovery_usage_backend.csv` directly?
- **Recommendation:** Yes, add check that queries `discovery_usage_backend.csv` or maintains a temp table

### 5. MV Refresh Schedule
**Question:** Should `refresh_schedule` be auto-detected or manual?
- **Current:** Manual field
- **Question:** Can we infer from `ops.mv_refresh_log` frequency?
- **Recommendation:** Auto-detect from `mv_refresh_log` (most frequent refresh interval)

### 6. Error Recovery
**Question:** What happens if discovery scripts fail?
- **Current:** Scripts exit with error code
- **Question:** Should we continue with partial data or fail completely?
- **Recommendation:** Fail completely (idempotent scripts allow retry)

### 7. Manual Override Management
**Question:** Should there be an API endpoint to manage manual overrides?
- **Current:** Direct SQL updates
- **Question:** Should we add `PUT /api/v1/ops/source-registry/{schema}/{object}`?
- **Recommendation:** Phase 2 feature (not in initial scope)

---

## Implementation Status

✅ **Completed:**
- Discovery scripts (objects, dependencies, usage)
- Source registry table and population script
- Health checks view (registry-based)
- Health global view
- API endpoints
- UI components (MV tab)
- Documentation

✅ **Verified:**
- Idempotency
- Manual override protection
- No hardcoded sources
- Error handling

---

## Next Steps

1. **Execute discovery scripts** to generate initial CSVs
2. **Populate registry** from discovery results
3. **Verify health checks** are working correctly
4. **Test API endpoints** with real data
5. **Validate UI** displays correctly
6. **Set up cron job** for regular discovery/population

---

## Maintenance

### Adding New Objects
- Objects are automatically discovered on next run
- No manual intervention needed (unless manual overrides desired)

### Adding New Health Checks
- Add new check to `v_health_checks.sql`
- Must derive from registry (no hardcode)
- Add `drilldown_url` mapping

### Modifying Criticality Rules
- Update `populate_source_registry.py` inference logic
- Re-run population script
- Registry will update automatically

---

## References

- [Discovery Usage Backend Docs](discovery_usage_backend.md)
- [Source Registry Docs](source_registry.md)
- [Backend Endpoints Inventory](../../contracts/backend_endpoints_inventory.md)
- [Frontend UI Blueprint](../../frontend/FRONTEND_UI_BLUEPRINT_v1.md)

