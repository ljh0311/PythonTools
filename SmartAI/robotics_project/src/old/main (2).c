// main.c
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "encoder.h"
#include "ultrasonic.h"
#include "motor.h"

// PID constants
#define Kp 0.05f   // Proportional gain
#define Ki 0.005f  // Integral gain
#define Kd 0.01f   // Derivative gain

// Turn compensation factor (adjust this based on testing)
#define TURN_COMPENSATION 1.8f  // If turning 50° instead of 90°, use 90/50 = 1.8
// Movement tuning parameters - adjust these based on calibration results
#define TURN_ADJUSTMENT_FACTOR 0.1f    // Adjust if turns are not synchronized
#define FORWARD_ADJUSTMENT_FACTOR 0.1f  // Adjust if forward movement veers off
#define TEST_PAUSE_MS 1000             // Pause between movements

float base_speed_left = 1;  // Adjusted base speed
float base_speed_right = 1 * 0.85; // Adjusted base speed

void gpio_callback(uint gpio, uint32_t events) {
    if (gpio == LEFT_SENSOR_PIN || gpio == RIGHT_SENSOR_PIN) {
        encoder_gpio_callback(gpio, events);
    }
    else if (gpio == ECHO_PIN) {
        ultrasonic_gpio_callback(gpio, events);
    }
}

void stop_car() {
    leftmotor_stop();
    rightmotor_stop();
}

void flash_feedback() {
    leftmotor_forward(0.3f);
    rightmotor_forward(0.3f);
    sleep_ms(200);
    stop_car();
    sleep_ms(500);
}

void turn_by_angle(float target_degrees) {
    reset_encoder_counts();
    
    // Apply turn compensation factor
    float compensated_degrees = target_degrees * TURN_COMPENSATION;
    
    // Calculate arc length for the turn with compensation
    float turn_circumference = WHEELBASE_WIDTH_CM * M_PI;
    float arc_length = (fabsf(compensated_degrees) / 360.0f) * turn_circumference;
    
    // Calculate wheel distances
    float wheel_travel_distance = arc_length / 2.0f;
    
    // Convert to encoder notches needed for each wheel
    int32_t left_target_notches = (int32_t)(wheel_travel_distance / LEFT_CM_PER_NOTCH);
    int32_t right_target_notches = (int32_t)(wheel_travel_distance / RIGHT_CM_PER_NOTCH);
    
    flash_feedback();
    
    // PID variables for turn control
    float error = 0.0f;
    float last_error = 0.0f;
    float integral = 0.0f;
    absolute_time_t last_time = get_absolute_time();
    float smoothed_error = 0.0f;
    float alpha = 0.3f; // Smoothing factor
    
    if (target_degrees > 0) {  // Right turn
        leftmotor_forward(base_speed_left);
        rightmotor_backward(base_speed_right);
        
        while (get_left_encoder_count() < left_target_notches || 
               labs(get_right_encoder_count()) < right_target_notches) {
            
            absolute_time_t current_time = get_absolute_time();
            float delta_time = absolute_time_diff_us(last_time, current_time) / 1e6f;
            
            // Calculate error (maintain ratio between wheels during turn)
            float left_ratio = (float)get_left_encoder_count() / left_target_notches;
            float right_ratio = (float)labs(get_right_encoder_count()) / right_target_notches;
            error = left_ratio - right_ratio;
            
            // Error smoothing
            smoothed_error = alpha * error + (1.0f - alpha) * smoothed_error;
            
            // PID calculations
            integral += smoothed_error * delta_time;
            float derivative = (smoothed_error - last_error) / delta_time;
            
            // Limit integral windup
            if (integral > 1000.0f) integral = 1000.0f;
            if (integral < -1000.0f) integral = -1000.0f;
            
            float adjustment = (Kp * smoothed_error) + 
                             (Ki * integral) + 
                             (Kd * derivative);
            
            // Limit adjustment
            if (adjustment > 0.3f) adjustment = 0.3f;
            if (adjustment < -0.3f) adjustment = -0.3f;
            
            leftmotor_forward(base_speed_left - adjustment);
            rightmotor_backward(base_speed_right + adjustment);
            
            last_error = smoothed_error;
            last_time = current_time;
            
            sleep_ms(10);
        }
    } else {  // Left turn
        // Similar PID control for left turn
        leftmotor_backward(base_speed_left);
        rightmotor_forward(base_speed_right);
        
        while (labs(get_left_encoder_count()) < left_target_notches || 
               get_right_encoder_count() < right_target_notches) {
            
            absolute_time_t current_time = get_absolute_time();
            float delta_time = absolute_time_diff_us(last_time, current_time) / 1e6f;
            
            float left_ratio = (float)labs(get_left_encoder_count()) / left_target_notches;
            float right_ratio = (float)get_right_encoder_count() / right_target_notches;
            error = right_ratio - left_ratio;
            
            smoothed_error = alpha * error + (1.0f - alpha) * smoothed_error;
            
            integral += smoothed_error * delta_time;
            float derivative = (smoothed_error - last_error) / delta_time;
            
            if (integral > 1000.0f) integral = 1000.0f;
            if (integral < -1000.0f) integral = -1000.0f;
            
            float adjustment = (Kp * smoothed_error) + 
                             (Ki * integral) + 
                             (Kd * derivative);
            
            if (adjustment > 0.3f) adjustment = 0.3f;
            if (adjustment < -0.3f) adjustment = -0.3f;
            
            leftmotor_backward(base_speed_left + adjustment);
            rightmotor_forward(base_speed_right - adjustment);
            
            last_error = smoothed_error;
            last_time = current_time;
            
            sleep_ms(10);
        }
    }
    
    stop_car();
    flash_feedback();
}

void move_distance_cm(float distance_cm) {
    reset_encoder_counts();
    
    // Calculate notches needed for each wheel
    int32_t left_target_notches = (int32_t)(distance_cm / LEFT_CM_PER_NOTCH);
    int32_t right_target_notches = (int32_t)(distance_cm / RIGHT_CM_PER_NOTCH);
    
    flash_feedback();  // Flash feedback before starting
    
    // PID variables
    float error = 0.0f;
    float last_error = 0.0f;
    float integral = 0.0f;
    absolute_time_t last_time = get_absolute_time();
    float smoothed_error = 0.0f;
    float alpha = 0.3f; // Smoothing factor
    
    leftmotor_forward(base_speed_left);
    rightmotor_forward(base_speed_right);
    
    while (labs(get_left_encoder_count()) < left_target_notches || 
           labs(get_right_encoder_count()) < right_target_notches) {
        
        // PID calculations
        absolute_time_t current_time = get_absolute_time();
        float delta_time = absolute_time_diff_us(last_time, current_time) / 1e6f;
        
        // Calculate error between wheels
        error = get_left_encoder_count() - get_right_encoder_count();
        
        // Error smoothing
        smoothed_error = alpha * error + (1.0f - alpha) * smoothed_error;
        
        // Calculate PID terms
        integral += smoothed_error * delta_time;
        float derivative = (smoothed_error - last_error) / delta_time;
        
        // Limit integral windup
        if (integral > 1000.0f) integral = 1000.0f;
        if (integral < -1000.0f) integral = -1000.0f;
        
        // Calculate adjustment
        float adjustment = (Kp * smoothed_error) + 
                         (Ki * integral) + 
                         (Kd * derivative);
        
        // Limit adjustment
        if (adjustment > 0.3f) adjustment = 0.3f;
        if (adjustment < -0.3f) adjustment = -0.3f;
        
        // Apply adjustments
        leftmotor_forward(base_speed_left - adjustment);
        rightmotor_forward(base_speed_right + adjustment);
        
        // Update for next iteration
        last_error = smoothed_error;
        last_time = current_time;
        
        sleep_ms(10);
    }
    
    stop_car();
    flash_feedback();
}

void run_90_degree_turn_test(void) {
    sleep_ms(TEST_PAUSE_MS);
    turn_by_angle(90.0f);
}

void run_square_pattern_test(void) {
    for(int i = 0; i < 4; i++) {
        sleep_ms(TEST_PAUSE_MS);
        move_distance_cm(90.0f);
        sleep_ms(TEST_PAUSE_MS);
        turn_by_angle(90.0f);
    }
}

void run_forward_test(void) {
    sleep_ms(TEST_PAUSE_MS);
    move_distance_cm(90.0f);
}

int main() {
    stdio_init_all();

    // Initialize peripherals
    encoder_init();
    ultrasonic_init();

    // Initialize motor control pins
    gpio_init(IN1_PIN);
    gpio_set_dir(IN1_PIN, GPIO_OUT);
    gpio_init(IN2_PIN);
    gpio_set_dir(IN2_PIN, GPIO_OUT);
    gpio_init(IN3_PIN);
    gpio_set_dir(IN3_PIN, GPIO_OUT);
    gpio_init(IN4_PIN);
    gpio_set_dir(IN4_PIN, GPIO_OUT);

    // Initialize PWM and buttons
    setup_pwm(ENABLE_PIN, 2000);
    setup_pwm(ENABLE_PIN_RIGHT, 2000);
    setup_buttons();

    // Set up GPIO interrupts
    gpio_set_irq_enabled_with_callback(LEFT_SENSOR_PIN, 
        GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE, true, &gpio_callback);
    gpio_set_irq_enabled(RIGHT_SENSOR_PIN, 
        GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE, true);
    gpio_set_irq_enabled(ECHO_PIN, 
        GPIO_IRQ_EDGE_RISE | GPIO_IRQ_EDGE_FALL, true);

    // Initial feedback to show system is ready
    flash_feedback();

    while(1) {
        if (is_button_pressed(Button_Clockwise_Pin)) {  // GP20
            run_square_pattern_test();
        }
        
        if (is_button_pressed(Button_Counter_Pin)) {  // GP21
            run_90_degree_turn_test();
        }
        
        if (is_button_pressed(Button_Speed_Pin)) {  // GP22
            run_forward_test();
        }

        sleep_ms(100);
    }

    return 0;
}