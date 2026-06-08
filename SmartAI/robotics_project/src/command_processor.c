#include "command_processor.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static command_status_t last_status = CMD_SUCCESS;
static char last_error[256] = "";
static movement_status_t current_movement = MOVEMENT_IDLE;

// Initialize command processor
bool command_processor_init(void) {
    last_status = CMD_SUCCESS;
    memset(last_error, 0, sizeof(last_error));
    return true;
}

// Parse command string into command structure
command_t parse_command(const char* command_str) {
    command_t cmd = {CMD_UNKNOWN, 0.0f, false};
    
    if (!command_str || strlen(command_str) == 0) {
        snprintf(last_error, sizeof(last_error), "Empty command");
        last_status = CMD_INVALID_FORMAT;
        return cmd;
    }
    
    // Parse command type and parameter
    char command_type[32];
    float param = 0.0f;
    
    if (sscanf(command_str, "%31[^:]:%f", command_type, &param) >= 1) {
        // Convert to uppercase for comparison
        for (int i = 0; command_type[i]; i++) {
            command_type[i] = toupper(command_type[i]);
        }
        
        // Match command type
        if (strcmp(command_type, "FORWARD") == 0) {
            cmd.type = CMD_FORWARD;
            cmd.parameter = param;
            cmd.valid = validate_speed_factor(param);
        }
        else if (strcmp(command_type, "BACKWARD") == 0) {
            cmd.type = CMD_BACKWARD;
            cmd.parameter = param;
            cmd.valid = validate_speed_factor(param);
        }
        else if (strcmp(command_type, "LEFT") == 0) {
            cmd.type = CMD_LEFT;
            cmd.parameter = param;
            cmd.valid = validate_angle(param);
        }
        else if (strcmp(command_type, "RIGHT") == 0) {
            cmd.type = CMD_RIGHT;
            cmd.parameter = param;
            cmd.valid = validate_angle(param);
        }
        else if (strcmp(command_type, "STOP") == 0) {
            cmd.type = CMD_STOP;
            cmd.valid = true;
        }
        else if (strcmp(command_type, "LINE") == 0) {
            cmd.type = CMD_LINE_FOLLOW;
            cmd.valid = true;
        }
        else {
            snprintf(last_error, sizeof(last_error), "Unknown command: %s", command_type);
            last_status = CMD_INVALID_FORMAT;
        }
    } else {
        snprintf(last_error, sizeof(last_error), "Invalid command format");
        last_status = CMD_INVALID_FORMAT;
    }
    
    return cmd;
}

// Process command
command_status_t process_command(const char* command_str) {
    command_t cmd = parse_command(command_str);
    
    if (!cmd.valid) {
        return last_status;
    }
    
    // Execute command
    switch (cmd.type) {
        case CMD_FORWARD:
            if (current_movement != MOVEMENT_IDLE && current_movement != MOVEMENT_FORWARD) {
                stop_movement();
            }
            move_forward(cmd.parameter);
            current_movement = MOVEMENT_FORWARD;
            break;
            
        case CMD_BACKWARD:
            if (current_movement != MOVEMENT_IDLE && current_movement != MOVEMENT_BACKWARD) {
                stop_movement();
            }
            move_backward(cmd.parameter);
            current_movement = MOVEMENT_BACKWARD;
            break;
            
        case CMD_LEFT:
            if (current_movement != MOVEMENT_IDLE) {
                stop_movement();
            }
            turn_left(cmd.parameter);
            current_movement = MOVEMENT_TURNING;
            break;
            
        case CMD_RIGHT:
            if (current_movement != MOVEMENT_IDLE) {
                stop_movement();
            }
            turn_right(cmd.parameter);
            current_movement = MOVEMENT_TURNING;
            break;
            
        case CMD_STOP:
            stop_movement();
            current_movement = MOVEMENT_IDLE;
            break;
            
        case CMD_LINE_FOLLOW:
            if (current_movement != MOVEMENT_LINE_FOLLOWING) {
                start_line_following();
                current_movement = MOVEMENT_LINE_FOLLOWING;
            }
            break;
            
        default:
            snprintf(last_error, sizeof(last_error), "Command not implemented");
            last_status = CMD_NOT_IMPLEMENTED;
            return last_status;
    }
    
    last_status = CMD_SUCCESS;
    return last_status;
}

// Validate speed factor
bool validate_speed_factor(float speed_factor) {
    if (speed_factor < MIN_SPEED_FACTOR || speed_factor > MAX_SPEED_FACTOR) {
        snprintf(last_error, sizeof(last_error), 
                "Speed factor must be between %.2f and %.2f", 
                MIN_SPEED_FACTOR, MAX_SPEED_FACTOR);
        last_status = CMD_INVALID_PARAMETER;
        return false;
    }
    return true;
}

// Validate angle
bool validate_angle(float angle) {
    if (angle < -MAX_TURN_ANGLE || angle > MAX_TURN_ANGLE) {
        snprintf(last_error, sizeof(last_error), 
                "Angle must be between -%.1f and %.1f degrees", 
                MAX_TURN_ANGLE, MAX_TURN_ANGLE);
        last_status = CMD_INVALID_PARAMETER;
        return false;
    }
    return true;
}

// Get last error message
const char* get_last_error(void) {
    return last_error;
}

// Get last command status
command_status_t get_last_status(void) {
    return last_status;
} 