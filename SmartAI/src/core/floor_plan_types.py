# -*- coding: utf-8 -*-
"""
Shared floor plan data structures and utilities
Used across 2D demo, 3D simulation, and GUI
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import json
import os
from loguru import logger


class ObjectType(Enum):
    """Types of objects in the floor plan"""
    WALL = "wall"
    OBSTACLE = "obstacle"
    FURNITURE = "furniture"
    DOOR = "door"
    WINDOW = "window"


@dataclass
class FloorPlanObject:
    """2D object in the floor plan"""
    obj_type: ObjectType
    position: Tuple[float, float]  # x, y
    dimensions: Tuple[float, float]  # width, height
    color: Tuple[int, int, int]
    collision: bool = True
    name: str = ""
    rotation: float = 0.0  # degrees, default 0 (axis-aligned)


def create_default_floor_plan() -> List[FloorPlanObject]:
    """Create the default floor plan with walls, obstacles, and furniture"""
    objects = []
    
    # Object colors
    object_colors = {
        ObjectType.WALL: (150, 150, 150),
        ObjectType.OBSTACLE: (255, 0, 0),
        ObjectType.FURNITURE: (139, 69, 19),
        ObjectType.DOOR: (139, 69, 19),
        ObjectType.WINDOW: (173, 216, 230),
    }
    
    # Outer walls
    wall_thickness = 0.3
    wall_height = 2.5
    
    walls = [
        # Outer walls
        ((0, -10), (20, wall_thickness)),  # North
        ((0, 10), (20, wall_thickness)),   # South
        ((10, 0), (wall_thickness, 20)),   # East
        ((-10, 0), (wall_thickness, 20)),  # West
        
        # Internal walls
        ((-5, -5), (wall_thickness, 10)),  # Vertical wall 1
        ((5, 5), (wall_thickness, 10)),    # Vertical wall 2
        ((-5, 0), (10, wall_thickness)),   # Horizontal wall 1
        ((0, 5), (10, wall_thickness)),    # Horizontal wall 2
    ]
    
    for i, (pos, dim) in enumerate(walls):
        objects.append(FloorPlanObject(
            obj_type=ObjectType.WALL,
            position=pos,
            dimensions=dim,
            color=object_colors[ObjectType.WALL],
            collision=True,
            name=f"Wall_{i+1}"
        ))
    
    # Add obstacles
    obstacles = [
        ((-7, -7), (0.5, 0.5), "Red Cube"),
        ((7, 7), (0.5, 0.5), "Green Cube"),
        ((0, -8), (0.3, 0.3), "Blue Cylinder"),
    ]
    
    for pos, dim, name in obstacles:
        objects.append(FloorPlanObject(
            obj_type=ObjectType.OBSTACLE,
            position=pos,
            dimensions=dim,
            color=object_colors[ObjectType.OBSTACLE],
            collision=True,
            name=name
        ))
    
    # Add furniture
    furniture = [
        ((-3, 3), (1.5, 1), "Table"),
        ((3, -3), (1, 0.5), "Chair"),
    ]
    
    for pos, dim, name in furniture:
        objects.append(FloorPlanObject(
            obj_type=ObjectType.FURNITURE,
            position=pos,
            dimensions=dim,
            color=object_colors[ObjectType.FURNITURE],
            collision=True,
            name=name
        ))
    
    return objects


def save_floor_plan_to_json(objects: List[FloorPlanObject], filename: str = "floor_plan.json"):
    """Save floor plan objects to JSON file"""
    data = []
    for obj in objects:
        data.append({
            'type': obj.obj_type.value,
            'position': obj.position,
            'dimensions': obj.dimensions,
            'color': obj.color,
            'collision': obj.collision,
            'name': obj.name,
            'rotation': obj.rotation
        })
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Floor plan saved to {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to save floor plan: {e}")
        return False


def load_floor_plan_from_json(filename: str = "floor_plan.json") -> List[FloorPlanObject]:
    """Load floor plan objects from JSON file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        objects = []
        for item in data:
            obj = FloorPlanObject(
                obj_type=ObjectType(item['type']),
                position=tuple(item['position']),
                dimensions=tuple(item['dimensions']),
                color=tuple(item['color']),
                collision=item['collision'],
                name=item['name'],
                rotation=item.get('rotation', 0.0)  # Default to 0.0 if not present
            )
            objects.append(obj)
        
        logger.info(f"Floor plan loaded from {filename} with {len(objects)} objects")
        return objects
    except FileNotFoundError:
        logger.warning(f"No saved floor plan found at {filename}")
        return []
    except Exception as e:
        logger.error(f"Failed to load floor plan: {e}")
        return []


def generate_floor_plan_json():
    """Generate and save the default floor plan to JSON"""
    logger.info("Generating default floor plan...")
    objects = create_default_floor_plan()
    
    if save_floor_plan_to_json(objects):
        logger.info(f"Generated floor plan with {len(objects)} objects")
        return True
    else:
        logger.error("Failed to generate floor plan")
        return False


if __name__ == "__main__":
    # Generate the default floor plan when run directly
    generate_floor_plan_json() 