// SmartAI robot chassis — Variant C: Wide Stable
// Wide wheelbase for straight-line trim tuning and heavy battery.

$fn = 48;

body_w = 360;
body_l = 420;
body_h = 90;
wheel_d = 80;
wheel_w = 25;
wheelbase = 320;
track = 300;

module wheel() {
    rotate([90, 0, 0])
        cylinder(h = wheel_w, d = wheel_d, center = true);
}

// Low wide platform
difference() {
    hull() {
        translate([-body_w/2, -body_l/2, 0])
            cylinder(h = body_h, d = 40);
        translate([body_w/2, -body_l/2, 0])
            cylinder(h = body_h, d = 40);
        translate([body_w/2, body_l/2, 0])
            cylinder(h = body_h, d = 40);
        translate([-body_w/2, body_l/2, 0])
            cylinder(h = body_h, d = 40);
    }
    translate([0, 0, 15])
        cube([body_w - 30, body_l - 30, body_h], center = true);
}

for (x = [-wheelbase/2, wheelbase/2]) {
    for (y = [-track/2, track/2]) {
        translate([x, y, wheel_d/2])
            wheel();
    }
}

// Battery tray (rear)
translate([0, body_l/2 - 50, body_h + 12])
    cube([140, 80, 24], center = true);

// Dual ultrasonic (front corners)
for (sx = [-1, 1]) {
    translate([sx * (body_w/2 - 30), body_l/2 - 20, body_h + 10])
        cube([35, 14, 14], center = true);
}

// Pi stack (center)
translate([0, 0, body_h + 18])
    cube([90, 60, 28], center = true);
