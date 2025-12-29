import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import core.flight_processor as fp

# Mock route_converter.expand_route to avoid loading excel
fp.route_converter = MagicMock()
fp.route_converter.expand_route.return_value = ['WP1', 'WP2']

# Prepare Test Data
flight_data = {
    'callsign': 'TEST01',
    'dept': 'RKSI', # Incheon (37.4606, 126.4407)
    'dest': 'RJAA',
    'route': 'TEST_ROUTE',
    'speed': 'K0900', # 900 km/h
    'altitude': '370', # 37,000 ft
    'eobd': '2025-12-25',
    'eobt': '12:00',
    'eet': '' # No EET, force forward calc
}

# Coordinate Map
# RKSI: (37.4606, 126.4407)
# WP1: Close point (approx 40-50km away) -> climb phase
# WP2: Far point -> cruise phase
coord_map = {
    'WP1': (37.6, 126.8), 
    'WP2': (35.0, 129.0)
}

sectors = {} # Empty sectors
enroute_df = pd.DataFrame()

print("--- Running Trajectory Calculation (Climb Logic Verification) ---")
print(f"Departure: {flight_data['dept']} at {flight_data['eobt']}")
print(f"Target Altitude: FL{flight_data['altitude']}")

# Run Calculation
result = fp.calculate_trajectory(flight_data, coord_map, sectors, enroute_df, 'FIXPNT')

if result['status'] == 'success':
    for wp in result['waypoints']:
        time_str = wp['time']
        print(f"Waypoint {wp['name']}: {time_str}")
        
        # Parse HH:MM to compare minutes
        try:
             h, m = map(int, time_str.split(':'))
             t_min = h * 60 + m
             dept_min = 12 * 60
             diff_min = t_min - dept_min
             print(f"  -> +{diff_min} min from EOBT (12:00)")
        except:
             pass
else:
    print("Error:", result['message'])
