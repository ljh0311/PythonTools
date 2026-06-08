// encoder.h
#ifndef ENCODER_H
#define ENCODER_H

#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"

// Define pins for wheel encoders
#define LEFT_SENSOR_PIN 9
#define RIGHT_SENSOR_PIN 4

// Physical measurements
#define ENCODER_NOTCHES 20
#define WHEEL_DIAMETER_CM 6.4f
#define WHEELBASE_WIDTH_CM 11.5f  // Distance between wheels

// Calibrated values based on measured wheel rotation
#define LEFT_DEGREES_PER_NOTCH 10.75f  // Measured: 215° / 20 notches
#define RIGHT_DEGREES_PER_NOTCH 12.75f // Measured: 255° / 20 notches

// Calculate distance per notch for each wheel
#define LEFT_CM_PER_NOTCH ((LEFT_DEGREES_PER_NOTCH/360.0f) * (WHEEL_DIAMETER_CM * M_PI))
#define RIGHT_CM_PER_NOTCH ((RIGHT_DEGREES_PER_NOTCH/360.0f) * (WHEEL_DIAMETER_CM * M_PI))

void encoder_init(void);
void encoder_gpio_callback(uint gpio, uint32_t events);
int32_t get_left_encoder_count(void);
int32_t get_right_encoder_count(void);
void reset_encoder_counts(void);

#endif // ENCODER_H