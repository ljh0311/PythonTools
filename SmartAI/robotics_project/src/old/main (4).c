// main.c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "cyw43_arch.h"
#include "pico/cyw43_arch.h"
#include "encoder.h"
#include "ultrasonic.h"
#include "motor.h"

// PID constants
#define Kp 0.05f
#define Ki 0.005f
#define Kd 0.01f

// Base motor speeds
float base_speed_left = 1.0f;
float base_speed_right = 1.0f;

// WiFi configurations
#define WIFI_SSID "Your_SSID"
#define WIFI_PASSWORD "Your_PASSWORD"

// Buffer for incoming commands
#define CMD_BUFFER_SIZE 256
char command_buffer[CMD_BUFFER_SIZE];

// Function to stop the car
void stop_car() {
    leftmotor_stop();
    rightmotor_stop();
}

// Function to set motor speeds dynamically
void set_motor_speed(float left_speed, float right_speed) {
    leftmotor_forward(left_speed);
    rightmotor_forward(right_speed);
}

// Function to process commands
void process_command(const char *cmd) {
    char direction[16];
    int speed_percentage;

    // Parse the command
    if (sscanf(cmd, "%s %d", direction, &speed_percentage) == 2) {
        float speed_factor = speed_percentage / 100.0f;

        if (strcmp(direction, "FORWARD") == 0) {
            set_motor_speed(base_speed_left * speed_factor, base_speed_right * speed_factor);
        } else if (strcmp(direction, "BACKWARD") == 0) {
            leftmotor_backward(base_speed_left * speed_factor);
            rightmotor_backward(base_speed_right * speed_factor);
        } else if (strcmp(direction, "LEFT") == 0) {
            leftmotor_backward(base_speed_left * speed_factor);
            rightmotor_forward(base_speed_right * speed_factor);
        } else if (strcmp(direction, "RIGHT") == 0) {
            leftmotor_forward(base_speed_left * speed_factor);
            rightmotor_backward(base_speed_right * speed_factor);
        } else if (strcmp(direction, "STOP") == 0) {
            stop_car();
        } else {
            printf("Unknown command: %s\n", direction);
        }
    } else {
        printf("Invalid command format: %s\n", cmd);
    }
}

// Function to initialize WiFi
bool initialize_wifi() {
    if (cyw43_arch_init()) {
        printf("WiFi initialization failed!\n");
        return false;
    }

    cyw43_arch_enable_sta_mode();
    printf("Connecting to WiFi...\n");
    if (cyw43_arch_wifi_connect_blocking(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK)) {
        printf("Failed to connect to WiFi!\n");
        return false;
    }
    printf("Connected to WiFi.\n");
    return true;
}

// Main function
int main() {
    stdio_init_all();
    printf("Starting car control program...\n");

    // Initialize peripherals
    encoder_init();
    ultrasonic_init();
    setup_pwm(ENABLE_PIN, 2000);
    setup_pwm(ENABLE_PIN_RIGHT, 2000);

    // Initialize WiFi
    if (!initialize_wifi()) {
        return -1;
    }

    // Server loop to listen for commands
    while (1) {
        // Example: Replace this block with actual WiFi data receiving logic
        printf("Waiting for commands...\n");
        // Simulate receiving a command (replace with actual WiFi receive function)
        fgets(command_buffer, CMD_BUFFER_SIZE, stdin);

        // Process the received command
        process_command(command_buffer);

        sleep_ms(100);
    }

    // Cleanup
    cyw43_arch_deinit();
    return 0;
}
