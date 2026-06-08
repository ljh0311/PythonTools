#!/usr/bin/env python3
"""
3D Robot Simulation Demo
Demonstrates the 3D simulation environment for testing robot behavior
"""

import sys
import os
import time
import yaml
from loguru import logger
import pygame
import math

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.simulation.robot_simulator import RobotSimulator, SimulationConfig
from src.core.robot_state import RobotMode


def demo_basic_movement():
    """Demo basic robot movement"""
    logger.info("=== Basic Movement Demo ===")
    
    # Initialize Pygame for 2D visualization
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Basic Movement Demo")
    clock = pygame.time.Clock()
    pygame.font.init()
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simulator
    sim_config = SimulationConfig(
        simulation_fps=60,
        physics_fps=100,
        enable_physics=True,
        enable_collision=True,
        enable_sensors=True
    )
    
    simulator = RobotSimulator(config, sim_config)
    
    try:
        # Start simulation
        simulator.start()
        
        # Demo manual control with visualization
        logger.info("Testing manual movement...")
        
        # Forward movement
        simulator.test_manual_control("forward", 30)
        for _ in range(120):  # 2 seconds at 60fps
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        # Turn left
        simulator.test_manual_control("left", 20)
        for _ in range(60):  # 1 second
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        # Stop
        simulator.test_manual_control("stop")
        for _ in range(60):  # 1 second
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        # Turn right
        simulator.test_manual_control("right", 20)
        for _ in range(60):  # 1 second
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        # Backward
        simulator.test_manual_control("backward", 20)
        for _ in range(120):  # 2 seconds
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        # Stop
        simulator.test_manual_control("stop")
        for _ in range(60):  # 1 second
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
        
        logger.info("Basic movement demo completed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    finally:
        simulator.stop()
        pygame.quit()


def demo_navigation():
    """Demo autonomous navigation"""
    logger.info("=== Autonomous Navigation Demo ===")
    
    # Initialize Pygame for 2D visualization
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Navigation Demo")
    clock = pygame.time.Clock()
    pygame.font.init()
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simulator
    sim_config = SimulationConfig(
        simulation_fps=60,
        physics_fps=100,
        enable_physics=True,
        enable_collision=True,
        enable_sensors=True
    )
    
    simulator = RobotSimulator(config, sim_config)
    
    try:
        # Start simulation
        simulator.start()
        
        # Set robot to autonomous mode
        simulator.robot_state.set_mode(RobotMode.AUTONOMOUS)
        
        # Test navigation to different targets
        targets = [
            (5, 5),    # Top right
            (-5, -5),  # Bottom left
            (0, 8),    # North
            (0, -8),   # South
            (8, 0),    # East
            (-8, 0),   # West
        ]
        
        for i, (x, y) in enumerate(targets):
            logger.info(f"Navigating to target {i+1}: ({x}, {y})")
            simulator.test_navigation(x, y)
            
            # Wait for navigation to complete or timeout with visualization
            start_time = time.time()
            while time.time() - start_time < 30:  # 30 second timeout
                # Handle events
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        return
                
                # Draw visualization
                screen.fill((240, 240, 240))
                draw_2d_robot_view(screen, simulator)
                draw_target(screen, x, y, i+1)
                draw_ui_overlay(screen, simulator)
                pygame.display.flip()
                clock.tick(60)
                
                # Check navigation status
                status = simulator.get_simulation_status()
                nav_status = status['navigation_status']
                
                if nav_status['navigation_state'] == 'reached_goal':
                    logger.info(f"Reached target {i+1}")
                    break
                elif nav_status['navigation_state'] == 'stuck':
                    logger.warning(f"Got stuck trying to reach target {i+1}")
                    break
            
            # Reset robot position for next target
            simulator.set_robot_position(0, 0.1, 0, 0)
            time.sleep(1)
        
        logger.info("Navigation demo completed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    finally:
        simulator.stop()
        pygame.quit()


def draw_target(screen, x, y, target_num):
    """Draw a target marker on the 2D view"""
    scale = 20
    center_x, center_y = 400, 300
    screen_x = center_x + x * scale
    screen_y = center_y - y * scale
    
    # Draw target circle
    pygame.draw.circle(screen, (255, 0, 0), (int(screen_x), int(screen_y)), 10)
    pygame.draw.circle(screen, (255, 255, 255), (int(screen_x), int(screen_y)), 10, 2)
    
    # Draw target number
    font = pygame.font.Font(None, 24)
    text_surface = font.render(str(target_num), True, (255, 255, 255))
    text_rect = text_surface.get_rect(center=(screen_x, screen_y))
    screen.blit(text_surface, text_rect)


def demo_exploration():
    """Demo autonomous exploration"""
    logger.info("=== Autonomous Exploration Demo ===")
    
    # Initialize Pygame for 2D visualization
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Exploration Demo")
    clock = pygame.time.Clock()
    pygame.font.init()
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simulator
    sim_config = SimulationConfig(
        simulation_fps=60,
        physics_fps=100,
        enable_physics=True,
        enable_collision=True,
        enable_sensors=True
    )
    
    simulator = RobotSimulator(config, sim_config)
    
    try:
        # Start simulation
        simulator.start()
        
        # Set robot to autonomous mode
        simulator.robot_state.set_mode(RobotMode.AUTONOMOUS)
        
        # Start exploration
        logger.info("Starting autonomous exploration...")
        simulator.test_exploration()
        
        # Monitor exploration progress with visualization
        start_time = time.time()
        last_progress = 0
        
        while time.time() - start_time < 120:  # 2 minute timeout
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            
            # Draw visualization
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_exploration_progress(screen, simulator)
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
            
            # Check exploration status
            status = simulator.get_simulation_status()
            pathfinder_status = status['pathfinder_status']
            exploration_progress = pathfinder_status['exploration_percentage']
            
            if exploration_progress > last_progress + 5:  # Report every 5% progress
                logger.info(f"Exploration progress: {exploration_progress:.1f}%")
                last_progress = exploration_progress
            
            if exploration_progress > 80:  # Consider exploration complete at 80%
                logger.info("Exploration completed!")
                break
            
            nav_status = status['navigation_status']
            if nav_status['navigation_state'] == 'stuck':
                logger.warning("Exploration got stuck, resetting...")
                simulator.reset()
                simulator.test_exploration()
        
        logger.info("Exploration demo completed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    finally:
        simulator.stop()
        pygame.quit()


def demo_obstacle_avoidance():
    """Demo obstacle avoidance"""
    logger.info("=== Obstacle Avoidance Demo ===")
    
    # Initialize Pygame for 2D visualization
    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    pygame.display.set_caption("Obstacle Avoidance Demo")
    clock = pygame.time.Clock()
    pygame.font.init()
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simulator
    sim_config = SimulationConfig(
        simulation_fps=60,
        physics_fps=100,
        enable_physics=True,
        enable_collision=True,
        enable_sensors=True
    )
    
    simulator = RobotSimulator(config, sim_config)
    
    try:
        # Start simulation
        simulator.start()
        
        # Add test obstacles
        logger.info("Adding test obstacles...")
        simulator.add_test_obstacle((2, 0.25, 2), (0.5, 0.5, 0.5), (255, 0, 0))  # Red cube
        simulator.add_test_obstacle((-2, 0.25, -2), (0.5, 0.5, 0.5), (0, 255, 0))  # Green cube
        simulator.add_test_obstacle((0, 0.25, 3), (0.3, 0.5, 0.3), (0, 0, 255))  # Blue cylinder
        
        # Set robot to autonomous mode
        simulator.robot_state.set_mode(RobotMode.AUTONOMOUS)
        
        # Test navigation through obstacles
        logger.info("Testing navigation through obstacles...")
        simulator.test_navigation(5, 5)
        
        # Monitor for collision avoidance with visualization
        start_time = time.time()
        while time.time() - start_time < 60:  # 1 minute timeout
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return
            
            # Draw visualization
            screen.fill((240, 240, 240))
            draw_2d_robot_view(screen, simulator)
            draw_obstacles(screen, simulator)
            draw_target(screen, 5, 5, "G")
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            clock.tick(60)
            
            # Check navigation status
            status = simulator.get_simulation_status()
            robot_state = status['robot_state']
            
            if robot_state['obstacle_detected']:
                logger.info("Obstacle detected - avoidance in progress")
            
            nav_status = status['navigation_status']
            if nav_status['navigation_state'] == 'reached_goal':
                logger.info("Successfully navigated around obstacles!")
                break
            elif nav_status['navigation_state'] == 'stuck':
                logger.warning("Got stuck trying to avoid obstacles")
                break
        
        # Clean up test obstacles
        simulator.remove_test_obstacles()
        
        logger.info("Obstacle avoidance demo completed")
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    finally:
        simulator.stop()
        pygame.quit()


def draw_exploration_progress(screen, simulator):
    """Draw exploration progress information"""
    status = simulator.get_simulation_status()
    pathfinder_status = status['pathfinder_status']
    exploration_progress = pathfinder_status.get('exploration_percentage', 0)
    
    # Draw progress bar
    bar_width = 200
    bar_height = 20
    bar_x = 600
    bar_y = 50
    
    # Background
    pygame.draw.rect(screen, (100, 100, 100), (bar_x, bar_y, bar_width, bar_height))
    # Progress
    progress_width = int(bar_width * exploration_progress / 100)
    pygame.draw.rect(screen, (0, 255, 0), (bar_x, bar_y, progress_width, bar_height))
    # Border
    pygame.draw.rect(screen, (0, 0, 0), (bar_x, bar_y, bar_width, bar_height), 2)
    
    # Text
    font = pygame.font.Font(None, 24)
    text = f"Exploration: {exploration_progress:.1f}%"
    text_surface = font.render(text, True, (0, 0, 0))
    screen.blit(text_surface, (bar_x, bar_y - 25))


def draw_obstacles(screen, simulator):
    """Draw obstacles on the 2D view"""
    scale = 20
    center_x, center_y = 400, 300
    
    # Draw known obstacles (these are the ones we added in the demo)
    obstacles = [
        (2, 2, (255, 0, 0)),    # Red cube
        (-2, -2, (0, 255, 0)),  # Green cube
        (0, 3, (0, 0, 255)),    # Blue cylinder
    ]
    
    for x, y, color in obstacles:
        screen_x = center_x + x * scale
        screen_y = center_y - y * scale
        
        # Draw obstacle as a rectangle
        obstacle_size = 10
        rect = pygame.Rect(screen_x - obstacle_size, screen_y - obstacle_size, 
                          obstacle_size * 2, obstacle_size * 2)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 2)


def draw_ui_overlay(screen, simulator):
    """Draws a UI overlay with robot state and navigation info."""
    # Get state info
    status = simulator.get_simulation_status()
    robot_state = status['robot_state']
    nav_status = status['navigation_status']
    battery = robot_state.get('battery', 0)
    pos = robot_state.get('position', {})
    mode = robot_state.get('mode', 'unknown')
    obstacle = robot_state.get('obstacle_detected', False)
    nav_state = nav_status.get('state', 'unknown')
    goal = nav_status.get('goal', {})
    path_progress = nav_status.get('path_progress', {})
    
    # Prepare text
    lines = [
        f"Mode: {mode}",
        f"Position: x={pos.get('x', 0):.1f}, y={pos.get('y', 0):.1f}, θ={pos.get('theta', 0):.1f}°",
        f"Battery: {battery:.1f}%",
        f"Obstacle: {'YES' if obstacle else 'No'}",
        f"Nav State: {nav_state}",
        f"Goal: x={goal.get('x', None)}, y={goal.get('y', None)}",
        f"Path: {path_progress.get('current_index', 0)}/{path_progress.get('total_waypoints', 0)}",
    ]
    
    # Draw background
    overlay_rect = pygame.Rect(10, 10, 350, 25 * len(lines) + 20)
    pygame.draw.rect(screen, (30, 30, 30), overlay_rect, border_radius=8)
    pygame.draw.rect(screen, (200, 200, 200), overlay_rect, 2, border_radius=8)
    
    # Draw text
    font = pygame.font.Font(None, 28)
    for i, line in enumerate(lines):
        text_surface = font.render(line, True, (255, 255, 255))
        screen.blit(text_surface, (20, 20 + i * 25))


def draw_2d_robot_view(screen, simulator):
    """Draw a 2D top-down view of the robot and environment"""
    # Get robot position
    status = simulator.get_simulation_status()
    robot_pos = status['robot_position']
    x, y = robot_pos['x'], robot_pos['z']  # Use z as y for 2D view
    angle = robot_pos['orientation']
    
    # Scale and offset for screen coordinates
    scale = 20  # pixels per meter
    center_x, center_y = 400, 300
    screen_x = center_x + x * scale
    screen_y = center_y - y * scale  # Invert Y for screen coordinates
    
    # Draw grid
    for i in range(-20, 21):
        grid_x = center_x + i * scale
        pygame.draw.line(screen, (200, 200, 200), (grid_x, 0), (grid_x, 600))
        grid_y = center_y + i * scale
        pygame.draw.line(screen, (200, 200, 200), (0, grid_y), (800, grid_y))
    
    # Draw robot as a triangle
    robot_size = 15
    points = [
        (screen_x + robot_size * math.cos(angle), 
         screen_y - robot_size * math.sin(angle)),
        (screen_x + robot_size * math.cos(angle + 2.6), 
         screen_y - robot_size * math.sin(angle + 2.6)),
        (screen_x + robot_size * math.cos(angle - 2.6), 
         screen_y - robot_size * math.sin(angle - 2.6))
    ]
    pygame.draw.polygon(screen, (100, 150, 255), points)
    pygame.draw.polygon(screen, (0, 0, 0), points, 2)
    
    # Draw direction indicator
    end_x = screen_x + robot_size * 1.5 * math.cos(angle)
    end_y = screen_y - robot_size * 1.5 * math.sin(angle)
    pygame.draw.line(screen, (255, 0, 0), (screen_x, screen_y), (end_x, end_y), 3)


def demo_interactive():
    """Interactive demo with user control"""
    logger.info("=== Interactive Demo ===")
    logger.info("Controls:")
    logger.info("  W/A/S/D - Move camera")
    logger.info("  Mouse - Look around")
    logger.info("  Space/Shift - Move up/down")
    logger.info("  ESC - Exit")
    logger.info("")
    logger.info("Robot will explore autonomously while you observe")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create simulator
    sim_config = SimulationConfig(
        simulation_fps=60,
        physics_fps=100,
        enable_physics=True,
        enable_collision=True,
        enable_sensors=True
    )
    
    simulator = RobotSimulator(config, sim_config)
    
    try:
        # Start simulation
        simulator.start()
        
        # Set robot to autonomous mode and start exploration
        simulator.robot_state.set_mode(RobotMode.AUTONOMOUS)
        simulator.test_exploration()
        
        # Run the 3D simulation with UI overlay
        pygame.font.init()
        screen = pygame.display.get_surface()
        running = True
        while running:
            simulator.world.run_simulation(sim_config.simulation_fps)
            # Draw UI overlay after each frame
            draw_ui_overlay(screen, simulator)
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    finally:
        simulator.stop()


def main():
    """Main demo function"""
    logger.info("Smart Robot 3D Simulation Demo")
    logger.info("=" * 40)
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1].lower()
    else:
        print("Available demos:")
        print("  1. basic    - Basic movement testing")
        print("  2. nav      - Autonomous navigation")
        print("  3. explore  - Autonomous exploration")
        print("  4. obstacle - Obstacle avoidance")
        print("  5. interactive - Interactive 3D demo")
        print()
        demo_type = input("Enter demo type (or press Enter for interactive): ").strip().lower()
    
    if not demo_type:
        demo_type = "interactive"
    
    try:
        if demo_type == "basic":
            demo_basic_movement()
        elif demo_type == "nav":
            demo_navigation()
        elif demo_type == "explore":
            demo_exploration()
        elif demo_type == "obstacle":
            demo_obstacle_avoidance()
        elif demo_type == "interactive":
            demo_interactive()
        else:
            logger.error(f"Unknown demo type: {demo_type}")
            logger.info("Available demos: basic, nav, explore, obstacle, interactive")
    
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 