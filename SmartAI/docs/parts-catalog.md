# SmartAI parts catalog

Parts compatible with this project's stack: **Raspberry Pi GPIO**, **L298N-style dual motor driver**, **HC-SR04 ultrasonics**, **USB/CSI camera**, **differential drive**.

> Images link to vendor pages. Verify pinout and voltage before wiring — Pi GPIO is **3.3 V logic**.

---

## 1. Compute — Raspberry Pi 5 (4 GB+)

| Spec | Value |
|------|--------|
| Role | Host: Flask GUI, navigation, vision, motor trim |
| OS | Raspberry Pi OS (Bookworm) / Debian |
| GPIO | 3.3 V — use level shifting for 5 V sensor echo |
| SmartAI config | Simulation on Windows; `RPi.GPIO` on Pi |

![Raspberry Pi 5](https://www.raspberrypi.com/wp-content/uploads/2023/09/raspberry-pi-5-product-photo.jpg)

- [Raspberry Pi 5 product page](https://www.raspberrypi.com/products/raspberry-pi-5/)

---

## 2. Motor driver — L298N dual H-bridge

| Spec | Value |
|------|--------|
| Channels | 2 DC motors (left/right) |
| Logic | IN1–IN4 direction, ENA/ENB PWM speed |
| Motor supply | 7–12 V typical (separate from Pi logic) |
| SmartAI pins | See `config/robot_config.yaml` `hardware.left_motor` / `right_motor` |

Wiring notes:
- Share **GND** between Pi, driver, and battery.
- Do **not** feed 5 V motor-driver logic into Pi GPIO without level shift.
- [Pi forums — L298N wiring](https://forums.raspberrypi.com/viewtopic.php?t=76448)

---

## 3. Ultrasonic — HC-SR04 (×3: front, left, right)

| Spec | Value |
|------|--------|
| Range | ~2 cm – 400 cm |
| Trigger | 10 µs pulse on TRIG |
| Echo | 5 V output — **voltage divider required** on Pi |
| Divider | 1 kΩ + 2 kΩ (Echo → Pi GPIO) |
| SmartAI GPIO | front `5`, left `6`, right `13` |

![HC-SR04](https://cdn.shopify.com/s/files/1/0172/7444/9664/files/hc-sr04-ultrasonic-sensor-module.jpg)

- [The Pi Hut — HC-SR04 on Raspberry Pi](https://thepihut.com/blogs/raspberry-pi-tutorials/hc-sr04-ultrasonic-range-sensor-on-the-raspberry-pi)
- [Pi My Life Up tutorial](https://pimylifeup.com/raspberry-pi-distance-sensor/)

---

## 4. Camera — USB or CSI module

| Spec | Value |
|------|--------|
| SmartAI default | 640×480 @ 30 fps (`hardware.camera`) |
| Use | Visual odometry, obstacle hints, homeowner UI |
| Note | Blocking `read()` can stall ticks — headless tests disable camera |

Pi Camera Module 3 or USB UVC webcam (720p+).

---

## 5. Chassis options (complete platforms)

### A. RaspRover (Waveshare) — 4WD, metal, Pi 5

| Spec | Value |
|------|--------|
| Size | 172 × 183 × 132–251 mm (variant) |
| Drive | 4 wheels, ~0.65 m/s max |
| Extras | Camera, IMU, ESP32 co-processor, ROS2 Humble option |
| Fit | Strong match if you want turnkey vision + motion |

![RaspRover](https://www.waveshare.com/media/catalog/product/cache/1/image/9df78eab33525d08d6e5fb8d27136e95/r/a/rasprover-1.jpg)

- [Waveshare RaspRover](https://www.waveshare.com/product/robotics/mobile-robots/raspberry-pi-robots/rasprover.htm)

### B. MicroROS-Pi5 (Yahboom) — encoder motors + LiDAR

| Spec | Value |
|------|--------|
| Body | 238 × 153 × 124 mm, aluminum |
| Motors | 310 metal gear + encoders ×4 |
| Sensors | MS200 LiDAR, 6-axis IMU, 2 MP camera gimbal |
| Power | 7.4 V 2000 mAh 2S (~2 h) |
| Fit | Best for **encoder-based trim learning** and nav mesh |

![MicroROS-Pi5](https://cdn.shopify.com/s/files/1/0561/2341/8955/files/Yahboom_MicroROS-Pi5_Robot_Car_1.jpg)

- [Robocraze — MicroROS-Pi5](https://robocraze.com/products/microros-pi5-ros2-robot-car)

### C. XiaoR GEEK — 4-wheel differential (DIY)

| Spec | Value |
|------|--------|
| Material | Aluminum alloy |
| Mounting | Holes for Pi 5, ultrasonics, camera |
| Fit | Blank platform — closest to **custom SmartAI** wiring |

- [Tindie — XiaoR 4WD chassis](https://www.tindie.com/products/xiaor-geek/4-wheel-differential-chassis-robotic-platform/)

### D. Yahboom TT-motor acrylic kit — budget DIY

| Spec | Value |
|------|--------|
| Motors | 4× TT geared DC |
| Material | 2.5 mm acrylic |
| Fit | Cheap test rig; add your own Pi + L298N + HC-SR04 |

- [Yahboom chassis kit](https://www.motormaker.net/product/4106/yahboom-smart-robot-chassis-kit-with-4-tt-motor-4-wheels-robot-car-chassis-for-umo-r3-raspberry-pi-jetson-nano-electronic-diy-learning-kit)

---

## 6. Recommended bill of materials (minimal SmartAI build)

| Qty | Part | Notes |
|-----|------|--------|
| 1 | Raspberry Pi 5 4 GB | + 27 W USB-C PSU |
| 1 | L298N motor driver | Or integrated Pi hat |
| 2 | DC geared motors + wheels | ~200–250 mm wheelbase |
| 3 | HC-SR04 + resistor kit | Echo dividers per sensor |
| 1 | USB webcam or Pi Camera | Matches `device_id: 0` |
| 1 | 2S LiPo + BMS | Match motor voltage |
| 1 | Chassis (C or D above) | Mount ultrasonics front/left/right |

---

## 7. Match to SmartAI software

| Feature | Hardware need |
|---------|----------------|
| Motor trim sliders | Any dual-motor driver |
| Auto-learn trim | Encoder feedback or IMU/VO (MicroROS-Pi5 class) |
| Ultrasonic proximity | HC-SR04 ×3 + dividers |
| Autonomous nav | Flat floor + optional LiDAR for replanning |
| Web + GUI | Pi on same LAN as phone/laptop |

---

## Sources

- [ThinkRobotics — beginner chassis guide (2025)](https://thinkrobotics.com/blogs/diy-projects/top-10-robotics-kits-for-beginners-in-2025)
- [Waveshare RaspRover specs](https://www.waveshare.com/product/robotics/mobile-robots/raspberry-pi-robots/rasprover.htm)
- [Robocraze MicroROS-Pi5 specs](https://robocraze.com/products/microros-pi5-ros2-robot-car)
