"""
Autonomous Navigation Controller
Handles autonomous robot navigation, obstacle avoidance, and path following
"""

import time
import math
import threading
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
from loguru import logger
import json
import os
import random
import ast

from ..core.robot_state import RobotState, RobotMode, Position
from ..hardware.motor_controller import MotorController
from ..hardware.sensor_manager import SensorManager
from .pathfinder import Pathfinder, PathPoint


class NavigationState(Enum):
    """States of autonomous navigation"""
    IDLE = "idle"
    PLANNING = "planning"
    FOLLOWING_PATH = "following_path"
    AVOIDING_OBSTACLE = "avoiding_obstacle"
    REPLANNING_ROUTE = "replanning_route"  # New state for route replanning
    REACHED_GOAL = "reached_goal"
    STUCK = "stuck"
    ERROR = "error"
    BACKTRACKING = "backtracking"
    REACTIVATING = "reactivating"  # New state for reactivation after timeout


@dataclass
class NavigationGoal:
    """Navigation goal with position and tolerance"""
    x: float
    y: float
    tolerance: float = 0.1  # meters
    max_speed: float = 0.83  # m/s (3 km/h)
    timeout: float = 30.0   # seconds


class AutonomousController:
    """Autonomous navigation controller"""
    
    def __init__(self, robot_state: RobotState, motor_controller: MotorController,
                 sensor_manager: SensorManager, pathfinder: Pathfinder):
        self.robot_state = robot_state
        self.motor_controller = motor_controller
        self.sensor_manager = sensor_manager
        self.pathfinder = pathfinder
        
        # Navigation state
        self.nav_state = NavigationState.IDLE
        self.current_goal: Optional[NavigationGoal] = None
        self.current_path: List[PathPoint] = []
        self.path_index = 0
        
        # Control parameters
        self.max_linear_speed = 0.83  # m/s (3 km/h)
        self.max_angular_speed = 1.0  # rad/s
        self.position_tolerance = 0.1  # meters
        self.orientation_tolerance = 0.1  # radians
        
        # Obstacle avoidance
        self.obstacle_threshold = 0.3  # meters
        self.emergency_stop_threshold = 0.15  # meters
        self.avoidance_speed = 0.3  # m/s (increased from 0.2)
        self.obstacle_clearance = 0.075  # 7.5cm clearance (middle of 5-10cm range) - minimum distance to maintain from obstacles
        
        # Adaptive speed control parameters
        self.safe_distance = 1.0  # meters - distance where speed starts to reduce (increased for higher speed)
        self.min_safe_distance = 0.4  # meters - distance where speed is at minimum (increased for safety)
        self.min_speed_scale = 0.5  # minimum speed multiplier (50% of max speed, increased from 30%)
        self.speed_recovery_rate = 0.15  # speed recovery rate per control cycle (increased for faster response)
        self.last_speed_scale = 1.0  # track previous speed scale for smooth transitions
        
        # Proactive route replanning parameters
        self.route_replan_threshold = 1.5  # meters - distance to start considering replanning (increased from 1.5m)
        self.route_replan_trigger = 1.0    # meters - distance to trigger replanning (increased from 1.0m)
        self.max_replan_attempts = 3       # Maximum replanning attempts
        self.replan_attempts = 0           # Current replanning attempts
        self.last_replan_time = 0          # Time of last replanning attempt
        self.replan_cooldown = 5.0         # Seconds between replanning attempts
        
        # Reactivation parameters for timeout recovery
        self.max_reactivation_attempts = 5  # Maximum reactivation attempts
        self.reactivation_attempts = 0      # Current reactivation attempts
        self.reactivation_strategies = [
            'backup_and_turn',
            'spin_in_place',
            'wiggle_movement',
            'aggressive_backup',
            'random_movement',
            'aggressive_random_walk'  # New strategy
        ]
        self.current_reactivation_strategy = 0
        self.reactivation_start_time = 0
        self.reactivation_timeout = 10.0  # Seconds for each reactivation attempt
        
        # PID control for path following
        self.linear_kp = 1.0
        self.angular_kp = 2.0
        self.angular_ki = 0.1
        self.angular_kd = 0.5
        
        # Control loop
        self.control_thread = None
        self.running = False
        self.control_frequency = 20  # Hz
        self.last_control_time = time.time()
        
        # Safety
        self.emergency_stop = False
        self.last_goal_time = time.time()
        
        # Exploration
        self.exploration_mode = False
        self.explored_positions = set()
        self.explored_cells = set()  # Track explored grid cells
        
        # Frontier-based exploration
        self.frontiers = []  # List of frontier cells (i, j)
        self.frontier_cache = {}  # Cache for frontier calculations {(i, j): (score, timestamp)}
        self.frontier_cache_timeout = 5.0  # Cache timeout in seconds
        self.failed_frontiers = set()  # Track frontiers that failed to reach
        self.frontier_failure_threshold = 3  # Max failures before marking as unreachable
        self.frontier_failure_count = {}  # Track failure count per frontier
        self.recent_positions = []  # Track recent positions for loop detection
        
        # Exploration metrics
        self.exploration_start_time = None
        self.exploration_distance = 0.0
        self.exploration_last_position = None
        self.frontiers_visited = 0
        self.frontier_success_count = 0
        self.exploration_area = 0.0
        
        # Learning data save optimization
        self.last_learning_save_time = 0.0
        self.learning_save_cooldown = 10.0  # Minimum seconds between saves
        self.learning_data_changed = False
        
        # Validation tracking
        self.last_validation_time = 0.0
        self.validation_interval = 300.0  # 5 minutes in seconds
        self.last_validation_stats = None
        self.validation_count = 0
        
        # Add to AutonomousController __init__
        self.max_backtrack_attempts = 5
        self.backtrack_attempts = 0
        self.last_turn_direction = 1  # 1 for left, -1 for right
        self.max_recovery_attempts = 10
        self.recovery_attempts = 0
        
        self.stuck_locations = []  # List of dicts: [{"count": N, "x": X, "y": Y}, ...]
        self.stuck_locations_file = os.path.join(os.path.dirname(__file__), '../../stuck_locations.json')
        self.stuck_location_counter = 0  # Counter for assigning counts to new stuck locations
        
        self.min_distance_to_goal = float('inf')
        self.min_distance_to_waypoint = float('inf')  # Track progress to current waypoint
        self.last_progress_time = time.time()
        self.last_position_check_time = time.time()
        self.last_position = None  # Track last position for movement detection
        self.progress_threshold = 0.2  # meters
        self.stuck_position_threshold = 0.1  # meters - if robot moves less than this, consider stuck
        self.stuck_time_threshold = 5.0  # seconds - time before considering stuck if not moving
        
        self.wandering = False
        self.wander_turning = False
        self.wander_turn_start = 0
        self.wander_turn_duration = 0
        # Smart backtracking
        self.backtracking = False
        self.backtrack_start_time = 0
        # Navmesh logging
        self.navmesh_edges = {}  # {(from_cell, to_cell): [waypoints]}
        self.last_navmesh_cell = None
        self.current_navmesh_path = []
        self.navmesh_file = 'navmesh.json'
        self.load_navmesh()
        
        # --- Learning structures ---
        self.valid_paths = {}  # {(from_cell, to_cell): [waypoints]}
        self.areas_of_caution = set()  # set of (i, j) grid cells
        # Note: stuck_locations is initialized above as a list
        self._load_learning_data()
        
        logger.info("Autonomous controller initialized")
    
    def start(self):
        """Start the autonomous controller"""
        if not self.running:
            self.running = True
            self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
            self.control_thread.start()
            logger.info("Autonomous controller started")
    
    def stop(self):
        """Stop the autonomous controller"""
        self.running = False
        self.nav_state = NavigationState.IDLE
        self.current_goal = None
        self.current_path = []
        self.path_index = 0
        self.emergency_stop = True
        self.motor_controller.stop()
        logger.info("Autonomous controller stopped")
    
    def navigate_to(self, x: float, y: float, tolerance: float = 0.1, 
                   max_speed: float = 0.83, timeout: float = 30.0) -> bool:
        """Navigate to a specific position"""
        if self.nav_state != NavigationState.IDLE:
            logger.warning("Navigation already in progress")
            return False
        
        self.current_goal = NavigationGoal(x, y, tolerance, max_speed, timeout)
        self.last_goal_time = time.time()
        self.nav_state = NavigationState.PLANNING
        self.emergency_stop = False
        
        # Reset replanning state for new navigation
        self.replan_attempts = 0
        self.last_replan_time = 0
        
        self.min_distance_to_goal = float('inf')
        self.last_progress_time = time.time()
        
        logger.info(f"Starting navigation to ({x:.2f}, {y:.2f})")
        return True
    
    def start_exploration(self):
        """Start autonomous exploration mode"""
        if self.nav_state != NavigationState.IDLE:
            logger.warning("Navigation already in progress")
            return False
        
        self.exploration_mode = True
        self.explored_positions.clear()
        self.nav_state = NavigationState.PLANNING
        self.emergency_stop = False
        
        # Initialize exploration metrics
        self.exploration_start_time = time.time()
        self.exploration_distance = 0.0
        current_pos = self.robot_state.get_position()
        self.exploration_last_position = (current_pos.x, current_pos.y)
        self.frontiers_visited = 0
        self.frontier_success_count = 0
        self.exploration_area = 0.0
        self.recent_positions = []
        self.frontier_failure_count = {}
        
        logger.info("Starting autonomous exploration")
        return True
    
    def stop_exploration(self):
        """Stop exploration mode"""
        self.exploration_mode = False
        self.nav_state = NavigationState.IDLE
        self.current_goal = None
        self.motor_controller.stop()
        logger.info("Exploration stopped")
    
    def emergency_stop_navigation(self):
        """Emergency stop all navigation"""
        self.emergency_stop = True
        self.nav_state = NavigationState.IDLE
        self.current_goal = None
        self.current_path = []
        self.recovery_attempts = 0
        self.motor_controller.stop()
        logger.warning("Emergency stop activated")
    
    def _control_loop(self):
        """Main control loop for autonomous navigation"""
        while self.running:
            try:
                if not self.emergency_stop:
                    # Debug print for robot position
                    self._update_navigation()
                time.sleep(1.0 / self.control_frequency)
            except Exception as e:
                logger.error(f"Error in control loop: {e}")
                self.nav_state = NavigationState.ERROR
                self.motor_controller.stop()
    
    def _update_navigation(self):
        """Update navigation state and control"""
        try:
            if self.exploration_mode and self.wandering:
                self._wander()
                return
            current_time = time.time()
            
            # Periodic validation during exploration mode
            if self.exploration_mode:
                time_since_last_validation = current_time - self.last_validation_time
                if time_since_last_validation >= self.validation_interval:
                    self._validate_learning_data()
                    self.last_validation_time = current_time
                    self.validation_count += 1
            
            # Track progress toward goal and current waypoint
            if self.current_goal:
                current_pos = self.robot_state.get_position()
                dist_to_goal = math.hypot(self.current_goal.x - current_pos.x, self.current_goal.y - current_pos.y)
                
                # Check progress toward final goal
                if dist_to_goal < self.min_distance_to_goal - self.progress_threshold:
                    self.min_distance_to_goal = dist_to_goal
                    self.last_progress_time = current_time
                
                # Also track progress toward current waypoint if following path
                if self.nav_state == NavigationState.FOLLOWING_PATH and self.current_path and self.path_index < len(self.current_path):
                    waypoint = self.current_path[self.path_index]
                    dist_to_waypoint = math.hypot(waypoint.x - current_pos.x, waypoint.y - current_pos.y)
                    if dist_to_waypoint < self.min_distance_to_waypoint - self.progress_threshold:
                        self.min_distance_to_waypoint = dist_to_waypoint
                        self.last_progress_time = current_time
                
                # Check if robot is actually moving (not just stuck in place)
                if self.last_position is not None:
                    movement = math.hypot(current_pos.x - self.last_position[0], current_pos.y - self.last_position[1])
                    if movement > self.stuck_position_threshold:
                        # Robot is moving, reset stuck timer
                        self.last_progress_time = current_time
                    elif current_time - self.last_progress_time > self.stuck_time_threshold:
                        # Robot hasn't moved enough and timeout exceeded
                        # Check motor speeds before declaring stuck
                        left_speed, right_speed = self.motor_controller.get_speeds()
                        motor_speed_magnitude = (abs(left_speed) + abs(right_speed)) / 2.0
                        
                        # Only declare stuck if motors are actually trying to move
                        if motor_speed_magnitude > 1.0:  # Motors are commanded to move
                            logger.warning(f"Robot appears stuck - movement: {movement:.3f}m in {current_time - self.last_progress_time:.1f}s, motor speeds: L={left_speed:.2f}, R={right_speed:.2f}")
                        else:
                            logger.debug(f"Robot not moving - motor speeds are low: L={left_speed:.2f}, R={right_speed:.2f}, movement: {movement:.3f}m")
                        
                        # Force progress update to prevent immediate timeout
                        self.last_progress_time = current_time
                        # Try to recover by checking if we can skip waypoint or replan
                        if self.nav_state == NavigationState.FOLLOWING_PATH and self.current_path:
                            # If very close to waypoint, advance to next one
                            if self.path_index < len(self.current_path):
                                waypoint = self.current_path[self.path_index]
                                dist_to_waypoint = math.hypot(waypoint.x - current_pos.x, waypoint.y - current_pos.y)
                                if dist_to_waypoint < self.position_tolerance * 2:  # More lenient threshold
                                    logger.info(f"Advancing stuck robot past waypoint {self.path_index} (distance: {dist_to_waypoint:.3f}m)")
                                    self.path_index += 1
                                    self.min_distance_to_waypoint = float('inf')
                                    self.last_progress_time = current_time
                
                # Update last position
                self.last_position = (current_pos.x, current_pos.y)
                self.last_position_check_time = current_time
            
            # Track recent positions for loop detection (exploration mode)
            if self.exploration_mode:
                current_pos = self.robot_state.get_position()
                self.recent_positions.append((current_pos.x, current_pos.y))
                # Keep only last 20 positions
                if len(self.recent_positions) > 20:
                    self.recent_positions = self.recent_positions[-20:]
            
            # Check timeout based on progress
            if (self.current_goal and 
                current_time - self.last_progress_time > self.current_goal.timeout):
                logger.warning("Navigation timeout (no progress)")
                
                # For exploration mode, track frontier failures
                if self.exploration_mode and self.current_goal:
                    current_pos = self.robot_state.get_position()
                    grid_size = self.robot_state.config['navigation']['grid_size']
                    goal_i = int(self.current_goal.y // grid_size)
                    goal_j = int(self.current_goal.x // grid_size)
                    frontier_cell = (goal_i, goal_j)
                    
                    # Check if we're stuck in a loop (revisiting same areas)
                    if hasattr(self, 'recent_positions'):
                        recent_positions = getattr(self, 'recent_positions', [])
                        if len(recent_positions) > 10:
                            # Check if we've been in similar positions recently
                            similar_positions = sum(1 for p in recent_positions[-10:] 
                                                  if math.hypot(p[0] - current_pos.x, p[1] - current_pos.y) < 0.5)
                            if similar_positions > 5:
                                logger.warning("Exploration loop detected - revisiting same areas")
                                # Mark current frontier as failed
                                if frontier_cell not in self.failed_frontiers:
                                    self.failed_frontiers.add(frontier_cell)
                                    logger.info(f"Marked frontier {frontier_cell} as failed (loop detection)")
                    
                    # Track frontier failure
                    frontier_failures = getattr(self, 'frontier_failure_count', {})
                    if frontier_cell not in frontier_failures:
                        frontier_failures[frontier_cell] = 0
                    frontier_failures[frontier_cell] += 1
                    self.frontier_failure_count = frontier_failures
                    
                    # If frontier failed too many times, mark as unreachable
                    if frontier_failures[frontier_cell] >= self.frontier_failure_threshold:
                        self.failed_frontiers.add(frontier_cell)
                        logger.warning(f"Frontier {frontier_cell} marked as unreachable after {frontier_failures[frontier_cell]} failures")
                        # Try alternative frontier
                        if self._try_alternative_frontier():
                            logger.info("Switched to alternative frontier")
                            self._reset_recovery_attempts()
                            return
                
                self.recovery_attempts += 1
                if self.recovery_attempts <= self.max_recovery_attempts:
                    logger.info(f"Attempting reactivation {self.recovery_attempts}/{self.max_recovery_attempts}")
                    self.nav_state = NavigationState.REACTIVATING
                    self.reactivation_start_time = time.time()
                    self.reactivation_attempts = 0
                    self.current_reactivation_strategy = 0
                    current_pos = self.robot_state.get_position()
                    self.stuck_position = (current_pos.x, current_pos.y)
                    return
                else:
                    logger.warning("Max recovery attempts reached - attempting global replan before declaring stuck")
                    if self._attempt_global_replan():
                        logger.info("Global replan successful - resuming navigation")
                        self._reset_recovery_attempts()
                        self.nav_state = NavigationState.PLANNING
                        return
                    else:
                        # For exploration mode, try alternative frontier before giving up
                        if self.exploration_mode and self._try_alternative_frontier():
                            logger.info("Switched to alternative frontier after global replan failed")
                            self._reset_recovery_attempts()
                            return
                        logger.error("Global replan failed - robot is permanently stuck")
                        self._record_stuck_location()
                        self.nav_state = NavigationState.ERROR
                        self.motor_controller.stop()
                        return
            
            # State machine
            try:
                if self.nav_state == NavigationState.IDLE:
                    if self.exploration_mode:
                        self._start_exploration_planning()
                
                elif self.nav_state == NavigationState.PLANNING:
                    self._plan_path()
                
                elif self.nav_state == NavigationState.FOLLOWING_PATH:
                    self._follow_path()
                
                elif self.nav_state == NavigationState.AVOIDING_OBSTACLE:
                    self._avoid_obstacle()
                
                elif self.nav_state == NavigationState.REPLANNING_ROUTE:
                    self._replan_route()
                
                elif self.nav_state == NavigationState.REACTIVATING:
                    self._handle_reactivation()
                
                elif self.nav_state == NavigationState.REACHED_GOAL:
                    self._handle_goal_reached()
                
                elif self.nav_state == NavigationState.STUCK:
                    self._handle_stuck()
                
                elif self.nav_state == NavigationState.ERROR:
                    self.motor_controller.stop()
                    return
                
                elif self.nav_state == NavigationState.BACKTRACKING:
                    # Reverse for a short time (e.g., 1 second)
                    if not hasattr(self, 'backtrack_start_time'):
                        self.backtrack_start_time = time.time()
                    elapsed = time.time() - self.backtrack_start_time
                    if elapsed < 1.0:
                        self.motor_controller.set_speeds(-0.4, -0.4)  # Increased backtracking speed
                    else:
                        self.motor_controller.stop()
                        # Check if obstacle is still too close
                        sensor_data = self.sensor_manager.get_sensor_data()
                        front_distance = sensor_data['ultrasonic']['front'].value
                        if front_distance < self.emergency_stop_threshold:
                            self.backtrack_attempts += 1
                            if self.backtrack_attempts < self.max_backtrack_attempts:
                                self.backtrack_start_time = time.time()  # Backtrack again
                            else:
                                logger.warning("Max backtrack attempts reached, robot is stuck.")
                                self.nav_state = NavigationState.STUCK
                                del self.backtrack_start_time
                        else:
                            # Use LIDAR (ultrasonic) to decide turn direction
                            left_distance = sensor_data['ultrasonic']['left'].value
                            right_distance = sensor_data['ultrasonic']['right'].value
                            # If both sides are blocked, just backtrack again
                            if left_distance < self.emergency_stop_threshold and right_distance < self.emergency_stop_threshold:
                                self.backtrack_start_time = time.time()  # Backtrack again
                            else:
                                # Prefer the more open side
                                if left_distance > right_distance:
                                    turn_direction = 1  # left
                                elif right_distance > left_distance:
                                    turn_direction = -1  # right
                                else:
                                    turn_direction = self.last_turn_direction * -1  # alternate
                                self.last_turn_direction = turn_direction
                                # Turn in place for a short time (e.g., 0.7s)
                                self.turn_start_time = time.time()
                                self.turn_duration = 0.7
                                self.turning = True
                                self.turn_direction = turn_direction
                                self.nav_state = NavigationState.BACKTRACKING
                                return
                
                else:
                    logger.warning(f"Unknown navigation state: {self.nav_state}")
                    self.nav_state = NavigationState.ERROR
                    
            except (ValueError, AttributeError) as e:
                logger.error(f"State machine configuration error: {e}")
                self.nav_state = NavigationState.ERROR
                self.motor_controller.stop()
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Hardware communication error in state machine: {e}")
                self.nav_state = NavigationState.ERROR
                self.motor_controller.stop()
            except Exception as e:
                logger.error(f"Unexpected error in state machine: {e}")
                self.nav_state = NavigationState.ERROR
                self.motor_controller.stop()
                
            # Handle turning in place as part of backtracking
            if hasattr(self, 'turning') and self.turning:
                elapsed = time.time() - self.turn_start_time
                if elapsed < self.turn_duration:
                    # Turn in place: left positive, right negative
                    speed = 0.2
                    self.motor_controller.set_speeds(speed * self.turn_direction, -speed * self.turn_direction)
                    return
                else:
                    self.motor_controller.stop()
                    self.turning = False
                    del self.turn_start_time
                    del self.turn_duration
                    del self.turn_direction
                    # After turning, try to re-plan
                    self.nav_state = NavigationState.PLANNING
                
            # At the end of each navigation update, mark the current cell as explored
            self._mark_current_cell_explored()
            
        except Exception as e:
            logger.error(f"Error in _update_navigation: {e}")
            self.nav_state = NavigationState.ERROR
            self.motor_controller.stop()
    
    def _mark_current_cell_explored(self):
        """Mark the robot's current grid cell as explored."""
        pos = self.robot_state.get_position()
        grid_size = self.robot_state.config['navigation']['grid_size']
        i = int(pos.y // grid_size)
        j = int(pos.x // grid_size)
        self.explored_cells.add((i, j))

    def _get_unexplored_cells(self):
        """Return a list of unexplored grid cells."""
        map_width = self.robot_state.config['navigation']['map_width']
        map_height = self.robot_state.config['navigation']['map_height']
        grid_size = self.robot_state.config['navigation']['grid_size']
        n_rows = int(map_height // grid_size)
        n_cols = int(map_width // grid_size)
        unexplored = []
        for i in range(n_rows):
            for j in range(n_cols):
                if (i, j) not in self.explored_cells and not self.pathfinder.is_obstacle(j, i):
                    unexplored.append((i, j))
        return unexplored
    
    def _detect_frontiers(self):
        """Detect frontier cells - unexplored cells adjacent to explored ones."""
        map_width = self.robot_state.config['navigation']['map_width']
        map_height = self.robot_state.config['navigation']['map_height']
        grid_size = self.robot_state.config['navigation']['grid_size']
        n_rows = int(map_height // grid_size)
        n_cols = int(map_width // grid_size)
        
        frontiers = []
        # 4-connected neighbors (up, down, left, right)
        neighbor_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        for i in range(n_rows):
            for j in range(n_cols):
                # Skip if already explored or is obstacle
                if (i, j) in self.explored_cells or self.pathfinder.is_obstacle(j, i):
                    continue
                
                # Check if this unexplored cell has at least one explored neighbor
                is_frontier = False
                for di, dj in neighbor_dirs:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n_rows and 0 <= nj < n_cols:
                        if (ni, nj) in self.explored_cells:
                            is_frontier = True
                            break
                
                if is_frontier:
                    # Skip if this frontier has failed too many times
                    if (i, j) not in self.failed_frontiers:
                        frontiers.append((i, j))
        
        self.frontiers = frontiers
        return frontiers

    def _score_frontier(self, frontier_i: int, frontier_j: int, robot_pos: Position) -> float:
        """Score a frontier using multi-criteria evaluation.
        
        Returns a score (lower is better) based on:
        - Distance to robot (weight: 0.3)
        - Exploration potential - unexplored neighbors (weight: 0.4)
        - Path feasibility (weight: 0.2)
        - Obstacle clearance (weight: 0.1)
        """
        grid_size = self.robot_state.config['navigation']['grid_size']
        map_width = self.robot_state.config['navigation']['map_width']
        map_height = self.robot_state.config['navigation']['map_height']
        n_rows = int(map_height // grid_size)
        n_cols = int(map_width // grid_size)
        
        # Convert frontier to world coordinates
        cell_x = frontier_j * grid_size + grid_size / 2
        cell_y = frontier_i * grid_size + grid_size / 2
        
        # 1. Distance score (normalized, weight: 0.3)
        distance = math.hypot(cell_x - robot_pos.x, cell_y - robot_pos.y)
        max_distance = math.hypot(map_width, map_height)
        distance_score = (distance / max_distance) * 0.3 if max_distance > 0 else 0.3
        
        # 2. Exploration potential - count unexplored neighbors (weight: 0.4)
        neighbor_dirs = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        unexplored_neighbors = 0
        for di, dj in neighbor_dirs:
            ni, nj = frontier_i + di, frontier_j + dj
            if 0 <= ni < n_rows and 0 <= nj < n_cols:
                if (ni, nj) not in self.explored_cells and not self.pathfinder.is_obstacle(nj, ni):
                    unexplored_neighbors += 1
        # Normalize: max 8 neighbors, invert so more neighbors = lower score
        exploration_potential = (1.0 - min(unexplored_neighbors / 8.0, 1.0)) * 0.4
        
        # 3. Path feasibility - check if path exists (weight: 0.2)
        path_feasible = 1.0  # Assume feasible by default
        try:
            path = self.pathfinder.find_path(robot_pos.x, robot_pos.y, cell_x, cell_y)
            if not path or len(path) == 0:
                path_feasible = 0.0  # No path found
        except:
            path_feasible = 0.0
        path_score = (1.0 - path_feasible) * 0.2
        
        # 4. Obstacle clearance - check nearby obstacles (weight: 0.1)
        obstacle_count = 0
        check_radius = 2  # Check 2 cells around frontier
        for di in range(-check_radius, check_radius + 1):
            for dj in range(-check_radius, check_radius + 1):
                ni, nj = frontier_i + di, frontier_j + dj
                if 0 <= ni < n_rows and 0 <= nj < n_cols:
                    if self.pathfinder.is_obstacle(nj, ni):
                        obstacle_count += 1
        obstacle_score = min(obstacle_count / (check_radius * 2 + 1) ** 2, 1.0) * 0.1
        
        total_score = distance_score + exploration_potential + path_score + obstacle_score
        return total_score
    
    def _select_best_frontier(self) -> Optional[Tuple[float, float]]:
        """Select the best frontier based on scoring."""
        if not self.frontiers:
            return None
        
        robot_pos = self.robot_state.get_position()
        current_time = time.time()
        
        best_frontier = None
        best_score = float('inf')
        
        for frontier_i, frontier_j in self.frontiers:
            # Check cache first
            cache_key = (frontier_i, frontier_j)
            if cache_key in self.frontier_cache:
                cached_score, cache_time = self.frontier_cache[cache_key]
                if current_time - cache_time < self.frontier_cache_timeout:
                    score = cached_score
                else:
                    # Cache expired, recalculate
                    score = self._score_frontier(frontier_i, frontier_j, robot_pos)
                    self.frontier_cache[cache_key] = (score, current_time)
            else:
                # Not in cache, calculate and store
                score = self._score_frontier(frontier_i, frontier_j, robot_pos)
                self.frontier_cache[cache_key] = (score, current_time)
            
            if score < best_score:
                best_score = score
                best_frontier = (frontier_i, frontier_j)
        
        if best_frontier:
            grid_size = self.robot_state.config['navigation']['grid_size']
            cell_x = best_frontier[1] * grid_size + grid_size / 2
            cell_y = best_frontier[0] * grid_size + grid_size / 2
            return (cell_x, cell_y)
        
        return None
    
    def _try_alternative_frontier(self) -> bool:
        """Try to switch to an alternative frontier when current one fails.
        
        Returns True if successfully switched to alternative frontier.
        """
        if not self.exploration_mode or not self.current_goal:
            return False
        
        # Get current goal's frontier cell
        grid_size = self.robot_state.config['navigation']['grid_size']
        current_goal_i = int(self.current_goal.y // grid_size)
        current_goal_j = int(self.current_goal.x // grid_size)
        current_frontier = (current_goal_i, current_goal_j)
        
        # Detect frontiers again to get fresh list
        frontiers = self._detect_frontiers()
        
        if not frontiers:
            return False
        
        # Try to find an alternative frontier (not the current one and not failed)
        robot_pos = self.robot_state.get_position()
        alternatives = []
        
        for frontier_i, frontier_j in frontiers:
            if (frontier_i, frontier_j) != current_frontier:
                if (frontier_i, frontier_j) not in self.failed_frontiers:
                    # Score this alternative
                    score = self._score_frontier(frontier_i, frontier_j, robot_pos)
                    alternatives.append(((frontier_i, frontier_j), score))
        
        if not alternatives:
            return False
        
        # Select best alternative
        alternatives.sort(key=lambda x: x[1])  # Sort by score
        best_alt = alternatives[0][0]
        
        # Set new goal
        cell_x = best_alt[1] * grid_size + grid_size / 2
        cell_y = best_alt[0] * grid_size + grid_size / 2
        self.current_goal = NavigationGoal(cell_x, cell_y, 0.2, 0.3, 15.0)
        self.nav_state = NavigationState.PLANNING
        self.min_distance_to_goal = float('inf')
        self.last_progress_time = time.time()
        
        logger.info(f"Switched to alternative frontier: ({cell_x:.2f}, {cell_y:.2f})")
        return True
    
    def _start_exploration_planning(self):
        """Start planning for exploration using frontier-based target selection."""
        self._mark_current_cell_explored()
        
        # Validate learning data at exploration start
        if self.validation_count == 0:  # Only validate on first exploration start
            self._validate_learning_data()
            self.last_validation_time = time.time()
            self.validation_count += 1
        
        # Detect frontiers
        frontiers = self._detect_frontiers()
        
        if not frontiers:
            logger.info("No frontiers found, switching to wandering mode.")
            self.wandering = True
            self.current_goal = None
            return
        
        # Select best frontier
        self.wandering = False
        target_cell = self._select_best_frontier()
        
        if target_cell:
            self.current_goal = NavigationGoal(target_cell[0], target_cell[1], 0.2, 0.3, 15.0)
            self.nav_state = NavigationState.PLANNING
            
            # Log frontier selection with metrics
            progress = self._calculate_exploration_progress()
            exploration_time = time.time() - self.exploration_start_time if self.exploration_start_time else 0
            logger.info(f"Exploration target (frontier-based): ({target_cell[0]:.2f}, {target_cell[1]:.2f}) | "
                      f"Frontiers: {len(frontiers)} | Progress: {progress['exploration_percentage']:.1f}% | "
                      f"Time: {exploration_time:.1f}s | Distance: {self.exploration_distance:.2f}m")
        else:
            logger.info("No suitable frontier found, switching to wandering mode.")
            self.wandering = True
            self.current_goal = None
    
    def _plan_path(self):
        """Plan path to current goal"""
        if not self.current_goal:
            self.nav_state = NavigationState.IDLE
            return
        
        current_pos = self.robot_state.get_position()
        
        # Find path using pathfinder
        path = self.pathfinder.find_path(
            current_pos.x, current_pos.y,
            self.current_goal.x, self.current_goal.y
        )
        
        if path:
            if len(path) > 0:
                self.current_path = path
                self.path_index = 0
                self.nav_state = NavigationState.FOLLOWING_PATH
                
                # Reset progress tracking for new path
                self.min_distance_to_goal = float('inf')
                self.min_distance_to_waypoint = float('inf')
                self.last_progress_time = time.time()
                self.last_position = (current_pos.x, current_pos.y)
                
                # Initialize waypoint distance
                if len(path) > 0:
                    first_waypoint = path[0]
                    self.min_distance_to_waypoint = math.hypot(
                        first_waypoint.x - current_pos.x,
                        first_waypoint.y - current_pos.y
                    )
                
                logger.info(f"Path planned with {len(path)} waypoints")
            else:
                logger.warning("No path found to goal")
                self.nav_state = NavigationState.STUCK
        else:
            logger.warning("No path found to goal")
            self.nav_state = NavigationState.STUCK
    
    def _follow_path(self):
        """Follow the planned path"""
        if not self.current_path or self.path_index >= len(self.current_path):
            self.nav_state = NavigationState.REACHED_GOAL
            return
        
        # Check for obstacles
        if self._check_obstacles():
            self.nav_state = NavigationState.AVOIDING_OBSTACLE
            return
        
        # Get current waypoint
        waypoint = self.current_path[self.path_index]
        current_pos = self.robot_state.get_position()
        
        # Calculate distance to waypoint
        distance = math.sqrt(
            (waypoint.x - current_pos.x)**2 + (waypoint.y - current_pos.y)**2
        )
        
        # Reset waypoint progress tracking when starting new waypoint
        if distance < self.min_distance_to_waypoint:
            self.min_distance_to_waypoint = distance
        
        # Move to next waypoint if close enough
        if distance < self.position_tolerance:
            self.path_index += 1
            self.min_distance_to_waypoint = float('inf')  # Reset for next waypoint
            logger.debug(f"Reached waypoint {self.path_index-1}/{len(self.current_path)}")
            
            # If this was the last waypoint, check if we're close enough to goal
            if self.path_index >= len(self.current_path) and self.current_goal:
                dist_to_goal = math.hypot(self.current_goal.x - current_pos.x, self.current_goal.y - current_pos.y)
                if dist_to_goal <= self.current_goal.tolerance:
                    self.nav_state = NavigationState.REACHED_GOAL
                else:
                    # Path completed but not at goal - need to plan final approach
                    logger.debug(f"Path completed but {dist_to_goal:.3f}m from goal, planning final approach")
                    self.nav_state = NavigationState.PLANNING
            return
        
        # Calculate distance to goal for minimum speed check
        dist_to_goal = math.hypot(self.current_goal.x - current_pos.x, self.current_goal.y - current_pos.y) if self.current_goal else float('inf')
        
        # Calculate control commands
        linear_cmd, angular_cmd = self._calculate_path_control(waypoint)
        
        # Ensure minimum linear speed when moving (to overcome noise/friction)
        # Only apply minimum if we're not very close to the final goal
        if self.path_index < len(self.current_path) - 1 or dist_to_goal > self.position_tolerance * 2:
            min_linear_speed = 0.1  # m/s - minimum to overcome friction/noise
            if abs(linear_cmd) > 0.01 and abs(linear_cmd) < min_linear_speed:
                # Scale up to minimum speed while preserving direction
                linear_cmd = math.copysign(min_linear_speed, linear_cmd)
        
        # Get sensor data
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        left_distance = sensor_data['ultrasonic']['left'].value
        right_distance = sensor_data['ultrasonic']['right'].value
        min_distance = min([front_distance, left_distance, right_distance])
        
        # Enhanced LIDAR-based environment learning and proactive planning
        self._process_lidar_data(front_distance, left_distance, right_distance)
        
        # Reset recovery attempts if robot has clear space and is making progress
        if (front_distance > self.robot_state.config['robot']['safety_distances']['comfortable'] and
            min(left_distance, right_distance) > 0.3 and
            self.recovery_attempts > 0):
            logger.info("Robot has clear space and is making progress - resetting recovery attempts")
            self._reset_recovery_attempts()
        
        # Calculate adaptive speed scaling based on proximity to objects
        speed_scale = self._calculate_adaptive_speed_scale(front_distance, left_distance, right_distance)
        
        # Update exploration distance metrics
        if self.exploration_mode and self.exploration_last_position:
            dist = math.hypot(current_pos.x - self.exploration_last_position[0], 
                            current_pos.y - self.exploration_last_position[1])
            self.exploration_distance += dist
            self.exploration_last_position = (current_pos.x, current_pos.y)
        
        # --- Define grid_size ONCE here ---
        grid_size = self.robot_state.config['navigation']['grid_size']
        
        # Log speed adjustment for debugging and areas of caution
        if speed_scale < 1.0:
            logger.debug(f"Speed reduced to {speed_scale:.2f} due to proximity - L:{left_distance:.2f}m, R:{right_distance:.2f}m, F:{front_distance:.2f}m")
            i = int(current_pos.y // grid_size)
            j = int(current_pos.x // grid_size)
            self.areas_of_caution.add((i, j))
        
        # Log valid path (navmesh) as valid_paths
        if self.last_navmesh_cell is not None and self.last_navmesh_cell != (int(current_pos.x // grid_size), int(current_pos.y // grid_size)):
            from_cell = self.last_navmesh_cell
            to_cell = (int(current_pos.x // grid_size), int(current_pos.y // grid_size))
            edge = (from_cell, to_cell)
            if edge not in self.valid_paths:
                self.valid_paths[edge] = list(self.current_navmesh_path)
                self.learning_data_changed = True
                self._save_learning_data()
            self.current_navmesh_path = []
        self.current_navmesh_path.append((current_pos.x, current_pos.y))
        self.last_navmesh_cell = (int(current_pos.x // grid_size), int(current_pos.y // grid_size))
        
        # Immediate obstacle avoidance if obstacle is very close
        if front_distance < self.route_replan_trigger:
            logger.warning(f"Obstacle too close ({front_distance:.2f}m) - switching to obstacle avoidance")
            self.nav_state = NavigationState.AVOIDING_OBSTACLE
            return
        
        # Proactive route replanning when obstacle detected at a moderate distance
        allow_replan = True
        if hasattr(self, 'last_replan_position'):
            last_x, last_y = self.last_replan_position
            moved = math.hypot(current_pos.x - last_x, current_pos.y - last_y)
            if moved < 0.05:
                allow_replan = False
                logger.debug(f"Replanning skipped: robot has not moved enough since last replan ({moved:.2f}m)")
        
        if (self.route_replan_trigger <= front_distance < self.route_replan_threshold and
            self.nav_state not in [NavigationState.BACKTRACKING, NavigationState.AVOIDING_OBSTACLE, NavigationState.REPLANNING_ROUTE] and
            allow_replan):
            current_time = time.time()
            if (current_time - self.last_replan_time > self.replan_cooldown and 
                self.replan_attempts < self.max_replan_attempts):
                logger.info(f"LIDAR detected obstacle at {front_distance:.2f}m - proactively planning alternate route")
                self.replan_attempts += 1
                self.last_replan_time = current_time
                self.last_replan_position = (current_pos.x, current_pos.y)
                if self._attempt_route_replanning():
                    logger.info("Alternate route found - switching to new path")
                    return
                else:
                    logger.warning("No alternate route found - continuing with current path")
            else:
                logger.debug(f"Route replanning skipped - cooldown: {current_time - self.last_replan_time:.1f}s, attempts: {self.replan_attempts}")
        
        # Apply motor commands
        left_speed, right_speed = self._apply_motor_commands(linear_cmd, angular_cmd)
        self.motor_controller.set_speeds(left_speed * speed_scale, right_speed * speed_scale)
        
        # Learning data is now saved automatically when it changes (with cooldown)
    
    def _avoid_obstacle(self):
        """Avoid detected obstacles by turning until the path ahead is clear"""
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        left_distance = sensor_data['ultrasonic']['left'].value
        right_distance = sensor_data['ultrasonic']['right'].value
        comfortable = self.robot_state.config['robot']['safety_distances']['comfortable']
        clearance_to_resume = max(comfortable, 1.2)  # Require at least 1.2m clear to resume

        # Emergency stop if obstacle too close (accounting for clearance)
        effective_emergency_threshold = self.emergency_stop_threshold + self.obstacle_clearance
        if front_distance < effective_emergency_threshold:
            self.motor_controller.stop()
            logger.warning(f"Emergency stop - obstacle too close ({front_distance:.3f}m < {effective_emergency_threshold:.3f}m)")
            self.nav_state = NavigationState.BACKTRACKING
            self.backtrack_start_time = time.time()
            self.backtrack_attempts = 0
            return

        # If obstacle is still within comfortable distance, keep turning (faster)
        if front_distance < clearance_to_resume:
            # Turn toward the more open side, ensuring clearance is maintained
            # Check which side has more clearance (must be at least obstacle_clearance)
            left_has_clearance = left_distance >= self.obstacle_clearance
            right_has_clearance = right_distance >= self.obstacle_clearance
            
            if left_has_clearance and right_has_clearance:
                # Both sides have clearance, choose the more open side
                if left_distance > right_distance:
                    turn_direction = 1  # left
                else:
                    turn_direction = -1  # right
            elif left_has_clearance:
                # Only left has clearance
                turn_direction = 1  # left
            elif right_has_clearance:
                # Only right has clearance
                turn_direction = -1  # right
            else:
                # Neither side has sufficient clearance, choose the better side but log warning
                logger.warning(f"Insufficient side clearance - left: {left_distance:.3f}m, right: {right_distance:.3f}m (need {self.obstacle_clearance:.3f}m)")
                if left_distance > right_distance:
                    turn_direction = 1  # left
                else:
                    turn_direction = -1  # right
            
            turn_speed = 1.0  # Faster turn speed for avoidance
            self.motor_controller.set_speeds(-turn_speed * turn_direction, turn_speed * turn_direction)
            logger.info(f"Turning in place to clear obstacle (dir: {'left' if turn_direction==1 else 'right'}, speed: {turn_speed}, maintaining {self.obstacle_clearance*100:.1f}cm clearance)")
            return

        # Check that we have sufficient clearance on all sides before resuming
        if (front_distance >= clearance_to_resume and 
            left_distance >= self.obstacle_clearance and 
            right_distance >= self.obstacle_clearance):
            # Path ahead is clear with sufficient clearance, resume path following
            self.motor_controller.stop()
            logger.info(f"Obstacle cleared with sufficient clearance (front: {front_distance:.2f}m, left: {left_distance:.2f}m, right: {right_distance:.2f}m), resuming path following.")
        else:
            # Still need to maintain clearance, keep turning
            if left_distance > right_distance:
                turn_direction = 1  # left
            else:
                turn_direction = -1  # right
            turn_speed = 0.5  # Slower turn to fine-tune clearance
            self.motor_controller.set_speeds(-turn_speed * turn_direction, turn_speed * turn_direction)
            logger.debug(f"Fine-tuning clearance - turning {'left' if turn_direction==1 else 'right'}")
        
        # Reset recovery attempts since obstacle was successfully cleared
        if self.recovery_attempts > 0:
            logger.info("Obstacle successfully cleared - resetting recovery attempts")
            self._reset_recovery_attempts()
        
        self.nav_state = NavigationState.FOLLOWING_PATH
    
    def _handle_goal_reached(self):
        """Handle reaching the navigation goal"""
        if self.exploration_mode:
            # Mark position as explored
            current_pos = self.robot_state.get_position()
            self.explored_positions.add((current_pos.x, current_pos.y))
            
            # Update exploration metrics
            self.frontiers_visited += 1
            self.frontier_success_count += 1
            
            # Calculate exploration area (approximate)
            grid_size = self.robot_state.config['navigation']['grid_size']
            self.exploration_area = len(self.explored_cells) * (grid_size ** 2)
            
            # Log frontier success
            if self.current_goal:
                logger.info(f"Frontier reached successfully: ({self.current_goal.x:.2f}, {self.current_goal.y:.2f}) | "
                          f"Frontiers visited: {self.frontiers_visited} | Success rate: "
                          f"{(self.frontier_success_count / max(self.frontiers_visited, 1) * 100):.1f}%")
            
            # Start next exploration target
            self.nav_state = NavigationState.PLANNING
            self._start_exploration_planning()
        else:
            # Regular navigation complete
            self.motor_controller.stop()
            self.nav_state = NavigationState.IDLE
            self.current_goal = None
            
            # Reset recovery and reactivation state for successful navigation
            self.recovery_attempts = 0
            self.replan_attempts = 0
            self.last_replan_time = 0
            self._reset_recovery_attempts()
            
            logger.info("Navigation goal reached")
    
    def _handle_stuck(self):
        """Handle robot getting stuck"""
        logger.warning("Robot appears to be stuck")
        # Log stuck location
        current_pos = self.robot_state.get_position()
        # Use _record_stuck_location() which handles the new format
        self._record_stuck_location()
        
        # Try to rewind along the previous path
        if self.current_path and self.path_index > 0:
            logger.info("Attempting to rewind along previous path")
            
            # Back up to previous waypoint
            prev_index = max(0, self.path_index - 1)
            prev_waypoint = self.current_path[prev_index]
            
            # Calculate direction to previous waypoint
            current_pos = self.robot_state.get_position()
            dx = prev_waypoint.x - current_pos.x
            dy = prev_waypoint.y - current_pos.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance > 0.1:  # Only rewind if there's a meaningful distance
                # Move backward toward previous waypoint
                self.motor_controller.set_speeds(-20, -20)  # Slow backward movement
                time.sleep(2.0)
                self.motor_controller.stop()
                
                # Update path index to previous waypoint
                self.path_index = prev_index
                logger.info(f"Rewound to waypoint {prev_index}")
            else:
                # If too close to previous waypoint, try simple backup and turn
                self.motor_controller.set_speeds(-30, -30)  # Back up
                time.sleep(1.0)
                self.motor_controller.set_speeds(-50, 50)   # Turn
                time.sleep(2.0)
                self.motor_controller.stop()
        else:
            # No path history, use simple backup and turn
            self.motor_controller.set_speeds(-30, -30)  # Back up
            time.sleep(1.0)
            self.motor_controller.set_speeds(-50, 50)   # Turn
            time.sleep(2.0)
            self.motor_controller.stop()
        
        # Try planning again
        self.nav_state = NavigationState.PLANNING
    
    def _check_obstacles(self) -> bool:
        """Check for obstacles in the path, accounting for clearance distance"""
        sensor_data = self.sensor_manager.get_sensor_data()
        # Effective threshold includes clearance distance to trigger avoidance earlier
        effective_obstacle_threshold = self.obstacle_threshold + self.obstacle_clearance
        return sensor_data['ultrasonic']['front'].value < effective_obstacle_threshold
    
    def _calculate_path_control(self, waypoint: PathPoint) -> Tuple[float, float]:
        """Calculate linear and angular control commands for path following"""
        current_pos = self.robot_state.get_position()
        
        # Calculate desired heading to waypoint
        dx = waypoint.x - current_pos.x
        dy = waypoint.y - current_pos.y
        desired_heading = math.atan2(dy, dx)
        
        # Calculate heading error
        heading_error = desired_heading - current_pos.theta
        
        # Normalize angle to [-pi, pi]
        while heading_error > math.pi:
            heading_error -= 2 * math.pi
        while heading_error < -math.pi:
            heading_error += 2 * math.pi
        
        # Calculate distance to waypoint
        distance = math.sqrt(dx*dx + dy*dy)
        
        # PID control for angular velocity
        angular_cmd = self.angular_kp * heading_error
        
        # Limit angular command
        angular_cmd = max(-self.max_angular_speed, min(self.max_angular_speed, angular_cmd))
        
        # Linear velocity based on distance and heading error
        linear_cmd = self.linear_kp * distance * (1.0 - abs(heading_error) / math.pi)
        linear_cmd = max(0.0, min(self.max_linear_speed, linear_cmd))
        
        return linear_cmd, angular_cmd
    
    def _apply_motor_commands(self, linear_cmd: float, angular_cmd: float):
        """Apply motor commands based on linear and angular velocities"""
        # Convert to wheel speeds (differential drive)
        wheel_base = 0.25  # Distance between wheels
        
        left_speed = (linear_cmd - angular_cmd * wheel_base / 2) * 100  # Convert to percentage
        right_speed = (linear_cmd + angular_cmd * wheel_base / 2) * 100
        
        # Ensure minimum motor speed when moving to overcome friction/noise
        # Only if linear command is non-zero (robot is trying to move)
        if abs(linear_cmd) > 0.01:
            min_motor_speed = 5.0  # Minimum 5% speed to overcome friction
            if abs(left_speed) > 0.01 and abs(left_speed) < min_motor_speed:
                left_speed = math.copysign(min_motor_speed, left_speed)
            if abs(right_speed) > 0.01 and abs(right_speed) < min_motor_speed:
                right_speed = math.copysign(min_motor_speed, right_speed)
        
        # Limit speeds
        left_speed = max(-100, min(100, left_speed))
        right_speed = max(-100, min(100, right_speed))
        
        # Apply to motors
        return left_speed, right_speed
    
    def _calculate_exploration_progress(self) -> Dict[str, Any]:
        """Calculate exploration progress metrics.
        
        Returns a dictionary with:
        - exploration_percentage: Percentage of reachable area explored (excluding obstacles)
        - explored_cells: Number of explored cells
        - total_reachable_cells: Total reachable cells (excluding obstacles)
        - obstacle_cells: Number of obstacle cells
        - frontier_count: Number of detected frontiers
        """
        map_width = self.robot_state.config['navigation']['map_width']
        map_height = self.robot_state.config['navigation']['map_height']
        grid_size = self.robot_state.config['navigation']['grid_size']
        n_rows = int(map_height // grid_size)
        n_cols = int(map_width // grid_size)
        
        total_cells = n_rows * n_cols
        explored_count = len(self.explored_cells)
        
        # Count obstacle cells
        obstacle_count = 0
        for i in range(n_rows):
            for j in range(n_cols):
                if self.pathfinder.is_obstacle(j, i):
                    obstacle_count += 1
        
        # Total reachable cells = total - obstacles
        total_reachable = total_cells - obstacle_count
        
        # Calculate percentage (only considering reachable cells)
        if total_reachable > 0:
            exploration_percentage = (explored_count / total_reachable) * 100.0
        else:
            exploration_percentage = 0.0
        
        # Get frontier count
        frontiers = self._detect_frontiers()
        frontier_count = len(frontiers)
        
        return {
            'exploration_percentage': exploration_percentage,
            'explored_cells': explored_count,
            'total_reachable_cells': total_reachable,
            'obstacle_cells': obstacle_count,
            'frontier_count': frontier_count
        }
    
    def get_navigation_status(self) -> Dict[str, Any]:
        """Get current navigation status"""
        # Get current sensor data for speed information
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        left_distance = sensor_data['ultrasonic']['left'].value
        right_distance = sensor_data['ultrasonic']['right'].value
        
        # Calculate current speed scale
        current_speed_scale = self._calculate_adaptive_speed_scale(front_distance, left_distance, right_distance)
        
        # Calculate exploration progress if in exploration mode
        exploration_progress = None
        if self.exploration_mode:
            exploration_progress = self._calculate_exploration_progress()
        
        return {
            'state': self.nav_state.value,
            'goal': {
                'x': self.current_goal.x if self.current_goal else None,
                'y': self.current_goal.y if self.current_goal else None,
                'tolerance': self.current_goal.tolerance if self.current_goal else None
            },
            'path_progress': {
                'current_index': self.path_index,
                'total_waypoints': len(self.current_path),
                'path_length': len(self.current_path)
            },
            'exploration': {
                'mode': self.exploration_mode,
                'explored_positions': len(self.explored_positions),
                'progress': exploration_progress,
                'metrics': {
                    'exploration_time': time.time() - self.exploration_start_time if (self.exploration_mode and self.exploration_start_time) else 0,
                    'distance_traveled': self.exploration_distance,
                    'frontiers_visited': self.frontiers_visited,
                    'frontier_success_count': self.frontier_success_count,
                    'frontier_success_rate': (self.frontier_success_count / max(self.frontiers_visited, 1) * 100) if self.frontiers_visited > 0 else 0,
                    'exploration_area': self.exploration_area,
                    'validation': {
                        'validation_count': self.validation_count,
                        'last_validation_time': self.last_validation_time,
                        'time_since_last_validation': time.time() - self.last_validation_time if self.last_validation_time > 0 else None,
                        'last_validation_stats': self.last_validation_stats
                    } if self.exploration_mode else None
                } if self.exploration_mode else None
            },
            'emergency_stop': self.emergency_stop,
            'adaptive_speed': {
                'current_scale': current_speed_scale,
                'front_distance': front_distance,
                'left_distance': left_distance,
                'right_distance': right_distance,
                'safe_distance': self.safe_distance,
                'min_safe_distance': self.min_safe_distance
            },
            'reactivation': {
                'attempts': self.reactivation_attempts,
                'max_attempts': self.max_reactivation_attempts,
                'current_strategy': self.reactivation_strategies[self.current_reactivation_strategy] if self.nav_state == NavigationState.REACTIVATING else None,
                'strategy_index': self.current_reactivation_strategy,
                'total_strategies': len(self.reactivation_strategies)
            }
        }

    def get_status(self):
        """Return navigation status in the format expected by the GUI."""
        nav_status = self.get_navigation_status()
        # Map to GUI-expected keys
        return {
            'navigation_state': nav_status['state'],
            'target_position': {
                'x': nav_status['goal']['x'],
                'y': nav_status['goal']['y']
            },
            'total_waypoints': nav_status['path_progress']['total_waypoints']
        }

    def _initiate_turn(self, direction=1):
        # direction: 1 for left, -1 for right
        turn_speed = 0.6  # Increased turn speed for in-place turns
        self.motor_controller.set_speeds(-turn_speed * direction, turn_speed * direction)
        self.turn_start_time = time.time()

    def _handle_backtracking(self):
        """Handle backtracking when robot encounters obstacles"""
        if not hasattr(self, 'backtrack_start_time'):
            self.backtrack_start_time = time.time()
        
        elapsed = time.time() - self.backtrack_start_time
        
        # Backtrack for 1 second
        if elapsed < 1.0:
            self.motor_controller.set_speeds(-0.2, -0.2)
            return
        
        # Stop backtracking
        self.motor_controller.stop()
        
        # Check if obstacle is still too close
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        
        if front_distance < self.emergency_stop_threshold:
            self.backtrack_attempts += 1
            if self.backtrack_attempts < self.max_backtrack_attempts:
                # Reset backtrack timer for another attempt
                self.backtrack_start_time = time.time()
                logger.info(f"Obstacle still too close, backtracking again ({self.backtrack_attempts}/{self.max_backtrack_attempts})")
            else:
                logger.warning("Max backtrack attempts reached, switching to stuck recovery")
                self.nav_state = NavigationState.STUCK
                del self.backtrack_start_time
        else:
            # Obstacle cleared, decide turn direction based on sensor readings
            left_distance = sensor_data['ultrasonic']['left'].value
            right_distance = sensor_data['ultrasonic']['right'].value
            
            # If both sides are blocked, backtrack again
            if (left_distance < self.emergency_stop_threshold and 
                right_distance < self.emergency_stop_threshold):
                self.backtrack_start_time = time.time()
                logger.info("Both sides blocked, backtracking again")
            else:
                # Choose the more open side, or alternate if equal
                if left_distance > right_distance:
                    turn_direction = 1  # left
                elif right_distance > left_distance:
                    turn_direction = -1  # right
                else:
                    # Alternate direction if both sides are equally open
                    turn_direction = getattr(self, 'last_turn_direction', 1) * -1
                
                self.last_turn_direction = turn_direction
                self.turn_start_time = time.time()
                self.turn_duration = 0.7
                self.turning = True
                self.nav_state = NavigationState.AVOIDING_OBSTACLE
                logger.info(f"Turning {'left' if turn_direction == 1 else 'right'} to avoid obstacle")

    def _handle_stuck_recovery(self):
        """Handle recovery when robot is stuck"""
        if not hasattr(self, 'stuck_recovery_start_time'):
            self.stuck_recovery_start_time = time.time()
            self.stuck_recovery_attempts = 0
        
        elapsed = time.time() - self.stuck_recovery_start_time
        
        # Try different recovery strategies
        if self.stuck_recovery_attempts == 0:
            # First attempt: aggressive reverse
            if elapsed < 2.0:
                self.motor_controller.set_speeds(-0.3, -0.3)
                return
            else:
                self.motor_controller.stop()
                self.stuck_recovery_attempts += 1
                self.stuck_recovery_start_time = time.time()
                logger.info("Stuck recovery: attempting aggressive reverse")
        
        elif self.stuck_recovery_attempts == 1:
            # Second attempt: spin in place
            if elapsed < 1.5:
                self.motor_controller.set_speeds(0.2, -0.2)
                return
            else:
                self.motor_controller.stop()
                self.stuck_recovery_attempts += 1
                self.stuck_recovery_start_time = time.time()
                logger.info("Stuck recovery: attempting spin")
        
        elif self.stuck_recovery_attempts == 2:
            # Third attempt: try to find a new path
            logger.info("Stuck recovery: attempting path replanning")
            self.nav_state = NavigationState.PLANNING
            self.current_path = []  # Clear current path
            self.pathfinder.clear_cache()  # Clear pathfinder cache
            del self.stuck_recovery_start_time
            return
        
        else:
            # All recovery attempts failed
            logger.error("All stuck recovery attempts failed")
            self.nav_state = NavigationState.ERROR
            self.motor_controller.stop()
            del self.stuck_recovery_start_time

    def _handle_obstacle_recovery(self):
        """Handle recovery from obstacle avoidance"""
        if not hasattr(self, 'obstacle_recovery_start_time'):
            self.obstacle_recovery_start_time = time.time()
        
        elapsed = time.time() - self.obstacle_recovery_start_time
        
        # Check if we're still turning
        if hasattr(self, 'turning') and self.turning:
            if elapsed < self.turn_duration:
                # Continue turning
                return
            else:
                # Stop turning
                self.motor_controller.stop()
                self.turning = False
                del self.turn_start_time
                del self.turn_duration
        
        # Check if obstacle is still present
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        
        if front_distance < self.emergency_stop_threshold:
            # Obstacle still present, try different approach
            self.obstacle_recovery_attempts += 1
            if self.obstacle_recovery_attempts < self.max_obstacle_recovery_attempts:
                logger.info(f"Obstacle still present, trying different approach ({self.obstacle_recovery_attempts}/{self.max_obstacle_recovery_attempts})")
                self.nav_state = NavigationState.BACKTRACKING
                self.backtrack_attempts = 0  # Reset backtrack attempts
                del self.obstacle_recovery_start_time
            else:
                logger.warning("Max obstacle recovery attempts reached")
                self.nav_state = NavigationState.STUCK
                del self.obstacle_recovery_start_time
        else:
            # Obstacle cleared, resume navigation
            logger.info("Obstacle cleared, resuming navigation")
            self.nav_state = NavigationState.FOLLOWING_PATH
            self.obstacle_recovery_attempts = 0
            del self.obstacle_recovery_start_time

    def _replan_route(self):
        """Handle route replanning"""
        logger.info("Starting route replanning")
        self.nav_state = NavigationState.PLANNING
        self.current_path = []  # Clear current path
        self.pathfinder.clear_cache()  # Clear pathfinder cache
        self.explored_positions.clear()  # Clear explored positions
        self.explored_cells.clear()  # Clear explored cells
        self.backtrack_attempts = 0  # Reset backtrack attempts
        self.recovery_attempts = 0  # Reset recovery attempts
        self.last_turn_direction = 1  # Reset turn direction
        self.turn_start_time = None  # Reset turn start time
        self.turn_duration = None  # Reset turn duration
        self.turning = False  # Reset turning flag
        self.obstacle_recovery_attempts = 0  # Reset obstacle recovery attempts
        self.obstacle_recovery_start_time = None  # Reset obstacle recovery start time
        self.max_recovery_attempts = 5  # Reset max recovery attempts
        self.max_backtrack_attempts = 5  # Reset max backtrack attempts
        self.max_obstacle_recovery_attempts = 3  # Reset max obstacle recovery attempts
        self.emergency_stop = False  # Reset emergency stop
        self.last_goal_time = time.time()  # Reset last goal time
        self.exploration_mode = False  # Reset exploration mode
        self.current_goal = None  # Reset current goal
        self.path_index = 0  # Reset path index
        self.motor_controller.stop()  # Stop motors
        logger.info("Route replanning completed")

    def _attempt_route_replanning(self) -> bool:
        """Attempt to find an alternate route to the goal using enhanced LIDAR data"""
        if not self.current_goal:
            logger.warning("No current goal for route replanning")
            return False
        
        current_pos = self.robot_state.get_position()
        goal_x, goal_y = self.current_goal.x, self.current_goal.y
        
        logger.info(f"Attempting route replanning from ({current_pos.x:.2f}, {current_pos.y:.2f}) to ({goal_x:.2f}, {goal_y:.2f})")
        
        # Get enhanced LIDAR data for better decision making
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        left_distance = sensor_data['ultrasonic']['left'].value
        right_distance = sensor_data['ultrasonic']['right'].value
        
        # Analyze LIDAR history for better understanding of environment
        lidar_analysis = self._analyze_lidar_for_replanning()
        
        # Try different strategies for finding alternate routes with LIDAR insights
        
        # Strategy 1: Try to find a path that avoids the detected obstacle area using LIDAR data
        if self._try_lidar_guided_avoidance(current_pos, goal_x, goal_y, front_distance, left_distance, right_distance, lidar_analysis):
            return True
        
        # Strategy 2: Try to find a path with a wider safety margin
        if self._try_wider_path(current_pos, goal_x, goal_y):
            return True
        
        # Strategy 3: Try to find a path through less explored areas
        if self._try_exploration_path(current_pos, goal_x, goal_y):
            return True
        
        # Strategy 4: Try corridor-based navigation if LIDAR detected corridors
        if lidar_analysis.get('corridor_detected', False):
            if self._try_corridor_navigation(current_pos, goal_x, goal_y, lidar_analysis):
                return True
        
        logger.warning("All route replanning strategies failed")
        return False
    
    def _analyze_lidar_for_replanning(self) -> dict:
        """Analyze LIDAR history to provide insights for route replanning"""
        analysis = {
            'corridor_detected': False,
            'wall_following': None,  # 'left', 'right', or None
            'obstacle_density': 'low',
            'clear_directions': []
        }
        
        if not hasattr(self, 'lidar_history') or len(self.lidar_history) < 5:
            return analysis
        
        recent_readings = self.lidar_history[-5:]
        
        # Analyze corridor detection
        left_obstacles = [r['left'] for r in recent_readings if r['left'] < 1.0]
        right_obstacles = [r['right'] for r in recent_readings if r['right'] < 1.0]
        
        if len(left_obstacles) > 3 and len(right_obstacles) > 3:
            analysis['corridor_detected'] = True
        
        # Analyze wall following
        if len(left_obstacles) > len(right_obstacles) + 2:
            analysis['wall_following'] = 'left'
        elif len(right_obstacles) > len(left_obstacles) + 2:
            analysis['wall_following'] = 'right'
        
        # Analyze obstacle density
        front_obstacles = [r['front'] for r in recent_readings if r['front'] < 2.0]
        if len(front_obstacles) > 3:
            analysis['obstacle_density'] = 'high'
        elif len(front_obstacles) > 1:
            analysis['obstacle_density'] = 'medium'
        
        # Find clear directions
        avg_left = sum(r['left'] for r in recent_readings) / len(recent_readings)
        avg_right = sum(r['right'] for r in recent_readings) / len(recent_readings)
        
        if avg_left > 1.5:
            analysis['clear_directions'].append('left')
        if avg_right > 1.5:
            analysis['clear_directions'].append('right')
        
        return analysis
    
    def _try_lidar_guided_avoidance(self, current_pos, goal_x, goal_y, front_distance, left_distance, right_distance, lidar_analysis) -> bool:
        """Try to find a path using LIDAR-guided avoidance strategy"""
        logger.info("Trying LIDAR-guided avoidance strategy")
        
        # Calculate the direction to the goal
        dx = goal_x - current_pos.x
        dy = goal_y - current_pos.y
        goal_direction = math.atan2(dy, dx)
        
        # Use LIDAR analysis to determine best avoidance direction
        preferred_direction = None
        
        if lidar_analysis['clear_directions']:
            # Use LIDAR-detected clear directions
            if 'left' in lidar_analysis['clear_directions'] and 'right' in lidar_analysis['clear_directions']:
                # Both sides are clear, choose based on goal direction
                if abs(goal_direction - current_pos.theta) < math.pi/2:
                    preferred_direction = 'left' if left_distance > right_distance else 'right'
                else:
                    preferred_direction = 'right' if left_distance > right_distance else 'left'
            elif 'left' in lidar_analysis['clear_directions']:
                preferred_direction = 'left'
            elif 'right' in lidar_analysis['clear_directions']:
                preferred_direction = 'right'
        else:
            # Fall back to sensor-based decision
            if left_distance > right_distance:
                preferred_direction = 'left'
            else:
                preferred_direction = 'right'
        
        if preferred_direction:
            # Create avoidance waypoint
            if preferred_direction == 'left':
                avoidance_angle = goal_direction + math.pi/3  # 60 degrees left
            else:
                avoidance_angle = goal_direction - math.pi/3  # 60 degrees right
            
            # Use LIDAR data to determine safe avoidance distance, ensuring clearance is maintained
            # Ensure we maintain obstacle_clearance distance from obstacles
            min_side_distance = min(left_distance, right_distance)
            safe_distance = max(front_distance + 0.8, 2.5)  # At least 0.8m beyond obstacle
            # Ensure safe distance accounts for clearance
            if safe_distance < self.obstacle_clearance * 2:
                safe_distance = self.obstacle_clearance * 2  # At least 2x clearance for safety
            
            waypoint_x = current_pos.x + safe_distance * math.cos(avoidance_angle)
            waypoint_y = current_pos.y + safe_distance * math.sin(avoidance_angle)
            
            # Verify the waypoint maintains clearance from obstacles
            # Check if waypoint is too close to any known obstacles
            grid_x, grid_y = self.pathfinder.world_to_grid(waypoint_x, waypoint_y)
            if self.pathfinder.is_obstacle(grid_x, grid_y):
                # Waypoint is in obstacle, adjust to maintain clearance
                logger.debug(f"Adjusting avoidance waypoint to maintain {self.obstacle_clearance*100:.1f}cm clearance")
                # Move waypoint away from obstacle
                safe_distance = max(safe_distance, self.obstacle_clearance * 3)
                waypoint_x = current_pos.x + safe_distance * math.cos(avoidance_angle)
                waypoint_y = current_pos.y + safe_distance * math.sin(avoidance_angle)
            
            # Ensure waypoint is within map bounds
            waypoint_x = max(0, min(self.pathfinder.map_width, waypoint_x))
            waypoint_y = max(0, min(self.pathfinder.map_height, waypoint_y))
            
            # Try to find path through this waypoint
            path1 = self.pathfinder.find_path(current_pos.x, current_pos.y, waypoint_x, waypoint_y)
            if path1:
                path2 = self.pathfinder.find_path(waypoint_x, waypoint_y, goal_x, goal_y)
                if path2:
                    # Combine the paths
                    self.current_path = path1 + path2
                    self.path_index = 0
                    logger.info(f"LIDAR-guided avoidance path found successfully (direction: {preferred_direction})")
                    return True
        
        return False
    
    def _try_corridor_navigation(self, current_pos, goal_x, goal_y, lidar_analysis) -> bool:
        """Try corridor-based navigation using LIDAR corridor detection"""
        logger.info("Trying corridor navigation strategy")
        
        # If LIDAR detected a corridor, try to follow it
        if lidar_analysis['wall_following'] == 'left':
            # Follow left wall
            corridor_waypoint_x = current_pos.x + 1.0 * math.cos(current_pos.theta + math.pi/2)
            corridor_waypoint_y = current_pos.y + 1.0 * math.sin(current_pos.theta + math.pi/2)
        elif lidar_analysis['wall_following'] == 'right':
            # Follow right wall
            corridor_waypoint_x = current_pos.x + 1.0 * math.cos(current_pos.theta - math.pi/2)
            corridor_waypoint_y = current_pos.y + 1.0 * math.sin(current_pos.theta - math.pi/2)
        else:
            # No clear wall following, skip this strategy
            return False
        
        # Ensure waypoint is within map bounds
        corridor_waypoint_x = max(0, min(self.pathfinder.map_width, corridor_waypoint_x))
        corridor_waypoint_y = max(0, min(self.pathfinder.map_height, corridor_waypoint_y))
        
        # Try to find path through corridor waypoint
        path1 = self.pathfinder.find_path(current_pos.x, current_pos.y, corridor_waypoint_x, corridor_waypoint_y)
        if path1:
            path2 = self.pathfinder.find_path(corridor_waypoint_x, corridor_waypoint_y, goal_x, goal_y)
            if path2:
                self.current_path = path1 + path2
                self.path_index = 0
                logger.info("Corridor navigation path found successfully")
                return True
        
        return False

    def _handle_reactivation(self):
        """Handle robot reactivation after navigation timeout"""
        current_time = time.time()
        elapsed = current_time - self.reactivation_start_time
        
        # Check if current reactivation attempt has timed out
        if elapsed > self.reactivation_timeout:
            self.reactivation_attempts += 1
            if self.reactivation_attempts >= self.max_reactivation_attempts:
                logger.error("All reactivation attempts failed - switching to error state")
                self.nav_state = NavigationState.ERROR
                self.motor_controller.stop()
                return
            else:
                # Try next strategy
                self.current_reactivation_strategy = (self.current_reactivation_strategy + 1) % len(self.reactivation_strategies)
                self.reactivation_start_time = current_time
                logger.info(f"Switching to reactivation strategy {self.current_reactivation_strategy + 1}/{len(self.reactivation_strategies)}: {self.reactivation_strategies[self.current_reactivation_strategy]}")
        
        # Execute current reactivation strategy
        strategy = self.reactivation_strategies[self.current_reactivation_strategy]
        
        if strategy == 'backup_and_turn':
            self._execute_backup_and_turn(elapsed)
        elif strategy == 'spin_in_place':
            self._execute_spin_in_place(elapsed)
        elif strategy == 'wiggle_movement':
            self._execute_wiggle_movement(elapsed)
        elif strategy == 'aggressive_backup':
            self._execute_aggressive_backup(elapsed)
        elif strategy == 'random_movement':
            self._execute_random_movement(elapsed)
        elif strategy == 'aggressive_random_walk':
            self._execute_aggressive_random_walk(elapsed)
        else:
            logger.error(f"Unknown reactivation strategy: {strategy}")
            self.nav_state = NavigationState.ERROR
            self.motor_controller.stop()
    
    def _execute_backup_and_turn(self, elapsed):
        """Execute backup and turn strategy"""
        if elapsed < 2.0:
            # Back up for 2 seconds
            self.motor_controller.set_speeds(-0.3, -0.3)
            logger.info("Reactivation: Backing up...")
        elif elapsed < 4.0:
            # Turn in place for 2 seconds
            self.motor_controller.set_speeds(0.4, -0.4)
            logger.info("Reactivation: Turning in place...")
        else:
            # Stop and check if we can proceed
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Reactivation successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Reactivation not successful - will try next strategy")
    
    def _execute_spin_in_place(self, elapsed):
        """Execute spin in place strategy"""
        if elapsed < 3.0:
            # Spin in place for 3 seconds
            self.motor_controller.set_speeds(0.5, -0.5)
            logger.info("Reactivation: Spinning in place...")
        else:
            # Stop and check if we can proceed
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Reactivation successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Reactivation not successful - will try next strategy")
    
    def _execute_wiggle_movement(self, elapsed):
        """Execute wiggle movement strategy"""
        cycle_time = 1.0  # 1 second per wiggle cycle
        cycle = int(elapsed / cycle_time)
        cycle_elapsed = elapsed % cycle_time
        
        if cycle < 3:  # Do 3 wiggle cycles
            if cycle_elapsed < 0.5:
                # Wiggle left
                self.motor_controller.set_speeds(0.2, -0.2)
                logger.info(f"Reactivation: Wiggle cycle {cycle + 1}, left...")
            else:
                # Wiggle right
                self.motor_controller.set_speeds(-0.2, 0.2)
                logger.info(f"Reactivation: Wiggle cycle {cycle + 1}, right...")
        else:
            # Stop and check if we can proceed
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Reactivation successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Reactivation not successful - will try next strategy")
    
    def _execute_aggressive_backup(self, elapsed):
        """Execute aggressive backup strategy"""
        if elapsed < 2.0:
            # Aggressive backup for 2 seconds
            self.motor_controller.set_speeds(-0.6, -0.6)
            logger.info("Reactivation: Aggressive backup...")
        elif elapsed < 4.0:
            # Quick forward burst
            self.motor_controller.set_speeds(0.4, 0.4)
            logger.info("Reactivation: Forward burst...")
        else:
            # Stop and check if we can proceed
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Reactivation successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Reactivation not successful - will try next strategy")
    
    def _execute_random_movement(self, elapsed):
        """Execute random movement strategy"""
        if elapsed < 5.0:
            # Random movement pattern
            movement_phase = int(elapsed * 2) % 4  # 4 phases, 0.5s each
            
            if movement_phase == 0:
                # Forward
                self.motor_controller.set_speeds(0.3, 0.3)
                logger.info("Reactivation: Random movement - forward...")
            elif movement_phase == 1:
                # Turn left
                self.motor_controller.set_speeds(0.2, -0.2)
                logger.info("Reactivation: Random movement - turn left...")
            elif movement_phase == 2:
                # Backward
                self.motor_controller.set_speeds(-0.3, -0.3)
                logger.info("Reactivation: Random movement - backward...")
            else:
                # Turn right
                self.motor_controller.set_speeds(-0.2, 0.2)
                logger.info("Reactivation: Random movement - turn right...")
        else:
            # Stop and check if we can proceed
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Reactivation successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Reactivation not successful - will try next strategy")
    
    def _execute_aggressive_random_walk(self, elapsed):
        """Aggressive random walk: erratic, longer, higher speed movements to escape traps."""
        duration = 8.0  # 8 seconds
        if elapsed < duration:
            phase = int(elapsed * 2) % 6  # 6 phases, ~0.33s each
            if phase == 0:
                self.motor_controller.set_speeds(0.6, 0.6)  # Fast forward
                logger.info("Aggressive random walk: forward")
            elif phase == 1:
                self.motor_controller.set_speeds(-0.6, -0.6)  # Fast backward
                logger.info("Aggressive random walk: backward")
            elif phase == 2:
                self.motor_controller.set_speeds(0.6, -0.6)  # Fast left spin
                logger.info("Aggressive random walk: spin left")
            elif phase == 3:
                self.motor_controller.set_speeds(-0.6, 0.6)  # Fast right spin
                logger.info("Aggressive random walk: spin right")
            elif phase == 4:
                self.motor_controller.set_speeds(0.4, -0.2)  # Curve left
                logger.info("Aggressive random walk: curve left")
            else:
                self.motor_controller.set_speeds(-0.2, 0.4)  # Curve right
                logger.info("Aggressive random walk: curve right")
        else:
            self.motor_controller.stop()
            if self._check_if_reactivation_successful():
                logger.info("Aggressive random walk successful - resuming navigation")
                self._reset_recovery_attempts()
                self.nav_state = NavigationState.PLANNING
            else:
                logger.info("Aggressive random walk not successful - will try next strategy")
    
    def _check_if_reactivation_successful(self) -> bool:
        """Check if reactivation was successful by examining sensor data and position"""
        try:
            # Get current sensor data
            sensor_data = self.sensor_manager.get_sensor_data()
            front_distance = sensor_data['ultrasonic']['front'].value
            left_distance = sensor_data['ultrasonic']['left'].value
            right_distance = sensor_data['ultrasonic']['right'].value
            
            # Check if we have clear space ahead
            if front_distance < self.obstacle_threshold:
                logger.debug("Reactivation check failed: obstacle too close ahead")
                return False
            
            # Check if we have reasonable space on sides
            min_side_distance = min(left_distance, right_distance)
            if min_side_distance < self.emergency_stop_threshold:
                logger.debug("Reactivation check failed: insufficient side clearance")
                return False
            
            # Check if robot has moved from its original stuck position
            current_pos = self.robot_state.get_position()
            if hasattr(self, 'stuck_position'):
                distance_moved = math.sqrt(
                    (current_pos.x - self.stuck_position[0])**2 + 
                    (current_pos.y - self.stuck_position[1])**2
                )
                if distance_moved < 0.2:  # Must have moved at least 20cm
                    logger.debug(f"Reactivation check failed: insufficient movement ({distance_moved:.2f}m)")
                    return False
            
            logger.info("Reactivation check passed: robot has clear space and has moved")
            return True
            
        except Exception as e:
            logger.error(f"Error in reactivation check: {e}")
            return False
    
    def _reset_reactivation_state(self):
        """Reset reactivation state variables"""
        self.reactivation_attempts = 0
        self.current_reactivation_strategy = 0
        self.reactivation_start_time = 0
        if hasattr(self, 'stuck_position'):
            del self.stuck_position
        logger.info("Reactivation state reset")
    
    def _reset_recovery_attempts(self):
        """Reset all recovery-related counters"""
        if self.recovery_attempts > 0:
            logger.info("Resetting recovery attempts - robot has successfully recovered")
            self.recovery_attempts = 0
            self.replan_attempts = 0
            self.last_replan_time = 0
            self._reset_reactivation_state()
            self.min_distance_to_goal = float('inf')
            self.last_progress_time = time.time()
    
    def reactivate_robot(self) -> bool:
        """Manually trigger robot reactivation"""
        if self.nav_state == NavigationState.ERROR:
            logger.info("Manually triggering robot reactivation")
            self.nav_state = NavigationState.REACTIVATING
            self.reactivation_start_time = time.time()
            self.reactivation_attempts = 0
            self.current_reactivation_strategy = 0
            
            # Store current position as stuck position for movement verification
            current_pos = self.robot_state.get_position()
            self.stuck_position = (current_pos.x, current_pos.y)
            
            return True
        else:
            logger.warning("Cannot reactivate robot - not in ERROR state")
            return False

    def _update_exploration_map_with_lidar(self):
        """Update exploration map using 360° LIDAR scan to mark cells as explored and obstacles."""
        if not self.exploration_mode:
            return
        
        try:
            sensor_data = self.sensor_manager.get_sensor_data()
            lidar_scan = sensor_data.get('lidar_scan', [])
            
            if not lidar_scan:
                return
            
            current_pos = self.robot_state.get_position()
            grid_size = self.robot_state.config['navigation']['grid_size']
            map_width = self.robot_state.config['navigation']['map_width']
            map_height = self.robot_state.config['navigation']['map_height']
            n_rows = int(map_height // grid_size)
            n_cols = int(map_width // grid_size)
            
            max_range = getattr(self.sensor_manager, 'max_range', 2.0)
            
            def pos_to_cell(x, y):
                i = int(y // grid_size)
                j = int(x // grid_size)
                return i, j
            
            # Process each LIDAR ray
            for angle_deg, dist in lidar_scan:
                angle_rad = math.radians(angle_deg) + current_pos.theta
                
                # Calculate end point of ray
                end_x = current_pos.x + dist * math.cos(angle_rad)
                end_y = current_pos.y + dist * math.sin(angle_rad)
                
                # Mark all cells along the ray as explored
                num_steps = max(1, int(dist / grid_size))
                for s in range(num_steps):
                    t = s / max(num_steps, 1)
                    px = current_pos.x + t * (end_x - current_pos.x)
                    py = current_pos.y + t * (end_y - current_pos.y)
                    ci, cj = pos_to_cell(px, py)
                    
                    if 0 <= ci < n_rows and 0 <= cj < n_cols:
                        # Mark as explored if not already explored and not an obstacle
                        if (ci, cj) not in self.explored_cells:
                            if not self.pathfinder.is_obstacle(cj, ci):
                                self.explored_cells.add((ci, cj))
                                # Also mark in pathfinder
                                self.pathfinder.mark_explored(px, py)
                
                # Mark obstacle cell if LIDAR hit something (distance < max_range)
                if dist < max_range:
                    ci, cj = pos_to_cell(end_x, end_y)
                    if 0 <= ci < n_rows and 0 <= cj < n_cols:
                        # Mark as obstacle in pathfinder
                        self.pathfinder.add_obstacle(end_x, end_y, 0.2)
                        # Don't mark obstacle cells as explored
                        
        except Exception as e:
            logger.debug(f"Error updating exploration map with LIDAR: {e}")
    
    def _process_lidar_data(self, front_distance, left_distance, right_distance):
        """Process LIDAR data to learn environment and make proactive decisions"""
        # Define detection zones for different levels of awareness
        far_zone = 3.0      # 3m+ - long-range planning zone
        mid_zone = 2.0      # 2-3m - proactive planning zone  
        near_zone = 1.0     # 1-2m - immediate planning zone
        critical_zone = 0.5 # <1m - emergency zone
        
        # Store LIDAR data for environment learning
        if not hasattr(self, 'lidar_history'):
            self.lidar_history = []
        
        current_time = time.time()
        lidar_reading = {
            'timestamp': current_time,
            'front': front_distance,
            'left': left_distance,
            'right': right_distance,
            'position': self.robot_state.get_position()
        }
        self.lidar_history.append(lidar_reading)
        
        # Keep only recent history (last 100 readings)
        if len(self.lidar_history) > 100:
            self.lidar_history = self.lidar_history[-100:]
        
        # Analyze environment patterns
        self._analyze_environment_patterns()
        
        # Proactive planning based on LIDAR zones
        if front_distance < far_zone:
            # Long-range obstacle detected - start early planning
            if front_distance < mid_zone and front_distance >= near_zone:
                logger.debug(f"LIDAR: Mid-range obstacle detected at {front_distance:.2f}m - monitoring for route planning")
                self._update_environment_map(front_distance, left_distance, right_distance)
            
            elif front_distance < near_zone and front_distance >= critical_zone:
                logger.info(f"LIDAR: Near-range obstacle detected at {front_distance:.2f}m - immediate planning recommended")
                self._update_environment_map(front_distance, left_distance, right_distance)
                
                # Check if we should trigger immediate replanning
                if (self.nav_state == NavigationState.FOLLOWING_PATH and 
                    time.time() - self.last_replan_time > self.replan_cooldown):
                    logger.info("LIDAR: Triggering immediate route replanning due to near-range obstacle")
                    self._attempt_route_replanning()
        
        # Side obstacle analysis for corridor detection
        side_clearance = min(left_distance, right_distance)
        if side_clearance < 0.8:  # Narrow corridor detected
            logger.debug(f"LIDAR: Narrow corridor detected - side clearance: {side_clearance:.2f}m")
            self._handle_narrow_corridor(left_distance, right_distance)
        
        # Update pathfinder with learned obstacles
        self._update_pathfinder_with_lidar_data(front_distance, left_distance, right_distance)
        
        # Update exploration map with LIDAR raycasting if in exploration mode
        if self.exploration_mode:
            self._update_exploration_map_with_lidar()
    
    def _analyze_environment_patterns(self):
        """Analyze LIDAR history to detect environment patterns"""
        if len(self.lidar_history) < 10:
            return
        
        # Analyze recent readings for patterns
        recent_readings = self.lidar_history[-10:]
        
        # Check for consistent obstacles (walls, corridors)
        front_obstacles = [r['front'] for r in recent_readings if r['front'] < 2.0]
        left_obstacles = [r['left'] for r in recent_readings if r['left'] < 1.0]
        right_obstacles = [r['right'] for r in recent_readings if r['right'] < 1.0]
        
        # Detect wall following
        if len(left_obstacles) > 7:  # 70% of readings show left wall
            logger.debug("LIDAR: Detected left wall following pattern")
        elif len(right_obstacles) > 7:  # 70% of readings show right wall
            logger.debug("LIDAR: Detected right wall following pattern")
        
        # Detect corridor navigation
        if len(left_obstacles) > 5 and len(right_obstacles) > 5:
            logger.debug("LIDAR: Detected corridor navigation pattern")
    
    def _update_environment_map(self, front_distance, left_distance, right_distance):
        """Update internal environment map with LIDAR data"""
        current_pos = self.robot_state.get_position()
        min_obstacle_distance = 0.5  # Don't add obstacles too close to robot

        # Only add obstacles if they are not too close
        if front_distance > min_obstacle_distance and front_distance < 2.5:
            obstacle_x = current_pos.x + front_distance * math.cos(current_pos.theta)
            obstacle_y = current_pos.y + front_distance * math.sin(current_pos.theta)
            self.pathfinder.add_obstacle(obstacle_x, obstacle_y, 0.3)
            logger.debug(f"Added LIDAR obstacle at ({obstacle_x:.2f}, {obstacle_y:.2f})")

        # Same for left/right
        if left_distance > min_obstacle_distance and left_distance < 1.5:
            left_obstacle_x = current_pos.x + left_distance * math.cos(current_pos.theta + math.pi/2)
            left_obstacle_y = current_pos.y + left_distance * math.sin(current_pos.theta + math.pi/2)
            self.pathfinder.add_obstacle(left_obstacle_x, left_obstacle_y, 0.2)
            logger.debug(f"Added LIDAR left obstacle at ({left_obstacle_x:.2f}, {left_obstacle_y:.2f})")

        if right_distance > min_obstacle_distance and right_distance < 1.5:
            right_obstacle_x = current_pos.x + right_distance * math.cos(current_pos.theta - math.pi/2)
            right_obstacle_y = current_pos.y + right_distance * math.sin(current_pos.theta - math.pi/2)
            self.pathfinder.add_obstacle(right_obstacle_x, right_obstacle_y, 0.2)
            logger.debug(f"Added LIDAR right obstacle at ({right_obstacle_x:.2f}, {right_obstacle_y:.2f})")
    
    def _handle_narrow_corridor(self, left_distance, right_distance):
        """Handle navigation through narrow corridors"""
        # Adjust speed based on corridor width
        corridor_width = min(left_distance, right_distance)
        
        if corridor_width < 0.5:
            # Very narrow corridor - slow down significantly
            logger.warning(f"LIDAR: Very narrow corridor detected ({corridor_width:.2f}m) - reducing speed")
            # This will be handled by the speed scaling in _follow_path
        elif corridor_width < 0.8:
            # Narrow corridor - moderate speed reduction
            logger.info(f"LIDAR: Narrow corridor detected ({corridor_width:.2f}m) - moderate speed reduction")
    
    def _update_pathfinder_with_lidar_data(self, front_distance, left_distance, right_distance):
        """Update pathfinder grid with LIDAR-detected obstacles"""
        current_pos = self.robot_state.get_position()
        min_obstacle_distance = 0.5  # Don't add obstacles too close to robot

        # Create a more sophisticated obstacle mapping
        if front_distance > min_obstacle_distance and front_distance < 2.5:
            # Map front obstacles with uncertainty
            for dist in range(int(min_obstacle_distance * 10), int(front_distance * 10)):
                check_dist = dist * 0.1
                if check_dist < front_distance:
                    # This area is clear
                    continue
                else:
                    # This area is blocked
                    obstacle_x = current_pos.x + check_dist * math.cos(current_pos.theta)
                    obstacle_y = current_pos.y + check_dist * math.sin(current_pos.theta)
                    self.pathfinder.add_obstacle(obstacle_x, obstacle_y, 0.2)
                    logger.debug(f"Added LIDAR pathfinder obstacle at ({obstacle_x:.2f}, {obstacle_y:.2f})")
                    break  # Stop at first obstacle

    def _try_wider_path(self, current_pos, goal_x, goal_y) -> bool:
        """Try to find a path with a wider safety margin"""
        logger.info("Trying wider path strategy")
        
        # Temporarily increase safety margin in pathfinder
        original_margin = self.pathfinder.safety_margin
        self.pathfinder.safety_margin = original_margin * 1.5
        
        try:
            # Try to find path with wider margin
            new_path = self.pathfinder.find_path(current_pos.x, current_pos.y, goal_x, goal_y)
            if new_path and len(new_path) > 0:
                self.current_path = new_path
                self.path_index = 0
                logger.info("Wider path found successfully")
                return True
        finally:
            # Restore original safety margin
            self.pathfinder.safety_margin = original_margin
        
        return False
    
    def _try_exploration_path(self, current_pos, goal_x, goal_y) -> bool:
        """Try to find a path through less explored areas"""
        logger.info("Trying exploration path strategy")
        
        # This strategy would require more sophisticated exploration tracking
        # For now, we'll try a simple approach: find a path that goes through
        # areas that haven't been marked as explored
        
        # Get unexplored cells
        unexplored_cells = self._get_unexplored_cells()
        if not unexplored_cells:
            logger.debug("No unexplored cells available for exploration path")
            return False
        
        # Find the closest unexplored cell that's roughly in the direction of the goal
        dx = goal_x - current_pos.x
        dy = goal_y - current_pos.y
        goal_direction = math.atan2(dy, dx)
        
        best_cell = None
        best_score = float('inf')
        
        for cell_i, cell_j in unexplored_cells:
            cell_x, cell_y = self.pathfinder.grid_to_world(cell_j, cell_i)
            
            # Calculate distance to cell
            cell_dx = cell_x - current_pos.x
            cell_dy = cell_y - current_pos.y
            cell_distance = math.sqrt(cell_dx*cell_dx + cell_dy*cell_dy)
            
            # Calculate angle to cell
            cell_angle = math.atan2(cell_dy, cell_dx)
            angle_diff = abs(cell_angle - goal_direction)
            
            # Normalize angle difference to [0, pi]
            if angle_diff > math.pi:
                angle_diff = 2*math.pi - angle_diff
            
            # Score based on distance and angle alignment
            score = cell_distance + angle_diff * 2.0  # Weight angle difference more
            
            if score < best_score:
                best_score = score
                best_cell = (cell_x, cell_y)
        
        if best_cell:
            # Try to find path through this unexplored cell
            waypoint_x, waypoint_y = best_cell
            path1 = self.pathfinder.find_path(current_pos.x, current_pos.y, waypoint_x, waypoint_y)
            if path1:
                path2 = self.pathfinder.find_path(waypoint_x, waypoint_y, goal_x, goal_y)
                if path2:
                    self.current_path = path1 + path2
                    self.path_index = 0
                    logger.info("Exploration path found successfully")
                    return True
        
        return False


    def _record_stuck_location(self):
        pos = self.robot_state.get_position()
        grid_size = self.robot_state.config['navigation']['grid_size']
        i = int(pos.y // grid_size)
        j = int(pos.x // grid_size)
        x = j * grid_size + grid_size / 2
        y = i * grid_size + grid_size / 2
        
        # Check if this location is already recorded
        location_exists = any(
            abs(loc['x'] - x) < 0.01 and abs(loc['y'] - y) < 0.01 
            for loc in self.stuck_locations
        )
        
        if not location_exists:
            new_location = {
                "count": self.stuck_location_counter,
                "x": x,
                "y": y
            }
            self.stuck_locations.append(new_location)
            self.stuck_location_counter += 1
            self.learning_data_changed = True
            self._save_learning_data(force=True)  # Force save for stuck locations
            self.pathfinder.add_obstacle(x, y, 0.3)
            logger.info(f"Recorded stuck location at ({x:.2f}, {y:.2f}) with count {new_location['count']}")

    def get_stuck_locations(self):
        return list(self.stuck_locations)

    def _attempt_global_replan(self):
        """Attempt a full global replan from current position to goal. Returns True if successful."""
        if not self.current_goal:
            return False
        current_pos = self.robot_state.get_position()
        logger.info(f"Attempting global replan from ({current_pos.x:.2f}, {current_pos.y:.2f}) to ({self.current_goal.x:.2f}, {self.current_goal.y:.2f})")
        path = self.pathfinder.find_path(current_pos.x, current_pos.y, self.current_goal.x, self.current_goal.y)
        if path and len(path) > 1:
            self.current_path = path
            self.path_index = 0
            return True
        return False

    def _wander(self):
        """Wandering behavior: move forward, avoid obstacles, and mark explored. Includes smart backtracking and navmesh logging."""
        # Mark current cell as explored in both controller and pathfinder
        self._mark_current_cell_explored()
        pos = self.robot_state.get_position()
        self.pathfinder.mark_explored(pos.x, pos.y)
        grid_size = self.robot_state.config['navigation']['grid_size']
        grid_x, grid_y = int(pos.x // grid_size), int(pos.y // grid_size)
        current_cell = (grid_x, grid_y)

        # Navmesh logging: if entered a new cell, log the path
        if self.last_navmesh_cell is not None and self.last_navmesh_cell != current_cell:
            edge = (self.last_navmesh_cell, current_cell)
            if edge not in self.navmesh_edges:
                self.navmesh_edges[edge] = list(self.current_navmesh_path)
                logger.info(f"Navmesh: logged edge {edge} with {len(self.current_navmesh_path)} waypoints.")
                self.save_navmesh()
            self.current_navmesh_path = []
        self.current_navmesh_path.append((pos.x, pos.y))
        self.last_navmesh_cell = current_cell

        # If new unexplored cells are found, switch back to path-based exploration
        if self._get_unexplored_cells():
            logger.info("New unexplored cells found during wandering, switching back to exploration planning.")
            self.wandering = False
            self._start_exploration_planning()
            return

        # Smart backtracking: if in obstacle cell, backtrack to safe
        if self.pathfinder.is_obstacle(grid_x, grid_y):
            logger.warning(f"Robot is in obstacle at cell {current_cell}, initiating backtrack.")
            self._backtrack_to_safe()
            return

        # Wandering state machine: either moving forward or turning
        if self.backtracking:
            # Continue backtracking until in free cell or timeout
            if not self.pathfinder.is_obstacle(grid_x, grid_y):
                self.backtracking = False
                self.motor_controller.stop()
                logger.info("Backtracking complete, resuming wandering.")
                return
            if time.time() - self.backtrack_start_time > 2.0:  # 2 seconds max
                self.backtracking = False
                self.motor_controller.stop()
                logger.warning("Backtracking timed out, resuming wandering.")
                return
            # Keep reversing
            self.motor_controller.set_speeds(-0.4, -0.4)  # Increased backtracking speed
            logger.debug("Backtracking: reversing...")
            return

        if self.wander_turning:
            # Currently turning
            if time.time() - self.wander_turn_start < self.wander_turn_duration:
                # Continue turning
                turn_speed = 0.5  # Increased turn speed for higher base speed
                direction = self.wander_turn_direction
                self.motor_controller.set_speeds(turn_speed * direction, -turn_speed * direction)
                logger.debug(f"Wandering: turning {'left' if direction == 1 else 'right'}.")
                return
            else:
                # Done turning
                self.wander_turning = False
                self.motor_controller.stop()
                logger.debug("Wandering: finished turning, will move forward.")

        # If obstacle detected, start turning
        if self.sensor_manager.is_obstacle_detected():
            self.motor_controller.stop()
            self.wander_turning = True
            self.wander_turn_start = time.time()
            self.wander_turn_duration = random.uniform(0.7, 1.5)  # Random turn duration
            self.wander_turn_direction = random.choice([1, -1])  # Random left or right
            logger.info(f"Wandering: obstacle detected, turning {'left' if self.wander_turn_direction == 1 else 'right'} for {self.wander_turn_duration:.2f}s.")
            return

        # Otherwise, move forward
        # Get sensor data for adaptive speed control
        sensor_data = self.sensor_manager.get_sensor_data()
        front_distance = sensor_data['ultrasonic']['front'].value
        left_distance = sensor_data['ultrasonic']['left'].value
        right_distance = sensor_data['ultrasonic']['right'].value
        
        # Calculate adaptive speed scaling based on proximity to objects
        speed_scale = self._calculate_adaptive_speed_scale(front_distance, left_distance, right_distance)
        
        # Base forward speed for wandering
        base_forward_speed = 0.83  # m/s (3 km/h)
        adaptive_forward_speed = base_forward_speed * speed_scale
        
        # Log speed adjustment for debugging
        if speed_scale < 1.0:
            logger.debug(f"Wandering speed reduced to {speed_scale:.2f} due to proximity - L:{left_distance:.2f}m, R:{right_distance:.2f}m, F:{front_distance:.2f}m")
            # Log area of caution
            grid_size = self.robot_state.config['navigation']['grid_size']
            i = int(pos.y // grid_size)
            j = int(pos.x // grid_size)
            self.areas_of_caution.add((i, j))
            self.learning_data_changed = True
            self._save_learning_data()
        
        self.motor_controller.set_speeds(adaptive_forward_speed, adaptive_forward_speed)
        logger.debug(f"Wandering: moving forward at {adaptive_forward_speed:.2f} m/s (scale: {speed_scale:.2f}).")

    def _backtrack_to_safe(self):
        """Backtrack (reverse) until the robot is in a free cell."""
        if not self.backtracking:
            self.backtracking = True
            self.backtrack_start_time = time.time()
            self.motor_controller.set_speeds(-0.4, -0.4)  # Increased backtracking speed
            logger.info("Backtracking: started reversing to escape obstacle.")

    def save_navmesh(self):
        """Save navmesh_edges to a JSON file."""
        try:
            # Convert tuple keys to strings for JSON
            serializable_edges = {str(k): v for k, v in self.navmesh_edges.items()}
            navmesh_path = os.path.join(os.path.dirname(__file__), '../../', self.navmesh_file)
            with open(navmesh_path, 'w') as f:
                json.dump(serializable_edges, f, indent=2)
            logger.info(f"Navmesh saved to {navmesh_path} ({len(self.navmesh_edges)} edges)")
        except Exception as e:
            logger.error(f"Failed to save navmesh to {self.navmesh_file}: {e}")

    def load_navmesh(self):
        """Load navmesh_edges from a JSON file."""
        try:
            navmesh_path = os.path.join(os.path.dirname(__file__), '../../', self.navmesh_file)
            if os.path.exists(navmesh_path):
                with open(navmesh_path, 'r') as f:
                    data = json.load(f)
                # Convert string keys back to tuple
                self.navmesh_edges = {ast.literal_eval(k): v for k, v in data.items()}
                logger.info(f"Navmesh loaded from {navmesh_path} ({len(self.navmesh_edges)} edges)")
            else:
                logger.info(f"Navmesh file {navmesh_path} not found, starting fresh.")
                self.navmesh_edges = {}
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse navmesh file {self.navmesh_file}: {e}. Starting fresh.")
            self.navmesh_edges = {}
        except Exception as e:
            logger.error(f"Failed to load navmesh from {self.navmesh_file}: {e}. Starting fresh.")
            self.navmesh_edges = {}

    def _calculate_adaptive_speed_scale(self, front_distance: float, left_distance: float, right_distance: float) -> float:
        """
        Calculate adaptive speed scaling based on proximity to objects
        
        Args:
            front_distance: Distance to front obstacle (meters)
            left_distance: Distance to left obstacle (meters) 
            right_distance: Distance to right obstacle (meters)
            
        Returns:
            Speed scale factor between min_speed_scale and 1.0
        """
        # Start with full speed
        speed_scale = 1.0
        
        # Calculate speed reduction based on side proximity
        # Only consider left and right distances for gradual speed reduction
        # Front distance is handled separately for emergency stops
        
        # Get the minimum of left and right distances (closest side obstacle)
        closest_side_distance = min(left_distance, right_distance)
        
        # If side obstacle is within safe distance, reduce speed gradually
        if closest_side_distance < self.safe_distance:
            if closest_side_distance <= self.min_safe_distance:
                # At minimum safe distance, use minimum speed
                side_speed_scale = self.min_speed_scale
            else:
                # Gradual speed reduction between min_safe_distance and safe_distance
                distance_ratio = (closest_side_distance - self.min_safe_distance) / (self.safe_distance - self.min_safe_distance)
                side_speed_scale = self.min_speed_scale + (1.0 - self.min_speed_scale) * distance_ratio
            
            # Apply side speed reduction
            speed_scale = min(speed_scale, side_speed_scale)
        
        # Additional speed reduction if both sides are close (narrow corridor)
        if left_distance < self.safe_distance and right_distance < self.safe_distance:
            # Extra reduction for narrow corridors
            corridor_factor = min(left_distance, right_distance) / self.safe_distance
            corridor_speed_scale = self.min_speed_scale + (1.0 - self.min_speed_scale) * corridor_factor * 0.5
            speed_scale = min(speed_scale, corridor_speed_scale)
        
        # Smooth speed transitions to avoid jerky movement
        max_change = self.speed_recovery_rate
        speed_diff = speed_scale - self.last_speed_scale
        
        if abs(speed_diff) > max_change:
            if speed_diff > 0:
                speed_scale = self.last_speed_scale + max_change  # Gradual increase
            else:
                speed_scale = self.last_speed_scale - max_change  # Gradual decrease
        
        # Update last speed scale for next iteration
        self.last_speed_scale = speed_scale
        
        return speed_scale

    def set_adaptive_speed_parameters(self, safe_distance: float = None, min_safe_distance: float = None, 
                                    min_speed_scale: float = None, speed_recovery_rate: float = None):
        """
        Update adaptive speed control parameters
        
        Args:
            safe_distance: Distance where speed starts to reduce (meters)
            min_safe_distance: Distance where speed is at minimum (meters)
            min_speed_scale: Minimum speed multiplier (0.0 to 1.0)
            speed_recovery_rate: Speed recovery rate per control cycle
        """
        if safe_distance is not None:
            self.safe_distance = max(0.1, safe_distance)
            logger.info(f"Updated safe_distance to {self.safe_distance}m")
        
        if min_safe_distance is not None:
            self.min_safe_distance = max(0.1, min_safe_distance)
            logger.info(f"Updated min_safe_distance to {self.min_safe_distance}m")
        
        if min_speed_scale is not None:
            self.min_speed_scale = max(0.0, min(1.0, min_speed_scale))
            logger.info(f"Updated min_speed_scale to {self.min_speed_scale}")
        
        if speed_recovery_rate is not None:
            self.speed_recovery_rate = max(0.01, min(0.5, speed_recovery_rate))
            logger.info(f"Updated speed_recovery_rate to {self.speed_recovery_rate}")
        
        # Validate that min_safe_distance is less than safe_distance
        if self.min_safe_distance >= self.safe_distance:
            self.min_safe_distance = self.safe_distance * 0.5
            logger.warning(f"Adjusted min_safe_distance to {self.min_safe_distance}m to ensure it's less than safe_distance")
        
        logger.info("Adaptive speed parameters updated successfully")

    def _save_learning_data(self, force: bool = False):
        """Save valid paths, areas of caution, and stuck locations to JSON.
        
        Args:
            force: If True, save immediately regardless of cooldown. Use for critical saves.
        """
        current_time = time.time()
        
        # Check cooldown unless forced
        if not force:
            time_since_last_save = current_time - self.last_learning_save_time
            if time_since_last_save < self.learning_save_cooldown:
                # Still within cooldown, mark that data has changed but don't save yet
                self.learning_data_changed = True
                return
        
        # Only save if data has changed or forced
        if not force and not self.learning_data_changed:
            return
        
        data = {
            'valid_paths': {str(k): v for k, v in self.valid_paths.items()},
            'areas_of_caution': list(self.areas_of_caution),
            'stuck_locations': self.stuck_locations  # Already in new format: [{"count": N, "x": X, "y": Y}, ...]
        }
        try:
            with open(self.stuck_locations_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.last_learning_save_time = current_time
            self.learning_data_changed = False
            logger.info(f"Learning data saved to {self.stuck_locations_file}")
        except Exception as e:
            logger.error(f"Failed to save learning data: {e}")

    def _load_learning_data(self):
        """Load valid paths, areas of caution, and stuck locations from JSON."""
        try:
            with open(self.stuck_locations_file, 'r') as f:
                data = json.load(f)
            
            # Handle different formats
            if isinstance(data, list):
                # Old format: just a list of stuck locations (could be [x, y] tuples or old format)
                self.stuck_locations = []
                self.stuck_location_counter = 0
                for idx, item in enumerate(data):
                    if isinstance(item, (list, tuple)) and len(item) >= 2:
                        # Old format: [x, y] tuple
                        try:
                            x, y = float(item[0]), float(item[1])
                            self.stuck_locations.append({"count": idx, "x": x, "y": y})
                            self.pathfinder.add_obstacle(x, y, 0.3)  # Mark as obstacle
                        except (ValueError, TypeError):
                            logger.warning(f"Skipping invalid stuck location: {item}")
                    elif isinstance(item, dict) and 'x' in item and 'y' in item:
                        # New format: {"count": N, "x": X, "y": Y}
                        self.stuck_locations.append(item)
                        self.pathfinder.add_obstacle(item['x'], item['y'], 0.3)
                        if 'count' in item:
                            self.stuck_location_counter = max(self.stuck_location_counter, item['count'] + 1)
                self.valid_paths = {}
                self.areas_of_caution = set()
                logger.info(f"Loaded old format learning data from {self.stuck_locations_file}, migrated to new format")
            elif isinstance(data, dict):
                # New format: dictionary with multiple data types
                self.valid_paths = {ast.literal_eval(k): v for k, v in data.get('valid_paths', {}).items()}
                self.areas_of_caution = set(tuple(cell) for cell in data.get('areas_of_caution', []))
                
                # Load stuck locations in new format
                stuck_locs_data = data.get('stuck_locations', [])
                self.stuck_locations = []
                self.stuck_location_counter = 0
                
                for item in stuck_locs_data:
                    if isinstance(item, dict) and 'x' in item and 'y' in item:
                        # New format: {"count": N, "x": X, "y": Y}
                        self.stuck_locations.append(item)
                        self.pathfinder.add_obstacle(item['x'], item['y'], 0.3)
                        if 'count' in item:
                            self.stuck_location_counter = max(self.stuck_location_counter, item['count'] + 1)
                    elif isinstance(item, (list, tuple)) and len(item) >= 2:
                        # Migration from old [x, y] format
                        try:
                            x, y = float(item[0]), float(item[1])
                            self.stuck_locations.append({"count": self.stuck_location_counter, "x": x, "y": y})
                            self.pathfinder.add_obstacle(x, y, 0.3)
                            self.stuck_location_counter += 1
                        except (ValueError, TypeError):
                            logger.warning(f"Skipping invalid stuck location: {item}")
                
                logger.info(f"Learning data loaded from {self.stuck_locations_file}")
            else:
                logger.warning(f"Unknown data format in {self.stuck_locations_file}, starting fresh")
                self.valid_paths = {}
                self.areas_of_caution = set()
                self.stuck_locations = []
                self.stuck_location_counter = 0
        except FileNotFoundError:
            logger.info(f"Learning data file {self.stuck_locations_file} not found, starting fresh.")
            self.valid_paths = {}
            self.areas_of_caution = set()
            self.stuck_locations = []
            self.stuck_location_counter = 0
        except Exception as e:
            logger.error(f"Failed to load learning data: {e}")
            # Initialize with empty data on error
            self.valid_paths = {}
            self.areas_of_caution = set()
            self.stuck_locations = []
            self.stuck_location_counter = 0
    
    def _validate_path(self, path_key: Tuple, path_waypoints: List) -> bool:
        """Check if a saved path is still valid.
        
        Args:
            path_key: Tuple of (from_cell, to_cell) where cells are (i, j) grid coordinates
            path_waypoints: List of waypoints as [(x, y), ...] world coordinates
            
        Returns:
            True if path is valid (all waypoints clear AND path can be found), False otherwise
        """
        grid_size = self.robot_state.config['navigation']['grid_size']
        
        # Extract start and end cells from path_key
        from_cell, to_cell = path_key
        from_i, from_j = from_cell
        to_i, to_j = to_cell
        
        # Convert grid cells to world coordinates
        start_x = from_j * grid_size + grid_size / 2
        start_y = from_i * grid_size + grid_size / 2
        end_x = to_j * grid_size + grid_size / 2
        end_y = to_i * grid_size + grid_size / 2
        
        # Check 1: Verify all waypoints are not blocked
        for waypoint in path_waypoints:
            if len(waypoint) < 2:
                continue
            wx, wy = waypoint[0], waypoint[1]
            grid_x, grid_y = self.pathfinder.world_to_grid(wx, wy)
            if self.pathfinder.is_obstacle(grid_x, grid_y):
                return False
        
        # Check 2: Verify a path can still be found between start and end
        try:
            path = self.pathfinder.find_path(start_x, start_y, end_x, end_y)
            if not path or len(path) == 0:
                return False
        except Exception as e:
            logger.debug(f"Error checking path validity: {e}")
            return False
        
        return True
    
    def _validate_stuck_location(self, location: Tuple[float, float]) -> bool:
        """Check if a stuck location is still stuck.
        
        Args:
            location: World coordinates (x, y) of the stuck location
            
        Returns:
            True if location is still stuck (blocked OR no path exists), False if no longer stuck
        """
        loc_x, loc_y = location
        
        # Check 1: Verify location itself is clear (not blocked)
        grid_x, grid_y = self.pathfinder.world_to_grid(loc_x, loc_y)
        if self.pathfinder.is_obstacle(grid_x, grid_y):
            return True  # Still blocked, so still stuck
        
        # Check 2: Verify a path can be found from current robot position to location
        current_pos = self.robot_state.get_position()
        try:
            path = self.pathfinder.find_path(current_pos.x, current_pos.y, loc_x, loc_y)
            if path and len(path) > 0:
                return False  # Path exists and location is clear, no longer stuck
        except Exception as e:
            logger.debug(f"Error checking stuck location validity: {e}")
            # If we can't check path, assume still stuck to be safe
            return True
        
        return True  # No path found, still stuck
    
    def _validate_area_of_caution(self, area: Tuple[int, int]) -> str:
        """Check the status of an area of caution.
        
        Args:
            area: Grid coordinates (i, j) of the area of caution
            
        Returns:
            'keep' if still caution, 'remove' if now clear, 'stuck' if now blocked
        """
        i, j = area
        grid_size = self.robot_state.config['navigation']['grid_size']
        
        # Convert grid cell to world coordinates
        x = j * grid_size + grid_size / 2
        y = i * grid_size + grid_size / 2
        
        # Check if area is blocked
        grid_x, grid_y = self.pathfinder.world_to_grid(x, y)
        if self.pathfinder.is_obstacle(grid_x, grid_y):
            return 'stuck'  # Now blocked, should be marked as stuck
        
        # Check if area is clear (no nearby obstacles)
        # Check surrounding cells for obstacles
        has_nearby_obstacles = False
        check_radius = 1  # Check adjacent cells
        for di in range(-check_radius, check_radius + 1):
            for dj in range(-check_radius, check_radius + 1):
                ni, nj = i + di, j + dj
                if ni == i and nj == j:
                    continue
                grid_nx, grid_ny = self.pathfinder.world_to_grid(
                    nj * grid_size + grid_size / 2,
                    ni * grid_size + grid_size / 2
                )
                if self.pathfinder.is_obstacle(grid_nx, grid_ny):
                    has_nearby_obstacles = True
                    break
            if has_nearby_obstacles:
                break
        
        if has_nearby_obstacles:
            return 'keep'  # Still caution area
        else:
            return 'remove'  # Now clear, can be removed
    
    def _validate_learning_data(self):
        """Validate all saved learning data against current environment state.
        
        Removes invalid paths, locations that are no longer stuck, and updates areas of caution.
        """
        if not self.exploration_mode:
            return  # Only validate during exploration
        
        logger.info("Starting learning data validation...")
        
        validation_stats = {
            'paths_checked': 0,
            'paths_removed': 0,
            'stuck_locations_checked': 0,
            'stuck_locations_removed': 0,
            'areas_checked': 0,
            'areas_removed': 0,
            'areas_marked_stuck': 0
        }
        
        # Validate valid paths
        invalid_paths = []
        for path_key, path_waypoints in list(self.valid_paths.items()):
            validation_stats['paths_checked'] += 1
            if not self._validate_path(path_key, path_waypoints):
                invalid_paths.append(path_key)
                validation_stats['paths_removed'] += 1
        
        # Remove invalid paths
        for path_key in invalid_paths:
            del self.valid_paths[path_key]
            logger.debug(f"Removed invalid path: {path_key}")
        
        # Validate stuck locations
        locations_to_remove = []
        for location in list(self.stuck_locations):
            validation_stats['stuck_locations_checked'] += 1
            # Extract x, y from location dict
            if isinstance(location, dict) and 'x' in location and 'y' in location:
                loc_x, loc_y = location['x'], location['y']
            elif isinstance(location, (list, tuple)) and len(location) >= 2:
                # Handle old format during migration
                loc_x, loc_y = float(location[0]), float(location[1])
            else:
                logger.warning(f"Invalid stuck location format: {location}")
                locations_to_remove.append(location)
                continue
            
            if not self._validate_stuck_location((loc_x, loc_y)):
                locations_to_remove.append(location)
                validation_stats['stuck_locations_removed'] += 1
        
        # Remove locations that are no longer stuck
        for location in locations_to_remove:
            if location in self.stuck_locations:
                self.stuck_locations.remove(location)
                logger.info(f"Removed no longer stuck location: {location}")
        
        # Validate areas of caution
        areas_to_remove = []
        areas_to_mark_stuck = []
        for area in list(self.areas_of_caution):
            validation_stats['areas_checked'] += 1
            status = self._validate_area_of_caution(area)
            if status == 'remove':
                areas_to_remove.append(area)
                validation_stats['areas_removed'] += 1
            elif status == 'stuck':
                areas_to_mark_stuck.append(area)
                validation_stats['areas_marked_stuck'] += 1
        
        # Remove cleared areas
        for area in areas_to_remove:
            self.areas_of_caution.discard(area)
            logger.debug(f"Removed cleared area of caution: {area}")
        
        # Mark areas that are now stuck
        grid_size = self.robot_state.config['navigation']['grid_size']
        for area in areas_to_mark_stuck:
            i, j = area
            # Convert to world coordinates for stuck location
            stuck_x = j * grid_size + grid_size / 2
            stuck_y = i * grid_size + grid_size / 2
            stuck_location = (stuck_x, stuck_y)
            
            # Remove from areas of caution and add to stuck locations
            self.areas_of_caution.discard(area)
            # Check if this location is already recorded
            location_exists = any(
                abs(loc['x'] - stuck_x) < 0.01 and abs(loc['y'] - stuck_y) < 0.01 
                for loc in self.stuck_locations
            )
            if not location_exists:
                new_location = {
                    "count": self.stuck_location_counter,
                    "x": stuck_x,
                    "y": stuck_y
                }
                self.stuck_locations.append(new_location)
                self.stuck_location_counter += 1
                logger.info(f"Area of caution {area} is now blocked, marked as stuck location: ({stuck_x:.2f}, {stuck_y:.2f}) with count {new_location['count']}")
        
        # Log validation results
        logger.info(f"Validation complete: "
                   f"Paths: {validation_stats['paths_checked']} checked, {validation_stats['paths_removed']} removed | "
                   f"Stuck locations: {validation_stats['stuck_locations_checked']} checked, {validation_stats['stuck_locations_removed']} removed | "
                   f"Areas: {validation_stats['areas_checked']} checked, {validation_stats['areas_removed']} removed, {validation_stats['areas_marked_stuck']} marked as stuck")
        
        # Save cleaned data if any changes were made
        if (validation_stats['paths_removed'] > 0 or 
            validation_stats['stuck_locations_removed'] > 0 or 
            validation_stats['areas_removed'] > 0 or 
            validation_stats['areas_marked_stuck'] > 0):
            self.learning_data_changed = True
            self._save_learning_data(force=True)
        
        # Store validation stats for monitoring
        self.last_validation_stats = validation_stats

