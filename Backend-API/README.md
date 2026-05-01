# Backend API

A production-style backend service built with FastAPI, providing authentication, access control, and data management.

## Overview
This API handles core application logic including user authentication, protected routes, and data operations. It is designed to reflect real-world backend systems with a focus on scalability and performance.

---

## Features
- JWT authentication (access + refresh tokens)
- Role-Based Access Control (RBAC)
- CRUD operations
- Pagination, filtering, search
- Redis caching
- Rate limiting per IP
- Input validation and error handling

---

## Tech Stack
- FastAPI
- Redis
- PostgreSQL (optional)
- Docker

---

## Running the Service

### 1. Clone repo
git clone <your-repo-url>  
cd backend-api  

### 2. Create virtual environment
python -m venv venv  
source venv/bin/activate  (Linux/Mac)  
venv\Scripts\activate     (Windows)  

### 3. Install dependencies
pip install -r requirements.txt  

### 4. Start Redis (required)
docker run -p 6379:6379 redis  

### 5. Run API
uvicorn app.main:app --reload  

API will be available at:
http://localhost:8000  

Docs:
http://localhost:8000/docs  

---

## Example Usage

### Register user
POST /auth/register
```json
{
  "email": "test@example.com",
  "password": "password123"
}
