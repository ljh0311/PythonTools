# 3D Reconstruction from Video

This project implements a pipeline for creating 3D reconstructions from video input. It uses computer vision and Structure from Motion (SfM) techniques to generate 3D models from video sequences.

## Project Structure

```
3d_reconstruction/
├── src/           # Source code
├── data/          # Input video data
├── output/        # Generated 3D models and intermediate results
├── tests/         # Unit tests
└── docs/          # Documentation
```

## Features (Planned)

- Video frame extraction
- Feature detection and matching
- Camera pose estimation
- Dense reconstruction
- Mesh generation
- Texture mapping

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

(Documentation will be added as features are implemented)

## Dependencies

- OpenCV: Image processing and feature detection
- Open3D: 3D data processing and visualization
- COLMAP: Structure from Motion
- PyTorch3D: Deep learning-based 3D reconstruction (optional)

## License

MIT License 