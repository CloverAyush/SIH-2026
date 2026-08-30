import os
import argparse
import xml.etree.ElementTree as ET
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image, ImageDraw
import time

# Import our custom U-Net
try:
    from core.unet import UNet
except ModuleNotFoundError:
    # Fallback if files were uploaded flat (directly next to each other) on Colab
    from unet import UNet

class DARTISMaskDataset(Dataset):
    def __init__(self, data_dir, xml_dir, transform=None):
        """
        data_dir: Path to the .jpg files
        xml_dir: Path to the .xml PASCAL VOC files
        """
        self.data_dir = data_dir
        self.xml_dir = xml_dir
        self.transform = transform
        
        self.samples = []
        
        print("Scanning Dataset for U-Net Training...")
        # Only load images that have a matching .xml file (images with oil)
        for filename in os.listdir(xml_dir):
            if filename.endswith(".xml"):
                xml_path = os.path.join(xml_dir, filename)
                img_name = filename.replace(".xml", ".jpg")
                img_path = os.path.join(data_dir, img_name)
                
                if os.path.exists(img_path):
                    self.samples.append((img_path, xml_path))
                    
        print(f"Found {len(self.samples)} valid Oil images with XML Ground Truths.")

    def generate_mask(self, xml_path, img_width, img_height):
        # Create a pure black image (Water)
        mask = Image.new('L', (img_width, img_height), 0)
        draw = ImageDraw.Draw(mask)
        
        # Parse XML
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Draw white polygons for every bounding box (Oil)
        for obj in root.findall('object'):
            bndbox = obj.find('bndbox')
            if bndbox is not None:
                xmin = int(bndbox.find('xmin').text)
                ymin = int(bndbox.find('ymin').text)
                xmax = int(bndbox.find('xmax').text)
                ymax = int(bndbox.find('ymax').text)
                # Fill the bounding box with pure white (255)
                draw.rectangle([xmin, ymin, xmax, ymax], fill=255)
                
        return mask

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, xml_path = self.samples[idx]
        
        # Load Raw Image
        image = Image.open(img_path).convert('L')
        width, height = image.size
        
        # Generate Ground Truth Mask
        mask = self.generate_mask(xml_path, width, height)
        
        # Apply transforms (Resize to 224x224 and convert to Tensor)
        if self.transform:
            # We must apply the EXACT same transform to both image and mask
            # For masks, we do not normalize, we just scale 0-255 to 0.0-1.0
            image = self.transform(image)
            mask_transform = transforms.Compose([
                transforms.Resize((224, 224)),
                transforms.ToTensor()
            ])
            mask = mask_transform(mask)
            
        return image, mask

def train():
    parser = argparse.ArgumentParser(description="Train U-Net Segmenter (Colab Ready)")
    parser.add_argument('--data_dir', type=str, required=True, help='Path to .jpg images')
    parser.add_argument('--xml_dir', type=str, required=True, help='Path to .xml annotations')
    parser.add_argument('--epochs', type=int, default=50, help='Number of epochs to run (Default: 50 for GPU)')
    parser.add_argument('--batch_size', type=int, default=16, help='Batch size')
    args = parser.parse_args()

    # Hardware Check
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- TRAINING ON: {str(device).upper()} ---")

    # Transformations
    img_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.5], std=[0.5])
    ])

    # Dataset & Dataloader
    dataset = DARTISMaskDataset(args.data_dir, args.xml_dir, transform=img_transform)
    
    # 80/20 Split
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = torch.utils.data.random_split(dataset, [train_size, val_size])
    
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False)

    print(f"Training Set: {train_size} masks | Validation Set: {val_size} masks")

    # Initialize U-Net
    model = UNet(in_channels=1, out_channels=1).to(device)
    
    # BCEWithLogitsLoss is mathematically superior for 1-channel binary segmentation (Oil vs Water)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    best_val_loss = float('inf')

    # Training Loop
    for epoch in range(args.epochs):
        model.train()
        running_loss = 0.0
        start_time = time.time()
        
        print(f"\n[Epoch {epoch+1}/{args.epochs}]")
        for i, (images, masks) in enumerate(train_loader):
            images, masks = images.to(device), masks.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
            if (i+1) % 10 == 0:
                print(f"  Batch {i+1}/{len(train_loader)} - Loss: {loss.item():.4f}")

        # Validation Phase
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for images, masks in val_loader:
                images, masks = images.to(device), masks.to(device)
                outputs = model(images)
                loss = criterion(outputs, masks)
                val_loss += loss.item()

        avg_train_loss = running_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        epoch_time = time.time() - start_time
        
        print(f"-> Epoch Time: {epoch_time:.1f}s | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")
        
        # Save Best Model
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            # Create models dir if it doesn't exist
            os.makedirs('../models', exist_ok=True)
            torch.save(model.state_dict(), '../models/unet_best.pth')
            print(f"[*] New High Score! Model saved to unet_best.pth")

if __name__ == '__main__':
    train()
