# Image Feature Merger - Web Version

A Flask web application for merging multiple images into panoramas based on feature detection, matching, and blending.

## Features

- Upload multiple images to create panoramas
- Two merging modes:
  - Feature Merge: Uses SIFT/ORB feature detection to align and merge images
  - Side-by-Side Merge: Places images side by side with blended transitions
- Adjustable match threshold for feature detection quality
- Option to toggle between SIFT and ORB feature detectors
- Show feature matches between images
- View preprocessed image enhancement for feature detection
- Download merged results

## Requirements

- Python 3.8+
- OpenCV
- NumPy
- Flask
- Other dependencies listed in `requirements.txt`

## Installation

### Using Virtual Environment (Recommended)

1. Clone this repository:

   ```
   git clone https://github.com/yourusername/image-feature-merger.git
   cd image-feature-merger
   ```

2. Create and activate a virtual environment:
   - Windows:

   ```
   python -m venv venv
   venv\Scripts\activate
   ```

   - Linux/Mac:

   ```
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

## Running the Application

### Windows

Just run the `run_flask.bat` file by double-clicking it or from the command line:

## Usage

1. Upload at least two images using the file picker
2. Select the merge type:
   - Side-by-Side: Simple horizontal merge
   - Feature-Aligned Blend: Intelligent feature matching and blending
3. Adjust settings:
   - Match Threshold (0.1-0.9): Higher values mean stricter feature matching
   - Blend Transparency (0.1-0.9): Controls opacity in blended regions
   - ORB Detector: Enable for better results with night/low-light images
4. Click "Process Images" to generate the merged result
5. Use enhancement tools:
   - Show Feature Matches: Visualize detected matching points
   - Show Preprocessed Image: View image after enhancement
   - Manual Feature Matching: Manually select matching points
   - Enhance Panorama: Apply additional post-processing
6. Download the final result using the download button

## Credits

Based on the desktop version of Image Feature Merger, converted to a web application using Flask.
