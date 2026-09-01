// SmartAI robot chassis — Variant B: Tall Navigator
// Taller mast for camera + future LiDAR. Indoor navigation focus.

$fn = 48;

body_w = 300;
body_l = 400;
body_h = 100;
wheel_d = 70;
wheel_w = 22;
wheelbase = 280;
track = 240;
mast_h = 180;

module wheel() {
    rotate([90, 0, 0])
        cylinder(h = wheel_w, d = wheel_d, center = true);
}

// Rectangular aluminum-style base
difference() {
    cube([body_w, body_l, body_h], center = true);
    translate([0, 0, 5])
        cube([body_w - 20, body_l - 20, body_h], center = true);
}

for (x = [-wheelbase/2, wheelbase/2]) {
    for (y = [-track/2, track/2]) {
        translate([x, y, -body_h/2 + wheel_d/2])
            wheel();
    }
}

// Central mast
translate([0, -body_l/4, body_h/2])
    cylinder(h = mast_h, d = 35);

// LiDAR puck (placeholder)
translate([0, -body_l/4, body_h/2 + mast_h])
    cylinder(h = 30, d = 70);

// Camera module
translate([0, -body_l/4, body_h/2 + mast_h * 0.45])
    rotate([15, 0, 0])
        cube([60, 18, 22], center = true);

// Ultrasonic array bar
translate([0, body_l/2 - 25, body_h/2 + 20])
    cube([body_w - 40, 12, 14], center = true);
