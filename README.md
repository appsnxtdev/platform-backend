# AppsNxt Platform

A modern, secure, and scalable backend platform built with FastAPI and Supabase authentication.

## Features

- **Robust Authentication System**
  - User sign-up and sign-in
  - Password reset functionality
  - Password update
  - Token refresh
  - Session management
  - Email verification

- **PostgreSQL Database**
  - Async database operations with SQLAlchemy
  - Migration support with Alembic
  - Efficient connection pooling

- **Security**
  - JWT authentication
  - Role-based access control
  - Request rate limiting

- **Observability**
  - Comprehensive logging system
  - OpenTelemetry integration
  - Sentry error tracking

- **Performance Optimizations**
  - Async request handling
  - GZip compression
  - Redis caching support

## Tech Stack

- **FastAPI**: High-performance web framework
- **Supabase**: Auth provider with PostgreSQL backend
- **SQLAlchemy**: ORM with async support
- **Alembic**: Database migration tool
- **Pydantic**: Data validation and settings management
- **Loguru**: Advanced Python logging
- **Redis**: Caching and session storage
- **Celery**: Background task processing

## Getting Started

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Supabase account

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/appsnxt-platform.git
cd appsnxt-platform
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Set up environment variables by creating a `.env` file:
```
# Project Info
PROJECT_NAME=AppsNxt Platform
VERSION=1.0.0
API_V1_STR=/api/v1

# Security
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=appsnxt
POSTGRES_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Running Migrations

Initialize the database with the latest schema:

```bash
poetry run alembic upgrade head
```

### Starting the Server

Run the application with Uvicorn:

```bash
poetry run uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000/api/v1/`

## API Documentation

Once the server is running, you can access:

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/signup` | POST | Register a new user |
| `/auth/signin` | POST | Authenticate a user |
| `/auth/signout` | POST | Sign out a user |
| `/auth/reset-password` | POST | Request a password reset |
| `/auth/update-password` | POST | Update user password |
| `/auth/refresh-token` | POST | Refresh access token |

## Project Structure

```
appsnxt-platform/
├── app/
│   ├── config.py           # Application configuration
│   ├── database.py         # Database connection handling
│   ├── logging_config.py   # Logging configuration
│   ├── main.py             # FastAPI application setup
│   ├── middleware/         # Custom middleware
│   ├── models/             # SQLAlchemy models
│   ├── routes/             # API endpoints
│   ├── schemas/            # Pydantic schemas
│   └── services/           # Business logic
├── migrations/             # Alembic migrations
├── logs/                   # Application logs
├── tests/                  # Test suite
├── pyproject.toml          # Poetry dependencies
├── alembic.ini             # Alembic configuration
└── README.md               # Project documentation
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Docker Setup

This application can be run using Docker for easier deployment and development.

### Prerequisites

- Docker
- Docker Compose

### Quick Start

1. Build the Docker images:
   ```bash
   ./docker.sh build
   ```

2. Start the containers:
   ```bash
   ./docker.sh up
   ```

3. Run database migrations:
   ```bash
   ./docker.sh migrate
   ```

4. Access the application at http://localhost:8000

### Docker Commands

The `docker.sh` script provides several commands to help with Docker operations:

- `build`: Build the Docker images
- `up`: Start the containers in detached mode
- `down`: Stop and remove the containers
- `logs`: View logs from the containers
- `shell`: Open a shell in the app container
- `migrate`: Run database migrations
- `test`: Run tests in the container
- `help`: Show help message

Example:
```bash
./docker.sh logs
```

### Environment Variables

The following environment variables can be configured in the `docker-compose.yml` file:

- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secret key for JWT tokens
- `ENVIRONMENT`: Application environment (development, production)

### Production Deployment

For production deployment, you should:

1. Update the environment variables in `docker-compose.yml`
2. Use a production-grade PostgreSQL instance
3. Set up proper logging and monitoring
4. Configure HTTPS with a reverse proxy like Nginx
