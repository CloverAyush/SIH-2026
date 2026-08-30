import os
import sys
import json
import torch
import cv2
import numpy as np

# Ensure Python can find our core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.unet import UNet
from core.georeference import Georeferencer

def generate_geojson(gps_contours, output_file, image_id):
    """
    Formats the GPS coordinates into a standard GeoJSON FeatureCollection.
    GeoJSON requires coordinates in [Longitude, Latitude] format.
    """
    features = []
    
    for idx, contour in enumerate(gps_contours):
        # GeoJSON polygons must be closed (first and last coordinate must match)
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
    print(f"[*] GeoJSON saved to: {output_file}")


def extract(image_name):
    print(f"=========================================")
    print(f" PHASE 3: GEOREFERENCING PIPELINE")
    print(f"=========================================")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(base_dir, '../models/unet_best.pth')
    data_dir = os.path.join(base_dir, '../data/DARTIS/')
    tab_file = os.path.join(data_dir, 'DARTIS_2019.tab')
    
    image_path = os.path.join(data_dir, image_name)
    
    # 1. Initialize Georeferencer
    print(f"[*] Booting Georeferencing Engine...")
    geo = Georeferencer(tab_file)
    
    # 2. Initialize U-Net Brain
    print(f"[*] Booting U-Net AI...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = UNet(in_channels=1, out_channels=1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # 3. Process Image
    print(f"[*] Reading satellite image: {image_name}")
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Could not load {image_path}")
        
    original_h, original_w = image.shape
    
    # Resize to 224x224 for U-Net
    img_resized = cv2.resize(image, (224, 224)).astype(np.float32) / 255.0
    tensor = torch.from_numpy(img_resized).unsqueeze(0).unsqueeze(0).to(device)
    
    # 4. AI Inference
    print(f"[*] Running Neural Network...")
    with torch.no_grad():
        output = model(tensor)
        prediction = torch.sigmoid(output)[0, 0].cpu().numpy()
        
    # 5. Smart Thresholding (Otsu's Method)
    # Scale probabilities to 0-255
    heatmap = cv2.normalize(prediction, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    # Use Otsu's method to automatically find the perfect split between ocean and oil
    _, binary_mask = cv2.threshold(heatmap, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 6. Scale mask back up to the original image dimensions (e.g. 640x640)
    binary_mask = cv2.resize(binary_mask, (original_w, original_h), interpolation=cv2.INTER_NEAREST)
    
    # 7. OpenCV Contour Extraction
    print(f"[*] Tracing Oil Boundaries (OpenCV)...")
    contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter out tiny noise blobs (less than 20 pixels)
    valid_contours = [c for c in contours if cv2.contourArea(c) > 20]
    print(f"[*] Found {len(valid_contours)} valid oil slick(s).")
    
    if len(valid_contours) == 0:
        print("[!] No oil detected in this image.")
        return
        
    # 8. Georeference: Convert Pixels to GPS
    print(f"[*] Converting Pixels to GPS Coordinates...")
    gps_contours = geo.pixels_to_gps(image_name, valid_contours)
    
    # 9. Save to GeoJSON
    output_filename = os.path.join(base_dir, f'../{image_name.split(".")[0]}.geojson')
    generate_geojson(gps_contours, output_filename, image_name)
    print(f"[SUCCESS] Pipeline Complete!")

if __name__ == '__main__':
    # Test on ow-0004.jpg
    extract('ow-0004.jpg')
