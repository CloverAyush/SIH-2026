import os
import sys
import json
import argparse

import torch
import cv2
import numpy as np

# Ensure Python can find our core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.gatekeeper import RobustGatekeeperCNN
from core.unet import UNet
from core.georeference import Georeferencer


def _resolve_image_path(image_name, image_path=None, base_dir=None):
    if image_path and os.path.exists(image_path):
        return image_path

    if image_name is None:
        raise ValueError("image_name is required")

    if os.path.isabs(image_name) and os.path.exists(image_name):
        return image_name

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    candidate = os.path.abspath(os.path.join(base_dir, '../data/DARTIS/', os.path.basename(image_name)))
    if os.path.exists(candidate):
        return candidate

    if os.path.exists(os.path.abspath(os.path.join(base_dir, image_name))):
        return os.path.abspath(os.path.join(base_dir, image_name))

    return os.path.abspath(os.path.join(base_dir, '../data/DARTIS/', os.path.basename(image_name)))


def generate_geojson(gps_contours, output_file, image_id):
    """
    Formats the GPS coordinates into a standard GeoJSON FeatureCollection.
    GeoJSON requires coordinates in [Longitude, Latitude] format.
    """
    features = []
    for idx, contour in enumerate(gps_contours):
        if contour[0] != contour[-1]:
            contour.append(contour[0])

        feature = {
            "type": "Feature",
            "properties": {
                "id": f"{image_id}_slick_{idx}",
                "description": "Oil slick detected by U-Net AI",
                "source_image": image_id
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [contour]
            }
        }
        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)


def run_pipeline(image_name, image_path=None, base_dir=None):
    print(f"=========================================")
    print(f" FINAL PIPELINE DEMO: {image_name}")
    print(f"=========================================")

    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    resolved_image_path = _resolve_image_path(image_name, image_path=image_path, base_dir=base_dir)
    image_file_name = os.path.basename(resolved_image_path)

    result = {
        "image_name": image_file_name,
        "status": "running",
        "gatekeeper": None,
        "proof_image_path": None,
        "geojson": None,
        "origin_zone": None,
        "phase4": {"phase": "phase_4", "status": "not_run"},
        "trajectory": {
            "netcdf_path": None,
            "visualization_path": None,
        },
        "suspects": [],
    }

    gatekeeper_path = os.path.join(base_dir, '../models/robust_gatekeeper_best.pth')
    unet_path = os.path.join(base_dir, '../models/unet_best.pth')
    data_dir = os.path.join(base_dir, '../data/DARTIS/')
    tab_file = os.path.join(data_dir, 'DARTIS_2019.tab')
    image_path = resolved_image_path

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # --- PHASE 1: GATEKEEPER CNN ---
    print("\n[PHASE 1] Initializing Gatekeeper CNN...")
    gatekeeper = RobustGatekeeperCNN().to(device)
    gatekeeper.load_state_dict(torch.load(gatekeeper_path, map_location=device))
    gatekeeper.eval()

    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Could not load {image_path}")

    original_h, original_w = image.shape
    img_resized = cv2.resize(image, (224, 224)).astype(np.float32) / 255.0
    img_resized = (img_resized - 0.5) / 0.5
    tensor = torch.from_numpy(img_resized).unsqueeze(0).unsqueeze(0).to(device)

    print("[PHASE 1] Scanning image...")
    with torch.no_grad():
        output = gatekeeper(tensor)
        prob = torch.sigmoid(output)
        print(f"[PHASE 1] Oil probability: {prob.item():.6f}")
        predicted_class = 1 if prob.item() > 0.01 else 0

    result["gatekeeper"] = {
        "probability": float(prob.item()),
        "predicted_class": int(predicted_class),
    }

    if predicted_class == 0:
        print("[!] Gatekeeper Result: NO OIL DETECTED.")
        print("[!] Terminating pipeline after Phase 1.")
        result["status"] = "no_oil_detected"
        return result
    else:
        print("[+] Gatekeeper Result: OIL DETECTED. Proceeding to U-Net.")

    # --- PHASE 2: U-NET SEGMENTATION ---
    print("\n[PHASE 2] Initializing U-Net...")
    unet = UNet(in_channels=1, out_channels=1).to(device)
    unet.load_state_dict(torch.load(unet_path, map_location=device))
    unet.eval()

    print("[PHASE 2] Extracting pixel map...")
    with torch.no_grad():
        output = unet(tensor)
        prediction = torch.sigmoid(output)[0, 0].cpu().numpy()

    heatmap = cv2.normalize(prediction, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    _, binary_mask = cv2.threshold(heatmap, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    original_resized = cv2.resize(image.copy(), (224, 224))
    side_by_side = np.hstack((original_resized, binary_mask))
    proof_path = os.path.join(base_dir, f'../{image_file_name.split(".")[0]}_proof.jpg')
    cv2.imwrite(proof_path, side_by_side)
    print(f"[PHASE 2] SAVED VISUAL PROOF (Original vs Mask) TO: {proof_path}")
    result["proof_image_path"] = proof_path

    # --- PHASE 3: OPENCV & GEOREFERENCING ---
    print("\n[PHASE 3] OpenCV Tracing & Georeferencing...")
    binary_mask_full = cv2.resize(binary_mask, (original_w, original_h), interpolation=cv2.INTER_NEAREST)
    contours, _ = cv2.findContours(binary_mask_full, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid_contours = [c for c in contours if cv2.contourArea(c) > 20]

    print(f"[PHASE 3] Found {len(valid_contours)} continuous pixel polygon(s).")

    if len(valid_contours) == 0:
        print("[!] No oil detected to georeference. Halting pipeline.")
        result["status"] = "no_oil_contours"
        return result

    geo = Georeferencer(tab_file)
    gps_contours = geo.pixels_to_gps(image_file_name, valid_contours)

    geojson_name = image_file_name.replace('.jpg', '.geojson')
    geojson_path = os.path.join(base_dir, f'../{geojson_name}')
    generate_geojson(gps_contours, geojson_path, image_file_name)
    print(f"[PHASE 3] GeoJSON generated and saved to: {geojson_path}")
    with open(geojson_path, 'r') as f:
        result["geojson"] = json.load(f)

    # --- PHASE 4: PHYSICS & METEOROLOGICAL ENGINE ---
    print("\n[PHASE 4] PHYSICS & METEOROLOGICAL ENGINE")
    from core.physics import TrajectorySimulator
    print(f"[*] Booting Trajectory Simulator...")
    simulator = TrajectorySimulator(tab_file)
    result["trajectory"] = {
        "netcdf_path": simulator._trajectory_file_path(image_file_name, suffix='nc'),
        "visualization_path": simulator._trajectory_file_path(image_file_name, suffix='png'),
    }

    phase4_result = simulator.run_backtrack(geojson_path, image_file_name, hours_to_backtrack=48)
    result["phase4"] = phase4_result if isinstance(phase4_result, dict) else simulator.last_phase4_status
    if str(result["phase4"].get("status", "")).upper() == "FAILED":
        print("\n[!] Phase 4 aborted because no usable trajectory was produced.")
        result["status"] = "phase4_failed"
        return result

    # --- PHASE 5: ORIGIN ZONE EXTRACTION ---
    print("\n[PHASE 5] EXTRACTING ORIGIN SEARCH ZONE")
    origin_zone = simulator.extract_origin_zone(image_file_name)
    result["origin_zone"] = origin_zone
    if not origin_zone:
        print("[!] ERROR: Unable to continue to Phase 6 because no trajectory file was available.")
        result["status"] = "no_origin_zone"
        return result

    # --- PHASE 6: AIS VESSEL IDENTIFICATION ---
    from core.ais_tracker import VesselTracker
    tracker = VesselTracker()

    suspects = tracker.fetch_vessels_in_zone(
        min_lat=origin_zone["min_lat"],
        max_lat=origin_zone["max_lat"],
        min_lon=origin_zone["min_lon"],
        max_lon=origin_zone["max_lon"],
        target_time=origin_zone["target_time"]
    )

    ranked_suspects = []
    for ship in suspects:
        ship["attribution_score"] = tracker._score_vessel_for_attribution(ship, origin_zone)
        ranked_suspects.append(ship)

    result["suspects"] = ranked_suspects
    tracker.rank_and_print_suspects(ranked_suspects, origin_zone=origin_zone)

    print("\n=========================================")
    print(" PIPELINE EXECUTION COMPLETE!")
    print("=========================================")
    result["status"] = "success"
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run the end-to-end pipeline.")
    parser.add_argument('--image', type=str, default='ow-0450.jpg', help='The satellite image name (e.g. ow-0450.jpg)')
    parser.add_argument('--image-path', type=str, default=None, help='Optional explicit image path for the input image.')
    args = parser.parse_args()
    run_pipeline(args.image, image_path=args.image_path)
