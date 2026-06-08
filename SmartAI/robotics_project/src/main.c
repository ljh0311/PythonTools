#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "config.h"
#include "network.h"
#include "movement.h"
#include "command_processor.h"
#include "encoder.h"
#include "ultrasonic.h"
#include "motor.h"
#include "line_sensor.h"

// Function prototypes
static void init_led(void);
static void blink_led(void);
static void command_handler(const char* command);

int main() {
    stdio_init_all();
    
    // Initialize LED
    init_led();
    
    // Wait for USB connection
    while (!stdio_usb_connected()) {
        blink_led();
    }
    
    printf("\nUSB Serial initialized!\n");
    printf("\n=== Car Control Unit ===\n");
    printf("Starting initialization...\n");
    
    // Initialize subsystems
    if (!encoder_init()) {
        printf("Failed to initialize encoders\n");
        return 1;
    }
    
    if (!ultrasonic_init()) {
        printf("Failed to initialize ultrasonic sensor\n");
        return 1;
    }
    
    if (!motor_init()) {
        printf("Failed to initialize motors\n");
        return 1;
    }
    
    if (!line_sensor_init()) {
        printf("Failed to initialize line sensors\n");
        return 1;
    }
    
    if (!movement_init()) {
        printf("Failed to initialize movement control\n");
        return 1;
    }
    
    if (!command_processor_init()) {
        printf("Failed to initialize command processor\n");
        return 1;
    }
    
    if (!network_init()) {
        printf("Failed to initialize network\n");
        return 1;
    }
    
    // Set command callback
    network_set_command_callback(command_handler);
    
    printf("\nSystem ready!\n");
    printf("Waiting for commands...\n");
    
    // Main loop
    while (1) {
        // Poll network
        network_poll();
        
        // Print status periodically
        static uint32_t last_print_time = 0;
        uint32_t current_time = to_ms_since_boot(get_absolute_time());
        
        if (current_time - last_print_time > 1000) {
            movement_status_t status = get_movement_status();
            float speed = get_current_speed();
            float heading = get_current_heading();
            
            printf("Status: %d, Speed: %.2f, Heading: %.1f\n",
                   status, speed, heading);
            
            printf("Encoder counts - Left: %ld, Right: %ld\n",
                   get_left_encoder_count(),
                   get_right_encoder_count());
                   
            last_print_time = current_time;
        }
        
        // Check for obstacles
        if (is_obstacle_detected()) {
            emergency_stop();
            printf("Emergency stop: Obstacle detected!\n");
        }
        
        sleep_ms(10);
    }
    
    // Cleanup (never reached in this implementation)
    movement_cleanup();
    network_cleanup();
    
    return 0;
}

// Initialize LED
static void init_led(void) {
#ifdef PICO_DEFAULT_LED_PIN
    const uint LED_PIN = PICO_DEFAULT_LED_PIN;
    gpio_init(LED_PIN);
    gpio_set_dir(LED_PIN, GPIO_OUT);
#endif
}

// Blink LED
static void blink_led(void) {
#ifdef PICO_DEFAULT_LED_PIN
    gpio_put(PICO_DEFAULT_LED_PIN, 1);
    sleep_ms(250);
    gpio_put(PICO_DEFAULT_LED_PIN, 0);
    sleep_ms(250);
#else
    sleep_ms(500);
#endif
}

// Command handler callback
static void command_handler(const char* command) {
    command_status_t status = process_command(command);
    
    if (status != CMD_SUCCESS) {
        printf("Command error: %s\n", get_last_error());
    }
}
