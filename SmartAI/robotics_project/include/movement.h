#ifndef MOVEMENT_H
#define MOVEMENT_H

#include <stdbool.h>
#include "pico/stdlib.h"
#include "config.h"
#include "encoder.h"

// Movement status
typedef enum {
    MOVEMENT_IDLE,
    MOVEMENT_FORWARD,
    MOVEMENT_BACKWARD,
    MOVEMENT_TURNING,
    MOVEMENT_LINE_FOLLOWING,
    MOVEMENT_ERROR
} movement_status_t;

// Movement control functions
bool movement_init(void);
void movement_cleanup(void);

// Basic movement commands
void move_forward(float speed_factor);
void move_backward(float speed_factor);
void turn_left(float angle);
void turn_right(float angle);
void stop_movement(void);

// PID-controlled movement
void move_forward_pid(float target_speed, float distance_cm);
void move_backward_pid(float target_speed, float distance_cm);
void turn_by_angle_pid(float target_degrees);

// Line following
void start_line_following(void);
void stop_line_following(void);

// Status and diagnostics
movement_status_t get_movement_status(void);
float get_current_speed(void);
float get_current_heading(void);

// Emergency functions
void emergency_stop(void);
bool is_obstacle_detected(void);

#endif // MOVEMENT_H 