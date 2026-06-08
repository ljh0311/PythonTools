#ifndef NETWORK_H
#define NETWORK_H

#include <stdbool.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "lwip/pbuf.h"
#include "lwip/udp.h"
#include "config.h"

// Function prototypes
bool network_init(void);
bool wifi_connect(void);
bool udp_init(void);
void network_poll(void);
void network_cleanup(void);

// Callback type for command processing
typedef void (*command_callback_t)(const char* command);

// Set the callback for processing received commands
void network_set_command_callback(command_callback_t callback);

#endif // NETWORK_H 