# SmartCam GUI Features

This document explains the new GUI features that have been integrated into the SmartCam application, including splash screen, error dialog, and progress dialog functionality.

## Overview

The SmartCam application now includes enhanced GUI components that provide a better user experience:

- **Splash Screen**: Professional loading screen with progress animation
- **Error Dialog**: Comprehensive error reporting with recovery suggestions
- **Progress Dialog**: Real-time progress tracking for long operations
- **Configuration System**: Centralized settings management

## Features

### 1. Splash Screen

The splash screen provides a professional loading experience with:

- **Branded Interface**: SmartCam AI branding and version information
- **Progress Animation**: Smooth progress bar with status messages
- **Configurable Duration**: Adjustable splash screen duration via settings
- **Error Handling**: Graceful fallback if splash screen fails to load

#### Usage

```python
# Launch with splash screen
python launch_smartcam.py --splash

# Or directly in code
from gui.dialogs.splash_screen import SplashScreen

splash = SplashScreen(root, completion_callback=launch_main_app)
```

#### Configuration

The splash screen duration can be configured in `config/smartcam_settings.json`:

```json
{
  "GUI_CONFIG": {
    "splash_duration": 3000
  }
}
```

### 2. Error Dialog

The error dialog provides comprehensive error reporting with:

- **Detailed Error Information**: Error type, message, and timestamp
- **Stack Trace**: Collapsible technical details for debugging
- **Recovery Suggestions**: Context-aware suggestions for resolving issues
- **Copy to Clipboard**: Easy error reporting functionality
- **Recovery Actions**: Optional callback functions for automatic recovery

#### Usage

```python
# Show error dialog
from gui.dialogs.error_dialog import show_error_dialog

show_error_dialog(parent, error, context={
    "operation": "camera_initialize",
    "camera_id": 0
})
```

#### Error Context

The error dialog provides context-aware recovery suggestions based on:

- **Error Type**: Different suggestions for different exception types
- **Operation Context**: Camera, AI, storage, or GUI operations
- **System Context**: File paths, memory usage, network status
- **SmartCam-Specific**: Camera connection, AI model loading, etc.

### 3. Progress Dialog

The progress dialog provides real-time feedback for long operations:

- **Progress Tracking**: Visual progress bar with percentage
- **ETA Calculation**: Estimated time to completion
- **Status Messages**: Detailed status updates
- **Cancellation Support**: Allow users to cancel operations
- **Performance Optimized**: Throttled updates for smooth UI

#### Usage

```python
# Show progress dialog
from gui.dialogs.progress_dialog import show_progress, update_progress, close_progress

progress = show_progress(parent, "Initializing Camera", "Loading drivers...")
update_progress(0.5, "Testing AI components...")
close_progress()
```

#### Features

- **Never Shows 0%**: Always starts at 1% for immediate feedback
- **Smooth Animation**: Interpolated progress updates
- **ETA Calculation**: Based on recent progress samples
- **File Size Warnings**: Automatic warnings for large files
- **Throttled Updates**: Prevents UI freezing during rapid updates

### 4. Configuration System

Centralized configuration management with:

- **Default Settings**: Comprehensive default configurations
- **Persistent Storage**: Settings saved to JSON file
- **Category Organization**: GUI, Camera, AI, Storage, etc.
- **Validation**: Automatic validation and fallback to defaults

#### Configuration Categories

```json
{
  "GUI_CONFIG": {
    "splash_duration": 3000,
    "theme": "default",
    "window_size": "800x600"
  },
  "CAMERA_CONFIG": {
    "default_camera_id": 0,
    "default_resolution": [640, 480],
    "default_fps": 30
  },
  "AI_CONFIG": {
    "enable_face_detection": true,
    "enable_motion_detection": true,
    "detection_confidence": 0.5
  },
  "STORAGE_CONFIG": {
    "output_directory": "captures",
    "auto_cleanup_enabled": true,
    "cleanup_age_hours": 24
  },
  "ERROR_HANDLING": {
    "show_detailed_errors": true,
    "log_errors_to_file": true
  }
}
```

## Integration Examples

### Camera Initialization with Progress

```python
def initialize_camera_with_progress(self, camera_id):
    # Show progress dialog
    progress = show_progress(
        self.root, 
        "Initializing Camera", 
        "Setting up camera and AI components...",
        can_cancel=True,
        cancel_callback=self._cancel_camera_init
    )
    
    def init_camera():
        try:
            update_progress(0.2, "Loading camera drivers...")
            self.camera = SmartCamera(camera_id=camera_id)
            
            update_progress(0.5, "Initializing AI components...")
            self._test_detection_components()
            
            update_progress(0.8, "Finalizing setup...")
            self._setup_preview()
            
            update_progress(1.0, "Camera ready!")
            close_progress()
            
            self.root.after(0, self._on_camera_ready)
            
        except Exception as e:
            close_progress()
            self._on_camera_error(e)
    
    threading.Thread(target=init_camera, daemon=True).start()
```

### Error Handling with Recovery

```python
def handle_camera_error(self, error, context=None):
    if context is None:
        context = {}
    
    context.update({
        "operation": "camera_operation",
        "camera_id": self.selected_camera_id,
        "timestamp": datetime.now().isoformat()
    })
    
    # Show error dialog with recovery options
    show_error_dialog(
        self.root, 
        error, 
        context,
        recovery_callback=self._retry_camera_init
    )

def _retry_camera_init(self):
    """Recovery callback for camera initialization errors."""
    try:
        self._initialize_camera(self.selected_camera_id)
    except Exception as e:
        # If retry fails, show another error dialog
        show_error_dialog(self.root, e, {
            "operation": "camera_retry",
            "original_error": str(self.last_error)
        })
```

### Splash Screen Integration

```python
def launch_with_splash(self):
    """Launch application with splash screen."""
    try:
        root = tk.Tk()
        root.withdraw()  # Hide main window
        
        # Show splash screen
        splash = SplashScreen(
            root, 
            completion_callback=lambda: self._launch_main_app(root)
        )
        
    except Exception as e:
        # Fallback to direct launch
        self._launch_main_app(None)

def _launch_main_app(self, root):
    """Launch main application after splash screen."""
    try:
        if root:
            root.destroy()
        
        # Launch main application
        main_root = tk.Tk()
        app = SmartCameraGUI(main_root)
        main_root.mainloop()
        
    except Exception as e:
        handle_error(None, e, {
            "operation": "launch_main_application"
        })
```

## Launch Options

### Command Line Usage

```bash
# Launch with splash screen
python launch_smartcam.py --splash

# Launch GUI version
python launch_smartcam.py --gui

# Launch console version
python launch_smartcam.py --console

# Launch PC UI version
python launch_smartcam.py --device 2

# Launch with debug mode
python launch_smartcam.py --debug
```

### Direct Python Usage

```python
# Launch with splash screen
from main import run_with_splash_screen
run_with_splash_screen()

# Launch without splash screen
from main import main
main()

# Launch GUI with splash
from gui_app import _run_with_splash_screen
_run_with_splash_screen(device_type=1)
```

## Error Recovery Suggestions

The error dialog provides smart recovery suggestions based on error context:

### Camera Errors
- Check camera connection and drivers
- Try different USB ports
- Restart camera application
- Update camera drivers

### AI Model Errors
- Check model file integrity
- Verify sufficient memory
- Update AI dependencies
- Disable some AI features temporarily

### Storage Errors
- Check disk space
- Verify write permissions
- Check file path validity
- Try different storage location

### GUI Errors
- Restart application
- Check display settings
- Update graphics drivers
- Verify Python/Tkinter installation

## Performance Considerations

### Progress Dialog Optimization
- Throttled UI updates (100ms minimum)
- Smooth progress interpolation
- Efficient ETA calculation
- Background thread operations

### Error Dialog Optimization
- Lazy stack trace loading
- Collapsible technical details
- Efficient error context gathering
- Graceful fallback handling

### Splash Screen Optimization
- Configurable duration
- Non-blocking progress animation
- Immediate visual feedback
- Graceful error handling

## Troubleshooting

### Common Issues

1. **Splash Screen Not Showing**
   - Check GUI components availability
   - Verify tkinter installation
   - Check for import errors

2. **Error Dialog Not Appearing**
   - Verify error_dialog.py is available
   - Check parent window validity
   - Ensure proper error context

3. **Progress Dialog Freezing**
   - Check for blocking operations
   - Verify threading implementation
   - Monitor memory usage

4. **Configuration Not Loading**
   - Check config directory permissions
   - Verify JSON file format
   - Check for syntax errors

### Debug Mode

Enable debug mode for detailed logging:

```bash
python launch_smartcam.py --debug
```

Or set environment variable:

```bash
export SMARTCAM_DEBUG=1
python launch_smartcam.py
```

## Future Enhancements

- **Theme Support**: Customizable color schemes
- **Localization**: Multi-language support
- **Plugin System**: Extensible dialog components
- **Advanced Analytics**: Usage tracking and performance metrics
- **Cloud Integration**: Remote error reporting and recovery 