# -*- coding: utf-8 -*-
"""
Generate a rectangular 94m^2 floor plan with prioritized room sizes and kitchen separated by walls.
"""
import json
from src.core.floor_plan_types import FloorPlanObject, ObjectType

def rgb(r, g, b):
    return (r, g, b)

WALL_THICKNESS = 1.0
DOOR_THICKNESS = 0.1

# Room sizes (width x height, in meters)
living_w, living_h = 5.5, 5.8   # Living/Dining (top left)
master_w, master_h = 4.0, 5.5    # Master Bedroom (top right)
kitchen_w, kitchen_h = 3.0, 4.0  # Kitchen (bottom left)
bed3_w, bed3_h = 3.0, 4.7        # Bedroom 3 (bottom center)
bed2_w, bed2_h = 3.0, 4.7        # Bedroom 2 (bottom right)

# Calculate total width and height
width = living_w + master_w      # 5.5 + 4.0 = 9.5m
height = max(living_h, master_h) + max(kitchen_h, bed3_h, bed2_h)  # 5.8 + 4.7 = 10.5m

# Room origins (centered at (0,0) = center of living/dining)
living_cx, living_cy = -(master_w/2), (height/2 - living_h/2)
master_cx, master_cy = (living_w/2), (height/2 - master_h/2)
kitchen_cx, kitchen_cy = -(width/2) + kitchen_w/2, -(height/2) + kitchen_h/2
bed3_cx, bed3_cy = 0, -(height/2) + bed3_h/2
bed2_cx, bed2_cy = (width/2) - bed2_w/2, -(height/2) + bed2_h/2

objects = []

# --- Outer walls ---
objects += [
    FloorPlanObject(ObjectType.WALL, (0, height/2), (width, WALL_THICKNESS), rgb(150,150,150), True, "Top Wall"),
    FloorPlanObject(ObjectType.WALL, (0, -height/2), (width, WALL_THICKNESS), rgb(150,150,150), True, "Bottom Wall"),
    FloorPlanObject(ObjectType.WALL, (-width/2, 0), (WALL_THICKNESS, height), rgb(150,150,150), True, "Left Wall"),
    FloorPlanObject(ObjectType.WALL, (width/2, 0), (WALL_THICKNESS, height), rgb(150,150,150), True, "Right Wall"),
]

# --- Internal walls ---
# Living/Master divider (vertical)
objects.append(FloorPlanObject(ObjectType.WALL, (living_w/2, living_cy), (WALL_THICKNESS, living_h), rgb(150,150,150), True, "Living/Master Divider"))
# Living/Kitchen divider (horizontal)
objects.append(FloorPlanObject(ObjectType.WALL, (-(width/2) + kitchen_w, living_cy - living_h/2 - WALL_THICKNESS/2), (living_w - kitchen_w, WALL_THICKNESS), rgb(150,150,150), True, "Living/Kitchen Divider"))
# Master/Bed2 divider (vertical)
objects.append(FloorPlanObject(ObjectType.WALL, (living_w/2 + master_w/2, master_cy), (WALL_THICKNESS, master_h), rgb(150,150,150), True, "Master/Bed2 Divider"))
# Bed3/Bed2 divider (vertical)
objects.append(FloorPlanObject(ObjectType.WALL, (bed2_cx - bed2_w/2, bed3_cy), (WALL_THICKNESS, bed3_h), rgb(150,150,150), True, "Bed3/Bed2 Divider"))
# Bed3/Kitchen divider (vertical)
objects.append(FloorPlanObject(ObjectType.WALL, (kitchen_cx + kitchen_w/2, bed3_cy), (WALL_THICKNESS, bed3_h), rgb(150,150,150), True, "Bed3/Kitchen Divider"))
# Bed3/Living divider (horizontal)
objects.append(FloorPlanObject(ObjectType.WALL, (bed3_cx, living_cy - living_h/2 - WALL_THICKNESS/2), (bed3_w, WALL_THICKNESS), rgb(150,150,150), True, "Bed3/Living Divider"))
# Kitchen/Bed3 divider (horizontal)
objects.append(FloorPlanObject(ObjectType.WALL, (kitchen_cx, kitchen_cy + kitchen_h/2), (kitchen_w, WALL_THICKNESS), rgb(150,150,150), True, "Kitchen/Bed3 Divider"))

# --- Doors ---
objects.append(FloorPlanObject(ObjectType.DOOR, (-width/2, kitchen_cy), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Main Door"))
objects.append(FloorPlanObject(ObjectType.DOOR, (living_w/2, living_cy + living_h/4), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Living/Master Door"))
objects.append(FloorPlanObject(ObjectType.DOOR, (bed3_cx, living_cy - living_h/2 - WALL_THICKNESS), (1.0, DOOR_THICKNESS), rgb(139,69,19), False, "Living/Bed3 Door"))
objects.append(FloorPlanObject(ObjectType.DOOR, (bed2_cx - bed2_w/2, bed2_cy), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Bed3/Bed2 Door"))
objects.append(FloorPlanObject(ObjectType.DOOR, (kitchen_cx + kitchen_w/2, kitchen_cy), (DOOR_THICKNESS, 1.0), rgb(139,69,19), False, "Kitchen/Bed3 Door"))

# --- Furniture (bed and table per room) ---
objects.append(FloorPlanObject(ObjectType.FURNITURE, (living_cx + 1.0, living_cy), (2.0, 1.0), rgb(139,69,19), True, "Living Sofa"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (living_cx - 1.0, living_cy), (1.2, 0.8), rgb(139,69,19), True, "Living Table"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (master_cx, master_cy + 1.0), (2.0, 1.0), rgb(139,69,19), True, "Master Bed"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (master_cx, master_cy - 1.0), (1.2, 0.8), rgb(139,69,19), True, "Master Table"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (bed2_cx, bed2_cy + 1.0), (2.0, 1.0), rgb(139,69,19), True, "Bed2 Bed"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (bed2_cx, bed2_cy - 1.0), (1.2, 0.8), rgb(139,69,19), True, "Bed2 Table"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (bed3_cx, bed3_cy + 1.0), (2.0, 1.0), rgb(139,69,19), True, "Bed3 Bed"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (bed3_cx, bed3_cy - 1.0), (1.2, 0.8), rgb(139,69,19), True, "Bed3 Table"))
objects.append(FloorPlanObject(ObjectType.FURNITURE, (kitchen_cx, kitchen_cy + 0.5), (1.5, 0.6), rgb(139,69,19), True, "Kitchen Counter"))

# --- Save to JSON ---
def save_rectangular_floor_plan(filename="floor_plan.json"):
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
    print(f"Saved rectangular prioritized floor plan to {filename} with {len(objects)} objects.")

if __name__ == "__main__":
    save_rectangular_floor_plan() 