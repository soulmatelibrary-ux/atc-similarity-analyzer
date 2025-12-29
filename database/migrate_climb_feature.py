"""
Database Migration Script for Climb Feature

This script adds new columns and tables to support aircraft-type-based speed
and climb rate calculations.

Migration Steps:
1. Add columns to flights table (if not exist)
2. Add columns to waypoint_times table (if not exist)
3. Create climb_calculations table (if not exist)
4. Verify schema changes

Usage:
    python migrate_climb_feature.py [--dry-run] [--backup]

Options:
    --dry-run: Show what would be changed without executing
    --backup: Create backup before migration (default: False)
"""

import sqlite3
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil


class DatabaseMigration:
    """Handle database schema migration for climb feature"""

    def __init__(self, db_path, dry_run=False, backup=False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.backup = backup
        self.migrations_completed = []
        self.migrations_skipped = []
        self.errors = []

    def log(self, message, level='INFO'):
        """Log migration messages"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")

    def backup_database(self):
        """Create backup of database before migration"""
        if not os.path.exists(self.db_path):
            self.log(f"Database {self.db_path} not found", 'WARNING')
            return False

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{self.db_path}.backup_{timestamp}"

        try:
            shutil.copy2(self.db_path, backup_path)
            self.log(f"Database backed up to {backup_path}", 'SUCCESS')
            return True
        except Exception as e:
            self.log(f"Failed to backup database: {e}", 'ERROR')
            self.errors.append(f"Backup failed: {e}")
            return False

    def execute_sql(self, sql, description):
        """Execute SQL statement safely"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if self.dry_run:
                self.log(f"[DRY RUN] {description}", 'INFO')
                self.log(f"SQL: {sql}", 'DEBUG')
                self.migrations_skipped.append(description)
            else:
                cursor.execute(sql)
                conn.commit()
                self.log(f"✓ {description}", 'SUCCESS')
                self.migrations_completed.append(description)

            conn.close()
            return True

        except sqlite3.OperationalError as e:
            if "already exists" in str(e) or "duplicate column" in str(e):
                self.log(f"⊘ {description} (already exists)", 'SKIP')
                self.migrations_skipped.append(description)
                return True  # Not an error, column already exists
            else:
                self.log(f"✗ {description}: {e}", 'ERROR')
                self.errors.append(f"{description}: {e}")
                return False

        except Exception as e:
            self.log(f"✗ {description}: {e}", 'ERROR')
            self.errors.append(f"{description}: {e}")
            return False

    def add_flights_columns(self):
        """Add new columns to flights table"""
        columns = [
            ('calculated_speed_kmh', 'INTEGER', 'Speed calculation result in km/h'),
            ('speed_source', 'TEXT', "Source of speed: 'csv' | 'aircraft_profile' | 'default'"),
            ('climb_rate_fpm', 'INTEGER', 'Climb rate in feet per minute'),
            ('cruise_flight_level', 'INTEGER', 'Cruise Flight Level (CFL in Flight Levels)'),
            ('is_climbing', 'BOOLEAN DEFAULT 0', 'Whether flight is in climb phase at key points')
        ]

        for col_name, col_type, col_desc in columns:
            sql = f"ALTER TABLE flights ADD COLUMN {col_name} {col_type};"
            self.execute_sql(sql, f"Add {col_name} to flights table ({col_desc})")

    def add_waypoint_times_columns(self):
        """Add new columns to waypoint_times table"""
        columns = [
            ('altitude_ft', 'INTEGER', 'Altitude at waypoint in feet'),
            ('is_climbing', 'BOOLEAN DEFAULT 0', 'Whether aircraft is climbing at waypoint'),
            ('time_method', 'TEXT', "Calculation method used: 'simple_linear' | 'eet_backtrack'")
        ]

        for col_name, col_type, col_desc in columns:
            sql = f"ALTER TABLE waypoint_times ADD COLUMN {col_name} {col_type};"
            self.execute_sql(sql, f"Add {col_name} to waypoint_times table ({col_desc})")

    def create_climb_calculations_table(self):
        """Create climb_calculations table for method comparison"""
        sql = """
        CREATE TABLE IF NOT EXISTS climb_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            flight_id INTEGER NOT NULL,
            waypoint_name TEXT NOT NULL,
            waypoint_sequence INTEGER,

            -- 방법 A: 단순 선형 상승
            simple_linear_time TIME,
            simple_linear_altitude_ft INTEGER,
            simple_linear_distance_km REAL,

            -- 방법 B: EET 역계산
            eet_backtrack_time TIME,
            eet_backtrack_altitude_ft INTEGER,
            eet_backtrack_distance_km REAL,

            -- 비교 지표
            time_difference_seconds INTEGER,
            altitude_difference_ft INTEGER,

            -- 메타데이터
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(flight_id) REFERENCES flights(id) ON DELETE CASCADE
        );
        """
        self.execute_sql(sql, "Create climb_calculations table")

    def create_climb_calculations_indexes(self):
        """Create indexes for climb_calculations table"""
        indexes = [
            ('idx_climb_calculations_flight_id', 'CREATE INDEX IF NOT EXISTS idx_climb_calculations_flight_id ON climb_calculations(flight_id);'),
            ('idx_climb_calculations_waypoint', 'CREATE INDEX IF NOT EXISTS idx_climb_calculations_waypoint ON climb_calculations(waypoint_name);'),
            ('idx_climb_calculations_sequence', 'CREATE INDEX IF NOT EXISTS idx_climb_calculations_sequence ON climb_calculations(waypoint_sequence);')
        ]

        for idx_name, sql in indexes:
            self.execute_sql(sql, f"Create {idx_name}")

    def verify_schema(self):
        """Verify that all expected columns exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check flights table columns
            cursor.execute("PRAGMA table_info(flights)")
            flights_cols = {row[1] for row in cursor.fetchall()}

            expected_flights_cols = {
                'calculated_speed_kmh', 'speed_source', 'climb_rate_fpm',
                'cruise_flight_level', 'is_climbing'
            }

            missing_flights = expected_flights_cols - flights_cols
            if missing_flights:
                self.log(f"Missing columns in flights table: {missing_flights}", 'WARNING')
            else:
                self.log("✓ All expected columns exist in flights table", 'SUCCESS')

            # Check waypoint_times table columns
            cursor.execute("PRAGMA table_info(waypoint_times)")
            waypoint_cols = {row[1] for row in cursor.fetchall()}

            expected_waypoint_cols = {'altitude_ft', 'is_climbing', 'time_method'}
            missing_waypoint = expected_waypoint_cols - waypoint_cols
            if missing_waypoint:
                self.log(f"Missing columns in waypoint_times table: {missing_waypoint}", 'WARNING')
            else:
                self.log("✓ All expected columns exist in waypoint_times table", 'SUCCESS')

            # Check climb_calculations table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='climb_calculations'")
            if cursor.fetchone():
                self.log("✓ climb_calculations table exists", 'SUCCESS')
            else:
                self.log("✗ climb_calculations table does not exist", 'ERROR')

            conn.close()
            return True

        except Exception as e:
            self.log(f"Verification failed: {e}", 'ERROR')
            return False

    def run(self):
        """Execute migration"""
        self.log("=" * 80, 'INFO')
        self.log("Starting Database Migration for Climb Feature", 'INFO')
        self.log("=" * 80, 'INFO')

        if self.dry_run:
            self.log("DRY RUN MODE - No changes will be made", 'WARNING')

        # Backup if requested
        if self.backup and not self.dry_run:
            if not self.backup_database():
                self.log("Backup failed, aborting migration", 'ERROR')
                return False

        # Check database exists
        if not os.path.exists(self.db_path):
            self.log(f"Database not found: {self.db_path}", 'ERROR')
            return False

        # Run migrations
        self.log("\n1. Adding columns to flights table...", 'INFO')
        self.add_flights_columns()

        self.log("\n2. Adding columns to waypoint_times table...", 'INFO')
        self.add_waypoint_times_columns()

        self.log("\n3. Creating climb_calculations table...", 'INFO')
        self.create_climb_calculations_table()
        self.create_climb_calculations_indexes()

        self.log("\n4. Verifying schema...", 'INFO')
        self.verify_schema()

        # Summary
        self.log("\n" + "=" * 80, 'INFO')
        self.log("Migration Summary", 'INFO')
        self.log("=" * 80, 'INFO')
        self.log(f"Completed: {len(self.migrations_completed)}", 'INFO')
        for item in self.migrations_completed:
            self.log(f"  ✓ {item}", 'INFO')

        if self.migrations_skipped:
            self.log(f"Skipped: {len(self.migrations_skipped)}", 'INFO')
            for item in self.migrations_skipped:
                self.log(f"  ⊘ {item}", 'INFO')

        if self.errors:
            self.log(f"Errors: {len(self.errors)}", 'ERROR')
            for error in self.errors:
                self.log(f"  ✗ {error}", 'ERROR')
            return False

        self.log("\n✓ Migration completed successfully!", 'SUCCESS')
        return True


def main():
    parser = argparse.ArgumentParser(
        description='Database migration for climb feature'
    )
    parser.add_argument(
        '--db',
        default='database.db',
        help='Path to database file (default: database.db)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without executing'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before migration'
    )

    args = parser.parse_args()

    # Convert to absolute path
    db_path = os.path.abspath(args.db)

    # Run migration
    migration = DatabaseMigration(db_path, dry_run=args.dry_run, backup=args.backup)
    success = migration.run()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
