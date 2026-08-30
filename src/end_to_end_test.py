import os
import sys
import argparse

# Ensure Python can find our core modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="Run the end-to-end pipeline.")
    parser.add_argument('--image', type=str, default='ow-0450.jpg', help='The satellite image name (e.g. ow-0450.jpg)')
    parser.add_argument('--image-path', type=str, default=None, help='Optional explicit path to the input image.')
    args = parser.parse_args()
    run_pipeline(args.image, image_path=args.image_path)


if __name__ == '__main__':
    main()
