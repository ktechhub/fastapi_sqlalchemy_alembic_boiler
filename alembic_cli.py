"""
alembic_cli.py
This script allows you to manage Alembic migrations for multiple databases.
It supports generating new revisions, upgrading to the latest migration,
and downgrading to a specific revision for one or more databases.

usage: alembic_cli.py [-h] [--db DB] [--message MESSAGE] [--revision REVISION] {revision,upgrade,downgrade}

Run Alembic migrations for databases.

positional arguments:
  {revision,upgrade,downgrade}
                        Action to perform: 'revision', 'upgrade', or 'downgrade'.

options:
  -h, --help            show this help message and exit
  --db DB               Specify a database to run the migration for. Defaults to settings.DB_NAME.
  --message MESSAGE     Revision message (required for 'revision').
  --revision REVISION   Specify the revision for downgrade (required for 'downgrade').
"""

from datetime import datetime
import os
import argparse
from alembic.config import Config
from alembic import command
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")
from app.core.config import settings


# Define available databases (from environment variable or default to 'dev')
DATABASES = os.getenv("DATABASES", "dev").split(",")


def generate_db_url(db_name=settings.DB_NAME):
    """
    Generate the database URL for a specific database.
    Supports multiple databases by replacing the DB_NAME in the URL.

    Args:
        db_name (str): Name of the database.

    Returns:
        str: Generated database URL.
    """
    if settings.DB_ENGINE == "sqlite":
        return settings.DATABASE_URL  # SQLite doesn't use separate DB names
    return settings.DATABASE_URL.replace(settings.DB_NAME, db_name)


def create_revision(db_name, config_path, message):
    """
    Create a new revision for a specific database.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        message (str): Revision message.

    Returns:
        None
    """
    versions_dir = os.path.join("alembic", "versions")
    os.makedirs(versions_dir, exist_ok=True)

    config = Config(config_path)
    config.set_main_option("version_locations", versions_dir)
    config.set_main_option(
        "sqlalchemy.url",
        generate_db_url(db_name),
    )
    print(
        f"Creating revision for {db_name}: {config.get_main_option('sqlalchemy.url')}"
    )
    command.revision(config, message=message, autogenerate=True)


def upgrade_head(db_name, config_path):
    """
    Upgrade the database to the latest migration.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option(
        "sqlalchemy.url",
        generate_db_url(db_name),
    )
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Upgrading {db_name} to the latest migration.")
    command.upgrade(config, "head")


def downgrade(db_name, revision, config_path):
    """
    Downgrade the database to a specific revision.

    Args:
        db_name (str): The database name.
        revision (str): The target revision for the downgrade.
        config_path (str): Path to the Alembic configuration file.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Downgrading {db_name} to revision {revision}.")
    command.downgrade(config=config, revision=revision)


def migrate_database(db_name, action, config_path, message=None, revision=None):
    """
    Perform a migration action on a specific database.

    Args:
        db_name (str): The database name.
        action (str): The action to perform ('revision', 'upgrade', 'downgrade').
        config_path (str): Path to the Alembic configuration file.
        message (str, optional): Revision message (required for 'revision').
        revision (str, optional): Target revision (required for 'downgrade').

    Returns:
        None
    """
    if action == "revision":
        if not message:
            print("Error: Revision message is required for 'revision'.")
            return
        create_revision(db_name, config_path, message)
    elif action == "upgrade":
        upgrade_head(db_name, config_path)
    elif action == "downgrade":
        if not revision:
            print("Error: Revision is required for 'downgrade'.")
            return
        downgrade(db_name, revision, config_path)
    else:
        print(f"Error: Invalid action '{action}'.")


def migrate_all(action, config_path, message=None, revision=None):
    """
    Perform a migration action on all databases.

    Args:
        action (str): The action to perform ('revision', 'upgrade', 'downgrade').
        config_path (str): Path to the Alembic configuration file.
        message (str, optional): Revision message (required for 'revision').
        revision (str, optional): Target revision (required for 'downgrade').

    Returns:
        None
    """
    for db_name in DATABASES:
        migrate_database(db_name, action, config_path, message, revision)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Alembic migrations for databases."
    )
    parser.add_argument(
        "action",
        choices=["revision", "upgrade", "downgrade"],
        help="Action to perform: 'revision', 'upgrade', or 'downgrade'.",
    )
    parser.add_argument(
        "--db",
        help="Specify a database to run the migration for. Defaults to settings.DB_NAME.",
    )
    parser.add_argument("--message", help="Revision message (required for 'revision').")
    parser.add_argument(
        "--revision",
        help="Specify the revision for downgrade (required for 'downgrade').",
    )
    args = parser.parse_args()

    # Path to the Alembic configuration file
    config_path = "./alembic.ini"

    # Handle validation for downgrade action
    if args.action == "downgrade" and not args.revision:
        print("Error: Missing revision for 'downgrade'.")
        exit(1)

    # Default database name if --db is not provided
    db_name = args.db if args.db else settings.DB_NAME

    # Run migrations for a single database or all databases
    if db_name:
        if db_name in DATABASES or db_name == settings.DB_NAME:
            migrate_database(
                db_name, args.action, config_path, args.message, args.revision
            )
        else:
            print(f"Error: Database '{db_name}' not found in the list of databases.")
    else:
        migrate_all(args.action, config_path, args.message, args.revision)


"""
python alembic_cli.py revision --db dev --message "Add users table"
python alembic_cli.py upgrade --db dev
python alembic_cli.py downgrade --db dev --revision abc123456

python alembic_cli.py revision --message "Add users table"
python alembic_cli.py upgrade
python alembic_cli.py downgrade --db test_db --revision abc123456
"""
