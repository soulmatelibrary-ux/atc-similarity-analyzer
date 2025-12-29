#!/usr/bin/env python3
"""
Simple test to verify database integration works
Uses a small test dataset instead of the full file
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from core.flight_service import FlightService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Clean test database
test_db = 'database/test_simple.db'
if os.path.exists(test_db):
    os.remove(test_db)
if os.path.exists(f"{test_db}-wal"):
    os.remove(f"{test_db}-wal")
if os.path.exists(f"{test_db}-shm"):
    os.remove(f"{test_db}-shm")

try:
    # 1. Create a small test dataset
    print("\n=== TEST 1: Create small test dataset ===")
    test_flights = [
        {
            'CALLSIGN': 'AAL101',
            'DEPT_AIRPORT_CD': 'KJFK',
            'DEST_AIRPORT_CD': 'KLAX',
            'AIRCRAFT_TYPE': 'B777',
            'SPD': 'M450',
            'ALT': 'FL350',
            'ENR': 'AAL101',
            'INFO_CN': 'TEST',
            'EET': '0530',
            'EOBD': '2025-12-13',
            'EOBT': '10:00',
            '섹터진입진출시간': 'SEC1 1000-1010 SEC2 1015-1025'
        },
        {
            'CALLSIGN': 'UAL202',
            'DEPT_AIRPORT_CD': 'KJFK',
            'DEST_AIRPORT_CD': 'KLAX',
            'AIRCRAFT_TYPE': 'B787',
            'SPD': 'M460',
            'ALT': 'FL360',
            'ENR': 'UAL202',
            'INFO_CN': 'TEST',
            'EET': '0525',
            'EOBD': '2025-12-13',
            'EOBT': '10:05',
            '섹터진입진출시간': 'SEC1 1005-1015 SEC2 1020-1030'
        },
        {
            'CALLSIGN': 'DAL303',
            'DEPT_AIRPORT_CD': 'KORD',
            'DEST_AIRPORT_CD': 'KSFO',
            'AIRCRAFT_TYPE': 'A320',
            'SPD': 'M440',
            'ALT': 'FL340',
            'ENR': 'DAL303',
            'INFO_CN': 'TEST',
            'EET': '0400',
            'EOBD': '2025-12-13',
            'EOBT': '11:00',
            '섹터진입진출시간': 'SEC3 1100-1110 SEC4 1115-1125'
        }
    ]

    print(f"✓ Created {len(test_flights)} test flights")

    # 2. Initialize database and services
    print("\n=== TEST 2: Initialize database ===")
    db_manager = DatabaseManager(test_db)
    flight_service = FlightService(db_manager)
    print("✓ Database and services initialized")

    # 3. Process flights
    print("\n=== TEST 3: Process and save flights ===")
    result = flight_service.process_and_save_flights(
        test_flights,
        'test_flights.csv',
        1024
    )
    print(f"Result: {result['message']}")
    print(f"Inserted: {result['inserted_count']}")

    if result['inserted_count'] == 0:
        print("✗ No flights were inserted!")
        sys.exit(1)

    # 4. Verify flights in database
    print("\n=== TEST 4: Verify flights in database ===")
    db_flights = db_manager.get_all_flights()
    print(f"Total flights in DB: {len(db_flights)}")
    for flight in db_flights:
        print(f"  - {flight['callsign']}: {flight['id']}")

    # 5. Run similarity detection
    print("\n=== TEST 5: Run similarity detection ===")
    detection_result = flight_service.detect_similarities(min_overlap_minutes=2)
    print(f"Result: {detection_result['message']}")
    print(f"Similarities found: {detection_result['similarity_count']}")

    # 6. Get statistics
    print("\n=== TEST 6: Get statistics ===")
    stats = db_manager.get_statistics()
    print(f"Total flights: {stats['total_flights']}")
    print(f"Total similarities: {stats['total_similarities']}")
    print(f"Similarities with overlap: {stats['similarities_with_overlap']}")
    print(f"Level distribution: {stats['level_distribution']}")

    # 7. Get detailed similarity
    print("\n=== TEST 7: Get detailed similarity ===")
    similarities = db_manager.get_similarities(min_overlap_minutes=0, limit=10)
    if similarities:
        for sim in similarities:
            sim_dict = dict(sim)
            print(f"  {sim_dict['callsign_1']} ↔ {sim_dict['callsign_2']}: "
                  f"Level={sim_dict['similarity_level']}")
            details = db_manager.get_similarity_details(sim_dict['id'])
            if details:
                print(f"    - Sectors: {details['overlap_count']}")

    print("\n=== ✓ ALL TESTS PASSED ===\n")

except Exception as e:
    print(f"\n✗ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    if os.path.exists(test_db):
        os.remove(test_db)
    for ext in ['-wal', '-shm']:
        if os.path.exists(f"{test_db}{ext}"):
            os.remove(f"{test_db}{ext}")
