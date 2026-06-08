#ifndef COMMAND_PROCESSOR_H
#define COMMAND_PROCESSOR_H

#include <stdbool.h>
#include "pico/stdlib.h"
#include "config.h"
#include "movement.h"

// Command status
typedef enum {
    CMD_SUCCESS,
    CMD_INVALID_FORMAT,
    CMD_INVALID_PARAMETER,
    CMD_NOT_IMPLEMENTED,
    CMD_EXECUTION_ERROR
} command_status_t;

// Command types
typedef enum {
    CMD_FORWARD,
    CMD_BACKWARD,
    CMD_LEFT,
    CMD_RIGHT,
    CMD_STOP,
    CMD_LINE_FOLLOW,
    CMD_UNKNOWN
} command_type_t;

// Command structure
typedef struct {
    command_type_t type;
    float parameter;    // Speed factor, angle, etc.
    bool valid;
} command_t;

// Command processor functions
bool command_processor_init(void);
command_status_t process_command(const char* command_str);
command_t parse_command(const char* command_str);

// Command validation
bool validate_speed_factor(float speed_factor);
bool validate_angle(float angle);

// Status reporting
const char* get_last_error(void);
command_status_t get_last_status(void);

#endif // COMMAND_PROCESSOR_H 