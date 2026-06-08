# The Eyes - Web Version

This is the web version of The Eyes home security surveillance system. It provides a modern web interface for real-time multi-camera monitoring with motion detection, recording, and alerting capabilities.

## Features

- **Multi-Camera Monitoring**: View multiple camera feeds simultaneously in a customizable grid layout
- **Real-Time Video Streaming**: Low-latency camera feed streaming via WebSocket
- **Motion Detection**: Advanced background subtraction-based motion detection with visual indicators
- **Video Recording**: Start/stop recording per camera with motion-triggered recording support
- **Alert System**: Real-time alerts for motion detection and camera status changes
- **Responsive UI**: Modern, responsive interface that works on desktop and mobile devices
- **Layout Controls**: Dynamic grid layouts (auto, 1x1, 2x2, 3x3, 4x4) to match your viewing preferences

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher
- npm or yarn
- One or more cameras (webcams, IP cameras, or network cameras)

## Setup

### Backend Setup

1. Navigate to the web_version directory:
```bash
cd web_version
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install Python dependencies:
```bash
cd backend
pip install -r requirements.txt
```

4. Ensure the main project's src modules are accessible (they should be in the parent directory)

### Frontend Setup

1. Install Node.js dependencies:
```bash
cd frontend
npm install
```

## Running the Application

### Quick Start (Windows)

Use the provided batch script:
```bash
start_web.bat
```

This will:
- Start the backend server on http://localhost:8000
- Start the frontend development server on http://localhost:3000
- Open both in separate windows

### Manual Start

1. Start the backend server:
```bash
cd backend
python main.py
```

The backend will start on http://localhost:8000

2. In a new terminal, start the frontend development server:
```bash
cd frontend
npm start
```

The frontend will start on http://localhost:3000 and automatically open in your browser.

## Usage

1. **Allow Camera Access**: When prompted by your browser, allow camera access
2. **View Camera Feeds**: Camera feeds will appear in a grid layout
3. **Change Layout**: Use the layout dropdown to change how cameras are arranged
4. **Monitor Motion**: Motion detection indicators will appear on cameras when motion is detected
5. **Record Videos**: Click the record button on any camera to start/stop recording
6. **View Alerts**: Check the alerts panel for motion detection and system alerts
7. **Take Snapshots**: Click the camera icon on any camera view to save a snapshot

## API Endpoints

The backend provides the following REST API endpoints:

- `GET /health` - Health check and system status
- `GET /api/cameras` - List all available cameras
- `GET /api/motion/status` - Get motion detection status
- `POST /api/motion/config` - Configure motion detection settings
- `POST /api/recording/start` - Start recording for a camera
- `POST /api/recording/stop` - Stop recording for a camera
- `GET /api/recording/status` - Get recording status
- `GET /api/alerts` - Get alerts
- `POST /api/alerts/acknowledge` - Acknowledge alerts

### WebSocket Endpoints

- `ws://localhost:8000/ws/input` - Send camera frames from browser to backend
- `ws://localhost:8000/ws/camera/{camera_id}` - Receive processed camera streams from backend

## Configuration

Edit `config/config.json` in the main project directory to configure:

- Camera settings
- Motion detection sensitivity and zones
- Recording settings (codec, quality, file size limits)
- Alert preferences

## Development

- Backend code is in the `backend` directory
- Frontend code is in the `frontend/src` directory
- Components are in `frontend/src/components`
- The main application logic is in `App.js`
- WebSocket communication is handled in both `main.py` and `App.js`

## Troubleshooting

1. **Camera doesn't start:**
   - Check browser permissions (allow camera access)
   - Ensure no other application is using the camera
   - Try refreshing the page

2. **Backend connection fails:**
   - Ensure the backend server is running on port 8000
   - Check if port 8000 is available
   - Verify all Python dependencies are installed
   - Check backend logs for import errors

3. **No camera feeds appear:**
   - Check browser console for WebSocket errors
   - Verify cameras are detected (check backend logs)
   - Ensure camera permissions are granted

4. **Motion detection not working:**
   - Check if motion detection is enabled in config.json
   - Verify motion detection settings in the API
   - Check backend logs for motion detector initialization errors

5. **Recording fails:**
   - Ensure recording is enabled in config.json
   - Check disk space in the recordings directory
   - Verify write permissions for the recordings folder

## Security Notes

- The web version is designed for local network use
- For production deployment, configure CORS properly
- Use HTTPS in production for secure camera access
- Consider authentication for remote access

## Browser Compatibility

- Chrome/Edge (recommended)
- Firefox
- Safari (may have limited camera support)

## License

MIT
