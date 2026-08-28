#!/usr/bin/env python3
"""
Smart Robot System - Main Application
Autonomous house navigation robot with comprehensive control interface
"""

import sys
import os
import yaml
import signal
import threading
import time
from loguru import logger
import traceback

# Flask imports for web server
from flask import Flask, render_template, request, jsonify, send_from_directory
import webbrowser
import socket

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.robot_state import RobotState, RobotMode
from src.hardware.factory import create_hardware_transport
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager
from src.navigation.pathfinder import Pathfinder
from src.navigation.autonomous_controller import AutonomousController
from src.gui.robot_gui import RobotGUI
from src.vision.vision_fusion import VisionFusion
from src.integrations.bridge import SmartHomeBridge
from src.core.task_boss import TaskBoss
from src.plugins.defaults import register_default_plugins
from src.plugins.analysis.scene_analysis import SceneAnalysisPlugin
from src.plugins import registry as plugin_registry

# Add a global exception hook to log uncaught exceptions
def global_exception_hook(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Allow keyboard interrupts to exit quietly
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception:")
    logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
    print("A fatal error occurred. See logs/robot_system.log for details.")
    sys.exit(2)

sys.excepthook = global_exception_hook

class SmartRobotSystem:
    """Main robot system coordinator"""
    
    def __init__(self, config_path: str = "config/robot_config.yaml"):
        self.config_path = config_path
        self.config = None
        self.running = False
        
        # System components
        self.robot_state = None
        self.hardware_transport = None
        self.motor_controller = None
        self.sensor_manager = None
        self.pathfinder = None
        self.autonomous_controller = None
        self.vision_fusion = None
        self.smart_home = None
        self.task_boss = None
        self.gui = None
        self._plugin_context = {}
        
        # Flask web server
        self.flask_app = None
        self.web_server_thread = None
        self.web_port = 5000
        self.web_host = '0.0.0.0'  # Allow external connections
        
        # Setup logging
        self._setup_logging()
        
        # Load configuration
        self._load_config()
        
        # Initialize system
        self._initialize_system()
        
        # Setup Flask web server
        self._setup_web_server()
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_logging(self):
        """Setup logging configuration"""
        logger.remove()  # Remove default handler
        
        # Add console handler
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level="INFO"
        )
        
        # Add file handler
        logger.add(
            "logs/robot_system.log",
            rotation="10 MB",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level="DEBUG"
        )
        
        logger.info("Smart Robot System starting up...")
    
    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            logger.info(f"Configuration loaded from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            sys.exit(1)
    
    def _initialize_system(self):
        """Initialize all system components"""
        logger.info("Initializing robot system components...")
        
        # Define the init function for the GUI with access to self.config
        def init_all_components(config):
            """Initialize all components with the given config"""
            register_default_plugins()
            robot_state = RobotState(config)
            transport = create_hardware_transport(config)
            motor_controller = transport.motors.raw
            sensor_manager = transport.sensors.raw
            pathfinder = Pathfinder(config)
            vision_fusion = VisionFusion(config, pathfinder) if config.get("vision", {}).get("fusion_enabled", True) else None
            autonomous_controller = AutonomousController(
                robot_state, motor_controller, sensor_manager, pathfinder, vision_fusion
            )
            smart_home = SmartHomeBridge(config)
            ctx = {
                "config": config,
                "robot_state": robot_state,
                "motor_controller": motor_controller,
                "sensor_manager": sensor_manager,
                "pathfinder": pathfinder,
                "autonomous_controller": autonomous_controller,
                "vision_fusion": vision_fusion,
                "hardware": transport,
            }
            task_boss = TaskBoss(config, ctx, smart_home)
            ctx["task_boss"] = task_boss
            autonomous_controller.task_boss = task_boss
            scene_plugin = plugin_registry.get_analysis("scene_analysis")
            if scene_plugin and vision_fusion:
                scene_plugin.bind_vision_fusion(vision_fusion)
            ctx["scene_analysis"] = scene_plugin
            autonomous_controller._smartai_context = ctx
            ctx["smart_home"] = smart_home
            return robot_state, motor_controller, sensor_manager, pathfinder, autonomous_controller
        
        try:
            self.gui = RobotGUI.launch_with_loading(init_all_components, self.config)
            self.robot_state = self.gui.robot_state
            self.motor_controller = self.gui.motor_controller
            self.sensor_manager = self.gui.sensor_manager
            self.pathfinder = self.gui.pathfinder
            self.autonomous_controller = self.gui.autonomous_controller
            ctx = getattr(self.autonomous_controller, "_smartai_context", {})
            self._plugin_context = ctx
            self.hardware_transport = ctx.get("hardware")
            self.vision_fusion = ctx.get("vision_fusion")
            self.task_boss = ctx.get("task_boss")
            self.smart_home = ctx.get("smart_home")
            if self.vision_fusion:
                self.gui.vision_fusion = self.vision_fusion
            if self.task_boss:
                self.gui.task_boss = self.task_boss
            logger.info("All system components initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            print("A critical error occurred during initialization. See logs/robot_system.log for details.")
            sys.exit(1)
    
    def _setup_web_server(self):
        """Setup Flask web server with API routes"""
        try:
            self.flask_app = Flask(__name__)
            
            # Create templates directory if it doesn't exist
            os.makedirs('templates', exist_ok=True)
            os.makedirs('static', exist_ok=True)
            
            @self.flask_app.route('/')
            def index():
                return render_template('index.html')
            
            @self.flask_app.route('/api/status', methods=['GET'])
            def get_status():
                """Get current robot system status"""
                try:
                    return jsonify(self.get_system_status())
                except Exception as e:
                    logger.error(f"/api/status failed: {e}")
                    logger.error(traceback.format_exc())
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/move', methods=['POST'])
            def move_robot():
                """Move robot with specified direction and speed"""
                try:
                    data = request.get_json()
                    direction = data.get('direction', 'stop')
                    speed = data.get('speed', 50.0)
                    
                    if direction == 'forward':
                        self.motor_controller.move_forward(speed)
                    elif direction == 'backward':
                        self.motor_controller.move_backward(speed)
                    elif direction == 'left':
                        self.motor_controller.turn_left(speed)
                    elif direction == 'right':
                        self.motor_controller.turn_right(speed)
                    elif direction == 'stop':
                        self.motor_controller.stop_motors()
                    else:
                        return jsonify({'error': 'Invalid direction'}), 400
                    
                    return jsonify({'status': 'success', 'direction': direction, 'speed': speed})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/mode', methods=['POST'])
            def set_mode():
                """Set robot operation mode"""
                try:
                    data = request.get_json()
                    mode = data.get('mode', 'idle')
                    
                    robot_mode = RobotMode(mode)
                    self.robot_state.set_mode(robot_mode)
                    
                    return jsonify({'status': 'success', 'mode': mode})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/navigate', methods=['POST'])
            def navigate_to():
                """Navigate to target position"""
                try:
                    data = request.get_json()
                    x = float(data.get('x', 0))
                    y = float(data.get('y', 0))
                    
                    success = self.autonomous_controller.navigate_to(x, y)
                    
                    if success:
                        return jsonify({'status': 'success', 'target': {'x': x, 'y': y}})
                    else:
                        return jsonify({'error': 'Navigation already in progress'}), 400
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/explore', methods=['POST'])
            def start_exploration():
                """Start autonomous exploration"""
                try:
                    success = self.autonomous_controller.start_exploration()
                    
                    if success:
                        return jsonify({'status': 'success', 'action': 'exploration_started'})
                    else:
                        return jsonify({'error': 'Exploration already in progress'}), 400
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/stop', methods=['POST'])
            def stop_navigation():
                """Stop navigation and return to idle"""
                try:
                    self.autonomous_controller.stop()
                    self.robot_state.set_mode(RobotMode.IDLE)
                    return jsonify({'status': 'success', 'action': 'stopped'})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/emergency_stop', methods=['POST'])
            def emergency_stop():
                """Emergency stop all robot operations"""
                try:
                    self.robot_state.set_mode(RobotMode.EMERGENCY_STOP)
                    self.motor_controller.emergency_stop()
                    self.autonomous_controller.stop()
                    return jsonify({'status': 'success', 'action': 'emergency_stop'})
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/sensors', methods=['GET'])
            def get_sensors():
                """Get current sensor readings"""
                try:
                    sensor_data = self.sensor_manager.get_sensor_data()
                    return jsonify(sensor_data)
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/position', methods=['GET'])
            def get_position():
                """Get current robot position"""
                try:
                    position = self.robot_state.position
                    return jsonify({
                        'x': position.x,
                        'y': position.y,
                        'theta': position.theta
                    })
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/vision_features', methods=['GET', 'POST'])
            def vision_features():
                """Get or set vision feature states (visual odometry, dynamic obstacle, scene understanding)"""
                if not self.gui:
                    return jsonify({'error': 'GUI not initialized'}), 500
                if request.method == 'GET':
                    return jsonify({
                        'visual_odometry': getattr(self.gui, 'visual_odometry_enabled', False),
                        'dynamic_obstacle': getattr(self.gui, 'dynamic_obstacle_enabled', False),
                        'scene_understanding': getattr(self.gui, 'scene_understanding_enabled', False),
                        'camera_available': getattr(self.gui, 'camera_available', False)
                    })
                elif request.method == 'POST':
                    data = request.get_json()
                    if 'visual_odometry' in data:
                        self.gui.visual_odometry_enabled = bool(data['visual_odometry'])
                    if 'dynamic_obstacle' in data:
                        self.gui.dynamic_obstacle_enabled = bool(data['dynamic_obstacle'])
                    if 'scene_understanding' in data:
                        self.gui.scene_understanding_enabled = bool(data['scene_understanding'])
                    return jsonify({'status': 'success'})

            @self.flask_app.route('/api/camera', methods=['GET'])
            def get_camera():
                """Return a camera snapshot as a JPEG image"""
                if not self.gui or not getattr(self.gui, 'camera_available', False):
                    return jsonify({'error': 'Camera not available'}), 500
                # Get PIL image from GUI
                img = self.gui.get_camera_view_image()
                from io import BytesIO
                buf = BytesIO()
                img.save(buf, format='JPEG')
                buf.seek(0)
                from flask import send_file
                return send_file(buf, mimetype='image/jpeg', as_attachment=False, download_name='camera.jpg')
            
            @self.flask_app.route('/api/navmesh', methods=['GET'])
            def get_navmesh():
                """Return the navmesh edges as JSON."""
                try:
                    navmesh = getattr(self.autonomous_controller, 'navmesh_edges', {})
                    # Convert tuple keys to strings for JSON
                    serializable_edges = {str(k): v for k, v in navmesh.items()}
                    return jsonify(serializable_edges)
                except Exception as e:
                    return jsonify({'error': str(e)}), 500
            
            @self.flask_app.route('/api/learning_data', methods=['GET'])
            def get_learning_data():
                """Return learning data including stuck locations, areas of caution, and valid paths as JSON."""
                try:
                    learning_data = {
                        'stuck_locations': list(getattr(self.autonomous_controller, 'stuck_locations', set())),
                        'areas_of_caution': list(getattr(self.autonomous_controller, 'areas_of_caution', set())),
                        'valid_paths': getattr(self.autonomous_controller, 'valid_paths', {})
                    }
                    return jsonify(learning_data)
                except Exception as e:
                    return jsonify({'error': str(e)}), 500

            @self.flask_app.route('/api/task', methods=['POST'])
            def run_task():
                """Run a natural-language or tool task via TaskBoss (no direct motor PWM)."""
                if not self.task_boss:
                    return jsonify({'error': 'TaskBoss not initialized'}), 500
                try:
                    data = request.get_json() or {}
                    task = data.get('task', '')
                    if data.get('tool'):
                        result = self.task_boss.execute_tool(data['tool'], **data.get('args', {}))
                    else:
                        result = self.task_boss.run_task(task)
                    return jsonify(result)
                except Exception as e:
                    return jsonify({'error': str(e)}), 500

            @self.flask_app.route('/api/tools', methods=['GET'])
            def list_tools():
                if not self.task_boss:
                    return jsonify({'error': 'TaskBoss not initialized'}), 500
                return jsonify({'tools': self.task_boss.tools.list_tools()})

            @self.flask_app.route('/api/notifications', methods=['GET'])
            def get_notifications():
                """Recent robot notifications (log + API channel)."""
                if not self.task_boss:
                    return jsonify({'notifications': []})
                history = self.task_boss.mind.notifier.get_history(limit=20)
                return jsonify({'notifications': history})

            @self.flask_app.route('/api/blocked_path', methods=['GET', 'POST'])
            def blocked_path():
                """Get or resolve pending blocked-path state."""
                if not self.task_boss:
                    return jsonify({'error': 'TaskBoss not initialized'}), 500
                handler = self.task_boss.mind.blocked_path_handler
                if request.method == 'GET':
                    return jsonify({'pending': handler.get_pending_state()})
                data = request.get_json() or {}
                resolution_id = data.get('resolution_id')
                if resolution_id:
                    selected = handler.select_resolution(resolution_id)
                    if selected and selected.get('tool'):
                        result = self.task_boss.execute_tool(selected['tool'])
                        return jsonify({'selected': selected, 'result': result})
                    return jsonify({'error': 'Unknown resolution'}), 400
                return jsonify({'pending': handler.get_pending_state()})

            @self.flask_app.route('/api/smart_home/<action>', methods=['POST'])
            def smart_home_action(action):
                if not self.task_boss:
                    return jsonify({'error': 'TaskBoss not initialized'}), 500
                data = request.get_json() or {}
                tool_map = {
                    'on': 'turn_on_light',
                    'off': 'turn_off_light',
                    'state': 'get_device_state',
                }
                tool = tool_map.get(action)
                if not tool:
                    return jsonify({'error': 'Unknown action'}), 400
                return jsonify(self.task_boss.execute_tool(tool, **data))
            
            logger.info("Flask web server routes configured")
            
        except Exception as e:
            logger.error(f"Failed to setup web server: {e}")
            raise
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def start(self):
        """Start the robot system"""
        try:
            logger.info("Starting robot system...")
            
            # Start hardware components
            self.motor_controller.start()
            self.sensor_manager.start()
            logger.info("Hardware components started")
            
            # Start autonomous controller
            self.autonomous_controller.start()
            logger.info("Autonomous controller started")
            
            # Set robot to idle mode
            self.robot_state.set_mode(RobotMode.IDLE)
            
            # Start Flask web server
            if self.flask_app:
                self.web_server_thread = threading.Thread(
                    target=self.flask_app.run,
                    kwargs={
                        'host': self.web_host,
                        'port': self.web_port,
                        'debug': False,
                        'use_reloader': False,
                        'threaded': True,
                    },
                    daemon=True
                )
                self.web_server_thread.start()
                
                # Get local IP address
                local_ip = self._get_local_ip()
                web_url = f"http://{local_ip}:{self.web_port}"
                
                logger.info(f"Web server started at {web_url}")
                print(f"\nWeb interface: {web_url}")
                print("Control the robot from any device on your network.")
                print("Use the web UI or the desktop GUI.\n")
                
                # # Optionally open browser
                # try:
                #     webbrowser.open(web_url)
                # except:
                #     pass  # Browser might not be available
            
            self.running = True
            logger.info("Robot system started successfully")
            
            # Run GUI (this will block until GUI is closed)
            if self.gui:
                self.gui.run()
            
        except Exception as e:
            logger.error(f"Error starting robot system: {e}")
            self.shutdown()
    
    def _get_local_ip(self):
        """Get local IP address for network access"""
        try:
            # Connect to a remote address to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"
    
    def shutdown(self):
        """Shutdown the robot system gracefully"""
        if not self.running:
            return
        
        logger.info("Shutting down robot system...")
        self.running = False
        
        try:
            # Stop autonomous controller
            if self.autonomous_controller:
                self.autonomous_controller.stop()
                logger.info("Autonomous controller stopped")

            if self.task_boss:
                self.task_boss.shutdown()
                logger.info("TaskBoss stopped")
            
            # Stop hardware components
            if self.motor_controller:
                self.motor_controller.stop()
                logger.info("Motor controller stopped")
            
            if self.sensor_manager:
                self.sensor_manager.stop()
                logger.info("Sensor manager stopped")
            
            # Stop GUI
            if self.gui:
                self.gui.stop()
                logger.info("GUI stopped")
            
            # Stop web server
            if self.flask_app:
                logger.info("Web server stopped")
            
            logger.info("Robot system shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        
        finally:
            sys.exit(0)
    
    def get_system_status(self) -> dict:
        """Get comprehensive system status"""
        status = {
            'running': self.running,
            'robot_state': self.robot_state.get_status_summary() if self.robot_state else None,
            'motor_status': self.motor_controller.get_status() if self.motor_controller else None,
            'sensor_status': self.sensor_manager.get_sensor_status() if self.sensor_manager else None,
            'navigation_status': self.autonomous_controller.get_status() if self.autonomous_controller else None,
            'pathfinder_status': self.pathfinder.get_grid_status(include_grid=False) if self.pathfinder else None,
        }
        if self.vision_fusion:
            status['vision_fusion'] = self.vision_fusion.get_status()
        if self.task_boss:
            status['task_boss'] = self.task_boss.get_status()
        if self.smart_home:
            status['smart_home'] = self.smart_home.get_status()
        if self.hardware_transport:
            status['hardware_backend'] = self.hardware_transport.get_backend_name()
        return status


def main():
    """Main application entry point"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    robot_system = None
    try:
        robot_system = SmartRobotSystem()
        robot_system.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        print("Interrupted by user. Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}")
        logger.error(traceback.format_exc())
        print("A fatal error occurred. See logs/robot_system.log for details.")
    finally:
        if robot_system:
            robot_system.shutdown()
        else:
            print("System could not be started. Exiting.")
            sys.exit(1)


if __name__ == "__main__":
    main() 