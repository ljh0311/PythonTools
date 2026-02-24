# Image Merger

A web application for merging multiple images using computer vision techniques. This application combines a React frontend with a Python Flask backend to provide an intuitive interface for image stitching and blending.

## Features

- **Image Stitching**: Automatically merge multiple images using feature detection and matching
- **Multiple Algorithms**: Support for both SIFT and ORB feature detection algorithms
- **Manual Feature Matching**: Option to manually specify matching points between images
- **Image Preprocessing**: Automatic enhancement for night/low-light images
- **File Management**: Upload, view, and manage images and results
- **AI Feedback**: Get merge-setting suggestions from Ollama (text) or Google Gemini (vision: analyzes the merged image)
- **Responsive UI**: Modern Bootstrap-based interface

## Prerequisites

Before running this application, make sure you have the following installed:

- **Node.js** (version 14 or higher)
- **Python** (version 3.7 or higher)
- **pip** (Python package manager)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd image-merger
```

### 2. Install Frontend Dependencies

```bash
npm install
```

### 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

The project includes a `requirements.txt` with: `flask`, `opencv-python`, `numpy`, `werkzeug`, `requests`, and (optional for Gemini AI) `google-generativeai`.

## Running the Application

### 1. Start the Backend Server

Open a terminal and run:

```bash
python backend.py
```

The Flask server will start on `http://localhost:5000`

### 2. Start the Frontend Development Server

Open another terminal and run:

```bash
npm start
```

The React application will start on `http://localhost:3000` and automatically open in your browser.

## Usage

### Basic Image Merging

1. **Upload Images**: Click "Choose Files" and select at least 2 images to merge.
2. **Configure Settings**:
   - **Threshold**: Sets the minimum good match ratio for feature matching (0.5–0.9, affects how matches are selected).
   - **Alpha**: Adjusts blend transparency (0.0–1.0, where 1.0 is only the first image, 0.0 is only the second).
   - **Use ORB**: Toggle ON to use ORB (faster, less accurate); OFF for SIFT (default, more accurate).
   - **Blend Mode**: Choose from 'feature_aligned', 'multi_band', 'gradient_domain', 'simple_overlay', or 'panorama' for different merging styles.
   - **Feature Count**: Set number of features to detect (500–5000; higher can improve alignment for complex images).
   - **RANSAC Threshold**: Controls the inlier threshold for homography estimation (1.0–10.0; higher tolerates more misalignment).
3. **Merge Images**: Click "Merge Images" to process and merge the images.
4. **View Results**: The resulting merged image will appear below the form.

### Manual Feature Matching

For better control over the merging process:

1. Enable "Manual Feature Matching" checkbox
2. Click "Merge Images" to open the manual matching interface
3. Click corresponding points on both images to create matches
4. Ensure at least 4 matching points are selected
5. Submit to process the merge

### AI Feedback on Merge Settings

Use **Get AI Feedback** to have the app suggest merge configuration changes based on your feedback (and, when using Gemini, by analyzing the merged image).

- **Ollama (default)**: Text-only. Set `AI_PROVIDER=ollama` or leave unset. Requires [Ollama](https://ollama.ai) running locally (e.g. `ollama run llama3.2`).
- **Gemini (vision)**: The AI can look at the merged result image. Set `AI_PROVIDER=gemini` and provide `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) in the environment. Optionally set `GEMINI_MODEL` (e.g. `gemini-1.5-flash`). Keep the API key secret (env only, do not commit). When using Gemini, merge an image first so the backend can send it for analysis.

### File Management

- **View Files**: Navigate to the "View Files" page to see uploaded images and results
- **Maintenance**: Access maintenance tools through the "Maintenance" page

## Supported Image Formats

- PNG
- JPG/JPEG
- BMP
- SVG

## Technical Details

### Backend (Python/Flask)

- **Feature Detection**: Uses OpenCV's SIFT and ORB algorithms
- **Image Processing**: Automatic preprocessing for night/low-light images
- **File Storage**: Images stored in `static/uploads/` and results in `static/results/`
- **API Endpoints**:
  - `POST /merge`: Merge uploaded images
  - `POST /manual_match`: Process manual feature matching
  - `POST /adjust_config`: AI-adjusted merge config from user feedback (and, for Gemini, the merged image); body: `feedback`, `merge_config`, optional `result_image`
  - `GET /api/view_files`: List uploaded files and results

### Frontend (React/TypeScript)

- **UI Framework**: Bootstrap 5 with Bootstrap Icons
- **Routing**: React Router for navigation
- **State Management**: React hooks for local state
- **File Upload**: Drag-and-drop and file picker support

## Project Structure

```
image-merger/
├── backend.py              # Flask backend server
├── package.json            # Node.js dependencies
├── public/                 # Static assets
├── src/                    # React source code
│   ├── App.tsx            # Main application component
│   ├── maintain.tsx       # Maintenance page
│   └── viewfiles.tsx      # File management page
└── static/                 # Backend static files
    ├── uploads/           # Uploaded images
    └── results/           # Merged results
```

## Troubleshooting

### Common Issues

1. **Port Already in Use**: If port 3000 or 5000 is occupied, the application will prompt you to use a different port
2. **Image Upload Fails**: Ensure images are in supported formats and under 16MB
3. **Merge Fails**: Try adjusting the threshold or using manual feature matching
4. **Python Dependencies**: Make sure all required packages are installed

### Performance Tips

- Large images are automatically resized for better performance
- Use manual feature matching for complex image sets
- Adjust threshold values based on image similarity

## Development

### Adding New Features

1. **Backend**: Add new routes in `backend.py`
2. **Frontend**: Create new components in `src/`
3. **Styling**: Use Bootstrap classes or add custom CSS

### Building for Production

```bash
npm run build
```

This creates an optimized production build in the `build/` directory.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here] 