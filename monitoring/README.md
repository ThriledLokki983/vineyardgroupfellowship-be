# Monitoring App

## Overview

The **Monitoring** app provides comprehensive application health monitoring, performance tracking, and metrics collection for the Vineyard Group Fellowship platform. It offers real-time insights into system health, endpoint performance, and application readiness.

---

## Responsibilities

1. **Health Checks** - System health verification and readiness probes
2. **Performance Metrics** - Track API endpoint response times and performance
3. **Real-time Monitoring** - Live performance data and system statistics
4. **Endpoint Analytics** - Detailed metrics for individual API endpoints
5. **Metrics Management** - Clear and reset performance data

---

## Available Endpoints

### Base URL
```
/api/v1/monitoring/
```

### Endpoints

| Method | Endpoint | Description | Auth Required | Tags |
|--------|----------|-------------|---------------|------|
| GET | `/health/` | Basic health check | No | Monitoring |
| GET | `/healthz/` | Kubernetes health check | No | Monitoring |
| GET | `/ready/` | Readiness check | No | Monitoring |
| GET | `/metrics/` | Get performance metrics | Admin | Monitoring |
| GET | `/metrics/endpoints/` | Get endpoint-specific metrics | Admin | Monitoring |
| GET | `/metrics/realtime/` | Get real-time performance data | Admin | Monitoring |
| POST | `/metrics/clear/` | Clear all metrics | Admin | Monitoring |

---

## Endpoint Details

### 1. Health Check

**Endpoint:** `GET /api/v1/monitoring/health/`

**Purpose:** Verify that the application is running and responsive.

**Authentication:** None required

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-31T10:30:00Z",
  "environment": "production",
  "version": "1.0.0"
}
```

**Use Case:** Load balancers and monitoring services use this for health checks.

---

### 2. Kubernetes Health Check

**Endpoint:** `GET /api/v1/monitoring/healthz/`

**Purpose:** Kubernetes-compatible health check endpoint.

**Authentication:** None required

**Response:** Same as `/health/`

**Use Case:** Kubernetes liveness probes.

---

### 3. Readiness Check

**Endpoint:** `GET /api/v1/monitoring/ready/`

**Purpose:** Check if the application is ready to accept traffic (database connection, cache, etc.).

**Authentication:** None required

**Response:**
```json
{
  "status": "ready",
  "timestamp": "2025-10-31T10:30:00Z",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "migrations": "ok"
  }
}
```

**Possible Statuses:**
- `ready` - All systems operational
- `not_ready` - One or more systems unavailable

**Use Case:** Kubernetes readiness probes, deployment verification.

---

### 4. Performance Metrics

**Endpoint:** `GET /api/v1/monitoring/metrics/`

**Purpose:** Get overall application performance metrics.

**Authentication:** Admin required

**Response:**
```json
{
  "total_requests": 15420,
  "average_response_time": 145.2,
  "slowest_endpoint": "/api/v1/profiles/search/",
  "fastest_endpoint": "/api/v1/monitoring/health/",
  "error_rate": 0.02,
  "uptime_seconds": 864000,
  "memory_usage_mb": 512,
  "cpu_usage_percent": 25.5
}
```

**Use Case:** Performance monitoring dashboards, alerting systems.

---

### 5. Endpoint Metrics

**Endpoint:** `GET /api/v1/monitoring/metrics/endpoints/`

**Purpose:** Get detailed metrics for each API endpoint.

**Authentication:** Admin required

**Query Parameters:**
- `endpoint` (optional) - Filter by specific endpoint path
- `method` (optional) - Filter by HTTP method (GET, POST, etc.)
- `limit` (optional) - Limit number of results (default: 100)

**Response:**
```json
{
  "endpoints": [
    {
      "path": "/api/v1/auth/login/",
      "method": "POST",
      "total_requests": 1250,
      "average_response_time": 185.5,
      "min_response_time": 95.2,
      "max_response_time": 1250.8,
      "error_count": 15,
      "success_rate": 98.8,
      "last_accessed": "2025-10-31T10:25:00Z"
    },
    {
      "path": "/api/v1/profiles/me/",
      "method": "GET",
      "total_requests": 3420,
      "average_response_time": 85.3,
      "min_response_time": 45.1,
      "max_response_time": 450.2,
      "error_count": 5,
      "success_rate": 99.85,
      "last_accessed": "2025-10-31T10:29:45Z"
    }
  ],
  "total_endpoints": 42
}
```

**Use Case:** Identify slow endpoints, optimize performance bottlenecks.

---

### 6. Real-time Metrics

**Endpoint:** `GET /api/v1/monitoring/metrics/realtime/`

**Purpose:** Get current real-time performance data.

**Authentication:** Admin required

**Response:**
```json
{
  "timestamp": "2025-10-31T10:30:00Z",
  "current_requests_per_second": 15.2,
  "active_connections": 42,
  "current_response_time": 125.5,
  "memory_usage_mb": 512,
  "cpu_usage_percent": 25.5,
  "recent_requests": [
    {
      "endpoint": "/api/v1/profiles/me/",
      "method": "GET",
      "response_time": 95.2,
      "status_code": 200,
      "timestamp": "2025-10-31T10:29:58Z"
    }
  ]
}
```

**Use Case:** Live monitoring dashboards, real-time alerts.

---

### 7. Clear Metrics

**Endpoint:** `POST /api/v1/monitoring/metrics/clear/`

**Purpose:** Clear all collected performance metrics.

**Authentication:** Admin required

**Request:** No body required

**Response:**
```json
{
  "message": "Metrics cleared successfully",
  "cleared_at": "2025-10-31T10:30:00Z"
}
```

**Use Case:** Reset metrics after deployment, clear test data.

---

## Middleware

### Performance Monitoring Middleware

**Location:** `monitoring.middleware.performance.PerformanceMonitoringMiddleware`

**Purpose:** Automatically tracks response times and request counts for all API endpoints.

**Configuration:** Enabled globally in `settings.py`

**What it tracks:**
- Request count per endpoint
- Response times (min, max, average)
- HTTP status codes
- Error rates
- Request timestamps

---

## Models

The monitoring app uses in-memory storage for real-time metrics and may persist data to the database for historical analysis.

---

## Integration with Other Apps

### Authentication
- Health checks are public (no auth required)
- Metrics endpoints require admin authentication

### Core
- Uses core middleware infrastructure
- Integrates with security monitoring

---

## Configuration

### Environment Variables

```bash
# Enable/disable monitoring
ENABLE_MONITORING=True

# Metrics retention (hours)
METRICS_RETENTION_HOURS=24

# Real-time metrics update interval (seconds)
REALTIME_METRICS_INTERVAL=5
```

### Settings

```python
# In settings.py
MIDDLEWARE = [
    'monitoring.middleware.performance.PerformanceMonitoringMiddleware',
    # ... other middleware
]
```

---

## Usage Examples

### Frontend Integration

```javascript
// Check application health
async function checkHealth() {
  const response = await fetch('/api/v1/monitoring/health/');
  const data = await response.json();
  return data.status === 'healthy';
}

// Get performance metrics (admin only)
async function getPerformanceMetrics(token) {
  const response = await fetch('/api/v1/monitoring/metrics/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
}

// Get real-time metrics for dashboard
async function getRealTimeMetrics(token) {
  const response = await fetch('/api/v1/monitoring/metrics/realtime/', {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return await response.json();
}
```

### Kubernetes Configuration

```yaml
# Liveness probe
livenessProbe:
  httpGet:
    path: /api/v1/monitoring/healthz/
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

# Readiness probe
readinessProbe:
  httpGet:
    path: /api/v1/monitoring/ready/
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Monitoring Dashboard

```javascript
class MonitoringDashboard {
  constructor(token) {
    this.token = token;
    this.baseUrl = '/api/v1/monitoring';
  }

  async getMetrics() {
    const response = await fetch(`${this.baseUrl}/metrics/`, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return await response.json();
  }

  async getEndpointMetrics(endpoint = null) {
    let url = `${this.baseUrl}/metrics/endpoints/`;
    if (endpoint) {
      url += `?endpoint=${encodeURIComponent(endpoint)}`;
    }

    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${this.token}` }
    });
    return await response.json();
  }

  async startRealTimeMonitoring(callback, interval = 5000) {
    const fetchMetrics = async () => {
      const data = await fetch(`${this.baseUrl}/metrics/realtime/`, {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }).then(r => r.json());

      callback(data);
    };

    // Initial fetch
    await fetchMetrics();

    // Set up interval
    return setInterval(fetchMetrics, interval);
  }
}

// Usage
const dashboard = new MonitoringDashboard(adminToken);

// Get overall metrics
const metrics = await dashboard.getMetrics();
console.log(`Average response time: ${metrics.average_response_time}ms`);

// Get endpoint-specific metrics
const profileMetrics = await dashboard.getEndpointMetrics('/api/v1/profiles/me/');

// Start real-time monitoring
const intervalId = await dashboard.startRealTimeMonitoring((data) => {
  updateDashboard(data);
}, 5000);

// Stop monitoring when done
clearInterval(intervalId);
```

---

## Performance Considerations

1. **Metrics Storage** - Metrics are stored in-memory for fast access
2. **Retention** - Old metrics are automatically purged based on retention settings
3. **Overhead** - Middleware adds minimal overhead (~1-2ms per request)
4. **Scalability** - Designed for high-traffic environments

---

## Security

1. **Public Endpoints** - Health checks are intentionally public
2. **Admin Protection** - All metrics endpoints require admin authentication
3. **Rate Limiting** - Consider adding rate limiting to metrics endpoints
4. **Data Privacy** - No user PII is collected in metrics

---

## Future Enhancements

- [ ] Database persistence for historical metrics
- [ ] Alerting system for performance thresholds
- [ ] Integration with external monitoring services (Datadog, New Relic)
- [ ] Custom metrics and events tracking
- [ ] Performance regression detection
- [ ] Distributed tracing support

---

## Related Documentation

- [Core App README](../core/README.md)
- [API Documentation](/api/schema/swagger-ui/)
- [Performance Monitoring Guide](../../docs/performance.md)

---

**Last Updated:** October 31, 2025
