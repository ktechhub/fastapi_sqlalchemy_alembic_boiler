<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/ktechhub/doctoc)*

<!---toc start-->

- [API](#api)
  - [Overview](#overview)
  - [Features](#features)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Setup](#setup)
  - [Running with Docker](#running-with-docker)
  - [API Documentation](#api-documentation)
  - [Environment Variables](#environment-variables)
  - [Running Tests](#running-tests)
  - [Alembic Commands](#alembic-commands)
  - [License](#license)
  - [Contributing](#contributing)
  - [Contact](#contact)

<!---toc end-->

<!-- END doctoc generated TOC please keep comment here to allow auto update -->
# API

## Overview
The **API** is a FastAPI-based authentication and authorization service. It provides user authentication, role-based access control, and permission management. The API is designed to be secure, scalable, and easy to integrate with other services.

## Features
- **User Authentication**: Signup, login, logout, and token management
- **Role-Based Access Control (RBAC)**: Manage roles, permissions, and user roles
- **User Management**: CRUD operations on users
- **Permission Management**: Define and assign permissions to roles
- **Email Verification & Password Reset**
- **Secure Token Authentication** using OAuth2 and JWT
- **Redis Caching** (if applicable)
- **Task Scheduling** with background jobs

## Tech Stack
- **FastAPI** (Web framework)
- **SQLAlchemy** (Database ORM)
- **Alembic** (Database migrations)
- **Redis** (Caching and task queue, optional)
- **Docker** (Containerized deployment)
- **JWT/OAuth2** (Authentication)
- **Celery** (Task queue, optional)

## Project Structure
```plaintext
.
├── Dockerfile
├── LICENSE
├── README.md
├── alembic/                   # Database migrations
├── app/
│   ├── api/v1/                # API routes
│   ├── core/                  # Core configurations and logging
│   ├── cruds/                 # Database interaction layer
│   ├── database/              # Database setup and connections
│   ├── deps/                  # Dependencies and utilities
│   ├── mails/                 # Email sending service
│   ├── models/                # ORM models
│   ├── schemas/               # Pydantic schemas for validation
│   ├── tasks/                 # Background tasks and scheduled jobs
│   ├── tests/                 # Unit tests
│   ├── utils/                 # Utility functions
│   └── main.py                # Application entry point
├── docker-compose.yml
├── requirements.txt           # Python dependencies
└── test_users.py
```

## Installation
### Prerequisites
- Python 3.11
- Docker & Docker Compose (optional)
- Redis (optional, for caching and task queues)

### Setup
1. **Clone the repository:**
   ```sh
   git clone git@github.com:ktechhub/fastapi_sqlalchemy_alembic_boiler.git
   cd fastapi_sqlalchemy_alembic_boiler
   ```
2. **Create and activate a virtual environment:**
   ```sh
   python -m venv venv
   source venv/bin/activate   # On Windows use: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Run database migrations:**
   ```sh
   alembic upgrade head
   ```
5. **Start the application:**
   ```sh
   uvicorn app.main:app --reload
   ```

## Running with Docker
```sh
docker-compose up --build
```

## API Documentation
Once the application is running, the API docs can be accessed at:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Environment Variables
Create a `.env` file with the following variables:
```ini
API_VERSION
ENV
ALLOWED_HOSTS
MAIL_USERNAME
MAIL_PASSWORD
MAIL_FROM
MAIL_PORT
MAIL_SERVER
MAIL_FROM_NAME
REDIS_PASSWORD
REDIS_USERNAME
REDIS_PORT
REDIS_HOST
QUEUE_NAMES
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
DB_NAME
DB_ENGINE
JWT_SECRET_KEY
JWT_REFRESH_SECRET_KEY
S3_STORAGE_BUCKET
S3_STORAGE_HOST
S3_STORAGE_ACCESS_KEY
S3_STORAGE_SECRET_KEY
TELEGRAM_CHAT_ID
TELEGRAM_BOT_TOKEN
SERVICE_NAME
MEILI_SEARCH_URL
MEILI_SEARCH_API_KEY
```

## Running Tests
```sh
pytest
```

## Alembic Commands

1. Create a new migration:
    ```bash
    alembic revision --autogenerate -m "description of change"
    ```
2. Apply migrations:
    ```bash
    alembic upgrade head
    ```
3. Revert migrations:
    ```bash
    alembic downgrade -1
    ```
4. Check current migration:
    ```bash
    alembic current
    ```

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing
Pull requests are welcome! Please follow the contribution guidelines.

## Contact
For questions or support, please reach out to `support@ktechhub.com`. 🚀

