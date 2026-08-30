import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import pandas as pd
import time
from sklearn.model_selection import train_test_split

# Import the new ResNet18 model we just built
from core.gatekeeper import RobustGatekeeperCNN

class DARTISTrainDataset(Dataset):
    def __init__(self, image_paths, labels, is_train=True):
        self.image_paths = image_paths
        self.labels = labels
        
        # Training images get randomly flipped to prevent memorization
        if is_train:
            self.transform = transforms.Compose([
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(),
                transforms.RandomVerticalFlip(),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.5], std=[0.5])
            ])
        # Validation images are kept pure (no random flipping)
        else:
            self.transform = transforms.Compose([
                transforms.Grayscale(num_output_channels=1),
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
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

def load_data(data_dir, tab_file_path):
    print("Parsing Master Map...")
    df = pd.read_csv(tab_file_path, sep="\t", skiprows=49, header=0)
    
    all_paths = []
    all_labels = []
    
    for index, row in df.iterrows():
        image_class = str(row.iloc[0]).lower()
        image_name = str(row.iloc[1])
        full_path = os.path.join(data_dir, image_name)
        
        if os.path.exists(full_path):
            all_paths.append(full_path)
            label = 1 if ('oc' in image_class or 'ow' in image_class) else 0
            all_labels.append(label)
            
    # 80/20 Strict Split
    train_paths, val_paths, train_labels, val_labels = train_test_split(
        all_paths, all_labels, test_size=0.20, random_state=42
    )
    return train_paths, val_paths, train_labels, val_labels

def train_model():
    DATA_DIR = r"C:\Users\SHRI\.gemini\antigravity-ide\scratch\SIH26_FINAL\data\DARTIS"
    TAB_FILE = os.path.join(DATA_DIR, "DARTIS_2019.tab")
    SAVE_PATH = r"C:\Users\SHRI\.gemini\antigravity-ide\scratch\SIH26_FINAL\models\robust_gatekeeper_best.pth"
    EPOCHS = 3 # Kept to 3 epochs for demonstration time
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- TRAINING INITIALIZED ON: {device.type.upper()} ---")

    # 1. Load Data
    train_paths, val_paths, train_labels, val_labels = load_data(DATA_DIR, TAB_FILE)
    print(f"Training Set: {len(train_paths)} images")
    print(f"Validation Set: {len(val_paths)} images")
    
    train_dataset = DARTISTrainDataset(train_paths, train_labels, is_train=True)
    val_dataset = DARTISTrainDataset(val_paths, val_labels, is_train=False)
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    # 2. Build Brain
    model = RobustGatekeeperCNN().to(device)
    
    # 3. Setup Math (Loss & Optimizer)
    criterion = nn.BCEWithLogitsLoss() # Best for binary Yes/No classification
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    best_val_acc = 0.0
    
    # 4. The Training Loop
    for epoch in range(EPOCHS):
        print(f"\n[Epoch {epoch+1}/{EPOCHS}]")
        
        # --- TRAINING PHASE ---
        model.train()
        running_loss = 0.0
        start_time = time.time()
        
        for batch_idx, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad() # Clear old math
            outputs = model(images).squeeze() # Guess
            loss = criterion(outputs, labels) # Check error
            loss.backward() # Learn
            optimizer.step() # Update brain
            
            running_loss += loss.item()
            if (batch_idx + 1) % 10 == 0:
                print(f"  Batch {batch_idx+1}/{len(train_loader)} - Loss: {loss.item():.4f}")
                
        # --- VALIDATION PHASE (The Exam) ---
        model.eval()
        val_correct = 0
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images).squeeze()
                preds = (torch.sigmoid(outputs) > 0.5).float()
                val_correct += (preds == labels).sum().item()
                
        val_acc = (val_correct / len(val_dataset)) * 100
        epoch_time = time.time() - start_time
        
        print(f"-> Epoch Time: {epoch_time:.1f}s | Train Loss: {(running_loss/len(train_loader)):.4f} | Validation Accuracy: {val_acc:.2f}%")
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"[*] New High Score! Model saved to {SAVE_PATH}")

    print("\n======================================")
    print(f"TRAINING COMPLETE. Best Accuracy: {best_val_acc:.2f}%")
    print("======================================")

if __name__ == "__main__":
    train_model()
