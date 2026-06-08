import math
import time
import asyncio
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional
import numpy as np
from concurrent.futures import ThreadPoolExecutor

import ollama
from loguru import logger

from .robot_state import SensorData, Position

class RobotMind:
    """Main robot mind class - Asynchronous implementation for non-blocking operations"""
    def __init__(self, config: dict):
        self.config = config
        self.client = ollama.Client()
        self.model_name = config.get('robot', {}).get('model', 'llama3.1:8b')
        
        # Task and goal tracking
        self.current_task: Optional[str] = None
        self.current_goal: Optional[Position] = None
        
        # Thread pool executor for running blocking operations asynchronously
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="robo_mind")
        
        # Lock for thread-safe operations (threading.Lock for sync, asyncio.Lock created lazily for async)
        self._thread_lock = threading.Lock()
        self._async_lock = None  # Will be created lazily in async context
        
    def set_task(self, task: str, goal: Optional[Position] = None):
        """Assign a task to the robot with optional navigation goal"""
        self.current_task = task
        self.current_goal = goal
        if goal and hasattr(self, 'robot_state'):
            self.robot_state.target_position = goal
        logger.info(f"Task assigned: {task}" + (f" | Goal: ({goal.x:.2f}, {goal.y:.2f})" if goal else ""))
        
    async def think(self, sensor_data: SensorData, task: Optional[str] = None):
        """
        Main robot thinking loop (async, non-blocking).
        Uses Ollama LLM for reasoning/decision making using sensor data and current position.
        
        Args:
            sensor_data: Current sensor readings
            task: Optional task description (overrides current_task if provided)
            
        Returns:
            dict: Reasoning result with action, reason, and optional parameters
        """
        # Create async lock lazily if needed
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        
        async with self._async_lock:
            # Update robot state with new sensor data (this already updates status internally)
            # Run in executor to avoid blocking if update_sensors is CPU-intensive
            await asyncio.to_thread(self.robot_state.update_sensors, sensor_data)
            
            # Use provided task or current task
            active_task = task if task is not None else self.current_task
            
            # Get comprehensive status summary (run in executor if needed)
            status_summary = await asyncio.to_thread(self.robot_state.get_status_summary)
            
            # Gather relevant robot state info for LLM
            current_pos = self.robot_state.position
            sensors = self.robot_state.sensors
            
            # Build equipment capabilities list
            equipment = [
                "Motor Control: move_forward, move_backward, turn_left, turn_right, stop, differential_drive",
                "Sensors: ultrasonic (front/left/right), infrared (left/right), bumpers (left/right)",
                "Navigation: pathfinding, obstacle avoidance, position tracking"
            ]
            
            # Build situation awareness
            situation_parts = []
            situation_parts.append(f"Safe to Move: {status_summary['safe_to_move']}")
            situation_parts.append(f"Obstacle Detected: {status_summary['obstacle_detected']}")
            situation_parts.append(f"Emergency Stop: {status_summary['emergency_stop']}")
            
            if self.robot_state.target_position:
                target = self.robot_state.target_position
                distance = current_pos.distance_to(target)
                situation_parts.append(f"Target Position: ({target.x:.2f}, {target.y:.2f}) | Distance: {distance:.2f} cm")
            
            if hasattr(self.robot_state, 'current_path') and self.robot_state.current_path:
                situation_parts.append(f"Current Path: {len(self.robot_state.current_path)} waypoints")
            
            # Check for navigation state if autonomous_controller is available
            nav_state = None
            if hasattr(self, 'autonomous_controller') and hasattr(self.autonomous_controller, 'nav_state'):
                nav_state = self.autonomous_controller.nav_state
            
            # Prepare comprehensive prompt for LLM
            llm_prompt = (
                f"You are the robot's brain. Analyze the situation and decide on the best action.\n\n"
            )
            
            # Add task/goal context
            if active_task:
                llm_prompt += f"Current Task: {active_task}\n"
            if self.current_goal:
                llm_prompt += f"Navigation Goal: ({self.current_goal.x:.2f}, {self.current_goal.y:.2f})\n"
            if nav_state:
                llm_prompt += f"Navigation State: {nav_state.value if hasattr(nav_state, 'value') else nav_state}\n"
            
            llm_prompt += (
                f"\nAvailable Equipment:\n" + "\n".join(f"  - {eq}" for eq in equipment) + "\n\n"
                f"Current Situation:\n" + "\n".join(f"  - {s}" for s in situation_parts) + "\n\n"
                f"Sensor Readings:\n"
                f"  - Ultrasonic Front: {sensors.ultrasonic_front:.1f} cm\n"
                f"  - Ultrasonic Left: {sensors.ultrasonic_left:.1f} cm\n"
                f"  - Ultrasonic Right: {sensors.ultrasonic_right:.1f} cm\n"
                f"  - Infrared Left: {sensors.infrared_left}\n"
                f"  - Infrared Right: {sensors.infrared_right}\n"
                f"  - Bumper Left: {sensors.bumper_left}\n"
                f"  - Bumper Right: {sensors.bumper_right}\n\n"
                f"Position & Status:\n"
                f"  - Position: (x={current_pos.x:.2f}, y={current_pos.y:.2f}, theta={math.degrees(current_pos.theta):.1f}°)\n"
                f"  - Battery Level: {status_summary['battery']:.1f}%\n"
                f"  - System Status: {status_summary['status']}\n"
                f"  - Operation Mode: {status_summary['mode']}\n"
                f"  - Total Distance Traveled: {status_summary['total_distance']:.2f} cm\n"
                f"  - Operation Time: {status_summary['operation_time']:.1f} s\n\n"
                f"Decision Context:\n"
                f"  Based on the task, current situation, sensor data, and available equipment, decide the robot's next action.\n"
                f"  Consider safety first (obstacles, emergency stops), then task completion, then efficiency.\n\n"
                f"Respond in JSON format with:\n"
                f"  - action: one of [move_forward, move_backward, turn_left, turn_right, stop, differential_drive]\n"
                f"  - reason: brief explanation of your decision\n"
                f"  - parameters: optional dict with action-specific parameters (e.g., {{\"speed\": 50, \"angle\": 30}})\n"
                f"\nExample response: {{\"action\": \"move_forward\", \"reason\": \"path clear, proceeding to goal\", \"parameters\": {{\"speed\": 50}}}}\n"
            )

        # Query Ollama model asynchronously (run blocking call in executor)
        try:
            def _query_ollama():
                """Blocking Ollama query to be run in executor"""
                return self.client.chat(model=self.model_name, messages=[
                    {"role": "system", "content": "You are a helpful robotics control AI."},
                    {"role": "user", "content": llm_prompt}
                ])
            
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor, _query_ollama
            )
            llm_output = response['message']['content']
            logger.debug(f"Ollama output: {llm_output}")
        except Exception as e:
            logger.error(f"Ollama inference error: {e}")
            llm_output = '{"action":"stop","reason":"llm_error"}'

        # Parse Ollama output (this is fast, no need for executor)
        import json
        try:
            reasoning_result = json.loads(llm_output)
        except Exception as e:
            logger.warning(f"Failed to parse LLM output, using fallback. Output: {llm_output}")
            reasoning_result = {"action": "stop", "reason": "bad_llm_output"}

        return reasoning_result
    
    def think_sync(self, sensor_data: SensorData, task: Optional[str] = None):
        """
        Synchronous wrapper for think() method.
        Useful for backward compatibility or when running in non-async contexts.
        
        Args:
            sensor_data: Current sensor readings
            task: Optional task description (overrides current_task if provided)
            
        Returns:
            dict: Reasoning result with action, reason, and optional parameters
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.think(sensor_data, task))
    async def do_action(self, action: str, thought: str, reasoning_result: Optional[dict] = None):
        """
        Execute an action based on a thought/LLM output (async, non-blocking).
        Actions are routed to the appropriate hardware controllers per @src/hardware interfaces.
        
        Args:
            action: Action to execute
            thought: Reasoning/explanation for the action
            reasoning_result: Optional full reasoning result dict containing parameters
            
        Returns:
            bool: True if action executed successfully, False otherwise
        """
        logger.info(f"Executing action: {action} | Thought: {thought}")
        
        # Extract parameters if available
        parameters = {}
        if reasoning_result and 'parameters' in reasoning_result:
            parameters = reasoning_result['parameters']
        
        # Validate action before execution
        valid_actions = ["move_forward", "move_backward", "turn_left", "turn_right", 
                        "stop", "differential_drive"]
        if action not in valid_actions:
            logger.warning(f"Unknown action: {action}. Valid actions: {valid_actions}")
            action = "stop"  # Default to stop for safety
        
        # Check safety before executing movement actions
        if action in ["move_forward", "move_backward", "turn_left", "turn_right", "differential_drive"]:
            if not self.robot_state.safe_to_move:
                logger.warning(f"Action {action} blocked: not safe to move (obstacle detected or emergency stop)")
                await asyncio.to_thread(self.motor_controller.stop)
                return False
            if self.robot_state.emergency_stop:
                logger.warning(f"Action {action} blocked: emergency stop active")
                await asyncio.to_thread(self.motor_controller.stop)
                return False
        
        try:
            # Motor actions with parameter support (run in executor to avoid blocking)
            if action == "move_forward":
                speed = parameters.get('speed', 50.0)
                speed = max(0, min(100, speed))  # Clamp to valid range
                await asyncio.to_thread(self.motor_controller.move_forward, speed)
                
            elif action == "move_backward":
                speed = parameters.get('speed', 50.0)
                speed = max(0, min(100, speed))
                await asyncio.to_thread(self.motor_controller.move_backward, speed)
                
            elif action == "turn_left":
                # Support both 'speed' and 'angle' parameters
                speed = parameters.get('speed', 30.0)
                angle = parameters.get('angle', None)
                speed = max(0, min(100, speed))
                await asyncio.to_thread(self.motor_controller.turn_left, speed)
                # Note: angle parameter would require additional implementation for precise turning
                if angle:
                    logger.debug(f"Turn left angle requested: {angle}° (using speed-based turn)")
                    
            elif action == "turn_right":
                speed = parameters.get('speed', 30.0)
                angle = parameters.get('angle', None)
                speed = max(0, min(100, speed))
                await asyncio.to_thread(self.motor_controller.turn_right, speed)
                if angle:
                    logger.debug(f"Turn right angle requested: {angle}° (using speed-based turn)")
                    
            elif action == "stop":
                await asyncio.to_thread(self.motor_controller.stop)
                
            elif action == "differential_drive":
                linear_speed = parameters.get('linear_speed', 0.0)
                angular_speed = parameters.get('angular_speed', 0.0)
                # Clamp speeds to valid range
                linear_speed = max(-100, min(100, linear_speed))
                angular_speed = max(-100, min(100, angular_speed))
                await asyncio.to_thread(self.motor_controller.differential_drive, linear_speed, angular_speed)
                
            else:
                logger.error(f"Action {action} not implemented")
                return False

            # After movement or action, update sensors (run in executor)
            if hasattr(self, 'sensor_manager') and self.sensor_manager:
                if hasattr(self.sensor_manager, 'collect'):
                    await asyncio.to_thread(self.sensor_manager.collect)
            
            # Optionally, recalculate path if needed (if path is managed in robot_state)
            if hasattr(self.robot_state, "current_path") and hasattr(self, 'pathfinder') and self.pathfinder:
                # Note: pathfinder.update_path may not exist, so we check with hasattr
                if hasattr(self.pathfinder, 'update_path'):
                    await asyncio.to_thread(self.pathfinder.update_path, self.robot_state.current_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            # Emergency stop on error
            try:
                await asyncio.to_thread(self.motor_controller.stop)
            except:
                pass
            return False
    
    def do_action_sync(self, action: str, thought: str, reasoning_result: Optional[dict] = None):
        """
        Synchronous wrapper for do_action() method.
        Useful for backward compatibility or when running in non-async contexts.
        
        Args:
            action: Action to execute
            thought: Reasoning/explanation for the action
            reasoning_result: Optional full reasoning result dict containing parameters
            
        Returns:
            bool: True if action executed successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.do_action(action, thought, reasoning_result))
    
    def shutdown(self):
        """Clean up resources, shutdown executor"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)
    # def get_status(self) -> RobotStatus:
    #     """Get current robot status"""
    #     return self.robot_state.status
    
def main():
    """Test RobotMind .think() - uses sync wrapper for compatibility"""
    config = {
        'robot': {
            'name': 'Robot',
            'model': 'llama3.1:8b'
        }
    }
    sensor_data = SensorData(
        ultrasonic_front=10.0,
        ultrasonic_left=10.0,
        ultrasonic_right=10.0,
        infrared_left=False,
        infrared_right=False,
        bumper_left=False,
        bumper_right=False
    )
    robot_mind = RobotMind(config)
    # Use sync wrapper for testing
    result = robot_mind.think_sync(sensor_data)
    print("think() output:", result)
    
if __name__ == "__main__":
    main()