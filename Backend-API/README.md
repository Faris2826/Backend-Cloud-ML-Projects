# Backend API

A production-grade backend system with authentication, RBAC, CRUD operations, caching, and rate limiting.

## Features

- **JWT Authentication** with access & refresh tokens
- **Role-Based Access Control** (Admin / User)
- **Full CRUD** with pagination, filtering, sorting, and search
- **Redis Caching** for performance
- **Rate Limiting** (100 req/min per IP)
- **Input Validation** with Pydantic
- **Global Error Handling**
- **Docker & Docker Compose** ready

## Quick Start

### Local

```bash
pip install -r requirements.txt
# Make sure Redis is running locally
uvicorn app.main:app --reload
```

### Docker

```bash
docker-compose up --build
```

## API Overview

### Auth
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/register` | POST | Create account |
| `/auth/login` | POST | Get tokens (form-data) |
| `/auth/refresh` | POST | Refresh access token |

### Users
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/users/me` | GET | Current user |
| `/users` | GET | List users (admin only) |

### Items (CRUD)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/items` | POST | Create item |
| `/items` | GET | List items (paginated, filterable) |
| `/items/{id}` | GET | Get single item |
| `/items/{id}` | PUT | Update item |
| `/items/{id}` | DELETE | Delete item |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/stats` | GET | Platform stats |

## Example Flow

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","email":"alice@test.com","password":"secret123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=alice&password=secret123"

# Create item (use token from login)
curl -X POST http://localhost:8000/items \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"My Project","description":"A cool project","tags":["fastapi","backend"]}'

# List items with filters
curl "http://localhost:8000/items?search=project&sort_by=created_at&page=1&page_size=10" \
  -H "Authorization: Bearer <token>"
```

## Architecture

```
Client → Nginx (optional) → FastAPI → Redis (cache + rate limit)
                              ↓
                         PostgreSQL (swap in production)
```

## Production Checklist

- [ ] Swap in-memory DB for PostgreSQL + SQLAlchemy
- [ ] Add database migrations (Alembic)
- [ ] Use proper secrets management (Vault/AWS SM)
- [ ] Add structured logging (JSON)
- [ ] Prometheus metrics endpoint
- [ ] HTTPS / TLS termination
