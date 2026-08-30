import torch
import torch.nn as nn
import torchvision.models as models

class RobustGatekeeperCNN(nn.Module):
    """
    Module 1: The Industrial Gatekeeper (Classifier).
    Instead of a weak 3-layer CNN, this uses a ResNet-18 architecture.
    ResNet (Residual Network) is the industry standard for image classification 
    because its 'skip connections' prevent it from getting confused by look-alikes.
    
    It is modified here to accept 1-channel (Grayscale SAR) images instead of 3-channel (RGB).
    """
    def __init__(self):
        super(RobustGatekeeperCNN, self).__init__()
        
        # 1. Load the core ResNet-18 architecture (untrained blank slate)
        self.resnet = models.resnet18(weights=None)
        
        # 2. Modify the first layer
        # By default, ResNet expects 3-channel RGB images (Red, Green, Blue).
        # SAR satellite images are just 1-channel Grayscale (radar intensity).
        # We replace the first convolutional layer to accept 1 channel.
        original_conv1 = self.resnet.conv1
        self.resnet.conv1 = nn.Conv2d(
            in_channels=1, # Changed from 3 to 1
            out_channels=original_conv1.out_channels, 
            kernel_size=original_conv1.kernel_size, 
            stride=original_conv1.stride, 
            padding=original_conv1.padding, 
            bias=original_conv1.bias
        )
        
        # 3. Modify the final classification layer
        # By default, ResNet outputs 1000 classes (for ImageNet).
        # We only need 1 class (Oil vs No-Oil probability).
        num_features = self.resnet.fc.in_features
        self.resnet.fc = nn.Sequential(
            nn.Dropout(0.5), # Drops 50% of connections to prevent overfitting to look-alikes
            nn.Linear(num_features, 1) # Outputs a single number (Oil Probability)
        )

    def forward(self, x):
        return self.resnet(x)
