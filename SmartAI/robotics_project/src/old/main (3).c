#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "pico/cyw43_arch.h"
#include "encoder.h"
#include "ultrasonic.h"
#include "motor.h"
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "lwip/pbuf.h"
#include "lwip/udp.h"
#include "lwip/netif.h"
#include "cyw43.h"

// PID constants
#define Kp 0.05f  // Proportional gain
#define Ki 0.005f // Integral gain
#define Kd 0.01f  // Derivative gain

// Base motor speeds
float base_speed_left = 1.0f;
float base_speed_right = 1.0f * 0.85f;  // Right motor runs slower

// Turn compensation factor (adjust this based on testing)
#define TURN_COMPENSATION 1.8f // If turning 50° instead of 90°, use 90/50 = 1.8

// Movement tuning parameters
#define TURN_ADJUSTMENT_FACTOR 0.1f   // Adjust if turns are not synchronized
#define FORWARD_ADJUSTMENT_FACTOR 0.1f // Adjust if forward movement veers off
#define TEST_PAUSE_MS 1000            // Pause between movements

// WiFi configurations
#define WIFI_SSID "Your_SSID"
#define WIFI_PASSWORD "Your_PASSWORD"

// UDP port that the car will listen on for commands
#define CAR_PORT 4243

// Global UDP Protocol Control Block
struct udp_pcb *udp_pcb;

// Buffer for incoming commands
#define CMD_BUFFER_SIZE 256
char command_buffer[CMD_BUFFER_SIZE];

// Function to stop the car
void stop_car()
{
    leftmotor_stop();
    rightmotor_stop();
}

// Function to set motor speeds dynamically
void set_motor_speed(float left_speed, float right_speed)
{
    leftmotor_forward(left_speed);
    rightmotor_forward(right_speed);
}

// Function for feedback (flash motor)
void flash_feedback()
{
    leftmotor_forward(0.3f);
    rightmotor_forward(0.3f);
    sleep_ms(200);
    stop_car();
    sleep_ms(500);
}

// PID controller to calculate the required movement adjustments
float pid_control(float target, float current)
{
    static float previous_error = 0;
    static float integral = 0;

    float error = target - current;
    integral += error;
    float derivative = error - previous_error;

    float output = Kp * error + Ki * integral + Kd * derivative;

    previous_error = error;

    return output;
}

// Function to turn the car by a specified angle
void turn_by_angle(float target_degrees)
{
    reset_encoder_counts();

    // Apply turn compensation factor
    float compensated_degrees = target_degrees * TURN_COMPENSATION;

    // Calculate arc length for the turn
    float turn_circumference = WHEELBASE_WIDTH_CM * M_PI;
    float arc_length = (fabsf(compensated_degrees) / 360.0f) * turn_circumference;

    // Calculate wheel distances
    float wheel_travel_distance = arc_length / 2.0f;

    // Convert to encoder notches needed for each wheel
    int32_t left_encoder_target = wheel_travel_distance * ENCODER_TICKS_PER_CM;
    int32_t right_encoder_target = wheel_travel_distance * ENCODER_TICKS_PER_CM;

    // Execute the turn (assumes encoder logic is in place)
    while (get_left_encoder_ticks() < left_encoder_target || get_right_encoder_ticks() < right_encoder_target)
    {
        // Adjust speeds dynamically using PID control
        float left_speed = pid_control(left_encoder_target, get_left_encoder_ticks());
        float right_speed = pid_control(right_encoder_target, get_right_encoder_ticks());

        set_motor_speed(base_speed_left + left_speed, base_speed_right + right_speed);
    }

    stop_car(); // Stop after turning
}

// Function to process commands
void udp_receive_callback(void *arg, struct udp_pcb *pcb, struct pbuf *p,
                          const ip_addr_t *addr, u16_t port)
{
    if (p != NULL)
    {
        // Extract command string from the network packet
        char *command = (char *)p->payload;
        printf("Received command: %s\n", command);

        // Parse different movement commands
        // Format: DIRECTION:SPEED where speed is 0-100
        if (strncmp(command, "FORWARD:", 8) == 0)
        {
            int speed_factor = atoi(command + 8) / 100;
            set_motor_speed(base_speed_left * speed_factor, base_speed_right * speed_factor);
        }
        else if (strncmp(command, "BACKWARD:", 9) == 0)
        {
            int speed_factor = atoi(command + 9) / 100;
            leftmotor_backward(base_speed_left * speed_factor);
            rightmotor_backward(base_speed_right * speed_factor);
        }
        else if (strncmp(command, "LEFT:", 5) == 0)
        {
            int speed_factor = atoi(command + 5) / 100;
            leftmotor_backward(base_speed_left * speed_factor);
            rightmotor_forward(base_speed_right * speed_factor);
        }
        else if (strncmp(command, "RIGHT:", 6) == 0)
        {
            int speed_factor = atoi(command + 6) / 100;
            leftmotor_forward(base_speed_left * speed_factor);
            rightmotor_backward(base_speed_right * speed_factor);
        }
        else if (strcmp(command, "STOP") == 0)
        {
            stop_car();
        }

        // Always free the packet buffer when done
        pbuf_free(p);
    }
}

// Function to connect to WiFi network in station mode
bool setup_wifi_station()
{
    printf("WIFI >> Connecting to network: %s\n", WIFI_SSID);

    // Enable station (client) mode for WiFi
    cyw43_arch_enable_sta_mode();

    // Try to connect multiple times before giving up
    const int MAX_RETRIES = 3;
    for (int retry = 0; retry < MAX_RETRIES; retry++)
    {
        printf("\nWIFI >> Connection attempt %d of %d\n", retry + 1, MAX_RETRIES);

        // Connect with WPA2 Personal
        int err = cyw43_arch_wifi_connect_blocking(
            WIFI_SSID,
            WIFI_PASSWORD,
            CYW43_AUTH_WPA2_AES_PSK);

        // If connection successful, print IP address
        if (err == 0)
        {
            struct netif *netif = netif_default;
            if (netif)
            {
                printf("WIFI >> Connected successfully!\n");
                printf("WIFI >> IP Address: %s\n", ip4addr_ntoa(netif_ip4_addr(netif)));
                return true;
            }
        }
        else
        {
            printf("ERR >> Connection failed (error %d)\n", err);
            if (err == PICO_ERROR_TIMEOUT)
            {
                printf("ERR >> Connection timed out\n");
            }
            else if (err == PICO_ERROR_GENERIC)
            {
                printf("ERR >> Authentication failed - verify password\n");
            }
            else
            {
                printf("ERR >> Unknown error\n");
            }
        }

        // Wait between retries
        if (retry < MAX_RETRIES - 1)
        {
            printf("WIFI >> Waiting 3 seconds before retry...\n");
            sleep_ms(3000);
        }
    }

    return false;
}

// Function to initialize UDP server
bool setup_udp()
{
    printf("UDP >> Initializing UDP...\n");

    // Create new UDP Protocol Control Block
    udp_pcb = udp_new();
    if (udp_pcb == NULL)
    {
        printf("ERR >> Failed to create UDP PCB\n");
        return false;
    }

    // Bind to specific port to listen for commands
    err_t err = udp_bind(udp_pcb, IP_ADDR_ANY, CAR_PORT);
    if (err != ERR_OK)
    {
        printf("ERR >> Failed to bind UDP PCB (error %d)\n", err);
        return false;
    }
    printf("UDP >> Bound to port %d\n", CAR_PORT);

    // Register callback function for incoming packets
    udp_recv(udp_pcb, udp_receive_callback, NULL);
    printf("UDP >> Receive callback registered\n");

    return true;
}

// Main function
int main()
{
    // Initialize USB and peripherals
    stdio_init_all();
    encoder_init();
    ultrasonic_init();
    gpio_init(IN1_PIN);
    gpio_set_dir(IN1_PIN, GPIO_OUT);
    gpio_init(IN2_PIN);
    gpio_set_dir(IN2_PIN, GPIO_OUT);
    gpio_init(IN3_PIN);
    gpio_set_dir(IN3_PIN, GPIO_OUT);
    gpio_init(IN4_PIN);
    gpio_set_dir(IN4_PIN, GPIO_OUT);
    motor_init();

    // Connect to WiFi
    if (setup_wifi_station())
    {
        // Set up UDP communication
        if (setup_udp())
        {
            while (1)
            {
                tight_loop_contents();
            }
        }
    }

    // If we reach here, stop everything
    stop_car();
    return 0;
}
