# Backend API

A production-style backend service built with FastAPI, designed with scalability, performance, and clean architecture in mind.

## Overview
This service provides the core API layer of the system, handling authentication, access control, and data operations. It follows real-world backend design patterns, focusing on stateless architecture and performance optimisation.

## Features
- JWT-based authentication (access & refresh tokens)
- Role-Based Access Control (RBAC)
- Full CRUD functionality
- Pagination, filtering, and search
- Redis-based caching
- Rate limiting per IP
- Input validation using Pydantic
- Centralised error handling

## Tech Stack
- Python / FastAPI
- Redis
- PostgreSQL (configurable)
- Docker

## Running the Service

### Local
pip install -r requirements.txt  
uvicorn app.main:app --reload  

### Docker
docker-compose up --build  

## Key Design Decisions
- Stateless authentication using JWT for scalability
- Redis used for both caching and rate limiting to reduce database load
- RBAC implemented to reflect production-level access control
- Modular structure separating routes, services, and models
