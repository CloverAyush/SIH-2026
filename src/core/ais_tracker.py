import requests
import json
import os
import random
from datetime import datetime, timedelta

class VesselTracker:
    def __init__(self):
        self.api_url = "https://gateway.api.globalfishingwatch.org/v3/vessels/search"
        self.api_key = os.environ.get("GFW_API_KEY", "")

    def _normalize_timestamp(self, timestamp_value):
        if timestamp_value is None:
            return None
        try:
            if isinstance(timestamp_value, str):
                value = timestamp_value.strip()
                if value.endswith('Z'):
                    value = value[:-1] + '+00:00'
                return __import__('datetime').datetime.fromisoformat(value)
            return timestamp_value
        except ValueError:
            return None

    def _score_vessel_for_attribution(self, vessel, origin_zone):
        min_lat = float(origin_zone["min_lat"])
        max_lat = float(origin_zone["max_lat"])
        min_lon = float(origin_zone["min_lon"])
        max_lon = float(origin_zone["max_lon"])
        target_time = self._normalize_timestamp(origin_zone.get("target_time"))
        vessel_timestamp = self._normalize_timestamp(vessel.get("timestamp"))

        lat_center = (min_lat + max_lat) / 2.0
        lon_center = (min_lon + max_lon) / 2.0
        lat_span = max(max_lat - min_lat, 1e-9)
        lon_span = max(max_lon - min_lon, 1e-9)

        # Spatial evidence: normalized center distance to origin zone.
        lat_delta = abs(float(vessel.get("lat", 0.0)) - lat_center) / lat_span
        lon_delta = abs(float(vessel.get("lon", 0.0)) - lon_center) / lon_span
        spatial_distance = (lat_delta ** 2 + lon_delta ** 2) ** 0.5
        spatial_score = max(0.0, 40.0 * (1.0 - min(spatial_distance / 1.5, 1.0)))

        # Temporal evidence: target-time proximity.
        temporal_score = 0.0
        if target_time and vessel_timestamp:
            delta_hours = abs((target_time - vessel_timestamp).total_seconds() / 3600.0)
            temporal_score = max(0.0, 20.0 * (1.0 - min(delta_hours / 24.0, 1.0)))

        # Track-based spatial consistency: average historical point distance from zone center.
        track_score = 0.0
        track = vessel.get("track") if isinstance(vessel.get("track"), list) else []
        if track:
            track_distances = []
            for point in track:
                if not isinstance(point, dict):
                    continue
                try:
                    track_lat = float(point.get("lat", 0.0))
                    track_lon = float(point.get("lon", 0.0))
                    track_lat_delta = abs(track_lat - lat_center) / lat_span
                    track_lon_delta = abs(track_lon - lon_center) / lon_span
                    track_distance = (track_lat_delta ** 2 + track_lon_delta ** 2) ** 0.5
                    track_distances.append(track_distance)
                except (TypeError, ValueError):
                    continue
            if track_distances:
                avg_track_distance = sum(track_distances) / len(track_distances)
                track_score = max(0.0, 20.0 * (1.0 - min(avg_track_distance / 1.5, 1.0)))

        # Optional course/heading consistency from existing track data.
        course_score = 0.0
        if track and len(track) >= 2:
            try:
                first = track[0]
                last = track[-1]
                lon_delta_track = float(last.get("lon", 0.0)) - float(first.get("lon", 0.0))
                lat_delta_track = float(last.get("lat", 0.0)) - float(first.get("lat", 0.0))
                if lat_delta_track != 0.0 or lon_delta_track != 0.0:
                    heading = (90.0 - (57.2957795 * __import__('math').atan2(lon_delta_track, lat_delta_track))) % 360.0
                    candidates = []
                    for key in ("course_deg", "heading_deg"):
                        value = vessel.get(key)
                        if value is not None:
                            try:
                                candidates.append(float(value) % 360.0)
                            except (TypeError, ValueError):
                                pass
                    if candidates:
                        deltas = [min(abs(c - heading), 360.0 - abs(c - heading)) for c in candidates]
                        course_score = max(0.0, 8.0 * (1.0 - min(min(deltas) / 180.0, 1.0)))
            except (TypeError, ValueError, ZeroDivisionError):
                course_score = 0.0

        # Vessel type: moderate, not dominant.
        type_score = 0.0
        vessel_type = str(vessel.get("type", "")).lower()
        if vessel_type == "tanker":
            type_score = 10.0
        elif vessel_type == "cargo":
            type_score = 7.0
        elif vessel_type == "fishing":
            type_score = 5.0

        # SOG: mild behavioral evidence; slower or faster is not automatically suspicious.
        speed = float(vessel.get("sog_knots", 0.0) or 0.0)
        if speed <= 0:
            sog_score = 0.0
        else:
            ideal_speed = 10.0
            sog_score = max(0.0, 6.0 * (1.0 - min(abs(speed - ideal_speed) / 20.0, 1.0)))

        evidence = {
            "spatial": float(round(spatial_score, 2)),
            "temporal": float(round(temporal_score, 2)),
            "track": float(round(track_score, 2)),
            "course": float(round(course_score, 2)),
            "type": float(round(type_score, 2)),
            "sog": float(round(sog_score, 2)),
        }
        score = sum(evidence.values())
        vessel["attribution_score"] = int(round(max(0, min(100, score))))
        vessel["attribution_evidence"] = evidence
        return vessel["attribution_score"]

    def fetch_vessels_in_zone(self, min_lat, max_lat, min_lon, max_lon, target_time):
        """
        Queries the GFW API for vessels in the given bounding box around the target_time.
        Falls back to a realistic mock response if no API key is present.
        """
        print("\n--- [PHASE 6] INITIATING GLOBAL FISHING WATCH (GFW) AIS TRACKING ---")
        print(f"[*] Search Zone: Lat({min_lat:.4f} to {max_lat:.4f}), Lon({min_lon:.4f} to {max_lon:.4f})")
        print(f"[*] Target Spill Time: {target_time} UTC")
        
        if not self.api_key:
            print("[!] WARNING: No 'GFW_API_KEY' found in environment. The real API will reject us.")
            print("[!] Firing fallback Mock AIS API for demonstration continuity...")
            return self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
            
        print("[*] Connecting to live GFW API...")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # GFW API typically takes a bounding box or polygon for search
        # This is a conceptual representation of how the query would be structured
        params = {
            "where": f"lat >= {min_lat} AND lat <= {max_lat} AND lon >= {min_lon} AND lon <= {max_lon}",
            "start-date": str(target_time).split()[0], # e.g. 2019-03-17
            "end-date": str(target_time).split()[0]
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=headers)
            if response.status_code == 200:
                print("[+] Live API connection successful!")
                return response.json().get("entries", [])
            elif response.status_code == 401:
                print("[-] 401 Unauthorized: Invalid API Key. Falling back to mock data.")
                return self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
            else:
                print(f"[-] API Error {response.status_code}. Falling back to mock data.")
                return self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
        except Exception as e:
            print(f"[-] Network Error: {e}. Falling back to mock data.")
            return self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)

    def _mock_ais_response(self, min_lat, max_lat, min_lon, max_lon, target_time):
        """Generates deterministic synthetic AIS candidates near, but not all inside, the origin zone."""
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        target_dt = datetime.fromisoformat(str(target_time).replace('Z', '+00:00')) if isinstance(target_time, str) else target_time

        specs = [
            {"mmsi": "371302000", "shipname": "MV DELPHINUS", "type": "Tanker", "lat_offset": 0.160, "lon_offset": -0.140, "sog_knots": 5.2, "course_deg": 118, "heading_deg": 119, "time_offset_hours": 2.1},
            {"mmsi": "235070000", "shipname": "PACIFIC CATCH", "type": "Fishing", "lat_offset": -0.020, "lon_offset": 0.025, "sog_knots": 7.4, "course_deg": 214, "heading_deg": 212, "time_offset_hours": 0.4},
            {"mmsi": "412456000", "shipname": "EVER GIVEN", "type": "Cargo", "lat_offset": 0.085, "lon_offset": 0.040, "sog_knots": 17.4, "course_deg": 342, "heading_deg": 340, "time_offset_hours": -2.1},
            {"mmsi": "477123456", "shipname": "AURORA STAR", "type": "Passenger", "lat_offset": -0.133, "lon_offset": -0.091, "sog_knots": 15.8, "course_deg": 74, "heading_deg": 76, "time_offset_hours": 1.25},
            {"mmsi": "219998000", "shipname": "NORTH RAY", "type": "Tug", "lat_offset": 0.006, "lon_offset": 0.160, "sog_knots": 7.1, "course_deg": 305, "heading_deg": 300, "time_offset_hours": -0.75},
            {"mmsi": "636019123", "shipname": "BLUE MARLIN", "type": "Fishing", "lat_offset": -0.180, "lon_offset": -0.110, "sog_knots": 10.6, "course_deg": 196, "heading_deg": 198, "time_offset_hours": 3.0},
            {"mmsi": "255808000", "shipname": "ORBITAL TRADER", "type": "Cargo", "lat_offset": 0.062, "lon_offset": -0.068, "sog_knots": 13.9, "course_deg": 265, "heading_deg": 267, "time_offset_hours": -1.2},
            {"mmsi": "533004321", "shipname": "TIDEKEEPER", "type": "Tanker", "lat_offset": -0.040, "lon_offset": -0.165, "sog_knots": 5.8, "course_deg": 156, "heading_deg": 154, "time_offset_hours": 0.5},
        ]

        suspects = []
        for idx, spec in enumerate(specs):
            vessel_time = target_dt + timedelta(hours=spec["time_offset_hours"])
            lat = center_lat + spec["lat_offset"]
            lon = center_lon + spec["lon_offset"]
            track = []
            for step in range(4):
                track.append({
                    "lat": lat + (step - 1.5) * 0.0035,
                    "lon": lon + (step - 1.5) * 0.0040,
                    "timestamp": (vessel_time + timedelta(minutes=(step - 1) * 15)).isoformat(timespec="microseconds")
                })
            suspects.append({
                "mmsi": spec["mmsi"],
                "shipname": spec["shipname"],
                "type": spec["type"],
                "lat": lat,
                "lon": lon,
                "sog_knots": spec["sog_knots"],
                "course_deg": spec["course_deg"],
                "heading_deg": spec["heading_deg"],
                "timestamp": vessel_time.isoformat(timespec="microseconds"),
                "track": track,
                "synthetic": True,
                "source": "synthetic",
                "candidate_index": idx,
            })
        return suspects

    def rank_and_print_suspects(self, suspects, origin_zone=None):
        scored = []
        for ship in suspects:
            ship["attribution_score"] = self._score_vessel_for_attribution(ship, origin_zone) if origin_zone is not None else 0
            if origin_zone is not None:
                ship["attribution_evidence"] = ship.get("attribution_evidence", {})
            scored.append(ship)

        scored.sort(key=lambda s: s.get("attribution_score", 0), reverse=True)

        print("\n==========================================================")
        print("                 VESSEL SUSPECT REPORT                    ")
        print("==========================================================")
        print(f"{'MMSI':<12} | {'SHIP NAME':<26} | {'TYPE':<8} | {'SPEED(kts)':<10} | {'SCORE':<5} | {'RISK'}")
        print("-" * 90)

        for ship in scored:
            risk = "LOW"
            if ship["type"] == "Tanker" and ship["sog_knots"] < 5.0:
                risk = "HIGH (POTENTIAL DISCHARGE)"
            elif ship["type"] == "Tanker":
                risk = "MEDIUM"

            print(f"{ship['mmsi']:<12} | {ship['shipname']:<26} | {ship['type']:<8} | {ship['sog_knots']:<10} | {ship['attribution_score']:<5} | {risk}")
        print("==========================================================")
