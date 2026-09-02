# MARTRACE

## Maritime Oil Spill Detection, Drift Investigation & Vessel Attribution

MARTRACE is an intelligent oil-spill investigation prototype designed to help marine pollution investigators detect oil slicks from satellite imagery, characterize the detected spill, reconstruct its likely drift and origin using environmental data, and identify vessels that warrant further investigation using AIS evidence.

The system is designed around an investigation workflow, not just an oil-spill classifier.

## What is MARTRACE for?

When an oil spill is observed at sea, the critical question is not only:

> Is there oil?

It is also:

> Where is the spill, where could it have originated, how did it drift, and which vessels were potentially associated with that origin?

MARTRACE connects these stages into one automated workflow:

## Core Capabilities

### 1. Oil Spill Detection

MARTRACE uses a ResNet-18 based binary classifier to determine whether an input SAR image contains an oil spill.

The current prototype Gatekeeper V2 was trained and evaluated using a scene-based dataset split.

**Current frozen test performance:**

- Accuracy: **96.22%**
- Precision: **96.24%**
- Recall: **94.04%**
- F1 Score: **95.13%**
- ROC-AUC: **99.39%**
- PR-AUC: **99.20%**

The detector is designed to reduce false positives so that downstream investigation is only triggered when an oil-spill hypothesis is sufficiently strong.

### 2. Oil Spill Segmentation

After oil is detected, a U-Net model produces a pixel-level spill representation.

The resulting mask is converted into connected polygons that can be used for:

- Spill geometry
- Spatial visualization
- Geospatial analysis
- Downstream drift simulation

The current U-Net is a prototype component and is not considered final scientific validation.

### 3. Geospatial Characterization

The segmented spill is converted into geographic polygons and represented as GeoJSON.

This creates a bridge between computer-vision output and geographic/environmental analysis.

### 4. Environmental Drift Analysis

MARTRACE integrates:

- Copernicus Marine ocean-current data
- ERA5 meteorological wind data
- OpenDrift / OpenOil for particle-based drift simulation

The current prototype performs a backward drift simulation from the detected slick to estimate a plausible origin region.

Environmental data is cached locally after retrieval to avoid repeated downloads for the same analysis case.

### 5. AIS-Based Vessel Investigation

MARTRACE analyses vessel information around the inferred spill origin and time window.

The prototype uses an evidence-fusion scoring system based on:

- Spatio-temporal compatibility
- Trajectory compatibility
- Behavioral evidence
- Contextual evidence

The system produces an **Investigative Compatibility Score (0–100)** together with:

- Risk level
- Confidence level
- Evidence breakdown
- Human-readable reasons for the ranking

Only the highest-priority candidates are surfaced to the investigator.

### Important Attribution Principle

MARTRACE does **not** claim:

> Vessel X caused the spill.

Instead, it produces:

> Vessel X is a high-priority investigative candidate based on the available evidence.

This distinction is fundamental to the system's design.

## Investigation Dashboard

The frontend presents the investigation as a maritime intelligence workflow rather than exposing raw machine-learning outputs.

The dashboard is designed to communicate:

- Oil detection status
- Detection probability/confidence
- Segmentation results
- Spill geometry
- Environmental conditions
- Drift/backtracking results
- Inferred origin information
- AIS candidate rankings
- Evidence supporting each candidate

Internal file paths, raw JSON, credentials, and implementation details are intentionally hidden from the investigator-facing interface.


Current Prototype Architecture
Satellite Imagery
       │
       ▼
Oil / No-Oil Detection
       │
       ▼
Oil Spill Segmentation
       │
       ▼
Spill Geometry & Geospatialization
       │
       ▼
Oceanographic + Meteorological Data
       │
       ▼
Backward Drift Reconstruction
       │
       ▼
Estimated Origin Zone / Time
       │
       ▼
AIS Traffic Analysis
       │
       ▼
Investigative Compatibility Ranking
       │
       ▼
Investigator Dashboard

Frontend Dashboard
        │
        ▼
      FastAPI
        │
        ▼
   MARTRACE Pipeline
        │
        ├── Gatekeeper CNN
        │
        ├── U-Net
        │
        ├── Georeferencing
        │
        ├── Copernicus Marine
        │
        ├── ERA5
        │
        ├── OpenDrift / OpenOil
        │
        └── AIS Investigation

Running the Prototype
Backend

Create and activate the Python virtual environment, then install the project's required dependencies.

Configure the required environmental data credentials:

Copernicus Marine credentials for ocean currents
Copernicus Climate Data Store credentials for ERA5 wind data

Start the FastAPI backend.

Frontend

Start the frontend development server and open the dashboard in a browser.

The frontend communicates with the FastAPI /api/analyze endpoint.

Environmental Credentials

MARTRACE requires credentials for environmental data retrieval.

Copernicus Marine

Used for ocean-current data.

Copernicus Climate Data Store

Used for ERA5 wind data.

Credentials are local configuration and must never be committed to Git.

Data and Model Scope

The current prototype was developed using DARTIS-derived imagery for the initial Gatekeeper training and evaluation workflow.

This was useful for establishing and validating the detection stage, but its reported performance does not prove universal generalization to arbitrary Sentinel-1 products.

The intended SIH-scale evolution is to move toward Sentinel-1-native training and ingestion while retaining the downstream investigation architecture.

Prototype vs Future System

The current repository is a proof-of-concept for the complete investigation workflow.

Current prototype
Oil/no-oil detection
Spill segmentation
Polygon generation
Geospatial characterization
Environmental data integration
Backward drift simulation
AIS investigation framework
Evidence-based vessel ranking
Investigator dashboard
Planned SIH-scale improvements
Native Sentinel-1 product ingestion
Sentinel-1-native model training
Improved pixel-level segmentation
Multi-hypothesis spill-age estimation
Uncertainty-aware origin reconstruction
Real historical AIS integration
More rigorous vessel behavior modelling
Larger-scale validation across geographically diverse scenes
Production-grade deployment and data handling
Known Prototype Limitations

The current implementation intentionally demonstrates the complete investigation concept rather than claiming production readiness.

Key limitations include:

The current Gatekeeper was trained and evaluated on DARTIS-derived imagery.
Native Sentinel-1 product ingestion is planned for the full SIH implementation.
The current U-Net remains a prototype segmentation component.
The current drift reconstruction uses a fixed backtracking window and therefore represents a hypothesis rather than a definitive spill age.
The current AIS demonstration uses synthetic vessel data to validate the scoring and investigation workflow.
Real historical AIS integration is planned for the full system.
Further scientific validation is required before operational deployment.

These limitations are explicitly separated from the architectural direction of the full MARTRACE system.

Design Philosophy

MARTRACE is built around one principle:

Satellite detection tells us what happened at the observation point. Investigation requires reconstructing what happened before that observation.

Therefore, the system connects remote sensing, environmental modelling, geospatial analysis, and vessel intelligence into a single investigation workflow.

The objective is not to replace investigators.

It is to give investigators a faster, evidence-driven starting point for determining where a spill may have originated and which vessels deserve closer examination.

Attribution Philosophy

The vessel ranking system is an evidence-fusion mechanism.

It does not attempt to produce a probability of guilt.

Instead, it evaluates how compatible a vessel's observed AIS behavior is with the inferred spill origin hypothesis.

The current prototype considers:

spatial proximity
temporal compatibility
trajectory interaction
trajectory direction
behavioral changes
vessel context
AIS evidence quality

The resulting score is therefore an investigative prioritization score rather than a legal or causal attribution.

Status

Prototype complete for internal hackathon evaluation.

The current implementation demonstrates the major stages of the intended MARTRACE investigation workflow while explicitly identifying the components that require further scientific validation and production hardening for a full SIH implementation.