"""
Robot Simulator
Integrates 3D world simulation with robot control system
"""

import time
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
import numpy as np
from loguru import logger

from .world_3d import World3D, Robot3D, WorldObject, ObjectType
from ..core.robot_state import RobotState, RobotMode, Position, SensorData
from ..hardware.motor_controller import MotorController
from ..hardware.sensor_manager import SensorManager
from ..navigation.pathfinder import Pathfinder
from ..navigation.autonomous_controller import AutonomousController


@dataclass
class SimulationConfig:
    """Configuration for the robot simulation"""
    world_size: tuple = (50, 3, 50)  # width, height, depth
    robot_dimensions: tuple = (0.3, 0.2, 0.4)  # width, height, depth
    simulation_fps: int = 60
    physics_fps: int = 100
    enable_physics: bool = True
    enable_collision: bool = True
    enable_sensors: bool = True


class RobotSimulator:
    """Main robot simulation class"""
    
    def __init__(self, config: Dict[str, Any], sim_config: SimulationConfig = None):
        self.config = config
        self.sim_config = sim_config or SimulationConfig()
        
        # Simulation state
        self.running = False
        self.paused = False
        
        # 3D world
        self.world = World3D(1200, 800)
        
        # Robot components (simulated)
        self.robot_state = RobotState(config)
        self.motor_controller = MotorController(config)
        self.sensor_manager = SensorManager(config)
        self.pathfinder = Pathfinder(config)
        self.autonomous_controller = AutonomousController(
            self.robot_state, self.motor_controller,
            self.sensor_manager, self.pathfinder
        )
        
        # 3D robot representation
        self.robot_3d = Robot3D(
            position=(0, 0.1, 0),  # Slightly above ground
            orientation=0.0,
            dimensions=self.sim_config.robot_dimensions,
            color=(100, 150, 255)
        )
        self.world.add_robot(self.robot_3d)
        
        # Physics simulation
        self.physics_thread = None
        self.last_physics_time = time.time()
        
        # Sensor simulation (decoupled from physics)
        self.sensor_thread = None
        self.last_sensor_update = time.time()
        self.sensor_update_interval = 1.0 / 20  # 20Hz sensor updates (increased from 10Hz)
        
        # Pathfinder update optimization
        self.pathfinder_changed_cells = set()  # Track changed cells
        self.last_pathfinder_update = time.time()
        self.pathfinder_update_interval = 1.0 / 10  # 10Hz pathfinder updates
        
        # Movement simulation
        self.wheel_base = 0.25  # Distance between wheels
        self.wheel_radius = 0.05  # Wheel radius
        self.max_speed = 0.5  # m/s
        
        # Initialize simulation
        self._setup_simulation()
    
    def _setup_simulation(self):
        """Setup the simulation environment"""
        logger.info("Setting up robot simulation...")
        
        # Create custom world if needed
        self._create_custom_world()
        
        # Start physics thread
        if self.sim_config.enable_physics:
            self.physics_thread = threading.Thread(target=self._physics_loop, daemon=True)
            self.physics_thread.start()
        
        logger.info("Robot simulation setup complete")
    
    def _create_custom_world(self):
        """Create a custom world environment for testing"""
        # Clear default world and create custom one
        self.world.objects.clear()
        
        # Floor
        self.world.add_object(WorldObject(
            obj_type=ObjectType.FLOOR,
            position=(0, 0, 0),
            dimensions=(20, 0.1, 20),
            color=(200, 200, 200),
            collision=True
        ))
        
        # Walls
        wall_height = 2.5
        wall_thickness = 0.1
        
        # Create a maze-like environment
        walls = [
            # Outer walls
            ((0, wall_height/2, -10), (20, wall_height, wall_thickness)),  # North
            ((0, wall_height/2, 10), (20, wall_height, wall_thickness)),   # South
            ((10, wall_height/2, 0), (wall_thickness, wall_height, 20)),   # East
            ((-10, wall_height/2, 0), (wall_thickness, wall_height, 20)),  # West
            
            # Internal walls
            ((-5, wall_height/2, -5), (wall_thickness, wall_height, 10)),  # Vertical wall 1
            ((5, wall_height/2, 5), (wall_thickness, wall_height, 10)),    # Vertical wall 2
            ((-5, wall_height/2, 0), (10, wall_thickness, wall_thickness)), # Horizontal wall 1
            ((0, wall_height/2, 5), (10, wall_thickness, wall_thickness)),  # Horizontal wall 2
        ]
        
        for pos, dim in walls:
            self.world.add_object(WorldObject(
                obj_type=ObjectType.WALL,
                position=pos,
                dimensions=dim,
                color=(150, 150, 150),
                collision=True
            ))
        
        # Add some obstacles
        obstacles = [
            ((-7, 0.25, -7), (0.5, 0.5, 0.5), (255, 0, 0)),    # Red cube
            ((7, 0.25, 7), (0.5, 0.5, 0.5), (0, 255, 0)),      # Green cube
            ((0, 0.25, -8), (0.3, 0.5, 0.3), (0, 0, 255)),     # Blue cylinder
        ]
        
        for pos, dim, color in obstacles:
            self.world.add_object(WorldObject(
                obj_type=ObjectType.OBSTACLE,
                position=pos,
                dimensions=dim,
                color=color,
                collision=True
            ))
        
        # Add furniture
        furniture = [
            ((-3, 0.4, 3), (1.5, 0.8, 1), (139, 69, 19)),      # Table
            ((3, 0.3, -3), (1, 0.6, 0.5), (139, 69, 19)),      # Chair
        ]
        
        for pos, dim, color in furniture:
            self.world.add_object(WorldObject(
                obj_type=ObjectType.FURNITURE,
                position=pos,
                dimensions=dim,
                color=color,
                collision=True
            ))
    
    def _physics_loop(self):
        """Physics simulation loop (decoupled from sensor updates)"""
        while self.running:
            if not self.paused:
                current_time = time.time()
                dt = current_time - self.last_physics_time
                self.last_physics_time = current_time
                
                # Update robot physics
                self._update_robot_physics(dt)
                
                # Update pathfinder (throttled)
                if current_time - self.last_pathfinder_update >= self.pathfinder_update_interval:
                    self._update_pathfinder()
                    self.last_pathfinder_update = current_time
            
            time.sleep(1.0 / self.sim_config.physics_fps)
    
    def _sensor_update_loop(self):
        """Separate sensor update loop"""
        while self.running:
            if not self.paused and self.sim_config.enable_sensors:
                current_time = time.time()
                if current_time - self.last_sensor_update >= self.sensor_update_interval:
                    self._update_sensors()
                    self.last_sensor_update = current_time
            
            time.sleep(0.01)  # Small sleep to prevent busy waiting
    
    def _update_robot_physics(self, dt: float):
        """Update robot physics based on motor commands"""
        # Get current motor speeds
        left_speed, right_speed = self.motor_controller.get_current_speeds()
        
        # Convert to linear and angular velocities
        left_velocity = (left_speed / 100.0) * self.max_speed
        right_velocity = (right_speed / 100.0) * self.max_speed
        
        # Calculate robot movement
        linear_velocity = (left_velocity + right_velocity) / 2.0
        angular_velocity = (right_velocity - left_velocity) / self.wheel_base
        
        # Update robot position
        current_pos = self.robot_3d.position
        current_orientation = self.robot_3d.orientation
        
        # Calculate new position
        new_orientation = current_orientation + angular_velocity * dt
        
        # Calculate new position based on orientation
        new_x = current_pos[0] + linear_velocity * np.sin(new_orientation) * dt
        new_z = current_pos[2] + linear_velocity * np.cos(new_orientation) * dt
        new_y = current_pos[1]  # Keep same height
        
        # Check collision before updating
        if self.sim_config.enable_collision:
            if not self.world.check_collision((new_x, new_y, new_z), self.robot_3d.dimensions):
                self.robot_3d.position = (new_x, new_y, new_z)
                self.robot_3d.orientation = new_orientation
            else:
                # Collision detected - stop movement
                self.motor_controller.stop_motors()
        else:
            self.robot_3d.position = (new_x, new_y, new_z)
            self.robot_3d.orientation = new_orientation
        
        # Update robot state
        self.robot_state.update_position(
            new_x * 100,  # Convert to cm
            new_z * 100,  # Convert to cm
            new_orientation
        )
        
        # Update 3D world robot position
        self.world.update_robot_position(
            self.robot_3d.position[0],
            self.robot_3d.position[1],
            self.robot_3d.position[2],
            self.robot_3d.orientation
        )
    
    def _update_sensors(self):
        """Update sensor readings based on 3D world"""
        # Get sensor readings from 3D world
        sensor_readings = self.world.get_sensor_readings(
            self.robot_3d.position,
            self.robot_3d.orientation
        )
        
        # Create sensor data object
        sensor_data = SensorData(
            ultrasonic_front=sensor_readings['ultrasonic_front'],
            ultrasonic_left=sensor_readings['ultrasonic_left'],
            ultrasonic_right=sensor_readings['ultrasonic_right'],
            infrared_left=sensor_readings['infrared_left'],
            infrared_right=sensor_readings['infrared_right'],
            bumper_left=False,  # Could be enhanced with collision detection
            bumper_right=False,
            timestamp=time.time()
        )
        
        # Update robot state with sensor data
        self.robot_state.update_sensors(sensor_data)
        
        # Update sensor manager
        self.sensor_manager._update_all_sensors()
    
    def _update_pathfinder(self):
        """Update pathfinder with current robot position (optimized)"""
        # Update robot position in pathfinder grid
        robot_x = self.robot_state.position.x
        robot_y = self.robot_state.position.y
        
        self.pathfinder.update_robot_position(robot_x, robot_y)
        self.pathfinder.mark_explored(robot_x, robot_y)
        
        # Only update obstacles if world objects changed (track changes)
        # For now, we'll update obstacles but could be optimized further
        # by tracking which objects have moved
        obstacle_count = 0
        for obj in self.world.objects:
            if obj.collision and obj.obj_type in [ObjectType.WALL, ObjectType.OBSTACLE, ObjectType.FURNITURE]:
                # Convert 3D position to 2D grid
                grid_x = int(obj.position[0] * 100 / self.pathfinder.grid_size)
                grid_y = int(obj.position[2] * 100 / self.pathfinder.grid_size)
                
                # Add obstacle to pathfinder grid (only if not already an obstacle)
                if 0 <= grid_x < self.pathfinder.grid_width and 0 <= grid_y < self.pathfinder.grid_height:
                    cell_key = (grid_x, grid_y)
                    if cell_key not in self.pathfinder_changed_cells:
                        # Check if cell is already an obstacle
                        if self.pathfinder.grid[grid_y, grid_x] != 1:
                            self.pathfinder.grid[grid_y, grid_x] = 1  # Obstacle
                            self.pathfinder_changed_cells.add(cell_key)
                            obstacle_count += 1
        
        # Clear changed cells cache periodically to allow updates
        if len(self.pathfinder_changed_cells) > 1000:
            self.pathfinder_changed_cells.clear()
    
    def start(self):
        """Start the simulation"""
        logger.info("Starting robot simulation...")
        self.running = True
        
        # Start autonomous controller
        self.autonomous_controller.start()
        
        # Start sensor manager
        self.sensor_manager.start()
        
        # Start motor controller
        self.motor_controller.start()
        
        # Start physics loop
        if self.physics_thread is None:
            self.physics_thread = threading.Thread(target=self._physics_loop, daemon=True)
            self.physics_thread.start()
        
        # Start sensor update loop (separate from physics)
        if self.sensor_thread is None:
            self.sensor_thread = threading.Thread(target=self._sensor_update_loop, daemon=True)
            self.sensor_thread.start()
        
        logger.info("Robot simulation started")
    
    def stop(self):
        """Stop the simulation"""
        logger.info("Stopping robot simulation...")
        self.running = False
        
        # Stop all components
        self.autonomous_controller.stop()
        self.sensor_manager.stop()
        self.motor_controller.stop()
        
        # Wait for threads to finish
        if self.physics_thread:
            self.physics_thread.join(timeout=1.0)
        if self.sensor_thread:
            self.sensor_thread.join(timeout=1.0)
        
        # Close 3D world
        self.world.close()
        
        logger.info("Robot simulation stopped")
    
    def pause(self):
        """Pause the simulation"""
        self.paused = True
        logger.info("Simulation paused")
    
    def resume(self):
        """Resume the simulation"""
        self.paused = False
        logger.info("Simulation resumed")
    
    def reset(self):
        """Reset the simulation to initial state"""
        logger.info("Resetting simulation...")
        
        # Reset robot position
        self.robot_3d.position = (0, 0.1, 0)
        self.robot_3d.orientation = 0.0
        self.robot_3d.velocity = (0.0, 0.0, 0.0)
        self.robot_3d.angular_velocity = 0.0
        
        # Reset robot state
        self.robot_state.reset_position()
        self.robot_state.set_mode(RobotMode.IDLE)
        
        # Reset motor controller
        self.motor_controller.stop_motors()
        
        # Reset autonomous controller
        self.autonomous_controller.stop()
        self.autonomous_controller.start()
        
        # Reset pathfinder
        self.pathfinder.grid.fill(0)
        self.pathfinder.explored_nodes.clear()
        
        logger.info("Simulation reset complete")
    
    def run_simulation(self):
        """Run the complete simulation with 3D visualization"""
        try:
            self.start()
            
            # Run 3D world simulation
            self.world.run_simulation(self.sim_config.simulation_fps)
            
        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        except Exception as e:
            logger.error(f"Simulation error: {e}")
        finally:
            self.stop()
    
    def get_simulation_status(self) -> Dict[str, Any]:
        """Get comprehensive simulation status"""
        return {
            'running': self.running,
            'paused': self.paused,
            'robot_position': {
                'x': self.robot_3d.position[0],
                'y': self.robot_3d.position[1],
                'z': self.robot_3d.position[2],
                'orientation': self.robot_3d.orientation
            },
            'robot_state': self.robot_state.get_status_summary(),
            'motor_status': self.motor_controller.get_status(),
            'sensor_status': self.sensor_manager.get_sensor_status(),
            'navigation_status': self.autonomous_controller.get_status(),
            'pathfinder_status': self.pathfinder.get_grid_status(),
            'world_objects': len(self.world.objects)
        }
    
    def add_test_obstacle(self, position: tuple, dimensions: tuple, color: tuple = (255, 0, 0)):
        """Add a test obstacle to the world"""
        obstacle = WorldObject(
            obj_type=ObjectType.OBSTACLE,
            position=position,
            dimensions=dimensions,
            color=color,
            collision=True
        )
        self.world.add_object(obstacle)
        logger.info(f"Added test obstacle at {position}")
    
    def remove_test_obstacles(self):
        """Remove all test obstacles from the world"""
        self.world.objects = [obj for obj in self.world.objects 
                             if obj.obj_type != ObjectType.OBSTACLE]
        logger.info("Removed all test obstacles")
    
    def set_robot_position(self, x: float, y: float, z: float, orientation: float):
        """Set robot position manually"""
        self.robot_3d.position = (x, y, z)
        self.robot_3d.orientation = orientation
        self.robot_state.reset_position(x * 100, z * 100, orientation)
        logger.info(f"Set robot position to ({x}, {y}, {z}) with orientation {orientation}")
    
    def test_navigation(self, target_x: float, target_y: float):
        """Test navigation to a specific target"""
        logger.info(f"Testing navigation to ({target_x}, {target_y})")
        self.autonomous_controller.navigate_to(target_x, target_y)
    
    def test_exploration(self):
        """Test autonomous exploration"""
        logger.info("Testing autonomous exploration")
        self.autonomous_controller.start_exploration()
    
    def test_manual_control(self, command: str, speed: float = 50.0):
        """Test manual control commands"""
        logger.info(f"Testing manual control: {command} at speed {speed}")
        
        if command == "forward":
            self.motor_controller.move_forward(speed)
        elif command == "backward":
            self.motor_controller.move_backward(speed)
        elif command == "left":
            self.motor_controller.turn_left(speed)
        elif command == "right":
            self.motor_controller.turn_right(speed)
        elif command == "stop":
            self.motor_controller.stop_motors()
        else:
            logger.warning(f"Unknown command: {command}") 