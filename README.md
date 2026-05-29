# UrbanNest — Backend API

> A FastAPI + PostgreSQL backend for the UrbanNest residential society management platform, featuring role-based access control, JWT authentication, automated scheduling, and email notifications.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [API Reference](#api-reference)
- [Database](#database)
- [Authentication & Authorization](#authentication--authorization)
- [Background Jobs](#background-jobs)
- [Email Service](#email-service)
- [Docker](#docker)
- [Testing](#testing)

---

## Overview

UrbanNest API is a RESTful backend built with **FastAPI** and **PostgreSQL**. It powers four user roles — System Admin, Admin, Resident, and Security — each with their own dedicated routes and business logic. The API is designed to pair with the [UrbanNest UI](https://github.com/neel815/UrbanNest_UI) frontend.

---

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| [FastAPI](https://fastapi.tiangolo.com/) | 0.136.1 | Web framework & OpenAPI docs |
| [Uvicorn](https://www.uvicorn.org/) | 0.46.0 | ASGI server |
| [SQLAlchemy](https://www.sqlalchemy.org/) | 2.0.49 | ORM |
| [Alembic](https://alembic.sqlalchemy.org/) | 1.18.4 | Database migrations |
| [PostgreSQL](https://www.postgresql.org/) | — | Primary database (via psycopg2) |
| [Pydantic](https://docs.pydantic.dev/) | 2.13.3 | Data validation & settings |
| [python-jose](https://github.com/mpdavis/python-jose) | 3.3.0 | JWT token generation & verification |
| [passlib + bcrypt](https://passlib.readthedocs.io/) | 1.7.4 / 4.1.1 | Password hashing |
| [APScheduler](https://apscheduler.readthedocs.io/) | latest | Background job scheduling |
| [pytest](https://pytest.org/) | 7.4.3 | Testing framework |
| [httpx](https://www.python-httpx.org/) | 0.25.1 | Async HTTP client (used in tests) |

---

## Project Structure

```
UrbanNest_API/
├── app/
│   ├── main.py             # FastAPI app factory, middleware, router registration
│   ├── config.py           # Pydantic settings (reads from .env)
│   ├── database.py         # SQLAlchemy engine, session, Base
│   ├── models/             # SQLAlchemy ORM models
│   │   ├── user.py         # User, UserRole enum
│   │   ├── admin.py        # Building, Unit, Announcement, etc.
│   │   ├── resident.py     # ResidentProfile, MaintenanceRequest, Visitor, Payment, ForumPost
│   │   ├── security.py     # SecurityProfile, Incident, PatrolRoute, AccessLog
│   │   └── notification.py # Notification model
│   ├── routes/             # FastAPI routers (one per role)
│   │   ├── auth.py
│   │   ├── system_admin.py
│   │   ├── admin.py
│   │   ├── resident.py
│   │   ├── security.py
│   │   ├── notifications.py
│   │   └── health.py
│   ├── schemas/            # Pydantic request/response schemas
│   │   ├── auth.py
│   │   ├── system_admin.py
│   │   ├── admin.py
│   │   ├── resident.py
│   │   ├── security.py
│   │   └── notification.py
│   ├── services/           # Business logic layer
│   │   ├── auth_service.py
│   │   ├── system_admin_service.py
│   │   ├── admin_user_service.py
│   │   ├── resident_service.py
│   │   ├── security_service.py
│   │   ├── notification_service.py
│   │   ├── email_service.py
│   │   └── scheduler_service.py
│   ├── middleware/         # Custom FastAPI middleware
│   └── utils/              # Shared utilities
├── alembic/                # Database migration files
│   └── versions/           # Migration scripts (28+ migrations)
├── tests/
│   └── test_health.py      # Basic health and root endpoint tests
├── Dockerfile              # Production image (python:3.12-slim)
├── Dockerfile.dev          # Dev image with entrypoint (auto-migrate + reload)
├── entrypoint.sh           # Waits for DB, runs alembic upgrade, starts server
├── alembic.ini
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- **Python** 3.12+
- **PostgreSQL** 14+
- `pip` or a virtual environment manager

### Installation

```bash
# Clone the repository
git clone https://github.com/neel815/UrbanNest_API.git
cd UrbanNest_API

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt
```

### Database Setup

```bash
# Create the PostgreSQL database
createdb urbannest_db

# Run all migrations
alembic upgrade head
```

### Running the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API root:** `http://localhost:8000`
- **Interactive docs (Swagger UI):** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

---

## Environment Variables

Create a `.env` file in the project root. All variables are optional and fall back to their defaults.

```env
# Environment
ENV=development
DEBUG=True

# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_NAME=urbannest_db
# Or provide a full DSN to override the above:
# DATABASE_URL=postgresql://user:password@host:5432/dbname

# API
API_HOST=0.0.0.0
API_PORT=8000

# Security (JWT)
SECRET_KEY=your-strong-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Frontend URL (used in email links)
FRONTEND_URL=http://localhost:3000

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=your_email@gmail.com
SMTP_USE_TLS=True
```

> **Important:** Always change `SECRET_KEY` before deploying to production.

---

## Available Scripts

| Command | Description |
|---|---|
| `uvicorn app.main:app --reload` | Start dev server with auto-reload |
| `alembic upgrade head` | Apply all pending migrations |
| `alembic downgrade -1` | Roll back the last migration |
| `alembic revision --autogenerate -m "description"` | Generate a new migration |
| `pytest` | Run all tests |
| `pytest tests/ -v` | Run tests with verbose output |

---

## API Reference

All routes are prefixed with `/api`. Full interactive docs are available at `/docs`.

### Health
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/auth/login` | Login and receive JWT |
| POST | `/api/auth/register` | Register (invite-based) |
| POST | `/api/auth/forgot-password` | Request password reset email |
| POST | `/api/auth/reset-password` | Reset password using token |
| GET | `/api/auth/me` | Get current user profile |
| PUT | `/api/auth/me/profile` | Update current user profile |
| POST | `/api/auth/logout` | Logout |

### System Admin (`/api/system-admin/...`)
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/stats` | Platform-wide statistics |
| GET | `/dashboard/activity` | Recent platform activity |
| GET | `/dashboard/top-societies` | Top performing societies |
| GET/POST | `/buildings` | List / create buildings |
| PUT/DELETE | `/buildings/{id}` | Update / delete a building |
| GET | `/admins` | List all admins |
| POST | `/admins/invite` | Invite a new building admin |
| DELETE | `/admins/{id}` | Remove an admin |
| GET/PUT | `/settings/me` | View / update own settings |

### Admin (`/api/admin/...`)
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard/stats` | Building dashboard statistics |
| GET/POST | `/units` | List / create units |
| GET/POST | `/residents` | List residents |
| POST | `/residents/invite` | Invite a resident |
| GET | `/residents/detail/{id}` | Resident details |
| GET/POST | `/announcements` | Manage announcements |
| DELETE | `/announcements/{id}` | Delete announcement |
| GET | `/maintenance` | View all maintenance requests |
| POST | `/maintenance/{id}/start` | Start a maintenance job |
| POST | `/maintenance/{id}/resolve` | Resolve a maintenance request |
| POST | `/maintenance/{id}/cancel` | Cancel a maintenance request |
| GET/POST | `/payments` | List / create payments |
| POST | `/payments/bulk` | Bulk payment creation |
| POST | `/payments/individual` | Individual payment creation |
| POST | `/payments/{id}/mark-paid` | Mark a payment as paid |
| POST | `/payments/{id}/waive` | Waive a payment |
| POST | `/payments/trigger-overdue-check` | Manually trigger overdue check |
| GET/POST | `/security` | Manage security personnel |
| GET | `/security/stats` | Security statistics |
| POST | `/security/invite` | Invite a security staff member |
| GET/POST | `/patrol-routes` | Manage patrol routes |
| DELETE | `/patrol-routes/{id}` | Delete patrol route |
| GET/POST | `/events` | Manage community events |
| DELETE | `/events/{id}` | Delete event |

### Resident (`/api/resident/...`)
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard-stats` | Resident dashboard stats |
| GET/PUT | `/profile` | View / update profile |
| GET | `/announcements` | View announcements |
| GET/POST | `/maintenance` | View / submit maintenance requests |
| POST | `/maintenance/{id}/cancel` | Cancel a maintenance request |
| GET/POST | `/visitors` | Manage visitor pre-registrations |
| GET | `/payments` | View payment history |
| GET | `/events` | View community events |
| GET/POST | `/forum-posts` | View / create forum posts |

### Security (`/api/security/...`)
| Method | Path | Description |
|---|---|---|
| GET | `/dashboard-stats` | Security dashboard stats |
| GET | `/announcements` | View announcements |
| GET | `/visitors` | List visitors |
| GET | `/hosts` | List resident hosts |
| POST | `/visitors/{id}/approve` | Approve visitor |
| POST | `/visitors/{id}/deny` | Deny visitor |
| POST | `/visitors/{id}/checkin` | Check in visitor |
| POST | `/visitors/{id}/checkout` | Check out visitor |
| GET/POST | `/incidents` | View / report incidents |
| PUT | `/incidents/{id}` | Update incident |
| GET | `/access-points` | List access points |
| GET | `/access-logs` | View access logs |
| POST | `/access-points/{id}/toggle` | Toggle access point |
| GET | `/patrol-routes` | List patrol routes |
| GET/POST | `/patrol-rounds` | View / start patrol round |
| POST | `/patrol-rounds/{id}/complete` | Complete a patrol round |
| POST | `/patrol-rounds/{roundId}/checkpoints/{checkpointId}` | Visit a checkpoint |
| GET | `/logs` | View security logs |
| GET | `/reports` | List security reports |
| GET | `/reports/{id}/download` | Download a report |

### Notifications (`/api/notifications/...`)
| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | List notifications |
| POST | `/notifications/{id}/read` | Mark notification as read |
| POST | `/notifications/read-all` | Mark all as read |

---

## Database

The project uses **PostgreSQL** with **SQLAlchemy 2.0** (ORM) and **Alembic** for migrations.

### Key Models

| Model | Table | Description |
|---|---|---|
| `User` | `users` | All users; role-based (`system_admin`, `admin`, `resident`, `security`) |
| `Building` | `buildings` | Residential buildings/societies |
| `Unit` | `units` | Individual units within a building |
| `AdminProfile` | `admin_profiles` | Extended profile for building admins |
| `ResidentProfile` | `resident_profiles` | Extended profile for residents |
| `SecurityProfile` | `security_profiles` | Extended profile for security staff |
| `MaintenanceRequest` | `maintenance_requests` | Repair/maintenance tickets |
| `Visitor` | `visitors` | Visitor pre-registration and check-in |
| `Payment` | `payments` | Resident dues and payments |
| `Announcement` | `announcements` | Society-wide announcements |
| `Incident` | `incidents` | Security incident reports |
| `PatrolRoute` | `patrol_routes` | Defined security patrol paths |
| `Notification` | `notifications` | In-app notifications |
| `ForumPost` | `forum_posts` | Community forum posts |

### Running Migrations

```bash
# Apply all migrations (run on first setup and after pulling new changes)
alembic upgrade head

# Check current migration state
alembic current

# Create a new migration after modifying models
alembic revision --autogenerate -m "your description here"
```

> A seed migration (`2a3b4c5d6e7f_seed_test_accounts.py`) and a default system admin seed (`8aa2656418b8_seed_default_system_admin.py`) are included for development setup.

---

## Authentication & Authorization

Authentication uses **JWT Bearer tokens** (via `python-jose` + `bcrypt`).

**Login flow:**
1. `POST /api/auth/login` with `email` and `password`
2. Receive `access_token` and `role` in the response
3. Include the token in subsequent requests: `Authorization: Bearer <token>`

**Role enforcement** is done per-route in the service layer. Each role has a dedicated guard function (e.g., `require_system_admin`, `_require_security`).

**Password reset flow:**
1. `POST /api/auth/forgot-password` — sends a reset link via email
2. `POST /api/auth/reset-password` — validates the token and updates the password

Newly invited users are created with `must_reset_password=True` and are prompted to set a password on first login.

---

## Background Jobs

APScheduler runs a **daily cron job at midnight IST** to automatically mark overdue payments:

```python
# scheduler_service.py
def mark_overdue_payments():
    # Finds all PENDING payments past their due_date
    # Sets their status to OVERDUE
```

The scheduler starts and stops with the FastAPI application lifecycle (`startup` / `shutdown` events).

Admins can also trigger an overdue check manually via:
```
POST /api/admin/payments/trigger-overdue-check
```

---

## Email Service

The `email_service.py` sends HTML emails via SMTP (configured for Gmail by default). Email is used for:

- **Admin invitation** — sends login credentials to newly invited admins
- **Resident invitation** — sends welcome email with credentials to new residents
- **Password reset** — sends a secure reset link

HTML emails use a branded UrbanNest template (dark green header, clean layout).

Configure SMTP settings in `.env` (see [Environment Variables](#environment-variables)).

---

## Docker

### Production

```bash
docker build -t urbannest-api .
docker run -p 8000:8000 \
  -e DB_HOST=host.docker.internal \
  -e SECRET_KEY=your-secret \
  urbannest-api
```

The production image is based on `python:3.12-slim` and runs Uvicorn directly.

### Development (with auto-migrate)

```bash
docker build -f Dockerfile.dev -t urbannest-api-dev .
docker run -p 8000:8000 --env-file .env urbannest-api-dev
```

The dev image uses `entrypoint.sh` which:
1. Waits up to 60 seconds for PostgreSQL to be reachable
2. Runs `alembic upgrade head` automatically
3. Starts Uvicorn with `--reload`

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific file
pytest tests/test_health.py
```

Tests use **pytest** + **httpx** with FastAPI's `TestClient`. The suite currently covers health and root endpoint sanity checks. `pytest-asyncio` is configured for async route support.

---

## License

This project is private. All rights reserved.
