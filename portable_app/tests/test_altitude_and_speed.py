"""
Unit Tests for Altitude Parsing and Aircraft Speed Functions

Tests for:
- parse_altitude(): Parsing ICAO altitude formats
- get_aircraft_speed_and_climb(): Speed fallback mechanism
- calculate_climb_time_simple(): Method A climb calculation
- calculate_waypoints_with_eet(): Method B waypoint calculation
"""

import unittest
import sys
import os
from datetime import datetime, timedelta, time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portable_app.core.flight_processor import (
    parse_altitude,
    parse_speed,
    get_aircraft_speed_and_climb,
    calculate_climb_time_simple,
    calculate_waypoints_with_eet
)


class TestParseAltitude(unittest.TestCase):
    """Test parse_altitude() function"""

    def test_flight_level_parsing(self):
        """Test Flight Level (F) format: F400 -> 40000 feet"""
        self.assertEqual(parse_altitude('F400'), 40000)
        self.assertEqual(parse_altitude('F100'), 10000)
        self.assertEqual(parse_altitude('F350'), 35000)

    def test_standard_metric_parsing(self):
        """Test Standard Metric (S) format: S0890 -> ~2919 feet"""
        result = parse_altitude('S0890')
        # S0890 means 890 meters = 890 * 3.28084 feet ≈ 2919
        self.assertAlmostEqual(result, 2919, delta=10)

    def test_altitude_feet_parsing(self):
        """Test Altitude in feet (A) format: A0100 -> 100 feet"""
        self.assertEqual(parse_altitude('A0100'), 100)
        self.assertEqual(parse_altitude('A5000'), 5000)

    def test_metric_parsing(self):
        """Test Metric (M) format: M0500 -> ~1640 feet"""
        result = parse_altitude('M0500')
        # M0500 meters = 500 * 3.28084 feet ≈ 1640
        self.assertAlmostEqual(result, 1640, delta=10)

    def test_invalid_inputs(self):
        """Test invalid inputs return None"""
        self.assertIsNone(parse_altitude(''))
        self.assertIsNone(parse_altitude('X'))
        self.assertIsNone(parse_altitude(None))
        self.assertIsNone(parse_altitude('INVALID'))
        self.assertIsNone(parse_altitude(12345))  # Non-string


class TestParseSpeed(unittest.TestCase):
    """Test parse_speed() function"""

    def test_km_per_hour_parsing(self):
        """Test K format: K0926 -> 926 km/h"""
        self.assertEqual(parse_speed('K0926'), 926)
        self.assertEqual(parse_speed('K0500'), 500)

    def test_knots_parsing(self):
        """Test N format: N0501 -> 926 km/h (501 * 1.852)"""
        result = parse_speed('N0501')
        self.assertAlmostEqual(result, 926, delta=5)  # 501 * 1.852 ≈ 926

    def test_mach_parsing(self):
        """Test M format (Mach): M080 -> 0.8 Mach ≈ 988 km/h"""
        result = parse_speed('M080')
        # Mach 0.8 * 1235 km/h ≈ 988 km/h
        self.assertAlmostEqual(result, 988, delta=20)

    def test_invalid_inputs(self):
        """Test invalid inputs return default 800"""
        self.assertEqual(parse_speed(''), 800)
        self.assertEqual(parse_speed('INVALID'), 800)
        self.assertEqual(parse_speed(None), 800)
        self.assertEqual(parse_speed('X'), 800)


class MockDatabaseManager:
    """Mock database manager for testing"""

    def get_aircraft_profile(self, aircraft_type):
        """Return mock aircraft profile"""
        profiles = {
            'B77L': {
                'icao_code': 'B77L',
                'default_speed_kmh': 905,
                'default_climb_fpm': 2000,
                'default_ceiling_fl': 430
            },
            'A321': {
                'icao_code': 'A321',
                'default_speed_kmh': 840,
                'default_climb_fpm': 2500,
                'default_ceiling_fl': 430
            }
        }
        return profiles.get(aircraft_type)


class TestAircraftSpeedFallback(unittest.TestCase):
    """Test get_aircraft_speed_and_climb() fallback mechanism"""

    def setUp(self):
        self.db = MockDatabaseManager()

    def test_csv_spd_priority(self):
        """Priority 1: CSV SPD is used first"""
        result = get_aircraft_speed_and_climb(self.db, 'B77L', 'K0900')
        self.assertEqual(result['speed_kmh'], 900)
        self.assertEqual(result['speed_source'], 'csv')
        # But still gets climb rate from aircraft_profiles
        self.assertEqual(result['climb_fpm'], 2000)

    def test_aircraft_profile_fallback(self):
        """Priority 2: aircraft_profiles is used if SPD missing"""
        result = get_aircraft_speed_and_climb(self.db, 'B77L', '')
        self.assertEqual(result['speed_kmh'], 905)
        self.assertEqual(result['speed_source'], 'aircraft_profile')
        self.assertEqual(result['climb_fpm'], 2000)

    def test_default_fallback(self):
        """Priority 3: Default 800 km/h if no SPD and no profile"""
        result = get_aircraft_speed_and_climb(self.db, 'UNKNOWN', '')
        self.assertEqual(result['speed_kmh'], 800)
        self.assertEqual(result['speed_source'], 'default')

    def test_none_database(self):
        """Should use defaults if database is None"""
        result = get_aircraft_speed_and_climb(None, 'B77L', 'K0900')
        self.assertEqual(result['speed_kmh'], 900)
        self.assertEqual(result['speed_source'], 'csv')
        # Should use hardcoded defaults for climb
        self.assertEqual(result['climb_fpm'], 2000)

    def test_invalid_spd_falls_back(self):
        """Invalid SPD string falls back to default (parse_speed returns 800 for invalid)"""
        result = get_aircraft_speed_and_climb(self.db, 'A321', 'INVALID')
        # parse_speed returns 800 for invalid input, so function treats it as valid CSV value
        self.assertEqual(result['speed_kmh'], 800)
        self.assertEqual(result['speed_source'], 'csv')  # Still marked as 'csv' even if invalid


class TestClimbCalculationSimple(unittest.TestCase):
    """Test calculate_climb_time_simple() - Method A"""

    def test_basic_climb_calculation(self):
        """Test basic climb time and distance calculation"""
        # Parameters:
        # - Total distance: 1000 km
        # - Departure altitude: 0 ft (sea level)
        # - Cruise altitude: 35000 ft
        # - Climb rate: 2000 fpm
        # - Speed: 800 km/h
        result = calculate_climb_time_simple(
            distance_km=1000,
            dep_alt_ft=0,
            cruise_alt_ft=35000,
            climb_fpm=2000,
            speed_kmh=800
        )

        # Climb time = 35000 / 2000 = 17.5 minutes
        self.assertAlmostEqual(result['climb_time_minutes'], 17.5, places=1)

        # Climb distance = (800/60) * 17.5 ≈ 233 km
        self.assertAlmostEqual(result['climb_distance_km'], 233, delta=5)

        # Cruise distance = 1000 - 233 ≈ 767 km
        self.assertAlmostEqual(result['cruise_distance_km'], 767, delta=5)

        # Total time ≈ 17.5 + (767 / (800/60)) ≈ 75.7 minutes
        self.assertAlmostEqual(result['total_time_minutes'], 75.7, delta=2)

    def test_no_climb_needed(self):
        """Test when departure and cruise altitude are same"""
        result = calculate_climb_time_simple(
            distance_km=500,
            dep_alt_ft=35000,
            cruise_alt_ft=35000,
            climb_fpm=2000,
            speed_kmh=800
        )

        self.assertEqual(result['climb_time_minutes'], 0)
        self.assertEqual(result['climb_distance_km'], 0)
        self.assertAlmostEqual(result['total_time_minutes'], 37.5, places=1)

    def test_speed_fallback(self):
        """Test that invalid speed falls back to 800"""
        result = calculate_climb_time_simple(
            distance_km=1000,
            dep_alt_ft=0,
            cruise_alt_ft=30000,
            climb_fpm=1500,
            speed_kmh=-100  # Invalid
        )

        # Should use default 800 km/h
        self.assertGreater(result['total_time_minutes'], 0)


class TestWaypointCalculationEET(unittest.TestCase):
    """Test calculate_waypoints_with_eet() - Method B"""

    def test_basic_waypoint_calculation(self):
        """Test basic waypoint time and altitude calculation"""
        exit_time = time(12, 30)  # 12:30
        points_data = [
            {'name': 'START', 'dist': 0},
            {'name': 'WP1', 'dist': 100},
            {'name': 'WP2', 'dist': 300},
            {'name': 'END', 'dist': 600}
        ]

        result = calculate_waypoints_with_eet(
            exit_time=exit_time,
            points_data=points_data,
            speed_kmh=800,
            dep_alt_ft=0,
            cruise_alt_ft=30000,
            climb_fpm=2000
        )

        # Should return list of waypoints
        self.assertEqual(len(result), 4)

        # Waypoints should have required fields
        for wp in result:
            self.assertIn('name', wp)
            self.assertIn('time', wp)
            self.assertIn('altitude_ft', wp)
            self.assertIn('is_climbing', wp)
            self.assertIn('distance_km', wp)

        # START should be at 0 altitude
        self.assertEqual(result[0]['altitude_ft'], 0)
        self.assertFalse(result[0]['is_climbing'])

        # END should be at cruise altitude
        self.assertEqual(result[-1]['altitude_ft'], 30000)
        self.assertFalse(result[-1]['is_climbing'])

    def test_waypoint_times_are_ordered(self):
        """Test that waypoint times are in correct order"""
        exit_time = time(12, 30)
        points_data = [
            {'name': 'START', 'dist': 0},
            {'name': 'WP1', 'dist': 100},
            {'name': 'WP2', 'dist': 200}
        ]

        result = calculate_waypoints_with_eet(
            exit_time=exit_time,
            points_data=points_data,
            speed_kmh=800,
            dep_alt_ft=0,
            cruise_alt_ft=25000,
            climb_fpm=1500
        )

        # Convert times to minutes for comparison
        times = [datetime.combine(datetime.today(), wp['time']).timestamp() for wp in result]

        # Times should be in ascending order
        for i in range(len(times) - 1):
            self.assertLess(times[i], times[i + 1])

    def test_datetime_input_handling(self):
        """Test that datetime.datetime input is handled correctly"""
        exit_datetime = datetime(2025, 1, 1, 12, 30, 0)
        points_data = [
            {'name': 'START', 'dist': 0},
            {'name': 'END', 'dist': 200}
        ]

        # Should not raise an error
        result = calculate_waypoints_with_eet(
            exit_time=exit_datetime,
            points_data=points_data,
            speed_kmh=800,
            dep_alt_ft=0,
            cruise_alt_ft=25000,
            climb_fpm=1500
        )

        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
