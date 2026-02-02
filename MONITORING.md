# Monitoring and Health Checks Configuration

## Health Check Endpoints

### System Health
```bash
GET /api/healthz/
# Response: {"status": "ok"}
```

### Database Health
```bash
GET /api/health/database/
# Response: {"database": "connected", "migrations": "up_to_date"}
```

### Redis Health
```bash
GET /api/health/redis/
# Response: {"redis": "connected", "cache": "working"}
```

### Celery Health
```bash
GET /api/health/celery/
# Response: {"celery": "running", "workers": 2, "tasks": {"pending": 0, "active": 1}}
```

## Metrics Endpoints

### Application Metrics
```bash
GET /api/metrics/
# Prometheus-compatible metrics
```

### Business Metrics
```bash
GET /api/metrics/business/
# Custom business metrics for monitoring
```

## Alerting Configuration

### Critical Alerts
- Database connection failures
- Redis connection failures
- High error rates (>5%)
- Response time >2s
- Memory usage >90%

### Warning Alerts
- High response times (>1s)
- Queue backlog >100 tasks
- Memory usage >80%
- Disk usage >85%

## Logging Configuration

### Log Levels
- **ERROR**: System errors, exceptions
- **WARNING**: Performance issues, deprecated usage
- **INFO**: Business events, user actions
- **DEBUG**: Detailed debugging (development only)

### Log Aggregation
- Centralized logging with structured JSON
- Log rotation and retention policies
- Search and alerting capabilities

## Monitoring Stack Recommendations

### For Production:
1. **Prometheus** + **Grafana** for metrics and dashboards
2. **ELK Stack** (Elasticsearch, Logstash, Kibana) for logs
3. **Sentry** for error tracking (already configured)
4. **Uptime monitoring** (Pingdom, UptimeRobot)

### Docker Compose Monitoring
```yaml
# Add to docker-compose.prod.yml
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```