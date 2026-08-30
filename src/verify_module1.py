import os
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import pandas as pd
import time
from core.gatekeeper import SmallCNN

class DARTISDataset(Dataset):
    def __init__(self, data_dir, tab_file_path):
        self.data_dir = data_dir
        self.image_paths = []
        self.labels = []
        
        # Parse the PANGAEA .tab file
        print(f"Loading metadata from {tab_file_path}...")
        
        # The first 49 lines of the .tab file are header metadata. Data starts after.
        df = pd.read_csv(tab_file_path, sep="\t", skiprows=49, header=0)
        
        for index, row in df.iterrows():
            # Column 0 is the prefix class (oc, ow, nc, nw)
            # Column 1 is the image filename
            image_class = str(row.iloc[0]).lower()
            image_name = str(row.iloc[1])
            full_path = os.path.join(data_dir, image_name)
            
            if os.path.exists(full_path):
                self.image_paths.append(full_path)
                # Label 1 for Oil (oc, ow), Label 0 for No-Oil (nc, nw)
                label = 1 if ('oc' in image_class or 'ow' in image_class) else 0
                self.labels.append(label)
        
        print(f"Successfully linked {len(self.image_paths)} images to Ground Truth labels.")
        
        # Transformations: Convert to Grayscale, Resize to 224x224 (required by CNN), convert to Tensor
        self.transform = transforms.Compose([
            transforms.Grayscale(num_output_channels=1),
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            # Normalize to match standard neural network input ranges [-1, 1]
            transforms.Normalize(mean=[0.5], std=[0.5]) 
        ])

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        image = Image.open(img_path)
        tensor_image = self.transform(image)
        label = torch.tensor(self.labels[idx], dtype=torch.float32)
        return tensor_image, label

def run_evaluation():
    DATA_DIR = r"C:\Users\SHRI\.gemini\antigravity-ide\scratch\SIH26_FINAL\data\DARTIS"
    TAB_FILE = os.path.join(DATA_DIR, "DARTIS_2019.tab")
    MODEL_PATH = r"C:\Users\SHRI\.gemini\antigravity-ide\scratch\SIH26_FINAL\models\baseline_cnn.pth"

    print("--- MODULE 1: GATEKEEPER VERIFICATION ---")
    
    # 1. Load the Model
    model = SmallCNN()
    try:
        model.load_state_dict(torch.load(MODEL_PATH, map_location=torch.device('cpu')))
        print("Model weights loaded successfully.")
    except Exception as e:
        print(f"Failed to load model weights: {e}")
        return

    model.eval() # Set model to evaluation mode (turns off dropout)

    # 2. Prepare the Dataset
    dataset = DARTISDataset(DATA_DIR, TAB_FILE)
    dataloader = DataLoader(dataset, batch_size=128, shuffle=False, num_workers=0)

    # 3. Evaluation Loop
    print("\nStarting full dataset evaluation. This may take a few minutes on CPU...")
    start_time = time.time()
    
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0
    
    with torch.no_grad(): # Don't track gradients to save memory and speed up
        for batch_idx, (images, labels) in enumerate(dataloader):
            outputs = model(images)
            
            # The model outputs a raw number. We use Sigmoid to squash it between 0 and 1.
            probabilities = torch.sigmoid(outputs).squeeze()
            
            # Any probability > 50% is a positive prediction for Oil
            predictions = (probabilities > 0.5).float()
            
            # Tally results
            for pred, true_label in zip(predictions, labels):
                if pred == 1 and true_label == 1:
                    true_positives += 1
                elif pred == 0 and true_label == 0:
                    true_negatives += 1
                elif pred == 1 and true_label == 0:
                    false_positives += 1
                elif pred == 0 and true_label == 1:
                    false_negatives += 1
                    
            if (batch_idx + 1) % 5 == 0:
                print(f"Processed batch {batch_idx + 1}/{len(dataloader)}")

    # 4. Final Math
    total = true_positives + true_negatives + false_positives + false_negatives
    correct = true_positives + true_negatives
    accuracy = (correct / total) * 100 if total > 0 else 0
    
    end_time = time.time()
    
    print("\n======================================")
    print("VERIFICATION RESULTS")
    print("======================================")
    print(f"Total Images Evaluated: {total}")
    print(f"Time Taken: {round(end_time - start_time, 2)} seconds")
    print("--------------------------------------")
    print(f"True Positives (Correctly spotted oil): {true_positives}")
    print(f"True Negatives (Correctly ignored water): {true_negatives}")
    print(f"False Positives (Tricked by look-alikes): {false_positives}")
    print(f"False Negatives (Missed real oil): {false_negatives}")
    print("--------------------------------------")
    print(f"FINAL ACCURACY: {accuracy:.2f}%")
    print("======================================")

if __name__ == "__main__":
    run_evaluation()
