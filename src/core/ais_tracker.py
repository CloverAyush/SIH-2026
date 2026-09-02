import requests
import json
import os
import random
import math
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

    def _haversine_km(self, lat1, lon1, lat2, lon2):
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        d_phi = math.radians(lat2 - lat1)
        d_lambda = math.radians(lon2 - lon1)
        a = math.sin(d_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
        return 2.0 * r * math.asin(math.sqrt(a))

    def _distance_to_origin_zone(self, lat, lon, origin_zone):
        min_lat = float(origin_zone["min_lat"])
        max_lat = float(origin_zone["max_lat"])
        min_lon = float(origin_zone["min_lon"])
        max_lon = float(origin_zone["max_lon"])

        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return 0.0

        closest_lat = min(max(lat, min_lat), max_lat)
        closest_lon = min(max(lon, min_lon), max_lon)
        dx = 0.0 if min_lon <= lon <= max_lon else min(abs(lon - min_lon), abs(lon - max_lon))
        dy = 0.0 if min_lat <= lat <= max_lat else min(abs(lat - min_lat), abs(lat - max_lat))
        if dx == 0.0 and dy == 0.0:
            return 0.0
        if dx == 0.0:
            return self._haversine_km(lat, lon, closest_lat, closest_lon)
        if dy == 0.0:
            return self._haversine_km(lat, lon, closest_lat, closest_lon)
        return self._haversine_km(lat, lon, closest_lat, closest_lon)

    def _score_vessel_for_attribution(self, vessel, origin_zone):
        if not origin_zone:
            vessel["attribution_score"] = 0
            vessel["investigative_compatibility_score"] = 0
            vessel["risk"] = "LOW"
            vessel["confidence"] = "LOW"
            vessel["attribution_evidence"] = {"spatiotemporal": {"score": 0.0}, "trajectory": {"score": 0.0}, "behavioral": {"score": 0.0}, "context": {"score": 0.0}}
            vessel["human_reasons"] = []
            return 0

        min_lat = float(origin_zone["min_lat"])
        max_lat = float(origin_zone["max_lat"])
        min_lon = float(origin_zone["min_lon"])
        max_lon = float(origin_zone["max_lon"])
        target_time = self._normalize_timestamp(origin_zone.get("target_time"))

        track = vessel.get("track") if isinstance(vessel.get("track"), list) else []
        if not track:
            track = [{"lat": vessel.get("lat"), "lon": vessel.get("lon"), "timestamp": vessel.get("timestamp")}]

        track_points = []
        for point in track:
            if not isinstance(point, dict):
                continue
            try:
                ts = self._normalize_timestamp(point.get("timestamp"))
                lat = float(point.get("lat"))
                lon = float(point.get("lon"))
                track_points.append({"lat": lat, "lon": lon, "timestamp": ts})
            except (TypeError, ValueError):
                continue
        if not track_points:
            track_points = [{"lat": float(vessel.get("lat", 0.0)), "lon": float(vessel.get("lon", 0.0)), "timestamp": self._normalize_timestamp(vessel.get("timestamp"))}]

        closest_index = 0
        nearest_dist = float('inf')
        for idx, point in enumerate(track_points):
            dist = self._distance_to_origin_zone(point["lat"], point["lon"], origin_zone)
            if dist < nearest_dist:
                nearest_dist = dist
                closest_index = idx

        closest_point = track_points[closest_index]
        closest_time = closest_point["timestamp"]
        closest_hours = 0.0
        if target_time and closest_time:
            closest_hours = abs((target_time - closest_time).total_seconds() / 3600.0)

        spatial_score = 25.0 * math.exp(-nearest_dist / 18.0) if nearest_dist != float('inf') else 0.0
        temporal_score = 20.0 * math.exp(-closest_hours / 10.0) if target_time and closest_time else 0.0
        spatiotemporal_score = min(45.0, spatial_score + temporal_score)

        corridor_hits = 0
        corridor_score = 0.0
        for point in track_points:
            dist = self._distance_to_origin_zone(point["lat"], point["lon"], origin_zone)
            if dist <= 6.0:
                corridor_hits += 1
        if corridor_hits > 0:
            corridor_score = 15.0 * min(1.0, corridor_hits / 3.0)

        direction_score = 0.0
        if len(track_points) >= 3:
            ref = track_points[closest_index]
            before = track_points[max(0, closest_index - 1)]
            after = track_points[min(len(track_points) - 1, closest_index + 1)]
            try:
                bearing_before = math.degrees(math.atan2(after["lon"] - before["lon"], after["lat"] - before["lat"]))
                zone_bearing = math.degrees(math.atan2(ref["lon"] - ((min_lon + max_lon) / 2.0), ref["lat"] - ((min_lat + max_lat) / 2.0)))
                delta = min(abs((bearing_before - zone_bearing + 180.0) % 360.0 - 180.0), 180.0)
                direction_score = 10.0 * max(0.0, 1.0 - (delta / 90.0))
            except (TypeError, ValueError):
                direction_score = 0.0
        trajectory_score = min(25.0, corridor_score + direction_score)

        local_speeds = []
        for idx, point in enumerate(track_points):
            if idx == 0:
                continue
            prev = track_points[idx - 1]
            if prev["timestamp"] and point["timestamp"]:
                hours = max((point["timestamp"] - prev["timestamp"]).total_seconds() / 3600.0, 1.0 / 60.0)
                dist_km = self._haversine_km(prev["lat"], prev["lon"], point["lat"], point["lon"])
                local_speeds.append(dist_km / hours)

        speed_score = 0.0
        if local_speeds:
            mean_speed = sum(local_speeds) / len(local_speeds)
            local_speed = local_speeds[-1]
            if local_speed < mean_speed * 0.55 and mean_speed > 6.0:
                speed_score = 7.0 * min(1.0, (mean_speed - local_speed) / 8.0)

        course_change_score = 0.0
        if len(track_points) >= 4:
            bearings = []
            for idx in range(1, len(track_points)):
                prev = track_points[idx - 1]
                curr = track_points[idx]
                if prev["lat"] == curr["lat"] and prev["lon"] == curr["lon"]:
                    continue
                bearings.append(math.degrees(math.atan2(curr["lon"] - prev["lon"], curr["lat"] - prev["lat"])))
            if len(bearings) >= 3:
                deltas = []
                for idx in range(1, len(bearings)):
                    delta = abs((bearings[idx] - bearings[idx - 1] + 180.0) % 360.0 - 180.0)
                    deltas.append(delta)
                if deltas:
                    max_delta = max(deltas)
                    if max_delta > 35.0:
                        course_change_score = 7.0 * min(1.0, max_delta / 90.0)

        loiter_score = 0.0
        time_spent = 0.0
        for idx in range(1, len(track_points)):
            prev = track_points[idx - 1]
            curr = track_points[idx]
            if prev["timestamp"] and curr["timestamp"]:
                dt = (curr["timestamp"] - prev["timestamp"]).total_seconds() / 3600.0
                time_spent += dt
        loitering_points = sum(1 for point in track_points if self._distance_to_origin_zone(point["lat"], point["lon"], origin_zone) <= 4.0)
        if loitering_points >= 3 and time_spent >= 1.5:
            loiter_score = 6.0 * min(1.0, (loitering_points / 5.0))

        behavioral_score = min(20.0, speed_score + course_change_score + loiter_score)

        vessel_type = str(vessel.get("type", "")).lower()
        type_weight = {"tanker": 4.0, "cargo": 2.5, "fishing": 1.5, "tug": 1.0, "passenger": 1.0, "container": 2.0, "bulk carrier": 2.0, "vehicle carrier": 1.5, "reefer": 1.5}
        context_type_score = type_weight.get(vessel_type, 0.5)
        operational_relevance = 0.0
        if corridor_hits >= 2:
            operational_relevance = 4.0
        elif any(self._distance_to_origin_zone(point["lat"], point["lon"], origin_zone) <= 15.0 for point in track_points):
            operational_relevance = 2.5
        context_score = min(10.0, context_type_score + operational_relevance)

        total = min(100.0, spatiotemporal_score + trajectory_score + behavioral_score + context_score)
        total = round(total, 2)

        if total >= 75:
            risk = "CRITICAL"
        elif total >= 55:
            risk = "HIGH"
        elif total >= 30:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        if len(track_points) >= 6 and max(0.0, time_spent) >= 2.5 and nearest_dist <= 12.0:
            confidence = "HIGH"
        elif len(track_points) >= 4 and nearest_dist <= 25.0:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        reasons = []
        if nearest_dist < 50.0:
            reasons.append(f"Track passed {nearest_dist:.1f} km from the inferred origin zone.")
        else:
            reasons.append(f"Track remained farther than {nearest_dist:.1f} km from the inferred origin zone.")
        if closest_time and target_time:
            reasons.append(f"Closest approach occurred {closest_hours:.0f} hours from the inferred origin time.")
        if corridor_hits > 0:
            reasons.append("Historical track entered the inferred origin corridor.")
        else:
            reasons.append("Historical track did not enter the inferred origin corridor.")
        if direction_score > 0:
            reasons.append("Direction near closest approach was broadly compatible with the inferred spill geometry.")
        else:
            reasons.append("Approximate motion compatibility could not be established from the available spill geometry.")
        if speed_score > 0:
            reasons.append("Speed dropped sharply relative to the vessel's preceding track.")
        if course_change_score > 0:
            reasons.append("A course deviation was detected near the origin window.")
        if loiter_score > 0:
            reasons.append("The vessel showed unusually persistent presence near the origin corridor.")
        if context_type_score > 0:
            reasons.append(f"Vessel type provides weak contextual support ({vessel_type}).")

        evidence = {
            "spatiotemporal": {
                "score": round(spatiotemporal_score, 2),
                "spatial_proximity_km": round(nearest_dist, 2),
                "closest_approach_hours": round(closest_hours, 2),
                "details": "Spatial proximity and temporal alignment were combined into one spatio-temporal score.",
            },
            "trajectory": {
                "score": round(trajectory_score, 2),
                "corridor_hits": corridor_hits,
                "direction_compatibility_score": round(direction_score, 2),
                "details": "Origin corridor interaction and motion compatibility were assessed; motion compatibility is an approximation when spill trajectory direction is not explicitly available.",
            },
            "behavioral": {
                "score": round(behavioral_score, 2),
                "speed_anomaly_score": round(speed_score, 2),
                "course_change_score": round(course_change_score, 2),
                "loitering_score": round(loiter_score, 2),
                "details": "Behavioral evidence reflects speed anomaly, heading/course deviation, and unusual residence near the origin window.",
            },
            "context": {
                "score": round(context_score, 2),
                "vessel_type": vessel_type,
                "contextual_weight": round(context_type_score, 2),
                "operational_relevance": round(operational_relevance, 2),
                "details": "Contextual support is intentionally weak and based only on the synthetic vessel type and track behavior.",
            },
        }

        vessel["attribution_score"] = int(round(total))
        vessel["investigative_compatibility_score"] = int(round(total))
        vessel["risk"] = risk
        vessel["confidence"] = confidence
        vessel["attribution_evidence"] = evidence
        vessel["human_reasons"] = reasons
        return vessel["investigative_compatibility_score"]

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
            scored = self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
            scored.sort(key=lambda v: v.get("investigative_compatibility_score", 0), reverse=True)
            self.last_population = scored
            return scored

        print("[*] Connecting to live GFW API...")
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {
            "where": f"lat >= {min_lat} AND lat <= {max_lat} AND lon >= {min_lon} AND lon <= {max_lon}",
            "start-date": str(target_time).split()[0],
            "end-date": str(target_time).split()[0]
        }

        try:
            response = requests.get(self.api_url, params=params, headers=headers)
            if response.status_code == 200:
                print("[+] Live API connection successful!")
                return response.json().get("entries", [])
            elif response.status_code == 401:
                print("[-] 401 Unauthorized: Invalid API Key. Falling back to mock data.")
                scored = self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
                scored.sort(key=lambda v: v.get("investigative_compatibility_score", 0), reverse=True)
                self.last_population = scored
                return scored
            else:
                print(f"[-] API Error {response.status_code}. Falling back to mock data.")
                scored = self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
                scored.sort(key=lambda v: v.get("investigative_compatibility_score", 0), reverse=True)
                self.last_population = scored
                return scored
        except Exception as e:
            print(f"[-] Network Error: {e}. Falling back to mock data.")
            scored = self._mock_ais_response(min_lat, max_lat, min_lon, max_lon, target_time)
            scored.sort(key=lambda v: v.get("investigative_compatibility_score", 0), reverse=True)
            self.last_population = scored
            return scored

    def _mock_ais_response(self, min_lat, max_lat, min_lon, max_lon, target_time):
        """Deterministic synthetic AIS scenario: 60 vessels split into background, peripheral, plausible, and decoy roles."""
        center_lat = (min_lat + max_lat) / 2.0
        center_lon = (min_lon + max_lon) / 2.0
        target_dt = datetime.fromisoformat(str(target_time).replace('Z', '+00:00')) if isinstance(target_time, str) else target_time
        rng = random.Random(20240606)

        ship_names = [
            "AURORA BELL", "NORTH STAR", "RED OAK", "BLUE MARLIN", "TIDEKEEPER", "HARBOR VALE", "SEABRIDGE", "MALTESE PEARL",
            "SOUTHERN CAPE", "BAYVIEW", "ORBITAL TRADER", "RAVEN BAY", "GULF HORIZON", "SEA RANGER", "PINE ISLAND", "MORNING TIDE",
            "ATLANTIC REEF", "CINDER WAVE", "LISBON CHIEF", "SABLE CURRENT", "NIGHTWATCH", "PACIFIC CATCH", "SIERRA QUEEN", "COASTAL LIFT",
            "MARIAN FLEET", "WHITE PELICAN", "SEAHORSE", "MARINE RANGER", "BRIGHT HARBOR", "GOLDEN APEX", "DANUBE DELTA",
            "CROWN PASSAGE", "HARBOR SEEKER", "DIVERGENCE", "LANTERN LIGHT", "EASTERN PATH", "SALT BREEZE", "PORT VISION", "MOONLIT TIDE",
            "CURRENT LEAD", "RIVER GLACIER", "STORM BEARER", "DECKMASTER", "TERRA BELL", "FAIRWIND", "BAY CURRENT", "SOUTHERN DAWN",
            "IRON BREEZE", "COASTAL VISION", "GOLDEN HARBOR", "BALTIC GLIDE", "IRON DOLPHIN", "TRIDENT SKY", "BROADWAY STAR",
            "MARINER'S RISE", "SILVER QUAY", "DEEP HARBOR", "CURRENT SWELL", "SUNSET VENTURE", "NORTH BREEZE", "TIDEWALKER"
        ]
        vessel_types = ["tanker", "cargo", "fishing", "tug", "passenger", "container", "bulk carrier", "ferry", "research", "pleasure"]

        roles = ["background"] * 40 + ["peripheral"] * 10 + ["plausible"] * 5 + ["decoy"] * 5
        suspects = []

        for idx in range(60):
            role = roles[idx]
            vessel_type = vessel_types[idx % len(vessel_types)]
            shipname = ship_names[idx % len(ship_names)]
            angle = (idx * 37.0 + 11.0) % 360.0
            base_radius = 0.0
            time_offset = 0.0
            lat = center_lat
            lon = center_lon

            if role == "background":
                base_radius = 0.60 + (idx % 10) * 0.09
                time_offset = ((idx % 9) - 4) * 7.5 + rng.uniform(-1.5, 1.5)
                lat = center_lat + math.cos(math.radians(angle)) * (base_radius + rng.uniform(0.1, 0.45))
                lon = center_lon + math.sin(math.radians(angle)) * (base_radius * 1.4 + rng.uniform(0.12, 0.55))
            elif role == "peripheral":
                base_radius = 0.18 + (idx % 6) * 0.025
                time_offset = ((idx % 7) - 3) * 4.5 + rng.uniform(-1.0, 1.5)
                lat = center_lat + math.cos(math.radians(angle + 23.0)) * (base_radius + rng.uniform(0.03, 0.09))
                lon = center_lon + math.sin(math.radians(angle + 23.0)) * (base_radius * 1.45 + rng.uniform(0.04, 0.10))
            elif role == "plausible":
                base_radius = 0.05 + (idx % 4) * 0.035
                time_offset = ((idx % 5) - 2) * 1.8 + rng.uniform(-0.8, 0.8)
                lat = center_lat + math.cos(math.radians(angle + 80.0)) * base_radius
                lon = center_lon + math.sin(math.radians(angle + 80.0)) * base_radius * 1.25
            else:
                decoy_type = idx % 5
                if decoy_type == 0:
                    base_radius = 0.08 + 0.03 * (idx % 4)
                    time_offset = 9.0 + (idx % 4) * 4.0
                    lat = center_lat + math.cos(math.radians(angle + 12.0)) * base_radius
                    lon = center_lon + math.sin(math.radians(angle + 12.0)) * base_radius * 1.2
                elif decoy_type == 1:
                    base_radius = 0.30 + (idx % 3) * 0.12
                    time_offset = rng.uniform(-0.8, 0.8)
                    lat = center_lat + math.cos(math.radians(angle + 135.0)) * base_radius
                    lon = center_lon + math.sin(math.radians(angle + 135.0)) * base_radius * 1.4
                elif decoy_type == 2:
                    base_radius = 0.06 + (idx % 3) * 0.015
                    time_offset = rng.uniform(-2.0, 2.0)
                    lat = center_lat + math.cos(math.radians(angle + 210.0)) * base_radius
                    lon = center_lon + math.sin(math.radians(angle + 210.0)) * base_radius * 1.15
                elif decoy_type == 3:
                    base_radius = 0.42 + (idx % 4) * 0.08
                    time_offset = 5.0 + (idx % 3) * 2.5
                    lat = center_lat + math.cos(math.radians(angle + 275.0)) * base_radius
                    lon = center_lon + math.sin(math.radians(angle + 275.0)) * base_radius * 1.3
                else:
                    base_radius = 0.10 + (idx % 5) * 0.04
                    time_offset = rng.uniform(-1.3, 1.2)
                    lat = center_lat + math.cos(math.radians(angle + 305.0)) * base_radius
                    lon = center_lon + math.sin(math.radians(angle + 305.0)) * base_radius * 1.2

            vessel_time = target_dt + timedelta(hours=time_offset)
            track = []
            if role == "plausible":
                for step in range(6):
                    drift = -2.5 + step * 0.9
                    point_time = vessel_time + timedelta(hours=drift)
                    local_lat = lat + math.sin((idx + step) * 0.85) * 0.012 + (step - 2.5) * 0.002
                    local_lon = lon + math.cos((idx + step) * 0.92) * 0.014 + (step - 2.5) * 0.003
                    course = 40.0 + (idx % 5) * 12.0 + step * 9.0
                    sog = 6.5 + (idx % 4) * 1.2 + math.sin((idx + step) * 0.7) * 0.9
                    track.append({
                        "lat": round(local_lat, 6),
                        "lon": round(local_lon, 6),
                        "timestamp": point_time.isoformat(timespec="seconds"),
                        "sog_knots": round(sog, 2),
                        "course_deg": round(course, 2),
                        "heading_deg": round((course + 8.0) % 360.0, 2),
                    })
            elif role == "background":
                for step in range(5):
                    drift = -2.8 + step * 0.9
                    point_time = vessel_time + timedelta(hours=drift)
                    local_lat = lat + math.sin((idx + step) * 1.3) * 0.008 + (step - 2.0) * 0.0014
                    local_lon = lon + math.cos((idx + step) * 1.7) * 0.009 + (step - 2.0) * 0.0018
                    course = ((idx * 17) + step * 22) % 360.0
                    sog = 8.5 + (idx % 5) * 1.5 + math.sin((idx + step) * 0.8) * 1.2
                    track.append({
                        "lat": round(local_lat, 6),
                        "lon": round(local_lon, 6),
                        "timestamp": point_time.isoformat(timespec="seconds"),
                        "sog_knots": round(sog, 2),
                        "course_deg": round(course, 2),
                        "heading_deg": round((course + 3.0) % 360.0, 2),
                    })
            elif role == "peripheral":
                for step in range(6):
                    drift = -3.0 + step * 0.8
                    point_time = vessel_time + timedelta(hours=drift)
                    local_lat = lat + math.sin((idx + step) * 1.1) * 0.010 + (step - 2.5) * 0.0018
                    local_lon = lon + math.cos((idx + step) * 1.2) * 0.011 + (step - 2.5) * 0.0025
                    course = 95.0 + ((idx % 6) * 17.0) + step * 18.0
                    sog = 7.8 + (idx % 4) * 1.3
                    track.append({
                        "lat": round(local_lat, 6),
                        "lon": round(local_lon, 6),
                        "timestamp": point_time.isoformat(timespec="seconds"),
                        "sog_knots": round(sog, 2),
                        "course_deg": round(course, 2),
                        "heading_deg": round((course + 5.0) % 360.0, 2),
                    })
            else:
                decoy_kind = idx % 5
                for step in range(4 if decoy_kind == 4 else 5):
                    drift = -2.0 + step * 1.5
                    point_time = vessel_time + timedelta(hours=drift)
                    local_lat = lat + math.sin((idx + step) * 0.9) * (0.010 if decoy_kind != 3 else 0.008)
                    local_lon = lon + math.cos((idx + step) * 1.1) * (0.012 if decoy_kind != 3 else 0.009)
                    if decoy_kind == 1:
                        local_lat = lat + math.sin((idx + step) * 0.6) * 0.012 + step * 0.0009
                        local_lon = lon + math.cos((idx + step) * 0.8) * 0.015 - step * 0.0007
                    elif decoy_kind == 3:
                        local_lat = lat + math.sin((idx + step) * 1.5) * 0.006
                        local_lon = lon + math.cos((idx + step) * 1.3) * 0.008
                    course = ((idx * 11) + step * 21) % 360.0
                    sog = 7.0 + (idx % 4) * 1.3
                    track.append({
                        "lat": round(local_lat, 6),
                        "lon": round(local_lon, 6),
                        "timestamp": point_time.isoformat(timespec="seconds"),
                        "sog_knots": round(sog, 2),
                        "course_deg": round(course, 2),
                        "heading_deg": round((course + 2.0) % 360.0, 2),
                    })

            vessel = {
                "mmsi": str(200000000 + idx * 11 + (idx % 13) * 17),
                "shipname": shipname,
                "type": vessel_type.title(),
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "sog_knots": round(max(2.0, 6.0 + rng.uniform(-1.3, 3.2)), 2),
                "course_deg": round((idx * 19.0 + 33.0) % 360.0, 2),
                "heading_deg": round((idx * 19.0 + 35.0) % 360.0, 2),
                "timestamp": vessel_time.isoformat(timespec="seconds"),
                "track": track,
                "synthetic": True,
                "source": "synthetic",
                "candidate_index": idx,
                "population_role": role,
                "decoy_kind": idx % 5 if role == "decoy" else None,
            }
            self._score_vessel_for_attribution(vessel, {"min_lat": min_lat, "max_lat": max_lat, "min_lon": min_lon, "max_lon": max_lon, "target_time": target_time})
            vessel["evidence_breakdown"] = vessel.get("attribution_evidence", {})
            vessel["reasons"] = vessel.get("human_reasons", [])
            suspects.append(vessel)

        suspects.sort(key=lambda v: v.get("investigative_compatibility_score", 0), reverse=True)
        self.last_synthetic_population = suspects
        return suspects

    def rank_and_print_suspects(self, suspects, origin_zone=None):
        scored = []
        for ship in suspects:
            if origin_zone is not None:
                self._score_vessel_for_attribution(ship, origin_zone)
            scored.append(ship)

        scored.sort(key=lambda s: s.get("investigative_compatibility_score", s.get("attribution_score", 0)), reverse=True)
        top = scored[:5]

        print("\n==========================================================")
        print("                 VESSEL SUSPECT REPORT                    ")
        print("==========================================================")
        print(f"{'MMSI':<12} | {'SHIP NAME':<26} | {'TYPE':<10} | {'SCORE':<5} | {'RISK':<8} | {'CONFIDENCE'}")
        print("-" * 110)

        for ship in top:
            print(f"{ship['mmsi']:<12} | {ship['shipname']:<26} | {ship['type']:<10} | {ship['investigative_compatibility_score']:<5} | {ship['risk']:<8} | {ship['confidence']}")
            for reason in ship.get("human_reasons", [])[:3]:
                print(f"       - {reason}")
        print("==========================================================")
        return top
