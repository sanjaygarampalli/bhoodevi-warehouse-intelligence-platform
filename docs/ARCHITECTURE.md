# Architecture

## Current Backend Stack

- FastAPI
- PostgreSQL
- SQLAlchemy 2
- Alembic
- Pydantic v2
- JWT authentication
- Role Based Access Control

## Development Rule

This is an existing backend application. Do not generate a new project scaffold or rebuild working modules without a genuine architectural reason.

## Layer Order

Inspect and evolve the system in this order:

1. Folder structure
2. Database layer
3. Models
4. Schemas
5. CRUD
6. Services
7. API
8. Authentication
9. Business workflow
10. AI modules

## Backend Layering

API routes should validate requests and delegate business behavior to services.

Services should hold business workflow logic.

CRUD modules should perform database access only.

Models and migrations should remain normalized and backward compatible whenever possible.
