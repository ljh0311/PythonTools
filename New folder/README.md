# Image Feature Merger - Web Edition

A web-based application for merging images using computer vision techniques, built with Flask and OpenCV. This is the web version of the original desktop application, providing similar functionality through a browser interface.

## Features

- **Multiple Merge Methods**:
  - Feature-based panorama merging (SIFT/ORB detection)
  - Side-by-side merging with blended transitions
  - Feature-aligned blending with transparency control
  
- **Visual Analysis Tools**:
  - View feature matches between images
  - See preprocessed images for better understanding of feature detection
  - Toggle between SIFT and ORB detectors (ORB often works better for night images)
  
- **Responsive UI**:
  - Real-time thumbnail previews
  - Progress indicators
  - Downloadable results

## Requirements

- Python 3.8+
- OpenCV
- Flask
- NumPy
- Werkzeug

All dependencies are listed in `requirements.txt`.

## Installation

1. Clone this repository:

```
git clone https://github.com/yourusername/image-feature-merger.git
cd image-feature-merger
```

2. Create a virtual environment (recommended):

```
python -m venv venv
```

3. Activate the virtual environment:

   - On Windows:

     ```
     venv\Scripts\activate
     ```

   - On macOS/Linux:

     ```
     source venv/bin/activate
     ```

4. Install dependencies:

```
pip install -r requirements.txt
```

## Running the Application

1. Start the Flask server:

```
python app.py
```

2. Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

## Usage

1. **Upload Images**: Click the "Choose Files" button to select two or more images to merge.

2. **Choose Merge Type**:
   - **Feature Merge**: Advanced panorama creation with feature detection
   - **Side-by-Side**: Arrange images next to each other with blended transitions
   - **Blend**: Feature-aligned overlay with transparency control

3. **Adjust Settings**:
   - Match Threshold: Controls the strictness of feature matching
   - Blend Transparency: Adjusts the balance between images when blending
   - Toggle ORB/SIFT detector: Try ORB for better results with night images

4. **Process**: Click "Process Images" to generate the merged result.

5. **Additional Features**:
   - "Show Feature Matches": Visualize how features are matched between images
   - "Show Preprocessed Image": See how the image is enhanced for feature detection

6. **Save Results**: Use the "Download Result" button to save the merged image.

## Technical Details

This application uses OpenCV's feature detection and image processing capabilities:

- SIFT (Scale-Invariant Feature Transform) for detecting robust image features
- ORB (Oriented FAST and Rotated BRIEF) as an alternative feature detector
- Homography estimation for alignment of images
- Various blending techniques for seamless transitions

## Troubleshooting

- **Memory Issues**: Large images are automatically resized to improve performance
- **Poor Merging Results**: Try adjusting the threshold or changing the detector type
- **Error Messages**: Check the console for detailed error messages if merges fail

## License

[MIT License](LICENSE)

## Credits

This application is a web conversion of the original desktop application built with PyQt.
