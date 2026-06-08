#include "pid_controller.h"
#include <math.h>

// Initialize PID controller
void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float min_output, float max_output) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->min_output = min_output;
    pid->max_output = max_output;
    pid_reset(pid);
    pid->enabled = true;
}

// Reset PID controller state
void pid_reset(pid_controller_t *pid) {
    pid->integral = 0.0f;
    pid->prev_error = 0.0f;
    pid->target = 0.0f;
}

// Set target value
void pid_set_target(pid_controller_t *pid, float target) {
    pid->target = target;
}

// Compute PID output
float pid_compute(pid_controller_t *pid, float current_value) {
    if (!pid->enabled) {
        return 0.0f;
    }

    float error = pid->target - current_value;
    
    // Calculate P term
    float p_term = pid->kp * error;
    
    // Calculate I term
    pid->integral += error;
    float i_term = pid->ki * pid->integral;
    
    // Calculate D term
    float derivative = error - pid->prev_error;
    float d_term = pid->kd * derivative;
    
    // Save error for next iteration
    pid->prev_error = error;
    
    // Calculate total output
    float output = p_term + i_term + d_term;
    
    // Clamp output to limits
    if (output > pid->max_output) {
        output = pid->max_output;
        // Anti-windup: prevent integral from growing
        pid->integral -= error;
    } else if (output < pid->min_output) {
        output = pid->min_output;
        // Anti-windup: prevent integral from growing
        pid->integral -= error;
    }
    
    return output;
}

// Enable PID controller
void pid_enable(pid_controller_t *pid) {
    pid->enabled = true;
}

// Disable PID controller
void pid_disable(pid_controller_t *pid) {
    pid->enabled = false;
    pid_reset(pid);
}

// Set PID gains
void pid_set_gains(pid_controller_t *pid, float kp, float ki, float kd) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    // Reset integral term when changing gains
    pid->integral = 0.0f;
}

// Set output limits
void pid_set_output_limits(pid_controller_t *pid, float min_output, float max_output) {
    if (min_output < max_output) {
        pid->min_output = min_output;
        pid->max_output = max_output;
    }
}

// Check if PID output is stable
bool pid_is_stable(pid_controller_t *pid, float tolerance, uint32_t min_stable_time_ms) {
    static uint32_t stable_start_time = 0;
    static bool was_stable = false;
    
    float current_error = fabsf(pid->prev_error);
    bool is_within_tolerance = current_error <= tolerance;
    
    uint32_t current_time = to_ms_since_boot(get_absolute_time());
    
    if (is_within_tolerance) {
        if (!was_stable) {
            stable_start_time = current_time;
            was_stable = true;
        }
        return (current_time - stable_start_time) >= min_stable_time_ms;
    } else {
        was_stable = false;
        return false;
    }
}

// Get current error
float pid_get_error(pid_controller_t *pid) {
    return pid->prev_error;
} 