# Floor Plan Integration Guide

This guide explains how to use the unified floor plan system for your smart robot project.

## 📁 Files Created

### Core Files
- **`src/core/floor_plan_types.py`** - Shared data structures and utilities
- **`floor_plan.json`** - Default floor plan with walls, obstacles, and furniture
- **`generate_floor_plan.py`** - Script to generate the JSON file
- **`floor_plan_utils.py`** - Utility functions and examples

### Demo Files
- **`floor_plan_gui_demo.py`** - GUI demo showing camera and map integration
- **`gui_floor_plan_integration.py`** - Alternative GUI integration example

## 🏗️ Floor Plan Structure

### Data Types
```python
from src.core.floor_plan_types import ObjectType, FloorPlanObject

# Object types: WALL, OBSTACLE, FURNITURE, DOOR, WINDOW
# Each object has: position, dimensions, color, collision, name
```

### JSON Format
```json
[
  {
    "type": "wall",
    "position": [0, -10],
    "dimensions": [20, 0.1],
    "color": [150, 150, 150],
    "collision": true,
    "name": "Wall_1"
  }
]
```

## 🚀 Quick Start

### 1. Generate the Floor Plan
```bash
python generate_floor_plan.py
```
This creates `floor_plan.json` with the default environment.

### 2. Load in Your Applications
```python
from src.core.floor_plan_types import load_floor_plan_from_json

# Load floor plan objects
objects = load_floor_plan_from_json("floor_plan.json")
print(f"Loaded {len(objects)} objects")
```

### 3. Use in Different Components

#### 2D Simulation (`simple_2d_demo.py`)
- Already integrated! Uses shared floor plan types
- Press `L` to load from JSON, `S` to save changes

#### 3D Simulation (`simulation_demo.py`)
```python
from src.core.floor_plan_types import load_floor_plan_from_json

# Load objects for 3D rendering
floor_plan_objects = load_floor_plan_from_json("floor_plan.json")
for obj in floor_plan_objects:
    # Render 3D object at obj.position with obj.dimensions
    render_3d_object(obj.position, obj.dimensions, obj.color)
```

#### GUI (`robot_gui.py`)
```python
from src.core.floor_plan_types import load_floor_plan_from_json

# Load for camera rendering
objects = load_floor_plan_from_json("floor_plan.json")

# Update camera view
def update_camera_view(robot_pos, robot_angle):
    for obj in objects:
        # Calculate if object is visible
        # Render in camera panel
```

## 📷 Camera Integration

### Camera View Function
```python
def get_camera_view(robot_x, robot_y, robot_angle, floor_plan_objects):
    """Generate camera view based on robot position and floor plan"""
    # Transform objects to robot's local frame
    # Project to camera surface
    # Return rendered image
```

### Example Usage
```python
# In your GUI or simulation
camera_image = get_camera_view(robot.x, robot.y, robot.angle, floor_plan_objects)
camera_panel.update_image(camera_image)
```

## 🗺️ Map Integration

### 2D Map Rendering
```python
def render_floor_plan_map(canvas, floor_plan_objects, robot_pos=None):
    """Render floor plan as 2D map"""
    for obj in floor_plan_objects:
        # Convert world coordinates to screen coordinates
        # Draw object rectangle with appropriate color
        # Add labels for large objects
```

## 🔧 Integration Examples

### 1. Sensor Simulation
```python
def update_sensors(robot_pos, robot_angle, floor_plan_objects):
    """Update sensor readings based on floor plan"""
    for sensor in robot.sensors:
        reading = sensor.calculate_reading(robot_pos, robot_angle, floor_plan_objects)
        sensor.update_reading(reading)
```

### 2. Collision Detection
```python
def check_collision(robot_pos, robot_size, floor_plan_objects):
    """Check if robot collides with any objects"""
    for obj in floor_plan_objects:
        if obj.collision:
            if objects_intersect(robot_pos, robot_size, obj.position, obj.dimensions):
                return True
    return False
```

### 3. Pathfinding
```python
def create_navigation_map(floor_plan_objects, grid_size=0.1):
    """Create navigation grid from floor plan"""
    # Convert floor plan objects to grid obstacles
    # Return grid for pathfinding algorithm
```

## 🎮 Demo Applications

### Run GUI Demo
```bash
python floor_plan_gui_demo.py
```
- Shows camera view and 2D map
- Interactive robot position controls
- Real-time object detection

### Run Utilities Demo
```bash
python floor_plan_utils.py
```
- Demonstrates loading and saving
- Shows object details and statistics
- Provides integration examples

## 🔄 Workflow

### 1. Design Floor Plan
- Use `simple_2d_demo.py` in edit mode
- Add walls, obstacles, furniture
- Save with `S` key

### 2. Test in Simulations
- Load same floor plan in 2D and 3D demos
- Verify collision detection
- Test sensor readings

### 3. Integrate in GUI
- Load floor plan for camera rendering
- Use for map visualization
- Implement in monitoring panels

### 4. Deploy
- Use consistent floor plan across all components
- Update when environment changes
- Version control your floor plans

## 📋 Best Practices

### 1. Coordinate System
- Use consistent coordinate system (meters)
- Origin at center of environment
- Positive X: right, Positive Y: up

### 2. Object Naming
- Use descriptive names: "Kitchen Table", "Front Door"
- Include object type in name
- Avoid special characters

### 3. Collision Properties
- Set `collision=False` for doors and windows
- Use appropriate dimensions for realistic interaction
- Consider sensor visibility vs collision

### 4. File Management
- Keep floor plans in version control
- Use descriptive filenames: `kitchen_floor_plan.json`
- Document changes and updates

## 🐛 Troubleshooting

### Common Issues

1. **File not found**
   ```bash
   python generate_floor_plan.py  # Generate the file first
   ```

2. **Import errors**
   ```python
   import sys
   sys.path.append("src")  # Add src to path
   ```

3. **Camera shows no objects**
   - Check robot position and angle
   - Verify objects are within camera FOV
   - Ensure objects have collision=True

4. **Objects not rendering**
   - Check coordinate transformations
   - Verify object dimensions are reasonable
   - Test with simple test objects

## 📚 Next Steps

1. **Customize Environment**
   - Modify floor plan for your specific use case
   - Add more object types if needed
   - Create multiple floor plans for different scenarios

2. **Advanced Features**
   - Implement dynamic object updates
   - Add object properties (texture, material)
   - Create floor plan editor GUI

3. **Integration**
   - Connect to real robot sensors
   - Implement SLAM for automatic mapping
   - Add floor plan validation

## 📞 Support

For issues or questions:
1. Check the demo applications for examples
2. Review the utility functions in `floor_plan_utils.py`
3. Test with the provided demo files
4. Ensure all dependencies are installed

---

**Happy robot programming! 🤖** 