#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdbool.h>
#include "pico/stdlib.h"
#include "config.h"

// PID controller structure
typedef struct {
    float kp;           // Proportional gain
    float ki;           // Integral gain
    float kd;           // Derivative gain
    float min_output;   // Minimum output value
    float max_output;   // Maximum output value
    float integral;     // Integral term
    float prev_error;   // Previous error for derivative calculation
    float target;       // Target value
    bool enabled;       // Controller enabled flag
} pid_controller_t;

// PID controller functions
void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float min_output, float max_output);
void pid_reset(pid_controller_t *pid);
void pid_set_target(pid_controller_t *pid, float target);
float pid_compute(pid_controller_t *pid, float current_value);
void pid_enable(pid_controller_t *pid);
void pid_disable(pid_controller_t *pid);

// Tuning functions
void pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd);
void pid_set_output_limits(pid_controller_t *pid, float min_output, float max_output);

// Utility functions
bool pid_is_stable(pid_controller_t *pid, float tolerance, uint32_t min_stable_time_ms);
float pid_get_error(pid_controller_t *pid);

#endif // PID_CONTROLLER_H 