"""
Sensor Manager
Handles all robot sensors including ultrasonic, infrared, and bumper sensors
"""

import time
import threading
from typing import Dict, Optional, List
from dataclasses import dataclass
from loguru import logger

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available - using simulation mode")


@dataclass
class SensorReading:
    """Individual sensor reading"""
    value: float
    timestamp: float
    valid: bool = True


@dataclass
class SensorHealth:
    """Sensor health status"""
    available: bool
    last_reading_time: float
    error_count: int
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    max_consecutive_failures: int = 5


class UltrasonicSensor:
    """HC-SR04 ultrasonic distance sensor"""
    
    def __init__(self, trigger_pin: int, echo_pin: int, name: str = "ultrasonic"):
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.name = name
        self.last_reading = 0.0
        self.last_timestamp = 0.0
        self.health = SensorHealth(available=True, last_reading_time=time.time(), error_count=0)
        
        if GPIO_AVAILABLE:
            self._setup_pins()
    
    def _setup_pins(self):
        """Setup GPIO pins for ultrasonic sensor"""
        try:
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            GPIO.output(self.trigger_pin, GPIO.LOW)
            self.health.available = True
        except Exception as e:
            logger.error(f"Failed to setup ultrasonic sensor {self.name}: {e}")
            self.health.available = False
            self.health.last_error = str(e)
            self.health.error_count += 1
    
    def read_distance(self) -> float:
        """Read distance in centimeters"""
        if not GPIO_AVAILABLE:
            # Simulation mode - return random distance
            import random
            distance = random.uniform(20, 200)
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            return distance
        
        try:
            # Send trigger pulse
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # Wait for echo
            start_time = time.time()
            timeout = 0.1  # 100ms timeout
            
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                if time.time() - start_time > timeout:
                    self._update_health(False, "Echo timeout")
                    return 0.0
                start_time = time.time()
            
            # Measure echo duration
            echo_start = time.time()
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                if time.time() - echo_start > timeout:
                    self._update_health(False, "Echo duration timeout")
                    return 0.0
            
            echo_duration = time.time() - echo_start
            
            # Calculate distance (speed of sound = 343 m/s)
            distance = (echo_duration * 34300) / 2  # Convert to cm
            
            # Filter out invalid readings
            if 2 <= distance <= 400:  # HC-SR04 range
                self.last_reading = distance
                self.last_timestamp = time.time()
                self._update_health(True)
                return distance
            else:
                self._update_health(False, f"Invalid distance reading: {distance}")
                return self.last_reading if self.last_reading > 0 else 0.0
                
        except Exception as e:
            error_msg = f"Error reading ultrasonic sensor {self.name}: {e}"
            logger.error(error_msg)
            self._update_health(False, error_msg)
            return self.last_reading if self.last_reading > 0 else 0.0
    
    def _update_health(self, success: bool, error_msg: str = None):
        """Update sensor health status"""
        if success:
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            self.health.available = True
        else:
            self.health.consecutive_failures += 1
            self.health.error_count += 1
            if error_msg:
                self.health.last_error = error_msg
            
            # Mark as unavailable if too many consecutive failures
            if self.health.consecutive_failures >= self.health.max_consecutive_failures:
                self.health.available = False
    
    def is_available(self) -> bool:
        """Check if sensor is available and working"""
        return self.health.available and (time.time() - self.health.last_reading_time) < 10.0
    
    def get_health_status(self) -> dict:
        """Get sensor health status"""
        return {
            'available': self.is_available(),
            'last_reading_time': self.health.last_reading_time,
            'error_count': self.health.error_count,
            'consecutive_failures': self.health.consecutive_failures,
            'last_error': self.health.last_error,
            'last_reading': self.last_reading
        }


class InfraredSensor:
    """Infrared obstacle detection sensor"""
    
    def __init__(self, pin: int, name: str = "infrared"):
        self.pin = pin
        self.name = name
        self.last_reading = False
        self.last_timestamp = 0.0
        self.health = SensorHealth(available=True, last_reading_time=time.time(), error_count=0)
        
        if GPIO_AVAILABLE:
            self._setup_pin()
    
    def _setup_pin(self):
        """Setup GPIO pin for infrared sensor"""
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.health.available = True
        except Exception as e:
            logger.error(f"Failed to setup infrared sensor {self.name}: {e}")
            self.health.available = False
            self.health.last_error = str(e)
            self.health.error_count += 1
    
    def read_obstacle(self) -> bool:
        """Read obstacle detection (True = obstacle detected)"""
        if not GPIO_AVAILABLE:
            # Simulation mode - random obstacle detection
            import random
            obstacle_detected = random.random() < 0.1  # 10% chance of obstacle
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            return obstacle_detected
        
        try:
            # Most IR sensors are active low (LOW = obstacle detected)
            obstacle_detected = GPIO.input(self.pin) == GPIO.LOW
            self.last_reading = obstacle_detected
            self.last_timestamp = time.time()
            self._update_health(True)
            return obstacle_detected
            
        except Exception as e:
            error_msg = f"Error reading infrared sensor {self.name}: {e}"
            logger.error(error_msg)
            self._update_health(False, error_msg)
            return self.last_reading
    
    def _update_health(self, success: bool, error_msg: str = None):
        """Update sensor health status"""
        if success:
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            self.health.available = True
        else:
            self.health.consecutive_failures += 1
            self.health.error_count += 1
            if error_msg:
                self.health.last_error = error_msg
            
            # Mark as unavailable if too many consecutive failures
            if self.health.consecutive_failures >= self.health.max_consecutive_failures:
                self.health.available = False
    
    def is_available(self) -> bool:
        """Check if sensor is available and working"""
        return self.health.available and (time.time() - self.health.last_reading_time) < 10.0
    
    def get_health_status(self) -> dict:
        """Get sensor health status"""
        return {
            'available': self.is_available(),
            'last_reading_time': self.health.last_reading_time,
            'error_count': self.health.error_count,
            'consecutive_failures': self.health.consecutive_failures,
            'last_error': self.health.last_error,
            'last_reading': self.last_reading
        }


class BumperSensor:
    """Bumper/limit switch sensor"""
    
    def __init__(self, pin: int, name: str = "bumper"):
        self.pin = pin
        self.name = name
        self.last_reading = False
        self.last_timestamp = 0.0
        self.health = SensorHealth(available=True, last_reading_time=time.time(), error_count=0)
        
        if GPIO_AVAILABLE:
            self._setup_pin()
    
    def _setup_pin(self):
        """Setup GPIO pin for bumper sensor"""
        try:
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self.health.available = True
        except Exception as e:
            logger.error(f"Failed to setup bumper sensor {self.name}: {e}")
            self.health.available = False
            self.health.last_error = str(e)
            self.health.error_count += 1
    
    def read_pressed(self) -> bool:
        """Read bumper state (True = pressed)"""
        if not GPIO_AVAILABLE:
            # Simulation mode - random bumper press
            import random
            pressed = random.random() < 0.05  # 5% chance of bumper press
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            return pressed
        
        try:
            # Most bumper switches are active low (LOW = pressed)
            pressed = GPIO.input(self.pin) == GPIO.LOW
            self.last_reading = pressed
            self.last_timestamp = time.time()
            self._update_health(True)
            return pressed
            
        except Exception as e:
            error_msg = f"Error reading bumper sensor {self.name}: {e}"
            logger.error(error_msg)
            self._update_health(False, error_msg)
            return self.last_reading
    
    def _update_health(self, success: bool, error_msg: str = None):
        """Update sensor health status"""
        if success:
            self.health.last_reading_time = time.time()
            self.health.consecutive_failures = 0
            self.health.available = True
        else:
            self.health.consecutive_failures += 1
            self.health.error_count += 1
            if error_msg:
                self.health.last_error = error_msg
            
            # Mark as unavailable if too many consecutive failures
            if self.health.consecutive_failures >= self.health.max_consecutive_failures:
                self.health.available = False
    
    def is_available(self) -> bool:
        """Check if sensor is available and working"""
        return self.health.available and (time.time() - self.health.last_reading_time) < 10.0
    
    def get_health_status(self) -> dict:
        """Get sensor health status"""
        return {
            'available': self.is_available(),
            'last_reading_time': self.health.last_reading_time,
            'error_count': self.health.error_count,
            'consecutive_failures': self.health.consecutive_failures,
            'last_error': self.health.last_error,
            'last_reading': self.last_reading
        }


class SensorManager:
    """Manages all robot sensors"""
    
    def __init__(self, config: dict):
        self.config = config
        self.sensor_config = config['hardware']['sensors']
        
        # Initialize sensors
        self.ultrasonic_sensors = {}
        self.infrared_sensors = {}
        self.bumper_sensors = {}
        
        # Sensor data cache
        self.sensor_data = {}
        self.last_update = 0.0
        
        # Threading
        self.running = False
        self.update_thread = None
        self.lock = threading.Lock()
        
        # Initialize all sensors
        self._setup_sensors()
    
    def _setup_sensors(self):
        """Initialize all sensors"""
        try:
            # Setup ultrasonic sensors
            self.ultrasonic_sensors['front'] = UltrasonicSensor(
                self.sensor_config['ultrasonic_front'], 
                self.sensor_config['ultrasonic_front'] + 1,  # Echo pin is typically trigger + 1
                "front"
            )
            self.ultrasonic_sensors['left'] = UltrasonicSensor(
                self.sensor_config['ultrasonic_left'],
                self.sensor_config['ultrasonic_left'] + 1,
                "left"
            )
            self.ultrasonic_sensors['right'] = UltrasonicSensor(
                self.sensor_config['ultrasonic_right'],
                self.sensor_config['ultrasonic_right'] + 1,
                "right"
            )
            
            # Setup infrared sensors
            self.infrared_sensors['left'] = InfraredSensor(
                self.sensor_config['infrared_left'],
                "left"
            )
            self.infrared_sensors['right'] = InfraredSensor(
                self.sensor_config['infrared_right'],
                "right"
            )
            
            # Setup bumper sensors
            self.bumper_sensors['left'] = BumperSensor(
                self.sensor_config['bumper_left'],
                "left"
            )
            self.bumper_sensors['right'] = BumperSensor(
                self.sensor_config['bumper_right'],
                "right"
            )
            
            logger.info("All sensors initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize sensors: {e}")
            raise
    
    def start(self):
        """Start sensor update thread"""
        if self.running:
            return
        
        self.running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Sensor manager started")
    
    def stop(self):
        """Stop sensor manager"""
        self.running = False
        
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        
        logger.info("Sensor manager stopped")
    
    def _update_loop(self):
        """Main sensor update loop"""
        update_interval = 1.0 / self.config['control']['gui_update_rate']
        
        while self.running:
            try:
                self._update_all_sensors()
                time.sleep(update_interval)
                
            except Exception as e:
                logger.error(f"Error in sensor update loop: {e}")
                time.sleep(0.1)
    
    def _update_all_sensors(self):
        """Update all sensor readings"""
        timestamp = time.time()
        
        # Read ultrasonic sensors
        ultrasonic_readings = {}
        for name, sensor in self.ultrasonic_sensors.items():
            if sensor.is_available():
                distance = sensor.read_distance()
                ultrasonic_readings[name] = SensorReading(distance, timestamp, valid=True)
            else:
                ultrasonic_readings[name] = SensorReading(0.0, timestamp, valid=False)
        
        # Read infrared sensors
        infrared_readings = {}
        for name, sensor in self.infrared_sensors.items():
            if sensor.is_available():
                obstacle = sensor.read_obstacle()
                infrared_readings[name] = SensorReading(1.0 if obstacle else 0.0, timestamp, valid=True)
            else:
                infrared_readings[name] = SensorReading(0.0, timestamp, valid=False)
        
        # Read bumper sensors
        bumper_readings = {}
        for name, sensor in self.bumper_sensors.items():
            if sensor.is_available():
                pressed = sensor.read_pressed()
                bumper_readings[name] = SensorReading(1.0 if pressed else 0.0, timestamp, valid=True)
            else:
                bumper_readings[name] = SensorReading(0.0, timestamp, valid=False)
        
        # Update sensor data cache
        with self.lock:
            self.sensor_data = {
                'ultrasonic': ultrasonic_readings,
                'infrared': infrared_readings,
                'bumper': bumper_readings,
                'timestamp': timestamp
            }
            self.last_update = timestamp
    
    def get_sensor_data(self) -> dict:
        """Get current sensor data"""
        with self.lock:
            return self.sensor_data.copy()
    
    def get_ultrasonic_distance(self, sensor_name: str) -> float:
        """Get distance from specific ultrasonic sensor"""
        with self.lock:
            if 'ultrasonic' in self.sensor_data and sensor_name in self.sensor_data['ultrasonic']:
                reading = self.sensor_data['ultrasonic'][sensor_name]
                return reading.value if reading.valid else 0.0
            return 0.0
    
    def get_infrared_obstacle(self, sensor_name: str) -> bool:
        """Get obstacle detection from specific infrared sensor"""
        with self.lock:
            if 'infrared' in self.sensor_data and sensor_name in self.sensor_data['infrared']:
                reading = self.sensor_data['infrared'][sensor_name]
                return reading.value > 0 if reading.valid else False
            return False
    
    def get_bumper_pressed(self, sensor_name: str) -> bool:
        """Get bumper state from specific bumper sensor"""
        with self.lock:
            if 'bumper' in self.sensor_data and sensor_name in self.sensor_data['bumper']:
                reading = self.sensor_data['bumper'][sensor_name]
                return reading.value > 0 if reading.valid else False
            return False
    
    def get_min_distance(self) -> float:
        """Get minimum distance from all ultrasonic sensors"""
        distances = []
        for name in ['front', 'left', 'right']:
            distance = self.get_ultrasonic_distance(name)
            if distance > 0:
                distances.append(distance)
        
        return min(distances) if distances else float('inf')
    
    def is_obstacle_detected(self) -> bool:
        """Check if any obstacle is detected"""
        # Check ultrasonic sensors
        min_distance = self.get_min_distance()
        if min_distance < self.config['robot']['safety_distances']['critical']:
            return True
        
        # Check infrared sensors
        for name in ['left', 'right']:
            if self.get_infrared_obstacle(name):
                return True
        
        # Check bumper sensors
        for name in ['left', 'right']:
            if self.get_bumper_pressed(name):
                return True
        
        return False
    
    def get_sensor_status(self) -> dict:
        """Get comprehensive sensor status"""
        with self.lock:
            return {
                'ultrasonic': {
                    name: reading.value for name, reading in self.sensor_data.get('ultrasonic', {}).items()
                },
                'infrared': {
                    name: reading.value > 0 for name, reading in self.sensor_data.get('infrared', {}).items()
                },
                'bumper': {
                    name: reading.value > 0 for name, reading in self.sensor_data.get('bumper', {}).items()
                },
                'min_distance': self.get_min_distance(),
                'obstacle_detected': self.is_obstacle_detected(),
                'last_update': self.last_update,
                'hardware_available': GPIO_AVAILABLE
            }
    
    def check_sensor_availability(self) -> dict:
        """Check availability of all sensors"""
        availability = {
            'hardware_available': GPIO_AVAILABLE,
            'ultrasonic': {},
            'infrared': {},
            'bumper': {},
            'overall_status': 'unknown'
        }
        
        # Check ultrasonic sensors
        ultrasonic_available = 0
        for name, sensor in self.ultrasonic_sensors.items():
            is_available = sensor.is_available()
            availability['ultrasonic'][name] = {
                'available': is_available,
                'health': sensor.get_health_status()
            }
            if is_available:
                ultrasonic_available += 1
        
        # Check infrared sensors
        infrared_available = 0
        for name, sensor in self.infrared_sensors.items():
            is_available = sensor.is_available()
            availability['infrared'][name] = {
                'available': is_available,
                'health': sensor.get_health_status()
            }
            if is_available:
                infrared_available += 1
        
        # Check bumper sensors
        bumper_available = 0
        for name, sensor in self.bumper_sensors.items():
            is_available = sensor.is_available()
            availability['bumper'][name] = {
                'available': is_available,
                'health': sensor.get_health_status()
            }
            if is_available:
                bumper_available += 1
        
        # Determine overall status
        total_sensors = len(self.ultrasonic_sensors) + len(self.infrared_sensors) + len(self.bumper_sensors)
        available_sensors = ultrasonic_available + infrared_available + bumper_available
        
        if not GPIO_AVAILABLE:
            availability['overall_status'] = 'simulation_mode'
        elif available_sensors == 0:
            availability['overall_status'] = 'no_sensors_available'
        elif available_sensors < total_sensors:
            availability['overall_status'] = 'partial_availability'
        else:
            availability['overall_status'] = 'all_sensors_available'
        
        availability['summary'] = {
            'total_sensors': total_sensors,
            'available_sensors': available_sensors,
            'ultrasonic_available': ultrasonic_available,
            'infrared_available': infrared_available,
            'bumper_available': bumper_available
        }
        
        return availability
    
    def get_unavailable_sensors(self) -> List[str]:
        """Get list of unavailable sensors"""
        unavailable = []
        
        for name, sensor in self.ultrasonic_sensors.items():
            if not sensor.is_available():
                unavailable.append(f"ultrasonic_{name}")
        
        for name, sensor in self.infrared_sensors.items():
            if not sensor.is_available():
                unavailable.append(f"infrared_{name}")
        
        for name, sensor in self.bumper_sensors.items():
            if not sensor.is_available():
                unavailable.append(f"bumper_{name}")
        
        return unavailable
    
    def is_system_healthy(self) -> bool:
        """Check if the sensor system is healthy enough for operation"""
        availability = self.check_sensor_availability()
        
        # In simulation mode, always consider healthy
        if not GPIO_AVAILABLE:
            return True
        
        # Need at least one ultrasonic sensor for basic navigation
        ultrasonic_available = availability['summary']['ultrasonic_available']
        
        return ultrasonic_available > 0
    
    def get_sensor_health_message(self) -> str:
        """Get a user-friendly message about sensor health"""
        availability = self.check_sensor_availability()
        
        if not GPIO_AVAILABLE:
            return "Running in simulation mode - sensors simulated"
        
        if availability['overall_status'] == 'no_sensors_available':
            return "Sensor not available. Please check your setup"
        
        if availability['overall_status'] == 'partial_availability':
            unavailable = self.get_unavailable_sensors()
            return f"Some sensors unavailable: {', '.join(unavailable)}. Please check connections."
        
        return "All sensors operational" 