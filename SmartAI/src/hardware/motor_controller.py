"""
Motor Controller
Handles motor control for robot movement
"""

import time
import math
from typing import Tuple, Optional
import threading
from loguru import logger

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available - using simulation mode")


class MotorController:
    """Controls robot motors for movement"""
    
    def __init__(self, config: dict):
        self.config = config
        self.left_motor_config = config['hardware']['left_motor']
        self.right_motor_config = config['hardware']['right_motor']
        
        # Motor states
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_pwm = None
        self.right_pwm = None
        
        # Safety and limits
        self.max_speed = config['robot']['max_speed']
        self.min_speed = config['robot']['min_speed']
        self.acceleration = config['robot']['acceleration']
        
        # Threading
        self.running = False
        self.control_thread = None
        self.lock = threading.Lock()
        
        # Initialize hardware
        self._setup_hardware()
    
    def _setup_hardware(self):
        """Initialize GPIO pins and PWM for motors"""
        if not GPIO_AVAILABLE:
            logger.info("Running in simulation mode - no hardware initialization")
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Setup left motor pins
            GPIO.setup(self.left_motor_config['forward_pin'], GPIO.OUT)
            GPIO.setup(self.left_motor_config['backward_pin'], GPIO.OUT)
            GPIO.setup(self.left_motor_config['enable_pin'], GPIO.OUT)
            
            # Setup right motor pins
            GPIO.setup(self.right_motor_config['forward_pin'], GPIO.OUT)
            GPIO.setup(self.right_motor_config['backward_pin'], GPIO.OUT)
            GPIO.setup(self.right_motor_config['enable_pin'], GPIO.OUT)
            
            # Setup PWM
            self.left_pwm = GPIO.PWM(self.left_motor_config['enable_pin'], 
                                   self.left_motor_config['pwm_frequency'])
            self.right_pwm = GPIO.PWM(self.right_motor_config['enable_pin'], 
                                    self.right_motor_config['pwm_frequency'])
            
            # Start PWM
            self.left_pwm.start(0)
            self.right_pwm.start(0)
            
            logger.info("Motor hardware initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize motor hardware: {e}")
            raise
    
    def start(self):
        """Start motor control thread"""
        if self.running:
            return
        
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        logger.info("Motor controller started")
    
    def stop(self):
        """Stop motor control and cleanup"""
        self.running = False
        self.set_speeds(0, 0)
        
        if self.control_thread:
            self.control_thread.join(timeout=1.0)
        
        if GPIO_AVAILABLE:
            try:
                if self.left_pwm:
                    self.left_pwm.stop()
                if self.right_pwm:
                    self.right_pwm.stop()
                GPIO.cleanup()
            except Exception as e:
                logger.error(f"Error during motor cleanup: {e}")
        
        logger.info("Motor controller stopped")
    
    def set_speeds(self, left_speed: float, right_speed: float):
        """Set motor speeds (-100 to 100)"""
        with self.lock:
            self.left_speed = max(-100, min(100, left_speed))
            self.right_speed = max(-100, min(100, right_speed))
    
    def move_forward(self, speed: float = 50.0):
        """Move robot forward"""
        speed = max(0, min(100, speed))
        self.set_speeds(speed, speed)
    
    def move_backward(self, speed: float = 50.0):
        """Move robot backward"""
        speed = max(0, min(100, speed))
        self.set_speeds(-speed, -speed)
    
    def turn_left(self, speed: float = 30.0):
        """Turn robot left (in place)"""
        speed = max(0, min(100, speed))
        self.set_speeds(-speed, speed)
    
    def turn_right(self, speed: float = 30.0):
        """Turn robot right (in place)"""
        speed = max(0, min(100, speed))
        self.set_speeds(speed, -speed)
    
    def stop_motors(self):
        """Stop all motors"""
        self.set_speeds(0, 0)
    
    def differential_drive(self, linear_speed: float, angular_speed: float):
        """Differential drive control
        
        Args:
            linear_speed: Forward/backward speed (-100 to 100)
            angular_speed: Turning speed (-100 to 100, negative = left, positive = right)
        """
        # Convert to wheel speeds
        left_speed = linear_speed - angular_speed
        right_speed = linear_speed + angular_speed
        
        # Normalize to [-100, 100] range
        max_speed = max(abs(left_speed), abs(right_speed))
        if max_speed > 100:
            left_speed = (left_speed / max_speed) * 100
            right_speed = (right_speed / max_speed) * 100
        
        self.set_speeds(left_speed, right_speed)
    
    def _control_loop(self):
        """Main motor control loop"""
        while self.running:
            try:
                with self.lock:
                    left_speed = self.left_speed
                    right_speed = self.right_speed
                
                if GPIO_AVAILABLE:
                    self._set_motor_outputs(left_speed, right_speed)
                
                time.sleep(0.01)  # 100Hz control loop
                
            except Exception as e:
                logger.error(f"Error in motor control loop: {e}")
                time.sleep(0.1)
    
    def _set_motor_outputs(self, left_speed: float, right_speed: float):
        """Set actual motor outputs via GPIO"""
        if not GPIO_AVAILABLE:
            return
        
        try:
            # Left motor control
            self._set_single_motor(
                left_speed,
                self.left_motor_config['forward_pin'],
                self.left_motor_config['backward_pin'],
                self.left_pwm
            )
            
            # Right motor control
            self._set_single_motor(
                right_speed,
                self.right_motor_config['forward_pin'],
                self.right_motor_config['backward_pin'],
                self.right_pwm
            )
            
        except Exception as e:
            logger.error(f"Error setting motor outputs: {e}")
    
    def _set_single_motor(self, speed: float, forward_pin: int, backward_pin: int, pwm):
        """Control a single motor"""
        if not GPIO_AVAILABLE:
            return
        
        speed = max(-100, min(100, speed))
        abs_speed = abs(speed)
        
        # Set direction
        if speed > 0:
            GPIO.output(forward_pin, GPIO.HIGH)
            GPIO.output(backward_pin, GPIO.LOW)
        elif speed < 0:
            GPIO.output(forward_pin, GPIO.LOW)
            GPIO.output(backward_pin, GPIO.HIGH)
        else:
            GPIO.output(forward_pin, GPIO.LOW)
            GPIO.output(backward_pin, GPIO.LOW)
        
        # Set PWM duty cycle
        pwm.ChangeDutyCycle(abs_speed)
    
    def get_current_speeds(self) -> Tuple[float, float]:
        """Get current motor speeds"""
        with self.lock:
            return self.left_speed, self.right_speed
    
    def emergency_stop(self):
        """Emergency stop - immediately stop all motors"""
        logger.warning("Emergency stop activated")
        self.stop_motors()
        
        if GPIO_AVAILABLE:
            try:
                # Force all motor pins low
                GPIO.output(self.left_motor_config['forward_pin'], GPIO.LOW)
                GPIO.output(self.left_motor_config['backward_pin'], GPIO.LOW)
                GPIO.output(self.right_motor_config['forward_pin'], GPIO.LOW)
                GPIO.output(self.right_motor_config['backward_pin'], GPIO.LOW)
                
                if self.left_pwm:
                    self.left_pwm.ChangeDutyCycle(0)
                if self.right_pwm:
                    self.right_pwm.ChangeDutyCycle(0)
            except Exception as e:
                logger.error(f"Error during emergency stop: {e}")
    
    def get_status(self) -> dict:
        """Get motor controller status"""
        left_speed, right_speed = self.get_current_speeds()
        return {
            'left_speed': left_speed,
            'right_speed': right_speed,
            'running': self.running,
            'hardware_available': GPIO_AVAILABLE
        } 