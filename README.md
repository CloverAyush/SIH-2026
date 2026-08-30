# SIH26143: Intelligent Oil Spill Forensics Pipeline

This repository contains the complete end-to-end pipeline for detecting marine oil spills from Synthetic Aperture Radar (SAR) imagery, mathematically backtracking the spill using oceanic physics, and identifying the guilty vessel via AIS tracking.

This project was built for the Smart India Hackathon (Problem Statement 143: Oil Spill Detection).

## System Architecture

Our pipeline executes in 6 automated phases to perform a complete forensic analysis of an ocean region.

1. **Gatekeeper CNN (Phase 1):** A lightweight ResNet-18 model acts as a highly efficient primary filter. It scans raw SAR satellite imagery and halts the pipeline if no oil is detected, saving massive computational overhead.
2. **U-Net Segmentation (Phase 2):** If oil is detected, a deep U-Net architecture extracts a pixel-perfect binary mask of the slick, separating it from natural look-alikes like wind wakes and biogenic slicks.
3. **OpenCV Georeferencing (Phase 3):** The pixel mask is converted into a mathematically rigorous real-world GPS polygon (GeoJSON) using linear interpolation against satellite metadata.
4. **OpenOil Physics Engine (Phase 4):** 1,000 virtual oil particles are seeded inside the polygon. The script automatically fetches historical Copernicus Ocean Currents and ERA5 Wind Data, running a 48-hour backward physical simulation.
5. **Origin Zone Extraction (Phase 5):** The engine reads the binary `.nc` trajectory file using `xarray`, calculates the exact T-48h coordinates, and exports a GPS bounding box representing the "dump site".
6. **GFW AIS Integration (Phase 6):** The script connects to the Global Fishing Watch 4wings API to cross-reference the origin bounding box with live AIS transponders. It generates a ranked list of suspects based on Vessel Type (prioritizing Tankers) and Speed Over Ground anomalies.

## Project Structure

```text
SIH26_FINAL/
├── src/
│   ├── end_to_end_test.py      # Master Orchestrator (Run this file!)
│   ├── train_gatekeeper.py     # Training script for Phase 1
│   └── core/
│       ├── gatekeeper.py       # ResNet-18 Architecture
│       ├── unet.py             # U-Net Segmentation Architecture
│       ├── georeferencer.py    # Pixel-to-GPS conversion
│       ├── physics.py          # OpenDrift Backward Simulation
│       └── ais_tracker.py      # API interface for ship tracking
├── models/                     # (Ignored in Git) Place your .pth weights here
└── data/                       # (Ignored in Git) Place your raw SAR images here
```

## How to Run the Pipeline

1. **Install Dependencies:**
   Ensure you have a Python environment with PyTorch, OpenCV, xarray, and optionally OpenDrift installed.
   
2. **Execute the Forensics Script:**
   ```bash
   python src/end_to_end_test.py --image ow-0450.jpg
   ```

3. **Authentication (Optional):**
   To enable Phase 6 live tracking, set a valid Global Fishing Watch token in your environment variables:
   ```bash
   export GFW_API_KEY="your_token_here"
   ```
   *(If no token is found, the pipeline gracefully falls back to a demonstration mock to ensure presentation continuity).*

## Notes on OpenDrift
The physics engine (Phase 4) requires the `opendrift` library, which depends on C++ build tools often missing in standard Windows environments. If you are running this on Windows, the script will automatically bypass Phase 4 and use pre-calculated physics data for Phase 5 to ensure your demo never crashes. For full physics execution, run the pipeline on Linux or Google Colab.
