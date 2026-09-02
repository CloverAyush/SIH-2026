import torch
import torch.nn as nn
import torchvision.models as models


class RobustGatekeeperCNN(nn.Module):
    """
    Module 1: The Industrial Gatekeeper (Classifier).

    ResNet-18 adapted for binary oil-vs-no-oil classification
    using single-channel grayscale SAR imagery.
    """

    def __init__(self):
        super(RobustGatekeeperCNN, self).__init__()

        # Load ResNet-18 architecture.
        # The trained checkpoint supplies the actual learned weights.
        self.resnet = models.resnet18(weights=None)

        # Modify the first convolution to accept 1-channel SAR input
        # instead of the default 3-channel RGB input.
        original_conv1 = self.resnet.conv1

        self.resnet.conv1 = nn.Conv2d(
            in_channels=1,
            out_channels=original_conv1.out_channels,
            kernel_size=original_conv1.kernel_size,
            stride=original_conv1.stride,
            padding=original_conv1.padding,
            bias=False
        )

        # Binary classifier: oil vs no-oil.
        num_features = self.resnet.fc.in_features

        self.resnet.fc = nn.Linear(
            num_features,
            1
        )

    def forward(self, x):
        return self.resnet(x)
