#!/usr/bin/env python3
"""
Test script for SQLite database integration
Tests the complete flow: file upload -> DB storage -> similarity detection -> statistics
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from core.flight_service import FlightService
from utils.file_validator import FileValidator
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_database_integration():
    """Test the complete database integration flow"""

    try:
        # 1. Initialize database and services
        print("\n" + "="*60)
        print("TEST 1: Initialize Database and Services")
        print("="*60)

        db_path = os.path.join(os.path.dirname(__file__), 'database', 'test_similarity_detector.db')
        db_manager = DatabaseManager(db_path)
        flight_service = FlightService(db_manager)

        print(f"✓ Database initialized at: {db_path}")
        print(f"✓ FlightService initialized")

        # 2. Validate and load flight data from CSV
        print("\n" + "="*60)
        print("TEST 2: Validate and Load Flight Data")
        print("="*60)

        csv_path = os.path.join(os.path.dirname(__file__), 'uploads', 't_flightplan.csv')
        if not os.path.exists(csv_path):
            print(f"✗ CSV file not found: {csv_path}")
            return False

        validator = FileValidator()
        validation_result = validator.validate_file(csv_path)

        if validation_result['status'] == 'invalid':
            print(f"✗ File validation failed:")
            for error in validation_result['errors']:
                print(f"  - {error}")
            return False

        flights_data = validation_result['data'].to_dict('records')
        print(f"✓ File validated successfully: {len(flights_data)} flights")

        if validation_result['warnings']:
            print(f"⚠ Warnings:")
            for warning in validation_result['warnings']:
                print(f"  - {warning}")

        # 3. Process and save flights to database
        print("\n" + "="*60)
        print("TEST 3: Process and Save Flights to Database")
        print("="*60)

        file_size = os.path.getsize(csv_path)
        service_result = flight_service.process_and_save_flights(
            flights_data,
            'test_t_flightplan.csv',
            file_size
        )

        if service_result['status'] != 'success':
            print(f"✗ Flight processing failed: {service_result['message']}")
            return False

        print(f"✓ {service_result['inserted_count']} flights saved to database")
        if service_result.get('error_count', 0) > 0:
            print(f"⚠ {service_result['error_count']} flights had errors")

        # 4. Verify flights are in database
        print("\n" + "="*60)
        print("TEST 4: Verify Flights in Database")
        print("="*60)

        db_flights = db_manager.get_all_flights(limit=5)
        print(f"✓ Total flights in database: {len(db_manager.get_all_flights())}")
        print(f"✓ Sample flights (first 5):")
        for flight in db_flights[:5]:
            print(f"  - {flight['callsign']} ({flight['id']}): DEPT={flight['dept_airport_cd']} → DEST={flight['dest_airport_cd']}")

        # 5. Run similarity detection
        print("\n" + "="*60)
        print("TEST 5: Run Similarity Detection")
        print("="*60)

        min_overlap = 2
        detection_result = flight_service.detect_similarities(min_overlap)

        if detection_result['status'] != 'success':
            print(f"✗ Similarity detection failed: {detection_result['message']}")
            return False

        print(f"✓ {detection_result['similarity_count']} similarity pairs detected")

        # 6. Verify similarities in database
        print("\n" + "="*60)
        print("TEST 6: Verify Similarities in Database")
        print("="*60)

        similarities = db_manager.get_similarities(min_overlap, limit=10)
        print(f"✓ Total similarities with {min_overlap}+ min overlap: {len(db_manager.get_similarities(min_overlap, limit=10000))}")
        print(f"✓ Sample similarities (first 10):")

        for sim in similarities[:10]:
            sim_dict = dict(sim)
            print(f"  - {sim_dict['callsign_1']} ↔ {sim_dict['callsign_2']}: "
                  f"Level={sim_dict['similarity_level']}, "
                  f"Overlap={sim_dict['total_overlap_minutes']}min, "
                  f"Sectors={sim_dict['overlap_count']}")

        # 7. Get statistics
        print("\n" + "="*60)
        print("TEST 7: Get Statistics from Database")
        print("="*60)

        stats = db_manager.get_statistics()
        print(f"✓ Statistics:")
        print(f"  - Total flights: {stats['total_flights']}")
        print(f"  - Total similarities: {stats['total_similarities']}")
        print(f"  - Similarities with overlap: {stats['similarities_with_overlap']}")
        print(f"  - Similarity levels: {stats['level_distribution']}")
        if stats['sector_statistics']:
            print(f"  - Top 3 sectors by overlap count:")
            for sector in stats['sector_statistics'][:3]:
                print(f"    • {sector['sector_name']}: {sector['count']} overlaps, "
                      f"avg {sector['avg_minutes']:.1f} min")

        # 8. Test get_similarity_details
        print("\n" + "="*60)
        print("TEST 8: Get Similarity Details")
        print("="*60)

        if similarities:
            first_sim = dict(similarities[0])
            details = db_manager.get_similarity_details(first_sim['id'])
            if details:
                print(f"✓ Retrieved details for similarity ID {first_sim['id']}:")
                print(f"  - {details['callsign_1']} ↔ {details['callsign_2']}")
                print(f"  - Level: {details['similarity_level']}")
                print(f"  - Score: {details['similarity_score']}")
                print(f"  - Sector overlaps: {len(details['sector_overlaps'])}")
                if details['sector_overlaps']:
                    print(f"  - Sample sector overlaps:")
                    for overlap in details['sector_overlaps'][:3]:
                        print(f"    • {overlap['sector_name']}: "
                              f"{overlap['overlap_start']}-{overlap['overlap_end']} "
                              f"({overlap['overlap_minutes']}min)")

        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        return True

    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_database_integration()
    sys.exit(0 if success else 1)
