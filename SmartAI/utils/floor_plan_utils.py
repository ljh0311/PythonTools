# -*- coding: utf-8 -*-
"""
Floor Plan Utilities
Demonstrates how to load and use the floor plan JSON file
"""

import sys
import os

# Add the src directory to the path
sys.path.append("src")

from src.core.floor_plan_types import load_floor_plan_from_json, create_default_floor_plan, save_floor_plan_to_json


def load_floor_plan_demo():
    """Demonstrate loading the floor plan from JSON"""
    print("🔍 Loading floor plan from JSON file...")
    
    # Load floor plan from JSON
    objects = load_floor_plan_from_json("floor_plan.json")
    
    if objects:
        print(f"✅ Successfully loaded {len(objects)} objects from floor_plan.json")
        
        # Display object details
        print("\n📋 Floor Plan Objects:")
        for i, obj in enumerate(objects, 1):
            print(f"  {i}. {obj.name} ({obj.obj_type.value})")
            print(f"     Position: ({obj.position[0]:.1f}, {obj.position[1]:.1f})")
            print(f"     Size: {obj.dimensions[0]:.1f} x {obj.dimensions[1]:.1f}")
            print(f"     Collision: {'Yes' if obj.collision else 'No'}")
            print()
        
        # Count by type
        type_counts = {}
        for obj in objects:
            obj_type = obj.obj_type.value
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        print("📊 Object Summary:")
        for obj_type, count in type_counts.items():
            print(f"  - {obj_type.capitalize()}: {count}")
        
        return objects
    else:
        print("❌ Failed to load floor plan")
        return None


def create_custom_floor_plan_demo():
    """Demonstrate creating a custom floor plan"""
    print("\n🏗️  Creating custom floor plan...")
    
    # Start with default floor plan
    objects = create_default_floor_plan()
    
    # Add some custom objects
    from src.core.floor_plan_types import FloorPlanObject, ObjectType
    
    # Add a door
    door = FloorPlanObject(
        obj_type=ObjectType.DOOR,
        position=(0, -5),
        dimensions=(0.1, 1.0),
        color=(139, 69, 19),
        collision=False,  # Doors don't block movement
        name="Main Door"
    )
    objects.append(door)
    
    # Add a window
    window = FloorPlanObject(
        obj_type=ObjectType.WINDOW,
        position=(5, 8),
        dimensions=(0.1, 1.5),
        color=(173, 216, 230),
        collision=False,  # Windows don't block movement
        name="Window"
    )
    objects.append(window)
    
    # Save custom floor plan
    success = save_floor_plan_to_json(objects, "custom_floor_plan.json")
    
    if success:
        print(f"✅ Custom floor plan saved with {len(objects)} objects")
        print("📁 File: custom_floor_plan.json")
    else:
        print("❌ Failed to save custom floor plan")
    
    return objects


def integration_example():
    """Show how to integrate floor plan loading in your applications"""
    print("\n🔧 Integration Example:")
    print("Here's how to use the floor plan in your applications:")
    
    print("\n1. In your 2D simulation (simple_2d_demo.py):")
    print("   ```python")
    print("   from src.core.floor_plan_types import load_floor_plan_from_json")
    print("   floor_plan_objects = load_floor_plan_from_json('floor_plan.json')")
    print("   ```")
    
    print("\n2. In your 3D simulation (simulation_demo.py):")
    print("   ```python")
    print("   from src.core.floor_plan_types import load_floor_plan_from_json")
    print("   objects = load_floor_plan_from_json('floor_plan.json')")
    print("   for obj in objects:")
    print("       # Render 3D object based on obj.position, obj.dimensions, obj.color")
    print("   ```")
    
    print("\n3. In your GUI (robot_gui.py):")
    print("   ```python")
    print("   from src.core.floor_plan_types import load_floor_plan_from_json")
    print("   objects = load_floor_plan_from_json('floor_plan.json')")
    print("   # Use objects for camera rendering and collision detection")
    print("   ```")
    
    print("\n4. For camera/sensor simulation:")
    print("   ```python")
    print("   def update_camera_view(robot_pos, robot_angle, floor_plan_objects):")
    print("       for obj in floor_plan_objects:")
    print("           # Calculate if object is visible to camera")
    print("           # Render object in camera view")
    print("   ```")


def main():
    """Main demonstration function"""
    print("🏠 Floor Plan Utilities Demo")
    print("=" * 40)
    
    # Demo 1: Load existing floor plan
    objects = load_floor_plan_demo()
    
    # Demo 2: Create custom floor plan
    custom_objects = create_custom_floor_plan_demo()
    
    # Demo 3: Show integration examples
    integration_example()
    
    print("\n🎯 Next Steps:")
    print("1. Use load_floor_plan_from_json() in your applications")
    print("2. Modify the floor plan in the 2D demo and save it")
    print("3. Load the same floor plan in 3D simulation and GUI")
    print("4. Update camera panels to show real environment objects")


if __name__ == "__main__":
    main() 