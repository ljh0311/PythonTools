// motor.c
#include "motor.h"
#include "hardware/structs/clocks.h"
#include "hardware/clocks.h"
#include <stdio.h>

// Global variables
int duty_cycle = PWM_MAX_DUTY_CYCLE;
float speed = 0.5;

#define DEBOUNCE_DELAY_MS 50 // Debounce delay in milliseconds

// Function to set up PWM
void setup_pwm(uint pin, float frequency)
{
    gpio_set_function(pin, GPIO_FUNC_PWM);
    uint slice_num = pwm_gpio_to_slice_num(pin);
    pwm_set_wrap(slice_num, PWM_MAX_DUTY_CYCLE); // 16-bit resolution

    // Use clk_sys directly
    float clk_div = (float)clock_get_hz(clk_sys) / (frequency * PWM_MAX_DUTY_CYCLE);
    pwm_set_clkdiv(slice_num, clk_div);
    pwm_set_enabled(slice_num, true);
}

// Left motor functions
void leftmotor_forward(float speed)
{
    // Clamp speed
    if (speed > 1.0f) speed = 1.0f;
    if (speed < 0.0f) speed = 0.0f;

    uint16_t speed_value = (uint16_t)(speed * duty_cycle);
    gpio_put(IN1_PIN, 0);
    gpio_put(IN2_PIN, 1);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN);
    pwm_set_chan_level(slice_num, PWM_CHAN_A, speed_value);
}

void leftmotor_backward(float speed)
{
    // Clamp speed
    if (speed > 1.0f) speed = 1.0f;
    if (speed < 0.0f) speed = 0.0f;

    uint16_t speed_value = (uint16_t)(speed * duty_cycle);
    gpio_put(IN1_PIN, 1);
    gpio_put(IN2_PIN, 0);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN);
    pwm_set_chan_level(slice_num, PWM_CHAN_A, speed_value);
}

void leftmotor_stop()
{
    gpio_put(IN1_PIN, 0);
    gpio_put(IN2_PIN, 0);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN);
    pwm_set_chan_level(slice_num, PWM_CHAN_A, 0);
}

// Right motor functions
void rightmotor_forward(float speed)
{
    // Clamp speed
    if (speed > 1.0f) speed = 1.0f;
    if (speed < 0.0f) speed = 0.0f;

    uint16_t speed_value = (uint16_t)(speed * duty_cycle);
    gpio_put(IN3_PIN, 0);
    gpio_put(IN4_PIN, 1);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT);
    pwm_set_chan_level(slice_num, PWM_CHAN_B, speed_value);
}

void rightmotor_backward(float speed)
{
    // Clamp speed
    if (speed > 1.0f) speed = 1.0f;
    if (speed < 0.0f) speed = 0.0f;

    uint16_t speed_value = (uint16_t)(speed * duty_cycle);
    gpio_put(IN3_PIN, 1);
    gpio_put(IN4_PIN, 0);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT);
    pwm_set_chan_level(slice_num, PWM_CHAN_B, speed_value);
}

void rightmotor_stop()
{
    gpio_put(IN3_PIN, 0);
    gpio_put(IN4_PIN, 0);
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT);
    pwm_set_chan_level(slice_num, PWM_CHAN_B, 0);
}

// Function to set up buttons
void setup_buttons()
{
    gpio_init(Button_Clockwise_Pin);
    gpio_set_dir(Button_Clockwise_Pin, GPIO_IN);
    gpio_pull_up(Button_Clockwise_Pin);

    gpio_init(Button_Counter_Pin);
    gpio_set_dir(Button_Counter_Pin, GPIO_IN);
    gpio_pull_up(Button_Counter_Pin);

    gpio_init(Button_Speed_Pin);
    gpio_set_dir(Button_Speed_Pin, GPIO_IN);
    gpio_pull_up(Button_Speed_Pin);
}

bool is_button_pressed(uint gpio_pin)
{
    static absolute_time_t last_button_time[29] = {0}; // Assuming GPIO pins up to 28
    absolute_time_t current_time = get_absolute_time();

    if (gpio_get(gpio_pin) == 0) { // Active low button
        if (absolute_time_diff_us(last_button_time[gpio_pin], current_time) / 1000 > DEBOUNCE_DELAY_MS) {
            last_button_time[gpio_pin] = current_time;
            return true;
        }
    }
    return false;
}
