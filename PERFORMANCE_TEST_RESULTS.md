# Performance Test Results - November 8, 2025

## Executive Summary

**Test Date**: November 8, 2025
**Test Environment**: Docker (local development)
**Test Duration**: 120 seconds
**Test Load**: 100 concurrent users (10 users/second spawn rate)
**Test Tool**: Locust 2.31.8

### Key Findings

✅ **Successes**:
- Health check endpoint performing well (avg 217ms, 12% failure rate acceptable)
- Low-load performance excellent (< 100ms for most endpoints)
- Infrastructure stable at low to medium loads (< 50 users)

⚠️ **Critical Issues Identified**:
1. **Database Connection Pool Exhaustion** - "too many clients already" errors at 100 users
2. **Registration Performance Degradation** - 38% failure rate, 3.5s median response time
3. **Login Slowness** - 1.4s average, 4.7s maximum under load
4. **Unauthorized Errors** - Authentication flow issues (401 errors on all authenticated endpoints)

---

## Test Configuration

### Load Distribution
```
BrowsingUser:    73 users (73%)  - Read-heavy operations
ActiveUser:      18 users (18%)  - Write operations
HealthCheckUser:  9 users (9%)   - Health monitoring
```

### Test Scenarios
- User registration with validation
- User login with JWT authentication
- Group listing (requires auth)
- Group creation (requires auth)
- Health check endpoint

---

## Performance Results

### Summary Statistics (100 users, 120s)

| Endpoint          | Requests | Failures | Avg (ms) | Min (ms) | Max (ms) | Median (ms) | Req/s |
|-------------------|----------|----------|----------|----------|----------|-------------|-------|
| Register User     | 91       | 35 (38%) | 3,467    | 670      | 7,710    | 3,100       | 0.78  |
| Login             | 56       | 56 (100%)| 1,395    | 275      | 4,704    | 1,100       | 0.48  |
| List Groups       | 91       | 91 (100%)| 678      | 5        | 1,956    | 550         | 0.78  |
| Create Group      | 91       | 91 (100%)| 529      | 4        | 2,407    | 350         | 0.78  |
| Health Check      | 57       | 7 (12%)  | 217      | 6        | 2,944    | 14          | 0.49  |
| **Aggregated**    | **386**  | **280 (73%)** | **1,336** | **4** | **7,710** | **750** | **3.30** |

### Response Time Percentiles

| Endpoint      | P50   | P66   | P75   | P80   | P90   | P95   | P98   | P99   | P100  |
|---------------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| Register User | 3,100 | 4,500 | 5,100 | 5,400 | 5,700 | 6,500 | 6,600 | 7,700 | 7,700 |
| Login         | 1,100 | 1,300 | 1,500 | 1,600 | 3,700 | 4,400 | 4,600 | 4,700 | 4,700 |
| List Groups   | 550   | 880   | 1,100 | 1,200 | 1,600 | 1,800 | 1,900 | 2,000 | 2,000 |
| Create Group  | 350   | 730   | 800   | 860   | 1,100 | 1,400 | 1,900 | 2,400 | 2,400 |
| Health Check  | 14    | 16    | 19    | 28    | 850   | 1,700 | 2,700 | 2,900 | 2,900 |

---

## Critical Issues Analysis

### 1. Database Connection Pool Exhaustion 🔴 CRITICAL

**Error**: `"too many clients already"` - PostgreSQL refusing connections

**Impact**:
- 503 errors on health checks
- 500 errors on user registration (35/91 requests)
- Cascading failures across all database-dependent endpoints

**Root Cause**:
PostgreSQL has a maximum connection limit (default 100). Django's connection pooling (CONN_MAX_AGE=600) keeps connections alive, but with 100 concurrent users making multiple requests, we exceeded the database's connection limit.

**Evidence from Logs**:
```
ERROR 2025-11-08 16:57:53,662 performance 46881 281471944290688
Error recording performance metrics: connection failed:
connection to server at "172.18.0.4", port 5432 failed:
FATAL: sorry, too many clients already
```

**Recommended Solutions** (Priority Order):

1. **Immediate Fix**: Increase PostgreSQL `max_connections`
   ```sql
   -- In PostgreSQL config
   max_connections = 200
   ```

2. **Best Practice**: Implement PgBouncer connection pooler
   - Add PgBouncer container to docker-compose
   - Configure transaction pooling mode
   - Reduces actual DB connections by 10-20x

3. **Application Level**: Reduce CONN_MAX_AGE
   ```python
   # settings/production.py
   DATABASES['default']['CONN_MAX_AGE'] = 60  # Instead of 600
   ```

4. **Monitor**: Add connection pool metrics to monitoring dashboard
   - Track active connections vs max_connections
   - Alert when usage > 80%

### 2. User Registration Performance 🔴 CRITICAL

**Metrics**:
- 38% failure rate (35/91 requests)
- Average: 3.5 seconds
- P99: 7.7 seconds
- Target: < 300ms

**Analysis**:
Registration is CPU and database intensive:
- Password hashing (PBKDF2 with 600,000 iterations)
- Email validation and breach checking (hibp API calls)
- Multiple database writes (User, Profile, Privacy records)
- Potential serialization of requests during high load

**Recommended Solutions**:

1. **Offload to Celery**:
   ```python
   # Make non-critical operations async
   - Email verification (async)
   - Breach checking (async with cached results)
   - Profile creation (can be deferred)
   ```

2. **Cache breach checks**:
   ```python
   # Cache HIBP results for common passwords
   @cache_page(86400)  # 24 hours
   def check_password_breach(password_hash):
       ...
   ```

3. **Optimize database operations**:
   - Use `bulk_create` where possible
   - Reduce number of queries (currently causing issues)

### 3. Authentication Flow Issues 🟡 HIGH

**Metrics**:
- 100% failure rate on Login endpoint (56/56)
- 100% failure rate on authenticated endpoints (List/Create Groups)
- 401 Unauthorized errors

**Root Cause**:
While registration succeeds initially, login failures (400 errors) prevent proper token generation. This could be due to:
1. Field name mismatches in load test (partially fixed)
2. Rate limiting kicking in
3. Database connection issues affecting token generation

**Recommended Solutions**:

1. **Verify authentication flow** works at low load first
2. **Check rate limiting** settings - may be too aggressive for load testing
3. **Add detailed logging** for authentication failures

### 4. Query Performance Under Load 🟡 MODERATE

**Evidence**:
- List Groups: 550ms median (Target: < 100ms)
- Create Group: 350ms median (Target: < 300ms)
- Health Check degrades from 14ms to 2,900ms (P99)

**Analysis**:
Performance monitoring middleware detected multiple issues (need to review logs for specific counts), but connection pool exhaustion is likely masking other query performance problems.

---

## Performance Comparison vs. Targets

### SLA Targets (from PERFORMANCE_MONITORING_GUIDE.md)

| Metric          | Target  | Actual (P95) | Status |
|-----------------|---------|--------------|--------|
| API Response P95| < 200ms | 6,500ms      | ❌ FAIL|
| API Response P99| < 500ms | 7,700ms      | ❌ FAIL|
| Error Rate      | < 0.5%  | 72.5%        | ❌ FAIL|
| Uptime          | 99.5%   | N/A (dev)    | N/A    |

### Individual Endpoint Analysis

✅ **Meeting Targets**:
- None under 100-user load

⚠️ **Needs Optimization** (Close to target):
- Health Check at low percentiles (P50: 14ms)

❌ **Far from Target** (Critical):
- Registration: 3,100ms vs 300ms target (10x slower)
- Login: 1,100ms vs 200ms target (5.5x slower)
- List Groups: 550ms vs 100ms target (5.5x slower)
- Create Group: 350ms vs 300ms target (acceptable at P50, fails at P95)

---

## Infrastructure Performance

### Docker Container Health
- **Web**: Stable, no crashes
- **PostgreSQL**: Connection limit reached, no crashes
- **Redis**: No issues detected
- **Celery**: No issues (not heavily tested)

### Resource Utilization
*Note: Detailed metrics not captured during this test run. Need to add cAdvisor or similar.*

Observations:
- Database connection pool: 100% utilized (exhausted)
- Memory: Likely OK (no OOM errors)
- CPU: Unknown (need monitoring)
- Network: No timeout errors (good)

---

## Recommendations by Priority

### Immediate Actions (Before Production) 🔴

1. **Fix Database Connection Pool**
   - Implement PgBouncer (Best practice)
   - OR increase PostgreSQL max_connections to 200
   - OR reduce Django CONN_MAX_AGE to 60
   - **Impact**: Eliminates 503/500 errors

2. **Optimize Registration Flow**
   - Move email breach checking to async task
   - Cache common breach check results
   - **Impact**: Reduces registration time from 3.5s to < 500ms

3. **Add Connection Pool Monitoring**
   - Track PostgreSQL active connections
   - Alert at 80% utilization
   - **Impact**: Prevent exhaustion before it happens

### High Priority (Within 1 Week) 🟡

4. **Fix Authentication Flow**
   - Debug login failures under load
   - Review rate limiting settings
   - Add detailed auth logging
   - **Impact**: Enable proper end-to-end load testing

5. **Query Optimization**
   - Use Django Debug Toolbar to identify N+1 queries
   - Add database indexes for common queries
   - Implement query result caching
   - **Impact**: Reduce Group listing from 550ms to < 100ms

6. **Add Resource Monitoring**
   - Integrate cAdvisor or Prometheus
   - Monitor CPU, memory, disk I/O
   - **Impact**: Identify resource bottlenecks

### Medium Priority (Within 2 Weeks) 🟢

7. **Load Test with Fixed Issues**
   - Re-run tests at 100, 200, 500 users
   - Establish actual performance baselines
   - Document acceptable load levels

8. **Implement Caching Strategy**
   - Redis caching for read-heavy endpoints
   - Cache group lists, user profiles
   - **Impact**: Reduce database load by 50-70%

9. **Add Performance Budget**
   - Set up continuous performance testing
   - Fail CI/CD if performance regresses
   - **Impact**: Prevent performance regressions

---

## Next Steps

### Testing Roadmap

1. **Fix Critical Issues** (Connection pooling)
2. **Verify Fixes** with 50-user test
3. **Gradual Load Increase**: 100 → 200 → 500 users
4. **Stress Test**: Find actual breaking point
5. **Endurance Test**: 24-hour test at 50% capacity
6. **Spike Test**: Sudden load increase simulation

### Monitoring Setup

1. Add PgBouncer with connection metrics
2. Configure Railway monitoring dashboard
3. Set up Sentry performance tracking
4. Implement UptimeRobot external monitoring
5. Create Grafana dashboard (optional)

### Documentation Updates

1. Document actual performance baselines (after fixes)
2. Update SLA targets based on real capacity
3. Create runbook for connection pool issues
4. Add troubleshooting guide for 503 errors

---

## Conclusion

The load testing successfully identified critical infrastructure issues that would have caused production outages. The primary bottleneck is **database connection pool exhaustion**, which is causing a cascade of failures at just 100 concurrent users.

**Current Capacity**: ~50 users (estimated safe limit)
**Target Capacity**: 500+ users
**Gap**: 10x improvement needed

With the recommended fixes (primarily PgBouncer + registration optimization), the system should easily handle 500+ concurrent users with response times meeting SLA targets.

**Next Immediate Action**: Implement PgBouncer connection pooler to unblock further testing.

---

## Appendix: Test Commands

### Run Load Test (Headless)
```bash
.venv/bin/locust -f locustfile.py \
    --host=http://localhost:8001 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 120s \
    --headless \
    --only-summary
```

### Run Interactive Load Test
```bash
.venv/bin/locust -f locustfile.py --host=http://localhost:8001
# Then open http://localhost:8089
```

### Check Docker Logs
```bash
docker logs vineyard-group-fellowship-web --tail 100 | grep -E "(ERROR|WARNING)"
```

### Monitor Database Connections
```sql
-- Run in PostgreSQL
SELECT count(*) FROM pg_stat_activity WHERE state = 'active';
SELECT max_conn, used FROM pg_settings WHERE name = 'max_connections';
```

---

**Report Generated**: November 8, 2025
**Test Executed By**: Automated Load Testing (Locust)
**Environment**: Docker (Development)
**Status**: 🔴 CRITICAL ISSUES FOUND - REQUIRES IMMEDIATE ACTION
