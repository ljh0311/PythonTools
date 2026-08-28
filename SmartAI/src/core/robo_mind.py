import json
import math
import re
import time
import asyncio
import threading
from typing import Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

import ollama
from loguru import logger

from .robot_state import SensorData, Position
from .blocked_path_handler import BlockedPathHandler
from .notification_service import NotificationService
from .vision_path_handler import VisionPathHandler
from .proximity_context import format_proximity_for_llm, proximity_rule_decide

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
        self.notifier = NotificationService(config)
        self.blocked_path_handler = BlockedPathHandler(config, self.notifier)
        self.vision_path_handler = VisionPathHandler()
        self.vision_fusion = None
        self.context = None
        self.last_camera_frame = None
        self._ollama_available = False
        self._ollama_last_error: Optional[str] = None
        self._probe_ollama()
        
    def _probe_ollama(self) -> bool:
        """Check whether Ollama is reachable and the configured model exists."""
        try:
            listed = self.client.list()
            raw_names = []
            for m in getattr(listed, "models", []) or []:
                name = getattr(m, "model", None)
                if not name and isinstance(m, dict):
                    name = m.get("model") or m.get("name")
                if name:
                    raw_names.append(name)
            self._ollama_available = any(
                n == self.model_name or n.startswith(self.model_name.split(":")[0])
                for n in raw_names
            )
            if self._ollama_available:
                self._ollama_last_error = None
                logger.info(f"Ollama online — using model '{self.model_name}'")
            else:
                self._ollama_last_error = (
                    f"model '{self.model_name}' not found (have: {raw_names})"
                )
                logger.warning(f"Ollama reachable but {self._ollama_last_error}")
            return self._ollama_available
        except Exception as e:
            self._ollama_available = False
            self._ollama_last_error = str(e)
            logger.warning(f"Ollama offline: {e}")
            return False

    @staticmethod
    def _parse_llm_json(text: str) -> dict:
        """Parse JSON from LLM output, tolerating markdown fences."""
        text = text.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if fence:
            text = fence.group(1).strip()
        return json.loads(text)

    def set_task(self, task: str, goal: Optional[Position] = None):
        """Assign a task to the robot with optional navigation goal"""
        self.current_task = task
        self.current_goal = goal
        if goal and hasattr(self, 'robot_state'):
            self.robot_state.target_position = goal
        logger.info(f"Task assigned: {task}" + (f" | Goal: ({goal.x:.2f}, {goal.y:.2f})" if goal else ""))
        
    async def think(
        self,
        sensor_data: SensorData,
        task: Optional[str] = None,
        proximity_ctx: Optional[dict] = None,
    ):
        """
        Main robot thinking loop (async, non-blocking).
        Uses Ollama LLM for reasoning/decision making using sensor data and current position.
        
        Args:
            sensor_data: Current sensor readings
            task: Optional task description (overrides current_task if provided)
            proximity_ctx: Optional proximity dict (front_m/left_m/right_m, vision labels, …)
            
        Returns:
            dict: Reasoning result with action, reason, and optional parameters
        """
        # Create async lock lazily if needed
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        
        async with self._async_lock:
            if hasattr(self, "robot_state") and self.robot_state is not None:
                await asyncio.to_thread(self.robot_state.update_sensors, sensor_data)
            
            active_task = task if task is not None else self.current_task
            is_proximity = bool(proximity_ctx) or (
                isinstance(active_task, str) and "proximity" in active_task.lower()
            )

            vision_ctx = self.vision_path_handler.process_vision(self)
            frame_available = self.vision_path_handler.get_camera_frame(self) is not None
            has_vision_input = frame_available or vision_ctx.action != "clear"
            if (
                not is_proximity
                and has_vision_input
                and self.vision_path_handler.should_intercept(vision_ctx)
            ):
                return self.vision_path_handler.handle_vision_obstacle(vision_ctx)
            
            # Proximity reaction: prefer dedicated rules / prompt over blocked-path path
            if is_proximity and proximity_ctx:
                if not self._ollama_available:
                    self._probe_ollama()
                if not self._ollama_available:
                    logger.info("Decision source: proximity rule fallback (Ollama unavailable)")
                    return self._rule_based_fallback(
                        sensor_data, active_task, vision_ctx, proximity_ctx
                    )
                llm_prompt = (
                    "You are the robot's brain handling a proximity reaction.\n"
                    f"Current Task: {active_task}\n"
                    f"{format_proximity_for_llm(proximity_ctx)}\n"
                )
            else:
                nav_state = None
                replan_failures = 0
                if hasattr(self, 'autonomous_controller') and self.autonomous_controller:
                    nav = self.autonomous_controller
                    nav_state = nav.nav_state.value if hasattr(nav.nav_state, 'value') else str(nav.nav_state)
                    replan_failures = getattr(nav, 'replan_attempts', 0)
                if not has_vision_input and self.blocked_path_handler.detect_blocked_path(
                    sensor_data, nav_state, replan_failures, active_task
                ):
                    logger.info("Blocked-path rules triggered (no vision input)")
                    return self.blocked_path_handler.handle_blocked_path(
                        sensor_data, active_task, nav_state, replan_failures
                    )
                
                status_summary = await asyncio.to_thread(self.robot_state.get_status_summary)
                current_pos = self.robot_state.position
                sensors = self.robot_state.sensors
                
                tool_list = []
                if hasattr(self, 'tool_registry') and self.tool_registry:
                    tool_list = self.tool_registry.get_tool_names()
                equipment = [
                    "High-level tools (use these, NOT motor PWM): " + ", ".join(tool_list) if tool_list else "navigate_to, go_to_kitchen, return_to_home, start_exploration, stop, get_status, scan_surroundings",
                    "Sensors: ultrasonic (front/left/right), infrared, bumpers, camera vision fusion",
                    "Navigation: pathfinding, obstacle avoidance, vision-directed reroute",
                ]
                
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
                
                nav_state = None
                if hasattr(self, 'autonomous_controller') and hasattr(self.autonomous_controller, 'nav_state'):
                    nav_state = self.autonomous_controller.nav_state
                
                llm_prompt = (
                    f"You are the robot's brain. Analyze the situation and decide on the best action.\n\n"
                )
                
                if active_task:
                    llm_prompt += f"Current Task: {active_task}\n"
                if self.current_goal:
                    llm_prompt += f"Navigation Goal: ({self.current_goal.x:.2f}, {self.current_goal.y:.2f})\n"
                if nav_state:
                    llm_prompt += f"Navigation State: {nav_state.value if hasattr(nav_state, 'value') else nav_state}\n"

                vision_summary = self.vision_path_handler.format_for_llm(vision_ctx)
                if vision_summary:
                    llm_prompt += f"\n{vision_summary}\n"
                
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
                    f"  - tool: one of [{', '.join(tool_list) if tool_list else 'navigate_to, stop, get_status'}]\n"
                    f"  - args: optional dict of tool arguments (e.g. {{\"x\": 500, \"y\": 400}})\n"
                    f"  - reason: brief explanation\n"
                    f"\nDo NOT output raw motor commands. Use tools only.\n"
                    f"Example: {{\"tool\": \"navigate_to\", \"args\": {{\"x\": 500, \"y\": 400}}, \"reason\": \"heading to goal\"}}\n"
                )

        # Query Ollama model asynchronously (run blocking call in executor)
        if not self._ollama_available:
            self._probe_ollama()
        if not self._ollama_available:
            logger.info(
                f"Decision source: rule-based fallback "
                f"(Ollama unavailable: {self._ollama_last_error})"
            )
            return self._rule_based_fallback(sensor_data, task, vision_ctx, proximity_ctx)

        try:
            def _query_ollama():
                """Blocking Ollama query to be run in executor"""
                return self.client.chat(model=self.model_name, messages=[
                    {"role": "system", "content": "You are a helpful robotics control AI. Respond with JSON only."},
                    {"role": "user", "content": llm_prompt}
                ])
            
            logger.info(f"Decision source: Ollama model '{self.model_name}'")
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor, _query_ollama
            )
            llm_output = response['message']['content']
            logger.debug(f"Ollama output: {llm_output}")
        except Exception as e:
            logger.error(f"Ollama inference error: {e}")
            self._ollama_available = False
            self._ollama_last_error = str(e)
            logger.info("Decision source: rule-based fallback (Ollama inference failed)")
            return self._rule_based_fallback(sensor_data, task, vision_ctx, proximity_ctx)

        try:
            reasoning_result = self._parse_llm_json(llm_output)
            if "tool" not in reasoning_result and "action" in reasoning_result:
                reasoning_result["tool"] = reasoning_result.get("action")
            reasoning_result["source"] = "ollama"
        except Exception:
            logger.warning(f"Failed to parse LLM output, using fallback. Output: {llm_output}")
            logger.info("Decision source: rule-based fallback (invalid LLM JSON)")
            return self._rule_based_fallback(sensor_data, task, vision_ctx, proximity_ctx)

        return reasoning_result

    def _rule_based_fallback(
        self,
        sensor_data: SensorData,
        task: Optional[str] = None,
        vision_ctx=None,
        proximity_ctx: Optional[dict] = None,
    ) -> dict:
        """Offline demo fallback when Ollama is unavailable or output is invalid."""
        active_task = task if task is not None else self.current_task

        if proximity_ctx:
            pos = getattr(getattr(self, "robot_state", None), "position", None)
            return proximity_rule_decide(proximity_ctx, position=pos)

        if vision_ctx is None:
            vision_ctx = self.vision_path_handler.process_vision(self)
        if self.vision_path_handler.should_intercept(vision_ctx):
            result = self.vision_path_handler.handle_vision_obstacle(vision_ctx)
            result["source"] = "vision_fusion_fallback"
            return result

        nav_state = None
        replan_failures = 0
        if hasattr(self, 'autonomous_controller') and self.autonomous_controller:
            nav = self.autonomous_controller
            nav_state = nav.nav_state.value if hasattr(nav.nav_state, 'value') else str(nav.nav_state)
            replan_failures = getattr(nav, 'replan_attempts', 0)

        if self.blocked_path_handler.detect_blocked_path(
            sensor_data, nav_state, replan_failures, active_task
        ):
            return self.blocked_path_handler.handle_blocked_path(
                sensor_data, active_task, nav_state, replan_failures
            )

        if sensor_data.ultrasonic_front < 20.0 or sensor_data.bumper_left or sensor_data.bumper_right:
            return {"tool": "stop", "args": {}, "reason": "Obstacle too close — stopping for safety", "source": "rule_based_fallback"}

        if sensor_data.ultrasonic_front < 40.0:
            return {"tool": "scan_surroundings", "args": {}, "reason": "Obstacle ahead — scanning before proceeding", "source": "rule_based_fallback"}

        if active_task and "navigate" in active_task.lower():
            return {"tool": "get_status", "args": {}, "reason": "Continuing navigation task — checking status", "source": "rule_based_fallback"}

        return {"tool": "get_status", "args": {}, "reason": "Default safe status check (LLM offline)", "source": "rule_based_fallback"}
    
    def think_sync(
        self,
        sensor_data: SensorData,
        task: Optional[str] = None,
        proximity_ctx: Optional[dict] = None,
        timeout: Optional[float] = None,
    ):
        """
        Synchronous wrapper for think() method.
        
        Args:
            sensor_data: Current sensor readings
            task: Optional task description
            proximity_ctx: Optional proximity context dict
            timeout: Optional seconds; on expiry returns busy skip dict
            
        Returns:
            dict: Reasoning result with tool, reason, and optional parameters
        """
        async def _run():
            if timeout is None:
                return await self.think(sensor_data, task, proximity_ctx)
            return await asyncio.wait_for(
                self.think(sensor_data, task, proximity_ctx), timeout=timeout
            )

        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            if loop.is_running():
                fut = self.executor.submit(lambda: asyncio.run(_run()))
                return fut.result(timeout=(timeout + 0.5) if timeout else None)
            return loop.run_until_complete(_run())
        except asyncio.TimeoutError:
            logger.warning(f"think_sync timed out after {timeout}s — skipping")
            return {
                "tool": None,
                "args": {},
                "reason": "think timeout",
                "skipped": True,
                "source": "timeout",
            }
        except FuturesTimeoutError:
            logger.warning(f"think_sync executor timed out after {timeout}s — skipping")
            return {
                "tool": None,
                "args": {},
                "reason": "think timeout",
                "skipped": True,
                "source": "timeout",
            }
    async def do_action(self, action: str, thought: str, reasoning_result: Optional[dict] = None):
        """
        Legacy action executor — redirects to TaskBoss tools when available.
        Direct motor PWM is blocked when tool_registry is wired.
        """
        if hasattr(self, 'task_boss') and self.task_boss and reasoning_result:
            tool = reasoning_result.get("tool")
            if tool:
                args = reasoning_result.get("args", {})
                return self.task_boss.execute_tool(tool, **args)
            action = reasoning_result.get("action", action)

        logger.warning(
            f"Direct motor action '{action}' blocked — use TaskBoss tools. Stopping for safety."
        )
        if hasattr(self, 'motor_controller') and self.motor_controller:
            await asyncio.to_thread(self.motor_controller.stop_motors)
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