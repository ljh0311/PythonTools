#include "motor.h"

#include "pico/stdlib.h"
#include "hardware/pwm.h"
#include <stdint.h>
#include "hardware/structs/clocks.h"
#include "hardware/clocks.h"
#include <stdio.h>

// Define pins for motor control
#define IN1_PIN 0     // Changed to GPIO 0
#define IN2_PIN 1     // Changed to GPIO 1
#define IN3_PIN 2     // Changed to GPIO 2
#define IN4_PIN 3     // Changed to GPIO 3
#define ENABLE_PIN 16 // PWM pin for speed control
#define ENABLE_PIN_RIGHT 17

// Define buttons for motor control
#define Button_Clockwise_Pin 20
#define Button_Counter_Pin 21
#define Button_Speed_Pin 22

#define PWM_MAX_DUTY_CYCLE 65535
int my_clk_sys = 0;
int duty_cycle = PWM_MAX_DUTY_CYCLE;
float speed = 0.2;

// Function to set up PWM
void setup_pwm(uint pin, float frequency)
{
    gpio_set_function(pin, GPIO_FUNC_PWM);
    uint slice_num = pwm_gpio_to_slice_num(pin);
    pwm_set_wrap(slice_num, PWM_MAX_DUTY_CYCLE);                                      // 16-bit resolution for fine control of motor
    pwm_set_clkdiv(slice_num, (float)clock_get_hz(my_clk_sys) / (frequency * 65535)); // Alters frequency to enable the motor to work with the Pico's frequency
    pwm_set_enabled(slice_num, true);
}

// Function to control motor forward (clockwise)
void leftmotor_forward(uint16_t speed)
{
    gpio_put(IN1_PIN, 0);                               // IN1 = HIGH
    gpio_put(IN2_PIN, 1);                               // IN2 = LOW
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_A, speed);   // Set PWM duty cycle (0 - 65535)
}

// Function to control motor backward (counterclockwise)
void leftmotor_backward(uint16_t speed)
{
    gpio_put(IN1_PIN, 1);                               // IN1 = LOW
    gpio_put(IN2_PIN, 0);                               // IN2 = HIGH
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_A, speed);   // Set PWM duty cycle (0 - 65535)
}

// Function to stop the motor
void leftmotor_stop()
{
    gpio_put(IN1_PIN, 0);                               // IN1 = LOW
    gpio_put(IN2_PIN, 0);                               // IN2 = LOW
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_A, 0);       // Set PWM duty cycle to 0 (stop motor)
}

void rightmotor_forward(uint16_t speed)
{
    gpio_put(IN3_PIN, 0);                                     // IN3 = HIGH
    gpio_put(IN4_PIN, 1);                                     // IN4 = LOW
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_B, speed);         // Set PWM duty cycle (0 - 65535)
}

// Function to move right motor backward (counterclockwise)
void rightmotor_backward(uint16_t speed)
{
    gpio_put(IN3_PIN, 1);                                     // IN3 = LOW
    gpio_put(IN4_PIN, 0);                                     // IN4 = HIGH
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_B, speed);         // Set PWM duty cycle (0 - 65535)
}

// Function to stop the right motor
void rightmotor_stop()
{
    gpio_put(IN3_PIN, 0);                                     // IN3 = LOW
    gpio_put(IN4_PIN, 0);                                     // IN4 = LOW
    uint slice_num = pwm_gpio_to_slice_num(ENABLE_PIN_RIGHT); // Get PWM slice
    pwm_set_chan_level(slice_num, PWM_CHAN_B, 0);             // Set PWM duty cycle to 0 (stop motor)
}

void forwardMovement(float speed)
{
    leftmotor_forward(speed * duty_cycle); // Only single motor output
    rightmotor_forward(speed * duty_cycle * 0.95);
    printf("Foward Speed: %.2f\n", speed);

    sleep_ms(100);
}

void backwardMovement(float speed)
{
    leftmotor_backward(speed * duty_cycle);
    rightmotor_backward(speed * duty_cycle * 0.95);
    printf("Backward Speed: %.2f\n", speed);

    sleep_ms(100);
}

void gradualTurn(float speed, bool turn_left)
{
    if (turn_left)
    {
        leftmotor_forward(speed * duty_cycle);
        rightmotor_stop(); // Stop right motor for gradual left turn
    }
    else
    {
        rightmotor_forward(speed * duty_cycle);
        leftmotor_stop(); // Stop left motor for gradual right turn
    }
    printf("Gradual Turn Speed: %.2f\n", speed);

    sleep_ms(100);
}

// Function for sharp turn (e.g., one motor forward, one motor backward)
void sharpTurn(float speed, bool turn_left)
{
    if (turn_left)
    {
        leftmotor_backward(speed * duty_cycle);
        rightmotor_forward(speed * duty_cycle);
    }
    else
    {
        leftmotor_forward(speed * duty_cycle);
        rightmotor_backward(speed * duty_cycle);
    }
    printf("Sharp Turn Speed: %.2f\n", speed);

    sleep_ms(100);
}
float getSpeed()
{
    if (gpio_get(Button_Speed_Pin) == 0)
    {
        switch ((int)(speed * 10)) // Multiplying by 10 to handle float in switch
        {
        case 2: // speed == 0.2
            speed = 0.5;
            break;

        case 5: // speed == 0.5
            speed = 0.8;
            break;

        case 8: // speed == 0.8
            speed = 1;
        case 10:
        default: // For any other value, reset to 0.2
            speed = 0.2;
            break;
        }

        sleep_ms(500); // Debounce delay to avoid rapid toggling
    }
    return speed;
}

void setup_buttons()
{
    // Initialize button GPIOs
    gpio_init(Button_Counter_Pin);
    gpio_set_dir(Button_Counter_Pin, GPIO_IN);
    gpio_pull_up(Button_Counter_Pin); // Enable pull-up resistor

    gpio_init(Button_Clockwise_Pin);
    gpio_set_dir(Button_Clockwise_Pin, GPIO_IN);
    gpio_pull_up(Button_Clockwise_Pin); // Enable pull-up resistor

    gpio_init(Button_Speed_Pin);
    gpio_set_dir(Button_Speed_Pin, GPIO_IN);
    gpio_pull_up(Button_Speed_Pin); // Enable pull-up resistor
}
int main()
{
    gpio_init(IN1_PIN);
    gpio_set_dir(IN1_PIN, GPIO_OUT);
    gpio_init(IN2_PIN);
    gpio_set_dir(IN2_PIN, GPIO_OUT);
    gpio_init(IN3_PIN);
    gpio_set_dir(IN3_PIN, GPIO_OUT);
    gpio_init(IN4_PIN);
    gpio_set_dir(IN4_PIN, GPIO_OUT);
    stdio_init_all();

    setup_pwm(ENABLE_PIN, 2000); // Set PWM frequency to 1kHz
    setup_pwm(ENABLE_PIN_RIGHT, 2000);
    setup_buttons();

    while (true)
    {
        speed = 0.4;

        if (gpio_get(Button_Clockwise_Pin) == 0)
        {
            forwardMovement(speed);
            sleep_ms(10000);
            leftmotor_stop();
            rightmotor_stop();
            sleep_ms(500);
            backwardMovement(speed);
            sleep_ms(10000);
            leftmotor_stop();
            rightmotor_stop();
        }

        else if (gpio_get(Button_Counter_Pin) == 0)
        {
            backwardMovement(speed);
            sleep_ms(500);
            leftmotor_stop();
            rightmotor_stop();
        }
    }

    return 0;
}
