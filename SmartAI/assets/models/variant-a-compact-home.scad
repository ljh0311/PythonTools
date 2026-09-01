// SmartAI robot chassis — Variant A: Compact Home
// Units: millimeters. Export: OpenSCAD → File → Export → STL/GLB
// Y-up when imported to Blender; rotate -90° X for glTF if needed.

$fn = 48;

// From config/robot_config.yaml (cm → mm)
body_w = 300;
body_l = 400;
body_h = 120;
wheel_d = 65;
wheel_w = 20;
wheelbase = 250;
track = 220;

module wheel() {
    rotate([90, 0, 0])
        cylinder(h = wheel_w, d = wheel_d, center = true);
}

module ultrasonic_mount(x, y) {
    translate([x, y, body_h/2 + 8])
        cube([40, 16, 16], center = true);
}

difference() {
    // Main deck
    hull() {
        translate([0, 0, body_h/2])
            scale([1, 1.15, 0.35])
                sphere(d = min(body_w, body_l) * 0.9);
        translate([0, 0, body_h/2 + 15])
            cube([body_w * 0.85, body_l * 0.7, 30], center = true);
    }
    // Pi bay
    translate([0, 30, body_h/2 + 10])
        cube([85, 56, 25], center = true);
}

// Wheels
for (x = [-wheelbase/2, wheelbase/2]) {
    for (y = [-track/2, track/2]) {
        translate([x, y, wheel_d/2])
            wheel();
    }
}

// Ultrasonic bumps (front, left, right)
ultrasonic_mount(0, body_l/2 - 30);
ultrasonic_mount(-body_w/2 + 25, 0);
ultrasonic_mount(body_w/2 - 25, 0);

// Camera mast (low)
translate([0, -body_l/2 + 40, body_h + 15])
    cylinder(h = 40, d = 25);

translate([0, -body_l/2 + 40, body_h + 55])
    cube([50, 12, 30], center = true);
