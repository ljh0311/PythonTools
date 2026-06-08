"""
Pathfinding System
Handles route planning, obstacle avoidance, and autonomous navigation
"""

import math
import numpy as np
from typing import List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum
import heapq
from loguru import logger


class NodeType(Enum):
    """Types of grid nodes"""
    FREE = 0
    OBSTACLE = 1
    ROBOT = 2
    TARGET = 3
    PATH = 4
    EXPLORED = 5


@dataclass
class GridNode:
    """Node in the navigation grid"""
    x: int
    y: int
    node_type: NodeType
    cost: float = float('inf')
    parent: Optional['GridNode'] = None
    g_cost: float = float('inf')  # Cost from start
    h_cost: float = 0.0           # Heuristic cost to goal
    f_cost: float = float('inf')  # Total cost (g + h)
    
    def __lt__(self, other):
        return self.f_cost < other.f_cost
    
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y
    
    def __hash__(self):
        return hash((self.x, self.y))


@dataclass
class PathPoint:
    """Point in a navigation path"""
    x: float
    y: float
    theta: float  # Orientation in radians
    speed: float  # Speed at this point
    action: str   # Action to take (forward, turn, stop)


class Pathfinder:
    """A* pathfinding with obstacle avoidance"""
    
    def __init__(self, config: dict):
        self.config = config
        self.grid_size = config['navigation']['grid_size']
        self.map_width = config['navigation']['map_width']
        self.map_height = config['navigation']['map_height']
        
        # Calculate grid dimensions
        self.grid_width = int(self.map_width / self.grid_size)
        self.grid_height = int(self.map_height / self.grid_size)
        
        # Initialize grid
        self.grid = np.zeros((self.grid_height, self.grid_width), dtype=int)
        self.explored_nodes = set()
        
        # Path planning
        self.current_path = []
        self.target_position = None
        
        # Obstacle avoidance parameters
        self.robot_radius = max(config['robot']['width'], config['robot']['length']) / 2
        self.safety_margin = config['robot']['safety_distances']['comfortable']
        # Add clearance distance (5-10cm) to safety margin for path planning
        self.obstacle_clearance = 0.075  # 7.5cm clearance (middle of 5-10cm range)
        self.effective_safety_margin = self.safety_margin + self.obstacle_clearance
        
        # Movement directions (8-connected grid)
        self.directions = [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
    
    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to grid coordinates"""
        grid_x = int(x / self.grid_size)
        grid_y = int(y / self.grid_size)
        
        # Clamp to grid bounds
        grid_x = max(0, min(self.grid_width - 1, grid_x))
        grid_y = max(0, min(self.grid_height - 1, grid_y))
        
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """Convert grid coordinates to world coordinates"""
        x = (grid_x + 0.5) * self.grid_size
        y = (grid_y + 0.5) * self.grid_size
        return x, y
    
    def is_valid_position(self, x: float, y: float) -> bool:
        """Check if position is within map bounds"""
        return 0 <= x <= self.map_width and 0 <= y <= self.map_height
    
    def is_obstacle(self, grid_x: int, grid_y: int) -> bool:
        """Check if grid position contains an obstacle"""
        if not (0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height):
            return True
        
        return self.grid[grid_y, grid_x] == NodeType.OBSTACLE.value
    
    def add_obstacle(self, x: float, y: float, radius: float = None):
        """Add obstacle to the grid, accounting for clearance distance"""
        if radius is None:
            # Include clearance distance in obstacle expansion
            radius = self.robot_radius + self.effective_safety_margin
        
        grid_x, grid_y = self.world_to_grid(x, y)
        obstacle_radius_grid = int(radius / self.grid_size)
        
        # Mark all grid cells within obstacle radius
        for dx in range(-obstacle_radius_grid, obstacle_radius_grid + 1):
            for dy in range(-obstacle_radius_grid, obstacle_radius_grid + 1):
                nx, ny = grid_x + dx, grid_y + dy
                if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and
                    math.sqrt(dx*dx + dy*dy) <= obstacle_radius_grid):
                    self.grid[ny, nx] = NodeType.OBSTACLE.value
    
    def remove_obstacle(self, x: float, y: float, radius: float = None):
        """Remove obstacle from the grid"""
        if radius is None:
            radius = self.robot_radius
        
        grid_x, grid_y = self.world_to_grid(x, y)
        obstacle_radius_grid = int(radius / self.grid_size)
        
        # Clear all grid cells within obstacle radius
        for dx in range(-obstacle_radius_grid, obstacle_radius_grid + 1):
            for dy in range(-obstacle_radius_grid, obstacle_radius_grid + 1):
                nx, ny = grid_x + dx, grid_y + dy
                if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and
                    math.sqrt(dx*dx + dy*dy) <= obstacle_radius_grid):
                    self.grid[ny, nx] = NodeType.FREE.value
    
    def heuristic(self, node: GridNode, goal: GridNode) -> float:
        """Calculate heuristic cost (Euclidean distance)"""
        dx = abs(node.x - goal.x)
        dy = abs(node.y - goal.y)
        return math.sqrt(dx*dx + dy*dy) * self.grid_size
    
    def get_neighbors(self, node: GridNode) -> List[GridNode]:
        """Get valid neighboring nodes"""
        neighbors = []
        
        for dx, dy in self.directions:
            nx, ny = node.x + dx, node.y + dy
            
            if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and
                not self.is_obstacle(nx, ny)):
                
                neighbor = GridNode(nx, ny, NodeType.FREE)
                neighbors.append(neighbor)
        
        return neighbors
    
    def find_path(self, start_x: float, start_y: float, 
                  goal_x: float, goal_y: float) -> List[PathPoint]:
        """Find path from start to goal using A* algorithm"""
        # Convert to grid coordinates
        start_grid_x, start_grid_y = self.world_to_grid(start_x, start_y)
        goal_grid_x, goal_grid_y = self.world_to_grid(goal_x, goal_y)
        
        # Check if start or goal is in obstacle
        if self.is_obstacle(start_grid_x, start_grid_y):
            logger.warning("Start position is in obstacle")
            return []
        
        if self.is_obstacle(goal_grid_x, goal_grid_y):
            logger.warning("Goal position is in obstacle")
            return []
        
        # Initialize start and goal nodes
        start_node = GridNode(start_grid_x, start_grid_y, NodeType.ROBOT)
        goal_node = GridNode(goal_grid_x, goal_grid_y, NodeType.TARGET)
        
        start_node.g_cost = 0
        start_node.h_cost = self.heuristic(start_node, goal_node)
        start_node.f_cost = start_node.h_cost
        
        # Initialize open and closed sets
        open_set = [start_node]  # Only GridNode objects
        closed_set = set()       # Only (x, y) tuples
        came_from = {}           # Only (x, y) tuples as keys
        open_set_keys = set([(start_node.x, start_node.y)])
        
        while open_set:
            # Get node with lowest f_cost
            current = heapq.heappop(open_set)
            # Defensive: skip if current is a tuple
            if isinstance(current, tuple):
                continue
            open_set_keys.discard((current.x, current.y))
            # Check if we reached the goal
            if current.x == goal_node.x and current.y == goal_node.y:
                path = self._reconstruct_path(came_from, current, start_x, start_y, goal_x, goal_y)
                path = self._simplify_path(path)
                if path:
                    return path
            closed_set.add((current.x, current.y))
            # Check neighbors
            for neighbor in self.get_neighbors(current):
                neighbor_key = (neighbor.x, neighbor.y)
                if neighbor_key in closed_set:
                    continue
                # Calculate tentative g_cost
                tentative_g_cost = current.g_cost + self._distance(current, neighbor)
                # Check if this path is better
                if neighbor_key not in open_set_keys:
                    heapq.heappush(open_set, neighbor)
                    open_set_keys.add(neighbor_key)
                elif tentative_g_cost >= neighbor.g_cost:
                    continue
                # This path is better, record it
                came_from[neighbor_key] = current
                neighbor.g_cost = tentative_g_cost
                neighbor.h_cost = self.heuristic(neighbor, goal_node)
                neighbor.f_cost = neighbor.g_cost + neighbor.h_cost
        
        # No path found
        logger.warning("No path found to goal")
        return []
    
    def _distance(self, node1: GridNode, node2: GridNode) -> float:
        """Calculate distance between two nodes"""
        dx = abs(node1.x - node2.x)
        dy = abs(node1.y - node2.y)
        
        if dx == 0 or dy == 0:
            return self.grid_size  # Orthogonal movement
        else:
            return self.grid_size * math.sqrt(2)  # Diagonal movement
    
    def _reconstruct_path(self, came_from: dict, current: GridNode,
                         start_x: float, start_y: float,
                         goal_x: float, goal_y: float) -> List[PathPoint]:
        """Reconstruct path from A* result"""
        path = []
        
        # Reconstruct grid path
        grid_path = []
        current_key = (current.x, current.y)
        
        while current_key in came_from:
            grid_path.append(current)
            current = came_from[current_key]
            current_key = (current.x, current.y)
        
        grid_path.append(current)
        grid_path.reverse()
        
        # Convert to world coordinates and add orientation
        for i, node in enumerate(grid_path):
            x, y = self.grid_to_world(node.x, node.y)
            
            # Calculate orientation
            if i < len(grid_path) - 1:
                next_node = grid_path[i + 1]
                next_x, next_y = self.grid_to_world(next_node.x, next_node.y)
                theta = math.atan2(next_y - y, next_x - x)
            else:
                # Final point - maintain last orientation
                theta = path[-1].theta if path else 0.0
            
            # Determine speed based on path curvature
            speed = self.config['robot']['max_speed']
            if i > 0 and i < len(grid_path) - 1:
                # Reduce speed for turns
                prev_theta = path[-1].theta
                angle_diff = abs(theta - prev_theta)
                if angle_diff > math.pi/4:  # Sharp turn
                    speed = self.config['robot']['turn_speed']
            
            path_point = PathPoint(x, y, theta, speed, "move")
            path.append(path_point)
        
        return path
    
    def update_robot_position(self, x: float, y: float):
        """Update robot position on the grid"""
        # Clear previous robot position
        for i in range(self.grid_height):
            for j in range(self.grid_width):
                if self.grid[i, j] == NodeType.ROBOT.value:
                    self.grid[i, j] = NodeType.FREE.value
        
        # Mark new robot position
        grid_x, grid_y = self.world_to_grid(x, y)
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            self.grid[grid_y, grid_x] = NodeType.ROBOT.value
    
    def mark_explored(self, x: float, y: float):
        """Mark area as explored"""
        grid_x, grid_y = self.world_to_grid(x, y)
        self.explored_nodes.add((grid_x, grid_y))
        
        if 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height:
            if self.grid[grid_y, grid_x] == NodeType.FREE.value:
                self.grid[grid_y, grid_x] = NodeType.EXPLORED.value
    
    def get_next_exploration_target(self, robot_x: float, robot_y: float) -> Optional[Tuple[float, float]]:
        """Get next target for exploration"""
        robot_grid_x, robot_grid_y = self.world_to_grid(robot_x, robot_y)
        
        # Find unexplored areas near robot
        best_target = None
        best_score = float('inf')
        
        for grid_x in range(max(0, robot_grid_x - 20), min(self.grid_width, robot_grid_x + 21)):
            for grid_y in range(max(0, robot_grid_y - 20), min(self.grid_height, robot_grid_y + 21)):
                
                if (grid_x, grid_y) not in self.explored_nodes and not self.is_obstacle(grid_x, grid_y):
                    # Calculate score based on distance and exploration potential
                    distance = math.sqrt((grid_x - robot_grid_x)**2 + (grid_y - robot_grid_y)**2)
                    
                    # Prefer areas with more unexplored neighbors
                    unexplored_neighbors = 0
                    for dx, dy in self.directions:
                        nx, ny = grid_x + dx, grid_y + dy
                        if (0 <= nx < self.grid_width and 0 <= ny < self.grid_height and
                            (nx, ny) not in self.explored_nodes):
                            unexplored_neighbors += 1
                    
                    score = distance - unexplored_neighbors * 2  # Prefer areas with more neighbors
                    
                    if score < best_score:
                        best_score = score
                        best_target = (grid_x, grid_y)
        
        if best_target:
            return self.grid_to_world(best_target[0], best_target[1])
        
        return None
    
    def get_grid_status(self) -> dict:
        """Get current grid status"""
        return {
            'grid': self.grid.copy(),
            'explored_nodes': len(self.explored_nodes),
            'total_nodes': self.grid_width * self.grid_height,
            'exploration_percentage': len(self.explored_nodes) / (self.grid_width * self.grid_height) * 100,
            'grid_size': self.grid_size,
            'map_width': self.map_width,
            'map_height': self.map_height
        }
    
    def clear_cache(self):
        """Clear any cached pathfinding data"""
        # Reset explored nodes to force fresh pathfinding
        self.explored_nodes.clear()
        logger.info("Pathfinder cache cleared")

    def _simplify_path(self, path: List[PathPoint]) -> List[PathPoint]:
        # Remove unnecessary waypoints by checking line-of-sight
        if not path:
            return []
        simplified = [path[0]]
        i = 0
        while i < len(path) - 1:
            j = i + 1
            while j < len(path):
                if not self._line_of_sight(simplified[-1], path[j]):
                    break
                j += 1
            simplified.append(path[j-1])
            i = j - 1
        return simplified

    def _line_of_sight(self, p1: PathPoint, p2: PathPoint) -> bool:
        # Bresenham's line algorithm or similar to check for obstacles between p1 and p2
        # For now, use a simple step along the line
        steps = int(max(abs(p2.x - p1.x), abs(p2.y - p1.y)) / self.grid_size * 2)
        for k in range(1, steps):
            x = p1.x + (p2.x - p1.x) * k / steps
            y = p1.y + (p2.y - p1.y) * k / steps
            gx, gy = self.world_to_grid(x, y)
            if self.is_obstacle(gx, gy):
                return False
        return True 