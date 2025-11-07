"""
alembic_cli.py
This script allows you to manage Alembic migrations for multiple databases.
It supports all Alembic commands: revision, upgrade, downgrade, current, history,
show, stamp, check, merge, branches, and heads.

usage: alembic_cli.py [-h] [--db DB] [--message MESSAGE] [--revision REVISION]
                      [--revisions REVISIONS] [--indicate-current] [--verbose]
                      [--sql] [--rev-range REV_RANGE] [--head-only]
                      [--resolve-dependencies]
                      {revision,upgrade,downgrade,current,history,show,stamp,check,merge,branches,heads}

Run Alembic migrations for databases.

positional arguments:
  {revision,upgrade,downgrade,current,history,show,stamp,check,merge,branches,heads}
                        Action to perform.

options:
  -h, --help            show this help message and exit
  --db DB               Specify a database to run the migration for. Defaults to settings.DB_NAME.
  --message MESSAGE     Revision message (required for 'revision' and 'merge').
  --revision REVISION   Target revision (required for 'downgrade', 'upgrade', 'show', 'stamp').
  --revisions REVISIONS Comma-separated revisions to merge (required for 'merge').
  --indicate-current    Indicate current revision (for 'history').
  --verbose             Verbose output.
  --sql                 Don't emit SQL to database (for 'upgrade', 'downgrade', 'stamp').
  --rev-range           Revision range (for 'history').
  --head-only           Show only heads (for 'history').
  --resolve-dependencies
                        Resolve dependencies (for 'merge' and 'heads').
"""

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
    print(f"Creating revision for '{db_name}'")
    command.revision(config, message=message, autogenerate=True)


def upgrade_db(db_name, config_path, revision="head", sql=False):
    """
    Upgrade the database to a specific revision or latest migration.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        revision (str): Target revision (default: "head").
        sql (bool): If True, don't emit SQL to database.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option(
        "sqlalchemy.url",
        generate_db_url(db_name),
    )
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Upgrading {db_name} to revision {revision}.")
    command.upgrade(config, revision, sql=sql)


def downgrade_db(db_name, revision, config_path, sql=False):
    """
    Downgrade the database to a specific revision.

    Args:
        db_name (str): The database name.
        revision (str): The target revision for the downgrade.
        config_path (str): Path to the Alembic configuration file.
        sql (bool): If True, don't emit SQL to database.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Downgrading {db_name} to revision {revision}.")
    command.downgrade(config=config, revision=revision, sql=sql)


def show_current(db_name, config_path, verbose=False):
    """
    Display the current revision for a database.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        verbose (bool): Verbose output.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Current revision for {db_name}:")
    command.current(config, verbose=verbose)


def show_history(
    db_name,
    config_path,
    rev_range=None,
    verbose=False,
    indicate_current=False,
    head_only=False,
):
    """
    List changeset scripts in chronological order.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        rev_range (str, optional): Revision range.
        verbose (bool): Verbose output.
        indicate_current (bool): Indicate current revision.
        head_only (bool): Show only heads.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"History for {db_name}:")
    command.history(
        config,
        rev_range=rev_range,
        verbose=verbose,
        indicate_current=indicate_current,
        head_only=head_only,
    )


def show_revision(db_name, config_path, revision, verbose=False):
    """
    Show the revision(s) denoted by the given symbol.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        revision (str): The revision to show.
        verbose (bool): Verbose output.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Showing revision {revision} for {db_name}:")
    command.show(config, revision, verbose=verbose)


def stamp_revision(db_name, config_path, revision, sql=False):
    """
    'Stamp' the revision table with the given revision; don't run any migrations.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        revision (str): The revision to stamp.
        sql (bool): If True, don't emit SQL to database.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Stamping {db_name} with revision {revision}.")
    command.stamp(config, revision, sql=sql)


def check_revision(db_name, config_path):
    """
    Check if there are new upgrade operations available.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Checking {db_name} for new upgrade operations:")
    command.check(config)


def merge_revisions(
    db_name, config_path, revisions, message, resolve_dependencies=False
):
    """
    Merge two revisions together, creating a new revision file.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        revisions (str): Comma-separated list of revisions to merge.
        message (str): Revision message.
        resolve_dependencies (bool): Resolve dependencies.

    Returns:
        None
    """
    versions_dir = os.path.join("alembic", "versions")
    os.makedirs(versions_dir, exist_ok=True)

    config = Config(config_path)
    config.set_main_option("version_locations", versions_dir)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    print(f"Merging revisions {revisions} for {db_name}.")
    command.merge(
        config,
        revisions=revisions.split(","),
        message=message,
        resolve_dependencies=resolve_dependencies,
    )


def show_branches(db_name, config_path, verbose=False):
    """
    Show current branch points.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        verbose (bool): Verbose output.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Branch points for {db_name}:")
    command.branches(config, verbose=verbose)


def show_heads(db_name, config_path, verbose=False, resolve_dependencies=False):
    """
    Show current available heads in the script directory.

    Args:
        db_name (str): The database name.
        config_path (str): Path to the Alembic configuration file.
        verbose (bool): Verbose output.
        resolve_dependencies (bool): Resolve dependencies.

    Returns:
        None
    """
    config = Config(config_path)
    config.set_main_option("sqlalchemy.url", generate_db_url(db_name))
    config.set_main_option("version_locations", os.path.join("alembic", "versions"))
    print(f"Heads for {db_name}:")
    command.heads(config, verbose=verbose, resolve_dependencies=resolve_dependencies)


def migrate_database(
    db_name,
    action,
    config_path,
    message=None,
    revision=None,
    sql=False,
    verbose=False,
    indicate_current=False,
    rev_range=None,
    resolve_dependencies=False,
    revisions=None,
    head_only=False,
):
    """
    Perform a migration action on a specific database.

    Args:
        db_name (str): The database name.
        action (str): The action to perform.
        config_path (str): Path to the Alembic configuration file.
        message (str, optional): Revision message (required for 'revision' and 'merge').
        revision (str, optional): Target revision (required for 'downgrade', 'show', 'stamp').
        sql (bool): If True, don't emit SQL to database.
        verbose (bool): Verbose output.
        indicate_current (bool): Indicate current revision.
        rev_range (str, optional): Revision range (for 'history').
        resolve_dependencies (bool): Resolve dependencies (for 'merge' and 'heads').
        revisions (str, optional): Comma-separated revisions (required for 'merge').
        head_only (bool): Show only heads (for 'history').

    Returns:
        None
    """
    if action == "revision":
        if not message:
            print("Error: Revision message is required for 'revision'.")
            return
        create_revision(db_name, config_path, message)
    elif action == "upgrade":
        target_revision = revision if revision else "head"
        upgrade_db(db_name, config_path, target_revision, sql=sql)
    elif action == "downgrade":
        if not revision:
            print("Error: Revision is required for 'downgrade'.")
            return
        downgrade_db(db_name, revision, config_path, sql=sql)
    elif action == "current":
        show_current(db_name, config_path, verbose)
    elif action == "history":
        show_history(
            db_name, config_path, rev_range, verbose, indicate_current, head_only
        )
    elif action == "show":
        if not revision:
            print("Error: Revision is required for 'show'.")
            return
        show_revision(db_name, config_path, revision, verbose)
    elif action == "stamp":
        if not revision:
            print("Error: Revision is required for 'stamp'.")
            return
        stamp_revision(db_name, config_path, revision, sql=sql)
    elif action == "check":
        check_revision(db_name, config_path)
    elif action == "merge":
        if not revisions:
            print("Error: Revisions are required for 'merge'.")
            return
        if not message:
            print("Error: Revision message is required for 'merge'.")
            return
        merge_revisions(db_name, config_path, revisions, message, resolve_dependencies)
    elif action == "branches":
        show_branches(db_name, config_path, verbose)
    elif action == "heads":
        show_heads(db_name, config_path, verbose, resolve_dependencies)
    else:
        print(f"Error: Invalid action '{action}'.")


def migrate_all(
    action,
    config_path,
    message=None,
    revision=None,
    sql=False,
    verbose=False,
    indicate_current=False,
    rev_range=None,
    resolve_dependencies=False,
    revisions=None,
    head_only=False,
):
    """
    Perform a migration action on all databases.

    Args:
        action (str): The action to perform.
        config_path (str): Path to the Alembic configuration file.
        message (str, optional): Revision message (required for 'revision' and 'merge').
        revision (str, optional): Target revision (required for 'downgrade', 'show', 'stamp').
        sql (bool): If True, don't emit SQL to database.
        verbose (bool): Verbose output.
        indicate_current (bool): Indicate current revision.
        rev_range (str, optional): Revision range (for 'history').
        resolve_dependencies (bool): Resolve dependencies (for 'merge' and 'heads').
        revisions (str, optional): Comma-separated revisions (required for 'merge').
        head_only (bool): Show only heads (for 'history').

    Returns:
        None
    """
    for db_name in DATABASES:
        migrate_database(
            db_name,
            action,
            config_path,
            message,
            revision,
            sql,
            verbose,
            indicate_current,
            rev_range,
            resolve_dependencies,
            revisions,
            head_only,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run Alembic migrations for databases."
    )
    parser.add_argument(
        "action",
        choices=[
            "revision",
            "upgrade",
            "downgrade",
            "current",
            "history",
            "show",
            "stamp",
            "check",
            "merge",
            "branches",
            "heads",
        ],
        help="Action to perform.",
    )
    parser.add_argument(
        "--db",
        help="Specify a database to run the migration for. Defaults to settings.DB_NAME.",
    )
    parser.add_argument(
        "--message", help="Revision message (required for 'revision' and 'merge')."
    )
    parser.add_argument(
        "--revision",
        help="Target revision (required for 'downgrade', 'upgrade', 'show', 'stamp').",
    )
    parser.add_argument(
        "--revisions",
        help="Comma-separated revisions to merge (required for 'merge').",
    )
    parser.add_argument(
        "--indicate-current",
        action="store_true",
        help="Indicate current revision (for 'current' and 'history').",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose output.")
    parser.add_argument("--rev-range", help="Revision range (for 'history').")
    parser.add_argument(
        "--head-only",
        action="store_true",
        help="Show only heads (for 'history').",
    )
    parser.add_argument(
        "--sql",
        action="store_true",
        help="Don't emit SQL to database (for 'upgrade', 'downgrade', 'stamp').",
    )
    parser.add_argument(
        "--resolve-dependencies",
        action="store_true",
        help="Resolve dependencies (for 'merge' and 'heads').",
    )
    args = parser.parse_args()

    # Path to the Alembic configuration file
    config_path = "./alembic.ini"

    # Handle validation for actions that require specific arguments
    if args.action == "downgrade" and not args.revision:
        print("Error: Missing revision for 'downgrade'.")
        exit(1)
    if args.action == "show" and not args.revision:
        print("Error: Missing revision for 'show'.")
        exit(1)
    if args.action == "stamp" and not args.revision:
        print("Error: Missing revision for 'stamp'.")
        exit(1)
    if args.action == "merge" and not args.revisions:
        print("Error: Missing revisions for 'merge'.")
        exit(1)
    if args.action == "merge" and not args.message:
        print("Error: Missing message for 'merge'.")
        exit(1)

    # Default database name if --db is not provided
    db_name = args.db if args.db else settings.DB_NAME

    # Run migrations for a single database or all databases
    if db_name:
        if db_name in DATABASES or db_name == settings.DB_NAME:
            migrate_database(
                db_name,
                args.action,
                config_path,
                args.message,
                args.revision,
                args.sql,
                args.verbose,
                args.indicate_current,
                args.rev_range,
                args.resolve_dependencies,
                args.revisions,
                args.head_only,
            )
        else:
            print(f"Error: Database '{db_name}' not found in the list of databases.")
    else:
        migrate_all(
            args.action,
            config_path,
            args.message,
            args.revision,
            args.sql,
            args.verbose,
            args.indicate_current,
            args.rev_range,
            args.resolve_dependencies,
            args.revisions,
            args.head_only,
        )


"""
Examples:

# Revision commands
python alembic_cli.py revision --db dev --message "Add users table"
python alembic_cli.py revision --message "Add users table"

# Upgrade commands
python alembic_cli.py upgrade --db dev
python alembic_cli.py upgrade --db dev --revision abc123456
python alembic_cli.py upgrade --db dev --revision head --sql

# Downgrade commands
python alembic_cli.py downgrade --db dev --revision abc123456
python alembic_cli.py downgrade --db dev --revision abc123456 --sql

# Current revision
python alembic_cli.py current --db dev
python alembic_cli.py current --db dev --verbose

# History
python alembic_cli.py history --db dev
python alembic_cli.py history --db dev --verbose --indicate-current
python alembic_cli.py history --db dev --rev-range abc123:def456
python alembic_cli.py history --db dev --head-only

# Show revision
python alembic_cli.py show --db dev --revision abc123456
python alembic_cli.py show --db dev --revision abc123456 --verbose

# Stamp revision
python alembic_cli.py stamp --db dev --revision abc123456
python alembic_cli.py stamp --db dev --revision abc123456 --sql

# Check for new upgrades
python alembic_cli.py check --db dev

# Merge revisions
python alembic_cli.py merge --db dev --revisions abc123,def456 --message "Merge branches"
python alembic_cli.py merge --db dev --revisions abc123,def456 --message "Merge" --resolve-dependencies

# Show branches
python alembic_cli.py branches --db dev
python alembic_cli.py branches --db dev --verbose

# Show heads
python alembic_cli.py heads --db dev
python alembic_cli.py heads --db dev --verbose --resolve-dependencies
"""
