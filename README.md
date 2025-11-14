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
  - [Running Tests](#running-tests)
  - [Alembic Commands](#alembic-commands)
  - [Database Initialization](#database-initialization)
  - [Makefile Commands](#makefile-commands)
  - [Environment Configuration](#environment-configuration)
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
```sh
.
├── alembic
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions
├── alembic_cli.py
├── alembic.ini
├── app
│   ├── __init__.py
│   ├── api
│   │   ├── __init__.py
│   │   └── v1
│   │       ├── __init__.py
│   │       ├── auth
│   │       │   ├── __init__.py
│   │       │   ├── auth.py
│   │       │   ├── permissions.py
│   │       │   ├── profile.py
│   │       │   ├── referesh_token.py
│   │       │   ├── role_permissions.py
│   │       │   ├── roles.py
│   │       │   ├── router.py
│   │       │   ├── user_roles.py
│   │       │   └── users.py
│   │       ├── logs
│   │       │   ├── __init__.py
│   │       │   ├── activity_logs.py
│   │       │   ├── router.py
│   │       │   └── system_logs.py
│   │       └── router.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── defaults.py
│   │   ├── languages.py
│   │   └── loggers.py
│   ├── cruds
│   │   ├── __init__.py
│   │   ├── activity_logs.py
│   │   ├── base.py
│   │   ├── codes.py
│   │   ├── mixins.py
│   │   ├── permissions.py
│   │   ├── role_permissions.py
│   │   ├── roles.py
│   │   ├── user_roles.py
│   │   └── users.py
│   ├── database
│   │   ├── __init__.py
│   │   ├── base_class.py
│   │   └── get_session.py
│   ├── deps
│   │   ├── __init__.py
│   │   └── user.py
│   ├── mails
│   │   ├── __init__.py
│   │   ├── contents.py
│   │   ├── email_service.py
│   │   └── templates
│   │       └── email.html
│   ├── main.py
│   ├── media
│   ├── models
│   │   ├── __init__.py
│   │   ├── activity_logs.py
│   │   ├── base_mixins.py
│   │   ├── codes.py
│   │   ├── permissions.py
│   │   ├── role_permissions.py
│   │   ├── roles.py
│   │   ├── user_roles.py
│   │   └── users.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── activity_logs.py
│   │   ├── base_filters.py
│   │   ├── base_schema.py
│   │   ├── logs.py
│   │   ├── permissions.py
│   │   ├── role_permissions.py
│   │   ├── roles.py
│   │   ├── tokens.py
│   │   ├── user_deps.py
│   │   ├── user_roles.py
│   │   ├── users.py
│   │   └── verification_codes.py
│   ├── services
│   │   ├── __init__.py
│   │   ├── meili_search.py
│   │   ├── poison_queue.py
│   │   ├── redis_base.py
│   │   ├── redis_main.py
│   │   ├── redis_operations.py
│   │   └── redis_push.py
│   ├── static
│   ├── tasks
│   │   ├── __init__.py
│   │   ├── common
│   │   │   ├── __init__.py
│   │   │   ├── fake_users.py
│   │   │   ├── permissions.py
│   │   │   ├── role_permissions.py
│   │   │   └── roles.py
│   │   └── scheduler.py
│   ├── tests
│   │   └── __init__.py
│   └── utils
│       ├── __init__.py
│       ├── code.py
│       ├── object_storage.py
│       ├── password_util.py
│       ├── responses.py
│       ├── schema_as_form.py
│       ├── security_util.py
│       └── telegram.py
├── delayed_msgs.Dockerfile
├── delayed_msgs.py
├── docker-compose.yml
├── prod.docker-compose.yml
├── Dockerfile
├── init_db.py
├── LICENSE
├── logs
├── Makefile
├── README.md
├── redis_main.Dockerfile
├── requirements.txt
├── test_users.py
└── test.py
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
4. **Copy .env and update values:**
   ```sh
   cp .env.example .env
   ```
5. **Run database migrations:**
   ```sh
   python alembic_cli.py upgrade
   ```
6. **Initialize database with default data:**
   ```sh
   python init_db.py
   ```
   This will create:
   - Permissions
   - Roles
   - Role-permission associations
   - Test users for each role
   - Fake users for testing
   - Countries data
7. **Start the application:**
   ```sh
   uvicorn app.main:app --reload
   ```
8. **Start the RedisMessageProcessor:**
   ```sh
   python -m app.services.redis_main
   ```
9. **Start the DelayedMessageProcessor:**
   ```sh
   python delayed_msgs.py
   ```

## Running with Docker

### Basic Usage
```sh
docker-compose up --build
```

### Using Makefile (Recommended)
The Makefile provides convenient commands for common operations. See [Makefile Commands](#makefile-commands) section below.

## API Documentation
Once the application is running, the API docs can be accessed at:
- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## Running Tests
```sh
pytest
```

## Alembic Commands

1. **Create a new migration:**
    ```bash
    python alembic_cli.py revision --message "description of change"
    ```

2. **Apply migrations:**
    ```bash
    python alembic_cli.py upgrade
    ```
    Or using Makefile (in Docker):
    ```bash
    make alembic-upgrade
    ```

3. **Revert migrations:**
    ```bash
    python alembic_cli.py downgrade base
    ```

4. **Check current migration:**
    ```bash
    alembic current
    ```

## Database Initialization

After running database migrations, you need to populate the database with initial data (permissions, roles, test users, etc.).

### Using init_db.py (Recommended)

The `init_db.py` script runs all initialization tasks in the correct order:

```bash
# Direct execution
python init_db.py

# Or in Docker
docker exec app python3 init_db.py

# Or using Makefile
make init-db
```

**What it does:**
- Creates/updates permissions based on `default_actions`
- Creates/updates roles based on `default_roles`
- Syncs role-permission associations
- Creates test users for each default role
- Creates fake users for testing
- Syncs countries data

**Output:**
- Progress indicators for each task
- Success/failure summary
- Telegram notification with results

### Legacy Script

The `test_users.py` script is kept for backward compatibility but is deprecated. Use `init_db.py` instead.

## Makefile Commands

The Makefile provides convenient commands for common operations. It automatically selects the correct docker-compose file based on the `ENV` variable in your `.env` file.

### Environment-Based Configuration

The Makefile automatically selects docker-compose files based on `ENV`:
- `ENV=local` or `ENV=dev` → uses `docker-compose.yml`
- `ENV=prod` (or any other value) → uses `prod.docker-compose.yml`

### Available Commands

#### Docker Compose Commands

- **`make dc-up`** - Start containers in detached mode with build
  ```bash
  make dc-up
  ```

- **`make dc-up-with-logs`** - Start containers with logs visible
  ```bash
  make dc-up-with-logs
  ```

- **`make dc-down`** - Stop and remove containers
  ```bash
  make dc-down
  ```

#### Git Commands

- **`make git-update`** - Update code from repository
  - If `ENV=dev`: checks out `dev` branch and pulls from `origin dev`
  - Otherwise: checks out `main` branch and pulls from `origin main`
  ```bash
  make git-update
  ```

#### Database Commands

- **`make alembic-upgrade`** - Run database migrations
  ```bash
  make alembic-upgrade
  ```

- **`make init-db`** - Initialize database with default data
  ```bash
  make init-db
  ```

#### System Commands

- **`make nginx-reload`** - Reload Nginx configuration
  ```bash
  make nginx-reload
  ```

#### Deployment Commands

- **`make deploy`** - Full deployment workflow
  - Updates code from git
  - Stops containers
  - Starts containers
  - Waits for containers to start
  - Runs database migrations
  - Reloads Nginx
  ```bash
  make deploy
  ```

### Example Workflow

```bash
# 1. Set ENV in .env file
echo "ENV=dev" >> .env

# 2. Start containers
make dc-up

# 3. Run migrations
make alembic-upgrade

# 4. Initialize database
make init-db

# 5. For production deployment
make deploy
```

## Environment Configuration

The application uses environment variables from a `.env` file. Key variables include:

- **`ENV`** - Environment name (`local`, `dev`, or `prod`)
  - Affects which docker-compose file is used
  - Affects which git branch is used for updates

- **`DATABASE_URL`** - Database connection string
- **`REDIS_URL`** - Redis connection string (optional)
- **`SECRET_KEY`** - Secret key for JWT tokens
- **`DOMAIN`** - Application domain
- **`APP_NAME`** - Application name

Create a `.env` file based on `.env.example` and configure these values.

## License
This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing
Pull requests are welcome! Please follow the contribution guidelines.

## Contact
For questions or support, please reach out to `support@ktechhub.com`. 🚀

