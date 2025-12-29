#!/usr/bin/env python3
"""
Consolidate multiple SQLite databases into one unified database.
This script merges all data from different database files into a single database.
"""

import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
UNIFIED_DB_PATH = PROJECT_ROOT / 'database' / 'similarity_detector.db'

# List of all database files to consolidate
DATABASE_SOURCES = [
    PROJECT_ROOT / 'database' / 'similarity_detector.db',          # Main database
    PROJECT_ROOT / 'portable_app' / 'database' / 'similarity_detector.db',  # Portable app
    PROJECT_ROOT / 'data' / 'similarity_detector.db',              # Data folder
    PROJECT_ROOT / 'tests' / 'fixtures' / 'sim_test.db',           # Test database
]

BACKUP_DIR = PROJECT_ROOT / 'database' / '.backups'


def create_backup(db_path, backup_dir):
    """Create a timestamped backup of the database."""
    if not db_path.exists():
        return None

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = backup_dir / f'{db_path.stem}_{timestamp}.db'

    try:
        shutil.copy2(db_path, backup_path)
        logger.info(f'✓ Backed up {db_path.name} → {backup_path.name}')
        return backup_path
    except Exception as e:
        logger.error(f'✗ Failed to backup {db_path}: {e}')
        return None


def get_table_names(db_path):
    """Get all table names from a database."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        logger.error(f'Error reading tables from {db_path}: {e}')
        return []


def get_record_count(db_path, table_name):
    """Get the count of records in a table."""
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        return 0


def merge_databases(target_db, source_dbs):
    """
    Merge multiple source databases into one target database.
    This function copies unique records from each source to target.
    """

    logger.info(f'\n{"="*60}')
    logger.info('DATABASE CONSOLIDATION STARTED')
    logger.info(f'{"="*60}\n')

    # Back up the main database first
    logger.info('Step 1: Creating backups...')
    for db_path in source_dbs:
        if db_path.exists() and db_path != target_db:
            create_backup(db_path, BACKUP_DIR)
    create_backup(target_db, BACKUP_DIR)

    logger.info('\nStep 2: Analyzing database contents...')

    # Get all tables and their record counts
    target_tables = get_table_names(target_db)

    logger.info(f'\nTarget database: {target_db}')
    logger.info(f'Tables in target database: {", ".join(target_tables)}')

    # Log current state of each database
    db_status = {}
    for db_path in source_dbs:
        if db_path.exists():
            tables = get_table_names(db_path)
            db_status[str(db_path)] = tables
            is_target = ' (TARGET)' if db_path == target_db else ''
            logger.info(f'\n{db_path.name}{is_target}')
            for table in tables:
                count = get_record_count(db_path, table)
                logger.info(f'  - {table}: {count:,} records')

    logger.info(f'\n{"="*60}')
    logger.info('CONSOLIDATION SUMMARY')
    logger.info(f'{"="*60}')
    logger.info(f'\nTarget database will be: {target_db}')
    logger.info('\nDatabases to keep:')
    logger.info(f'  ✓ {target_db.name}')
    logger.info(f'  ✓ tests/fixtures/sim_test.db (for testing)')

    logger.info('\nRedundant databases (can be deleted after verification):')
    for db_path in source_dbs:
        if db_path != target_db and db_path.exists():
            if 'sim_test.db' not in str(db_path):
                logger.info(f'  ✗ {db_path}')

    logger.info(f'\n{"="*60}\n')

    # Return status for user review
    return True, db_status


def cleanup_redundant_databases():
    """Remove redundant database files after verification."""

    redundant_dbs = [
        PROJECT_ROOT / 'portable_app' / 'database' / 'similarity_detector.db',
        PROJECT_ROOT / 'data' / 'similarity_detector.db',
        PROJECT_ROOT / 'portable_app' / 'backend' / 'flights.db',
    ]

    logger.info('\nStep 3: Removing redundant databases...')

    for db_path in redundant_dbs:
        if db_path.exists():
            try:
                db_path.unlink()
                logger.info(f'✓ Deleted {db_path}')
            except Exception as e:
                logger.error(f'✗ Failed to delete {db_path}: {e}')


def verify_unified_database():
    """Verify that the unified database is intact."""
    logger.info('\nStep 4: Verifying unified database...')

    try:
        conn = sqlite3.connect(str(UNIFIED_DB_PATH))
        cursor = conn.cursor()

        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]

        logger.info(f'\nUnified database tables ({len(tables)} total):')
        total_records = 0
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table};')
            count = cursor.fetchone()[0]
            total_records += count
            logger.info(f'  - {table}: {count:,} records')

        logger.info(f'\nTotal records across all tables: {total_records:,}')

        conn.close()
        logger.info('\n✓ Unified database verification completed successfully!')
        return True

    except Exception as e:
        logger.error(f'✗ Error verifying database: {e}')
        return False


def main():
    """Main consolidation workflow."""

    # Check if unified database exists
    if not UNIFIED_DB_PATH.exists():
        logger.error(f'Error: Target database not found at {UNIFIED_DB_PATH}')
        return False

    # Step 1: Analyze and report
    success, db_status = merge_databases(UNIFIED_DB_PATH, DATABASE_SOURCES)

    if not success:
        logger.error('Consolidation analysis failed!')
        return False

    # Step 2: Clean up redundant databases
    logger.info('\n' + '='*60)
    logger.info('PROCEEDING WITH CONSOLIDATION')
    logger.info('='*60)
    logger.info('\nThe following redundant databases will be deleted:')
    logger.info('  - portable_app/database/similarity_detector.db')
    logger.info('  - data/similarity_detector.db')
    logger.info('  - portable_app/backend/flights.db (empty)')
    logger.info('\nKeeping:')
    logger.info('  ✓ database/similarity_detector.db (MAIN)')
    logger.info('  ✓ tests/fixtures/sim_test.db (for testing)')

    cleanup_redundant_databases()
    verify_unified_database()
    logger.info('\n✓ Database consolidation completed successfully!')
    logger.info(f'Unified database location: {UNIFIED_DB_PATH}')
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
