# Smart Robot System

A comprehensive autonomous house navigation robot system with real-time control interface, pathfinding, and obstacle avoidance capabilities.

## 🚀 Features

### Core Functionality

- **Autonomous Navigation**: A* pathfinding algorithm with obstacle avoidance
- **Real-time Control**: Manual and autonomous operation modes
- **Sensor Integration**: Ultrasonic, infrared, and bumper sensors
- **Motor Control**: Precise differential drive control
- **Safety Systems**: Emergency stop and collision detection

### User Interface

- **Modern GUI**: Dark-themed interface with multiple tabs
- **Real-time Monitoring**: Live sensor data and robot status
- **Map Visualization**: Interactive navigation map with exploration progress
- **Manual Control**: Intuitive movement controls with speed adjustment

### Navigation Capabilities

- **Path Planning**: Intelligent route calculation avoiding obstacles
- **Exploration Mode**: Autonomous area exploration and mapping
- **Return to Base**: Automatic return to home position
- **Obstacle Avoidance**: Real-time obstacle detection and avoidance

## 📋 Requirements

### Hardware Requirements

- **Raspberry Pi** (3B+ or 4 recommended)
- **DC Motors** (2x for differential drive)
- **Motor Driver Board** (L298N or similar)
- **Ultrasonic Sensors** (3x HC-SR04)
- **Infrared Sensors** (2x for obstacle detection)
- **Bumper Switches** (2x for collision detection)
- **Power Supply** (12V recommended)
- **Chassis and Wheels**

### Software Requirements

- **Python 3.8+**
- **Raspberry Pi OS** (or compatible Linux distribution)
- **Required Python packages** (see requirements.txt)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd SmartAI
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Hardware Setup

1. **Connect Motors**:
   - Left motor: GPIO 17 (forward), 18 (backward), 27 (enable)
   - Right motor: GPIO 22 (forward), 23 (backward), 24 (enable)

2. **Connect Sensors**:
   - Ultrasonic Front: GPIO 5 (trigger), 6 (echo)
   - Ultrasonic Left: GPIO 6 (trigger), 7 (echo)
   - Ultrasonic Right: GPIO 13 (trigger), 14 (echo)
   - Infrared Left: GPIO 19
   - Infrared Right: GPIO 26
   - Bumper Left: GPIO 20
   - Bumper Right: GPIO 21

3. **Power Supply**:
   - Connect 12V power supply to motor driver
   - Ensure proper grounding

### 4. Configuration

Edit `config/robot_config.yaml` to match your hardware setup:

```yaml
hardware:
  left_motor:
    forward_pin: 17
    backward_pin: 18
    enable_pin: 27
  # ... other settings
```

## 🚀 Usage

### Starting the System

```bash
python main.py
```

### GUI Interface

#### Manual Control Tab

- **Mode Selection**: Choose between Idle, Manual, Autonomous, etc.
- **Emergency Stop**: Immediate stop button for safety
- **Movement Controls**: Forward, backward, left, right buttons
- **Speed Control**: Adjustable speed slider (0-100%)

#### Monitoring Tab

- **Robot Status**: Real-time position, battery, operation time
- **Sensor Data**: Live readings from all sensors
- **System Status**: Mode, safety status, obstacle detection

#### Navigation Tab

- **Target Input**: Set destination coordinates
- **Navigation Controls**: Navigate to target, start exploration, return to base
- **Map Visualization**: Real-time navigation map with robot position
- **Exploration Progress**: Percentage of area explored

#### Settings Tab

- **Configuration**: View and edit robot settings
- **System Log**: Real-time log display

### Operation Modes

#### Manual Mode

- Use GUI buttons or keyboard controls
- Direct motor control with speed adjustment
- Real-time sensor feedback

#### Autonomous Mode

- Set target coordinates
- Robot automatically plans and follows path
- Obstacle avoidance and path replanning

#### Exploration Mode

- Robot autonomously explores unknown areas
- Builds map of environment
- Returns to base when complete

## 🔧 Configuration

### Robot Parameters

```yaml
robot:
  width: 30          # Robot width in cm
  length: 40         # Robot length in cm
  max_speed: 50      # Maximum speed in cm/s
  safety_distances:
    critical: 10     # Emergency stop distance
    warning: 30      # Warning distance
    comfortable: 50  # Comfortable navigation distance
```

### Navigation Settings

```yaml
navigation:
  grid_size: 10      # Grid resolution in cm
  map_width: 1000    # Map width in cm
  map_height: 1000   # Map height in cm
  exploration_mode: true
  return_to_base: true
```

## 🛡️ Safety Features

### Emergency Systems

- **Emergency Stop**: Immediate motor shutdown
- **Obstacle Detection**: Multiple sensor redundancy
- **Bumper Switches**: Physical collision detection
- **Battery Monitoring**: Low battery warnings

### Safety Distances

- **Critical**: 10cm - Emergency stop
- **Warning**: 30cm - Reduced speed
- **Comfortable**: 50cm - Normal operation

## 📊 System Architecture

```
Smart Robot System
├── Core (Robot State Management)
├── Hardware (Motor & Sensor Control)
├── Navigation (Pathfinding & Autonomous Control)
├── GUI (User Interface)
└── Configuration (Settings & Logging)
```

### Component Overview

- **RobotState**: Position tracking, mode management
- **MotorController**: Motor control and safety
- **SensorManager**: Sensor data collection and processing
- **Pathfinder**: A* pathfinding algorithm
- **AutonomousController**: Navigation coordination
- **RobotGUI**: User interface and visualization

## 🔍 Troubleshooting

### Common Issues

#### Hardware Not Detected

- Check GPIO pin connections
- Verify power supply voltage
- Test individual components

#### Navigation Problems

- Ensure sensors are properly calibrated
- Check for obstacles in path
- Verify map boundaries

#### GUI Issues

- Update Python packages
- Check display settings
- Verify matplotlib installation

### Log Files

- System logs: `logs/robot_system.log`
- Error details and debugging information
- Performance metrics and sensor data

## 🧪 Testing

### Simulation Mode

The system can run in simulation mode without hardware:

- Sensors generate random data
- Motors simulate movement
- Full GUI functionality available

### Hardware Testing

1. **Motor Test**: Verify motor connections and directions
2. **Sensor Test**: Check sensor readings and calibration
3. **Navigation Test**: Test pathfinding in known environment
4. **Safety Test**: Verify emergency stop functionality

## 📈 Performance

### Specifications

- **Update Rate**: 10Hz control loop
- **Sensor Accuracy**: ±1cm (ultrasonic), ±5cm (infrared)
- **Navigation Accuracy**: ±5cm position accuracy
- **Response Time**: <100ms emergency stop

### Optimization

- **Grid Resolution**: Adjustable for accuracy vs. performance
- **Update Frequency**: Configurable control loop rate
- **Memory Usage**: Efficient data structures for large maps

## 🤝 Contributing

### Development Setup

1. Fork the repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

### Code Style

- Follow PEP 8 guidelines
- Add type hints
- Include docstrings
- Write unit tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Raspberry Pi Foundation** for the hardware platform
- **OpenCV** for computer vision capabilities
- **Matplotlib** for visualization
- **CustomTkinter** for modern GUI components

## 📞 Support

For questions, issues, or contributions:

- Create an issue on GitHub
- Check the troubleshooting section
- Review the configuration documentation

---

**Note**: This system is designed for educational and research purposes. Always test in a safe environment before autonomous operation.
