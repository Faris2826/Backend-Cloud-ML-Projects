# Infrastructure Stack

A complete Docker Compose orchestration for the ML API + Backend API with monitoring, logging, and CI/CD.

## What's Included

| Service | Purpose | Port |
|---------|---------|------|
| `nginx` | Reverse proxy | `80` |
| `ml-api` | ML prediction service | internal |
| `backend-api` | Main backend API | internal |
| `redis` | Caching & rate limiting | `6379` |
| `postgres` | Primary database | `5432` |
| `prometheus` | Metrics collection | `9090` |
| `grafana` | Visualization dashboards | `3000` |
| `loki` | Log aggregation | `3100` |

## Project Structure

```
.
├── docker-compose.yml
├── .env.example
├── nginx/
│   └── nginx.conf
├── monitoring/
│   ├── prometheus.yml
│   ├── loki.yml
│   └── grafana/
│       ├── datasources/
│       └── dashboards/
├── ml-text-api/          # (Project 1)
├── backend-api/          # (Project 2)
└── .github/
    └── workflows/
        └── ci.yml
```

## Quick Start

```bash
# 1. Clone/copy Project 1 & 2 into this directory
cp -r ../ml-text-api ./ml-text-api
cp -r ../backend-api ./backend-api

# 2. Set environment
cp .env.example .env
# Edit .env with real values

# 3. Launch everything
docker-compose up --build -d

# 4. Access services
# API Gateway:     http://localhost
# Prometheus:      http://localhost:9090
# Grafana:         http://localhost:3000 (admin/admin)
# Loki:            http://localhost:3100
```

## API Routing

```
http://localhost/ml/health      → ML API health
http://localhost/ml/predict     → ML prediction
http://localhost/api/health     → Backend health
http://localhost/api/auth/...   → Backend auth
http://localhost/api/items/...  → Backend CRUD
```

## Monitoring

### Prometheus
- Scrapes both APIs every 15s
- Query metrics at `http://localhost:9090`

### Grafana
- Pre-configured with Prometheus & Loki datasources
- Build dashboards for:
  - Request rates & latencies
  - Error rates
  - Model prediction confidence
  - Cache hit rates

### Loki
- Aggregates logs from all containers
- Query logs in Grafana Explore

## CI/CD

GitHub Actions workflow (`ci.yml`):
- **Test**: Install deps, lint with ruff, build images
- **Deploy**: Triggered on `main` branch merges

## Scaling Considerations

```bash
# Scale ML API workers
docker-compose up -d --scale ml-api=3

# Add load balancer (already handled by Nginx upstream)
```

## Production Deployment

1. **Secrets**: Use Docker Swarm secrets or AWS Secrets Manager
2. **SSL**: Add certbot or AWS ACM with ALB
3. **DB**: Use managed RDS/Cloud SQL instead of containerized Postgres
4. **Monitoring**: Add Alertmanager for Prometheus alerts
5. **Backups**: Volume snapshots for Postgres & Grafana
