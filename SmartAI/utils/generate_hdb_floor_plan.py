# -*- coding: utf-8 -*-
"""
Generate HDB 4-room floor plan JSON for simulator
Origin (0,0) is at the center of the living/dining room
Includes all walls, doors, and major furniture
"""

import json
from src.core.floor_plan_types import FloorPlanObject, ObjectType

# Helper for color
def rgb(r, g, b):
    return (r, g, b)

# Wall thickness
WALL_THICKNESS = 0.3
DOOR_THICKNESS = 0.1

# Living/dining room is at origin (0,0)
# We'll use approximate positions and sizes (in meters)
objects = []

# --- Walls (outer boundary) ---
# Rectangle: width 11m, height 8.5m, centered at (0,0)
objects += [
    # Top
    FloorPlanObject(ObjectType.WALL, (0, 4.25), (11, WALL_THICKNESS), rgb(150,150,150), True, "Top Wall"),
    # Bottom
    FloorPlanObject(ObjectType.WALL, (0, -4.25), (11, WALL_THICKNESS), rgb(150,150,150), True, "Bottom Wall"),
    # Left
    FloorPlanObject(ObjectType.WALL, (-5.5, 0), (WALL_THICKNESS, 8.5), rgb(150,150,150), True, "Left Wall"),
    # Right
    FloorPlanObject(ObjectType.WALL, (5.5, 0), (WALL_THICKNESS, 8.5), rgb(150,150,150), True, "Right Wall"),
]

# --- Internal walls (approximate, based on floor plan) ---
# Bedroom walls
objects += [
    # Vertical wall between living/dining and bedrooms
    FloorPlanObject(ObjectType.WALL, (2.2, 2.2), (WALL_THICKNESS, 4.5), rgb(150,150,150), True, "Bedroom Divider"),
    # Horizontal wall for bedrooms (top)
    FloorPlanObject(ObjectType.WALL, (2.2, 4.25-1.2), (6.6, WALL_THICKNESS), rgb(150,150,150), True, "Bedroom Top Wall"),
    # Vertical wall between bedrooms
    FloorPlanObject(ObjectType.WALL, (4.2, 2.2), (WALL_THICKNESS, 4.5), rgb(150,150,150), True, "Bedroom Divider 2"),
    # Main bedroom right wall
    FloorPlanObject(ObjectType.WALL, (5.5-1.0, 2.2), (WALL_THICKNESS, 4.5), rgb(150,150,150), True, "Main Bedroom Wall"),
]

# Kitchen and service yard
objects += [
    # Kitchen left wall
    FloorPlanObject(ObjectType.WALL, (-3.8, -2.5), (WALL_THICKNESS, 3.5), rgb(150,150,150), True, "Kitchen Left Wall"),
    # Kitchen bottom wall
    FloorPlanObject(ObjectType.WALL, (-2.5, -4.25+1.0), (2.6, WALL_THICKNESS), rgb(150,150,150), True, "Kitchen Bottom Wall"),
    # Service yard right wall
    FloorPlanObject(ObjectType.WALL, (-1.2, -3.5), (WALL_THICKNESS, 2.0), rgb(150,150,150), True, "Service Yard Wall"),
]

# Bath/WC
objects += [
    FloorPlanObject(ObjectType.WALL, (1.2, -2.5), (WALL_THICKNESS, 3.0), rgb(150,150,150), True, "Bath Wall"),
    FloorPlanObject(ObjectType.WALL, (2.5, -3.5), (2.6, WALL_THICKNESS), rgb(150,150,150), True, "Bath Bottom Wall"),
]

# --- Doors ---
objects += [
    # Main entrance
    FloorPlanObject(ObjectType.DOOR, (-5.5+WALL_THICKNESS/2, -1.5), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Main Door"),
    # Bedroom doors
    FloorPlanObject(ObjectType.DOOR, (2.2, 0.5), (1.0, DOOR_THICKNESS), rgb(139,69,19), False, "Bedroom 1 Door"),
    FloorPlanObject(ObjectType.DOOR, (4.2, 0.5), (1.0, DOOR_THICKNESS), rgb(139,69,19), False, "Bedroom 2 Door"),
    FloorPlanObject(ObjectType.DOOR, (5.5-1.0, 0.5), (1.0, DOOR_THICKNESS), rgb(139,69,19), False, "Main Bedroom Door"),
    # Kitchen door
    FloorPlanObject(ObjectType.DOOR, (-2.5, -1.0), (1.0, DOOR_THICKNESS), rgb(139,69,19), False, "Kitchen Door"),
    # Bath/WC doors
    FloorPlanObject(ObjectType.DOOR, (1.2, -3.0), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Bath Door"),
    FloorPlanObject(ObjectType.DOOR, (2.5, -3.0), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "WC Door"),
]

# --- Furniture (approximate positions and sizes) ---
objects += [
    # Living room sofa
    FloorPlanObject(ObjectType.FURNITURE, (-2.5, 1.5), (2.0, 0.8), rgb(139,69,19), True, "Sofa"),
    # TV console
    FloorPlanObject(ObjectType.FURNITURE, (-4.0, 2.5), (1.0, 0.3), rgb(139,69,19), True, "TV Console"),
    # Dining table
    FloorPlanObject(ObjectType.FURNITURE, (0.0, -1.5), (1.5, 0.8), rgb(139,69,19), True, "Dining Table"),
    # Kitchen counter
    FloorPlanObject(ObjectType.FURNITURE, (-3.0, -2.5), (1.5, 0.6), rgb(139,69,19), True, "Kitchen Counter"),
    # Beds in bedrooms
    FloorPlanObject(ObjectType.FURNITURE, (3.0, 3.0), (2.0, 1.5), rgb(139,69,19), True, "Bedroom 1 Bed"),
    FloorPlanObject(ObjectType.FURNITURE, (5.0, 3.0), (2.0, 1.5), rgb(139,69,19), True, "Bedroom 2 Bed"),
    FloorPlanObject(ObjectType.FURNITURE, (5.0, 1.0), (2.0, 1.5), rgb(139,69,19), True, "Main Bedroom Bed"),
    # Wardrobes
    FloorPlanObject(ObjectType.FURNITURE, (3.0, 1.0), (1.0, 0.5), rgb(139,69,19), True, "Bedroom 1 Wardrobe"),
    FloorPlanObject(ObjectType.FURNITURE, (5.0, 1.0), (1.0, 0.5), rgb(139,69,19), True, "Bedroom 2 Wardrobe"),
    FloorPlanObject(ObjectType.FURNITURE, (6.0, 1.0), (1.0, 0.5), rgb(139,69,19), True, "Main Bedroom Wardrobe"),
]

# --- Save to JSON ---
def save_hdb_floor_plan(filename="floor_plan.json"):
    data = []
    for obj in objects:
        data.append({
            'type': obj.obj_type.value,
            'position': obj.position,
            'dimensions': obj.dimensions,
            'color': obj.color,
            'collision': obj.collision,
            'name': obj.name
        })
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Saved HDB floor plan to {filename} with {len(objects)} objects.")

if __name__ == "__main__":
    save_hdb_floor_plan() 