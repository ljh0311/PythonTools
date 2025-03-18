# Image Feature Merger Web Application

A web-based tool that automatically merges multiple images based on their common features. The application uses computer vision techniques to detect, match, and align image features, making it perfect for creating panoramas or combining overlapping images.

## Features

- 🌐 Web-based interface accessible from any device
- 📱 Responsive design that works on desktop and mobile
- 🔄 Automatic feature detection and matching using SIFT algorithm
- 📐 Automatic scaling, rotation, and perspective correction
- 🎚️ Adjustable matching threshold for fine-tuning results
- 🖼️ Support for multiple image formats (PNG, JPG, JPEG, BMP)
- 💾 Easy download of merged results
- 🔒 Secure file handling and processing

## Technical Details

- Backend: Python Flask
- Image Processing: OpenCV with SIFT feature detection
- Frontend: HTML5, Bootstrap 5, JavaScript
- File Processing: Supports files up to 16MB
- Security: Implements secure filename handling and file type validation

## Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

## Installation

1. Clone the repository or download the source code:
```bash
git clone <repository-url>
cd image-feature-merger
```

2. Create a virtual environment (recommended):
```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python -m venv venv
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Access the application:
   - Local access: Open `http://localhost:5000` in your web browser
   - Network access: Open `http://<your-ip-address>:5000` in any device on your network

3. Using the application:
   - Click "Choose Files" to select 2 or more images
   - Adjust the matching threshold if needed:
     - Higher values (closer to 0.9) = stricter matching, better accuracy but might miss some matches
     - Lower values (closer to 0.1) = more lenient matching, might include incorrect matches
   - Click "Merge Images" to start the process
   - Once complete, the merged image will be displayed
   - Use the "Download Merged Image" button to save the result

## Best Practices for Image Merging

1. Image Selection:
   - Use images with sufficient overlap (30-50% recommended)
   - Ensure images have distinct features or patterns
   - Maintain consistent lighting conditions between images
   - Avoid excessive motion blur

2. Performance Tips:
   - Keep image sizes reasonable (extremely large images may take longer to process)
   - Start with a threshold value of 0.7 and adjust as needed
   - Ensure images are in focus and well-lit

## Troubleshooting

1. "Not enough matches found":
   - Try decreasing the threshold value
   - Ensure images have overlapping areas
   - Check if images have sufficient distinct features

2. "Failed to merge images":
   - Verify that images have common areas
   - Try different combinations of images
   - Ensure images are not corrupted

3. Performance issues:
   - Reduce image sizes if processing is slow
   - Close other resource-intensive applications
   - Check available system memory

## Technical Implementation

The application uses several key technologies:

- **SIFT (Scale-Invariant Feature Transform)**: For robust feature detection that works regardless of image scale and rotation
- **RANSAC**: For finding the optimal homography matrix between images
- **Perspective Transformation**: For aligning and warping images into a common coordinate system
- **Alpha Blending**: For smooth transitions in overlapping areas

## Security Features

- File type validation
- Secure filename handling
- Automatic cleanup of temporary files
- Maximum file size limits
- Input sanitization

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]

## Authors

[Your Name/Organization]

## Acknowledgments

- OpenCV for computer vision capabilities
- Flask for the web framework
- Bootstrap for the UI components 