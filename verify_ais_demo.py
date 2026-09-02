import sys
from datetime import datetime

sys.path.insert(0, r'C:\Users\OM CHICKS\Desktop\SIH Final')

from src.core.ais_tracker import VesselTracker

origin = {
    'min_lat': 32.4,
    'max_lat': 33.1,
    'min_lon': -5.9,
    'max_lon': -5.2,
    'target_time': datetime(2024, 6, 1, 12, 0, 0),
}

tracker = VesselTracker()
vessels = tracker.fetch_vessels_in_zone(
    origin['min_lat'],
    origin['max_lat'],
    origin['min_lon'],
    origin['max_lon'],
    origin['target_time'],
)

scores = [v['investigative_compatibility_score'] for v in vessels]
roles = {v['population_role'] for v in vessels[:5]}
print('COUNT', len(vessels))
print('ALL_SCORED', all('investigative_compatibility_score' in v for v in vessels))
print('TOP5_COUNT', len(vessels[:5]))
print('SCORE_MIN_MAX', min(scores), max(scores))
print('SCORE_SET_SIZE', len(set(scores)))
print('TOP5', [(v['mmsi'], v['shipname'], v['population_role'], v['investigative_compatibility_score'], v['confidence']) for v in vessels[:5]])
print('UNIQUE_TOP5_ROLES', len(roles))
print('SPATIAL_TOP5', [(v['mmsi'], round(v['attribution_evidence']['spatiotemporal']['spatial_proximity_km'], 2), round(v['attribution_evidence']['spatiotemporal']['closest_approach_hours'], 2)) for v in vessels[:5]])
