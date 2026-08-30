import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import sys

# Ensure Python can find our core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.unet import UNet

def test_model():
    print("[*] Loading trained U-Net...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # Initialize the architecture
    model = UNet(in_channels=1, out_channels=1).to(device)
    
    # Load the brain
    model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models/unet_best.pth'))
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    # Select a test image containing oil
    image_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/DARTIS/ow-0004.jpg'))
    print(f"[*] Testing on image: {image_path}")
    
    # Load and preprocess the image exactly as we did in training
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        print("Error: Could not load image!")
        return
        
    original_image = image.copy()
    
    # Resize to 224x224 and normalize
    image = cv2.resize(image, (224, 224))
    image = image.astype(np.float32) / 255.0
    
    # Convert to tensor: shape (1, 1, 224, 224)
    image_tensor = torch.from_numpy(image).unsqueeze(0).unsqueeze(0).to(device)
    
    print("[*] Running inference...")
    with torch.no_grad():
        output = model(image_tensor)
        # Apply sigmoid to convert logits to probabilities
        prediction = torch.sigmoid(output)[0, 0].cpu().numpy()
        
        # Normalize the probabilities to 0-255 so it's clearly visible
        # The highest probability pixel becomes pure white (255)
        heatmap = cv2.normalize(prediction, None, 0, 255, cv2.NORM_MINMAX)
        heatmap = heatmap.astype(np.uint8)
    
    # Save the visual result directly using OpenCV so there is zero matplotlib faking
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../unet_test_ow0004.jpg'))
    
    # Put the original and the heatmap side by side
    original_resized = cv2.resize(original_image, (224, 224))
    side_by_side = np.hstack((original_resized, heatmap))
    
    cv2.imwrite(output_path, side_by_side)
    print(f"[SUCCESS] Visual test complete! Saved RAW OpenCV output to: {output_path}")

if __name__ == '__main__':
    test_model()
