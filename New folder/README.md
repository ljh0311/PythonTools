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

1. Clone this repository:
```
git clone <repository-url>
cd image-merger-web
```

2. Create a virtual environment (recommended):
```
python -m venv venv
```

3. Activate the virtual environment:
   - Windows:
   ```
   venv\Scripts\activate
   ```
   - Linux/Mac:
   ```
   source venv/bin/activate
   ```

4. Install dependencies:
```
pip install -r requirements.txt
```

## Running the Application

### Windows

Just run the `run_flask.bat` file by double-clicking it or from the command line:
```
run_flask.bat
```

### Manual Start

1. Set the Flask application environment variable:
   - Windows:
   ```
   set FLASK_APP=app.py
   set FLASK_DEBUG=1
   ```
   - Linux/Mac:
   ```
   export FLASK_APP=app.py
   export FLASK_DEBUG=1
   ```

2. Run the Flask development server:
```
python -m flask run
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Usage

1. Upload at least two images using the file picker
2. Select the merge type (Feature Merge or Side-by-Side)
3. Adjust the threshold slider for feature matching quality
4. Toggle ORB detector if needed (better for night images)
5. Click "Process Images" to create the panorama
6. Use the additional buttons to show feature matches or preprocessed images
7. Download the result using the download button

## Directory Structure

- `app.py`: The main Flask application
- `static/`: Static assets (CSS, JS, and temporary images)
  - `uploads/`: Temporary storage for uploaded images
  - `results/`: Storage for processed images and results
- `templates/`: HTML templates
  - `index.html`: Main application page

## Credits

Based on the desktop version of Image Feature Merger, converted to a web application using Flask.
