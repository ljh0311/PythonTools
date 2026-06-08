#ifndef CONFIG_H
#define CONFIG_H

// Network Configuration
#define WIFI_SSID "Linksys10995"  // TODO: Move to secure storage
#define WIFI_PASSWORD "qxqmnet545" // TODO: Move to secure storage
#define UDP_PORT 4242
#define WIFI_CONNECT_TIMEOUT_MS 10000

// Physical Configuration
#define ENCODER_NOTCHES 20
#define WHEEL_DIAMETER_CM 6.4f
#define WHEELBASE_WIDTH_CM 11.5f

// Motor Configuration
#define MIN_SPEED_FACTOR 0.6f
#define MAX_SPEED_FACTOR 1.0f
#define TURN_COMPENSATION 1.8f

// PID Configuration
// Line following PID constants
#define Kp_LINE 0.1f   // Proportional gain
#define Ki_LINE 0.01f  // Integral gain
#define Kd_LINE 0.02f  // Derivative gain

// Motor control PID constants
#define Kp_MOTOR 0.05f  // Proportional gain
#define Ki_MOTOR 0.005f // Integral gain
#define Kd_MOTOR 0.01f  // Derivative gain

// Safety Configuration
#define MAX_TURN_ANGLE 180.0f
#define EMERGENCY_STOP_DISTANCE_CM 10.0f
#define COMMAND_BUFFER_SIZE 128

#endif // CONFIG_H 