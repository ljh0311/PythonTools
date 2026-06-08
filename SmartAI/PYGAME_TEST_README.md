# Pygame Navigation Test

This directory contains two versions of the navigation test script:

## Files

1. **`test.py`** - Original matplotlib-based version (FIXED)
2. **`test_pygame.py`** - New pygame-based version
3. **`test_pygame_simple.py`** - Simple pygame test to verify installation
4. **`PYGAME_TEST_README.md`** - This file

## Key Differences

### Visualization Engine
- **Original (`test.py`)**: Uses matplotlib with TkAgg backend
- **Pygame (`test_pygame.py`)**: Uses pygame for real-time rendering

### Performance
- **Original**: Slower, more suitable for analysis and debugging
- **Pygame**: Faster, smoother real-time visualization (60 FPS)

### Features
Both versions support:
- Robot navigation visualization
- Obstacle avoidance
- LIDAR ray visualization
- Path planning display
- Learning data visualization
- Interactive testing

## Bug Fixes

### Dictionary Iteration Error
The original `test.py` had a bug where the `valid_paths` dictionary was being modified while being iterated over. This has been fixed in both versions by:

```python
# FIXED VERSION - Create a copy before iteration
valid_paths = learning_data.get('valid_paths', {}).copy()
for path_key, path_data in valid_paths.items():
    # ... process data
```

## Installation Requirements

### For Original Version (`test.py`)
```bash
pip install matplotlib numpy opencv-python
```

### For Pygame Version (`test_pygame.py`)
```bash
pip install pygame numpy opencv-python
```

## Usage

### Test Pygame Installation
```bash
python test_pygame_simple.py
```

### Run Original Version
```bash
python test.py
```

### Run Pygame Version
```bash
python test_pygame.py
```

## Interactive Commands

Both versions support the same interactive commands:
- `1` - Simple Navigation
- `2` - Obstacle Avoidance  
- `3` - Exploration
- `4` - Visual Odometry Test (if camera available)
- `5` - Demo Mode
- `6` - Debug Logging Toggle
- `7` - Quiet Mode
- `8` - Normal Mode
- `q` - Quit

## Pygame Controls

In the pygame version:
- **ESC** - Exit the visualization
- **Close Window** - Exit the application

## Advantages of Pygame Version

1. **Better Performance**: 60 FPS vs variable frame rate in matplotlib
2. **Smoother Animation**: Real-time rendering without blocking
3. **Better Event Handling**: More responsive to user input
4. **Lower Resource Usage**: More efficient for real-time applications
5. **Cross-platform**: Better compatibility across different systems

## Advantages of Matplotlib Version

1. **Better for Analysis**: Easier to add plots, graphs, and analysis tools
2. **More Plotting Options**: Rich set of visualization features
3. **Better for Debugging**: Can pause, zoom, and inspect data easily
4. **Integration**: Better integration with scientific computing workflows

## Troubleshooting

### Pygame Issues
If pygame doesn't work:
1. Install pygame: `pip install pygame`
2. Test with simple script: `python test_pygame_simple.py`
3. Check display drivers and OpenGL support

### Original Version Issues
If matplotlib doesn't work:
1. Install matplotlib: `pip install matplotlib`
2. Try different backend: `export MPLBACKEND=TkAgg`
3. Check Tkinter installation

## Performance Comparison

| Feature | Matplotlib Version | Pygame Version |
|---------|-------------------|----------------|
| Frame Rate | Variable (10-30 FPS) | Consistent 60 FPS |
| Memory Usage | Higher | Lower |
| CPU Usage | Higher | Lower |
| Responsiveness | Lower | Higher |
| Analysis Tools | Rich | Basic |

## Recommendations

- **Use Pygame version** for real-time navigation testing and demonstrations
- **Use Matplotlib version** for analysis, debugging, and development
- **Test both** to ensure compatibility with your system 