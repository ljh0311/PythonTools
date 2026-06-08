# -*- coding: utf-8 -*-
"""
Standalone script to generate the default floor plan JSON file
Run this script to create floor_plan.json with the default environment
"""

import sys
import os

# Add the src directory to the path
sys.path.append("src")

from src.core.floor_plan_types import generate_floor_plan_json, create_default_floor_plan, save_floor_plan_to_json


def main():
    """Generate the default floor plan JSON file"""
    print("Generating default floor plan JSON file...")
    
    # Generate the floor plan
    success = generate_floor_plan_json()
    
    if success:
        print("✅ Successfully generated floor_plan.json")
        print("📁 File location: floor_plan.json")
        
        # Show some details about the generated floor plan
        objects = create_default_floor_plan()
        print(f"📊 Floor plan contains {len(objects)} objects:")
        
        # Count by type
        type_counts = {}
        for obj in objects:
            obj_type = obj.obj_type.value
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        for obj_type, count in type_counts.items():
            print(f"   - {obj_type.capitalize()}: {count}")
        
        print("\n🎯 You can now use this file in:")
        print("   - 2D simulation (simple_2d_demo.py)")
        print("   - 3D simulation (simulation_demo.py)")
        print("   - GUI (robot_gui.py)")
        
    else:
        print("❌ Failed to generate floor plan JSON file")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 