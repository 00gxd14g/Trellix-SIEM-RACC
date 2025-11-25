#!/usr/bin/env python3
"""
Apply Database Migration Scripts

This script applies manual SQL migration scripts to the database.

Usage:
    python apply_migrations.py --upgrade    # Apply all pending migrations
    python apply_migrations.py --downgrade  # Rollback last migration
    python apply_migrations.py --verify     # Verify migrations

Author: Database Optimizer Agent
"""

import os
import sys
import argparse
import sqlite3
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_database_path():
    """Get database path from config"""
    backend_dir = Path(__file__).parent.parent
    db_path = backend_dir / 'database' / 'app.db'
    return str(db_path)


def create_migrations_table(conn):
    """Create migrations tracking table if it doesn't exist"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version VARCHAR(255) NOT NULL UNIQUE,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    """)
    conn.commit()
    logger.info("Migrations tracking table ready")


def get_applied_migrations(conn):
    """Get list of applied migrations"""
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY version")
    return {row[0] for row in cursor.fetchall()}


def get_available_migrations():
    """Get list of available migration files"""
    migrations_dir = Path(__file__).parent / 'versions' / 'manual'
    if not migrations_dir.exists():
        return []

    migration_files = sorted(migrations_dir.glob('*.sql'))
    return [(f.stem, f) for f in migration_files]


def apply_migration(conn, version, file_path, description=""):
    """Apply a single migration"""
    logger.info(f"Applying migration: {version}")

    try:
        # Read migration file
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract upgrade section
        if '-- UPGRADE:' in content and '-- DOWNGRADE:' in content:
            upgrade_section = content.split('-- DOWNGRADE:')[0]
            # Remove comments and metadata
            sql_statements = []
            for line in upgrade_section.split('\n'):
                line = line.strip()
                if line and not line.startswith('--') and not line.startswith('/*'):
                    sql_statements.append(line)
            sql = '\n'.join(sql_statements)
        else:
            sql = content

        # Execute migration
        cursor = conn.cursor()
        cursor.executescript(sql)

        # Record migration
        cursor.execute(
            "INSERT INTO schema_migrations (version, description) VALUES (?, ?)",
            (version, description)
        )
        conn.commit()

        logger.info(f"Successfully applied migration: {version}")
        return True

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to apply migration {version}: {e}")
        return False


def rollback_migration(conn, version, file_path):
    """Rollback a single migration"""
    logger.info(f"Rolling back migration: {version}")

    try:
        # Read migration file
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract downgrade section
        if '-- DOWNGRADE:' in content:
            downgrade_section = content.split('-- DOWNGRADE:')[1]
            if '-- VERIFICATION' in downgrade_section:
                downgrade_section = downgrade_section.split('-- VERIFICATION')[0]

            # Extract SQL from comments
            sql_statements = []
            in_comment_block = False
            for line in downgrade_section.split('\n'):
                line = line.strip()
                if line.startswith('/*'):
                    in_comment_block = True
                    continue
                if line.endswith('*/'):
                    in_comment_block = False
                    continue
                if in_comment_block and line and not line.startswith('--'):
                    sql_statements.append(line)

            if sql_statements:
                sql = '\n'.join(sql_statements)

                # Execute rollback
                cursor = conn.cursor()
                cursor.executescript(sql)

                # Remove migration record
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (version,))
                conn.commit()

                logger.info(f"Successfully rolled back migration: {version}")
                return True
            else:
                logger.warning(f"No downgrade script found for migration: {version}")
                return False

    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to rollback migration {version}: {e}")
        return False


def upgrade(db_path):
    """Apply all pending migrations"""
    conn = sqlite3.connect(db_path)
    create_migrations_table(conn)

    applied = get_applied_migrations(conn)
    available = get_available_migrations()

    pending = [(v, p) for v, p in available if v not in applied]

    if not pending:
        logger.info("No pending migrations to apply")
        conn.close()
        return

    logger.info(f"Found {len(pending)} pending migrations")

    for version, file_path in pending:
        if not apply_migration(conn, version, file_path):
            logger.error("Migration failed, stopping")
            break

    conn.close()
    logger.info("Migration process completed")


def downgrade(db_path):
    """Rollback the last applied migration"""
    conn = sqlite3.connect(db_path)
    create_migrations_table(conn)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT version FROM schema_migrations
        ORDER BY applied_at DESC LIMIT 1
    """)
    result = cursor.fetchone()

    if not result:
        logger.info("No migrations to rollback")
        conn.close()
        return

    last_version = result[0]
    logger.info(f"Rolling back migration: {last_version}")

    # Find migration file
    available = get_available_migrations()
    migration_file = None
    for version, file_path in available:
        if version == last_version:
            migration_file = file_path
            break

    if migration_file:
        rollback_migration(conn, last_version, migration_file)
    else:
        logger.error(f"Migration file not found for version: {last_version}")

    conn.close()


def verify(db_path):
    """Verify migrations status"""
    conn = sqlite3.connect(db_path)
    create_migrations_table(conn)

    applied = get_applied_migrations(conn)
    available = get_available_migrations()

    logger.info("\n" + "=" * 60)
    logger.info("MIGRATION STATUS")
    logger.info("=" * 60)

    logger.info(f"\nTotal available migrations: {len(available)}")
    logger.info(f"Applied migrations: {len(applied)}")
    logger.info(f"Pending migrations: {len(available) - len(applied)}")

    logger.info("\nApplied Migrations:")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT version, applied_at, description
        FROM schema_migrations
        ORDER BY applied_at
    """)
    for row in cursor.fetchall():
        version, applied_at, description = row
        logger.info(f"  - {version} (applied: {applied_at})")

    pending = [(v, p) for v, p in available if v not in applied]
    if pending:
        logger.info("\nPending Migrations:")
        for version, _ in pending:
            logger.info(f"  - {version}")

    logger.info("\n" + "=" * 60)

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Apply database migrations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--upgrade',
        action='store_true',
        help='Apply all pending migrations'
    )
    parser.add_argument(
        '--downgrade',
        action='store_true',
        help='Rollback the last migration'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify migrations status'
    )
    parser.add_argument(
        '--db',
        type=str,
        help='Database path (default: auto-detect)'
    )

    args = parser.parse_args()

    # Get database path
    db_path = args.db or get_database_path()

    if not os.path.exists(db_path):
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    logger.info(f"Using database: {db_path}")

    # Execute command
    if args.upgrade:
        upgrade(db_path)
    elif args.downgrade:
        downgrade(db_path)
    elif args.verify:
        verify(db_path)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
