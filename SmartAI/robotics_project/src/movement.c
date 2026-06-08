#include "movement.h"
#include "pid_controller.h"
#include "motor.h"
#include "ultrasonic.h"
#include "line_sensor.h"
#include <math.h>

// PID controllers
static pid_controller_t pid_left_motor;
static pid_controller_t pid_right_motor;
static pid_controller_t pid_line_following;

// Movement state
static movement_status_t movement_status = MOVEMENT_IDLE;
static float current_speed = 0.0f;
static float current_heading = 0.0f;

// Initialize movement control
bool movement_init(void) {
    // Initialize PID controllers
    pid_init(&pid_left_motor, Kp_MOTOR, Ki_MOTOR, Kd_MOTOR, -1.0f, 1.0f);
    pid_init(&pid_right_motor, Kp_MOTOR, Ki_MOTOR, Kd_MOTOR, -1.0f, 1.0f);
    pid_init(&pid_line_following, Kp_LINE, Ki_LINE, Kd_LINE, -1.0f, 1.0f);
    
    movement_status = MOVEMENT_IDLE;
    current_speed = 0.0f;
    current_heading = 0.0f;
    
    return true;
}

// Cleanup movement resources
void movement_cleanup(void) {
    stop_movement();
    pid_disable(&pid_left_motor);
    pid_disable(&pid_right_motor);
    pid_disable(&pid_line_following);
}

// Basic movement commands
void move_forward(float speed_factor) {
    if (speed_factor < MIN_SPEED_FACTOR) speed_factor = MIN_SPEED_FACTOR;
    if (speed_factor > MAX_SPEED_FACTOR) speed_factor = MAX_SPEED_FACTOR;
    
    // Check for obstacles
    if (is_obstacle_detected()) {
        emergency_stop();
        return;
    }
    
    // Set motor speeds
    set_motor_speed(speed_factor, speed_factor);
    current_speed = speed_factor;
    movement_status = MOVEMENT_FORWARD;
}

void move_backward(float speed_factor) {
    if (speed_factor < MIN_SPEED_FACTOR) speed_factor = MIN_SPEED_FACTOR;
    if (speed_factor > MAX_SPEED_FACTOR) speed_factor = MAX_SPEED_FACTOR;
    
    // Set motor speeds (negative for backward)
    set_motor_speed(-speed_factor, -speed_factor);
    current_speed = -speed_factor;
    movement_status = MOVEMENT_BACKWARD;
}

void turn_left(float angle) {
    if (angle > MAX_TURN_ANGLE) angle = MAX_TURN_ANGLE;
    
    // Calculate turn duration based on angle
    float turn_speed = MIN_SPEED_FACTOR;
    set_motor_speed(-turn_speed, turn_speed);
    
    // Update heading
    current_heading -= angle;
    if (current_heading < -180.0f) current_heading += 360.0f;
    
    movement_status = MOVEMENT_TURNING;
}

void turn_right(float angle) {
    if (angle > MAX_TURN_ANGLE) angle = MAX_TURN_ANGLE;
    
    // Calculate turn duration based on angle
    float turn_speed = MIN_SPEED_FACTOR;
    set_motor_speed(turn_speed, -turn_speed);
    
    // Update heading
    current_heading += angle;
    if (current_heading > 180.0f) current_heading -= 360.0f;
    
    movement_status = MOVEMENT_TURNING;
}

void stop_movement(void) {
    set_motor_speed(0.0f, 0.0f);
    current_speed = 0.0f;
    movement_status = MOVEMENT_IDLE;
    
    // Reset PID controllers
    pid_reset(&pid_left_motor);
    pid_reset(&pid_right_motor);
}

// PID-controlled movement
void move_forward_pid(float target_speed, float distance_cm) {
    // Enable PID controllers
    pid_enable(&pid_left_motor);
    pid_enable(&pid_right_motor);
    
    // Set targets
    pid_set_target(&pid_left_motor, target_speed);
    pid_set_target(&pid_right_motor, target_speed);
    
    // Movement will be controlled by PID in the main loop
    movement_status = MOVEMENT_FORWARD;
}

void move_backward_pid(float target_speed, float distance_cm) {
    // Enable PID controllers
    pid_enable(&pid_left_motor);
    pid_enable(&pid_right_motor);
    
    // Set targets (negative for backward)
    pid_set_target(&pid_left_motor, -target_speed);
    pid_set_target(&pid_right_motor, -target_speed);
    
    // Movement will be controlled by PID in the main loop
    movement_status = MOVEMENT_BACKWARD;
}

void turn_by_angle_pid(float target_degrees) {
    // Enable PID controllers
    pid_enable(&pid_left_motor);
    pid_enable(&pid_right_motor);
    
    float turn_speed = MIN_SPEED_FACTOR;
    if (target_degrees < 0) {
        // Turn left
        pid_set_target(&pid_left_motor, -turn_speed);
        pid_set_target(&pid_right_motor, turn_speed);
    } else {
        // Turn right
        pid_set_target(&pid_left_motor, turn_speed);
        pid_set_target(&pid_right_motor, -turn_speed);
    }
    
    movement_status = MOVEMENT_TURNING;
}

// Line following
void start_line_following(void) {
    pid_enable(&pid_line_following);
    movement_status = MOVEMENT_LINE_FOLLOWING;
}

void stop_line_following(void) {
    pid_disable(&pid_line_following);
    stop_movement();
}

// Status and diagnostics
movement_status_t get_movement_status(void) {
    return movement_status;
}

float get_current_speed(void) {
    return current_speed;
}

float get_current_heading(void) {
    return current_heading;
}

// Emergency functions
void emergency_stop(void) {
    stop_movement();
    movement_status = MOVEMENT_ERROR;
}

bool is_obstacle_detected(void) {
    float distance = get_ultrasonic_distance();
    return distance < EMERGENCY_STOP_DISTANCE_CM;
} 