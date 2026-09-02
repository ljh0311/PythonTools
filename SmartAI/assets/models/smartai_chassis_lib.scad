// SmartAI chassis library — Japandi Zen Slab Stack
// Units: mm. Origin: body center XY, Z = floor.
// GPIO ultrasonics: front GPIO5 (+Y), left GPIO6 (-X), right GPIO13 (+X)
// Avoid minkowski spheres — rounded_box uses offset + linear_extrude.

// --- Japandi palette (#hex → preview RGB) ---
COL_OFF_WHITE = [240 / 255, 237 / 255, 232 / 255, 1]; // #F0EDE8 body slab
COL_CHARCOAL  = [58 / 255, 58 / 255, 58 / 255, 1];   // #3A3A3A base skirt
COL_OAK       = [166 / 255, 124 / 255, 82 / 255, 1]; // #A67C52 top plate / column
COL_STONE     = [156 / 255, 156 / 255, 148 / 255, 1]; // #9C9C94 accents
COL_SHADOW    = [0.12, 0.12, 0.13, 1];               // 2 mm layer gap
COL_WHEEL     = [0.10, 0.10, 0.10, 1];
COL_TIRE      = [0.20, 0.20, 0.22, 1];
COL_SENSOR    = [0.18, 0.55, 0.78, 1];
COL_LENS      = [0.04, 0.04, 0.05, 1];

// Legacy aliases (variant MMU comments)
COL_BODY   = COL_OFF_WHITE;
COL_TRIM   = COL_OAK;
COL_BUMPER = COL_STONE;
COL_BATTERY = [0.35, 0.22, 0.12, 1];
COL_LIDAR  = COL_STONE;

HC_SR04_W = 45;
HC_SR04_H = 20;
HC_SR04_DEPTH = 16;
PI5_W = 85;
PI5_L = 56;
PI5_CLEARANCE = 2;
PI5_STACK_H = 25;

ZEN_SKIRT_H = 8;
ZEN_GAP_H   = 2;
ZEN_TOP_T   = 4;

function deck_bottom_z(wheel_d, clearance = 0) = wheel_d + clearance;
function zen_slab_h(body_h, skirt_h = ZEN_SKIRT_H, gap = ZEN_GAP_H, top_t = ZEN_TOP_T) =
    body_h - skirt_h - top_t - 2 * gap;

// --- Primitives (no minkowski) ---
module rounded_box(w, l, h, r) {
    linear_extrude(height = h, center = true)
        offset(r = r)
            square([w - 2 * r, l - 2 * r], center = true);
}

module rounded_prism_xy(w, l, h, r) {
    linear_extrude(height = h, center = true)
        offset(r = r)
            square([w - 2 * r, l - 2 * r], center = true);
}

// --- Zen slab layering ---
module shadow_gap(w, l, fillet, z_center, gap_h = ZEN_GAP_H, band_t = 2.5) {
    color(COL_SHADOW)
        translate([0, 0, z_center])
            linear_extrude(height = gap_h, center = true)
                difference() {
                    offset(r = fillet)
                        square([w - 2 * fillet, l - 2 * fillet], center = true);
                    offset(r = max(fillet - 1, 1))
                        square([w - 2 * fillet - 2 * band_t, l - 2 * fillet - 2 * band_t], center = true);
                }
}

module zen_slab_stack(body_w, body_l, body_h, fillet, z0,
                      skirt_h = ZEN_SKIRT_H, gap = ZEN_GAP_H, top_t = ZEN_TOP_T,
                      top_inset = 8) {
    slab_h = zen_slab_h(body_h, skirt_h, gap, top_t);
    z_skirt  = z0 + skirt_h / 2;
    z_gap1   = z0 + skirt_h + gap / 2;
    z_slab   = z0 + skirt_h + gap + slab_h / 2;
    z_gap2   = z0 + skirt_h + gap + slab_h + gap / 2;
    z_top    = z0 + skirt_h + gap + slab_h + gap + top_t / 2;
    tw = body_w - top_inset;
    tl = body_l - top_inset;
    tf = max(fillet - 4, 12);

    color(COL_CHARCOAL)
        translate([0, 0, z_skirt])
            rounded_box(body_w, body_l, skirt_h, fillet);

    shadow_gap(body_w, body_l, fillet, z_gap1, gap);

    color(COL_OFF_WHITE)
        translate([0, 0, z_slab])
            rounded_box(body_w, body_l, slab_h, fillet);

    shadow_gap(tw + 4, tl + 4, tf + 2, z_gap2, gap);

    color(COL_OAK)
        translate([0, 0, z_top])
            rounded_box(tw, tl, top_t, tf);
}

module zen_slab_hollow(body_w, body_l, body_h, fillet, z0, wall_t,
                       skirt_h = ZEN_SKIRT_H, gap = ZEN_GAP_H, top_t = ZEN_TOP_T) {
    slab_h = zen_slab_h(body_h, skirt_h, gap, top_t);
    z_slab = z0 + skirt_h + gap + slab_h / 2;
    translate([0, 0, z_slab])
        rounded_box(body_w - 2 * wall_t, body_l - 2 * wall_t, slab_h - wall_t + 2, max(fillet - 4, 10));
}

// --- Wheels: rear L/R drive + front-centre castor (+Y = front, -Y = rear) ---
module wheel(wheel_d, wheel_w, hub_d = 28) {
    translate([0, 0, wheel_d / 2])
        rotate([90, 0, 0]) {
            color(COL_TIRE)
                cylinder(h = wheel_w, d = wheel_d, center = true);
            color(COL_WHEEL)
                cylinder(h = wheel_w + 0.4, d = hub_d, center = true);
            color(COL_STONE)
                for (s = [-1, 1])
                    translate([0, s * (wheel_w / 2 - 1.5), 0])
                        cylinder(h = 3, d = hub_d * 0.55, center = true, $fn = 6);
        }
}

// Passive front castor (smaller, no motor boss)
module castor_wheel(castor_d, castor_w = 14) {
    translate([0, 0, castor_d / 2])
        rotate([90, 0, 0]) {
            color(COL_TIRE)
                cylinder(h = castor_w, d = castor_d, center = true);
            color(COL_STONE)
                cylinder(h = castor_w + 2, d = castor_d * 0.45, center = true);
        }
}

// wheel_distance = L/R spacing on rear axle (matches robot_config wheel_distance)
module place_wheels_trike(wheel_distance, drive_axle_y, wheel_d, wheel_w,
                          castor_y, castor_d = 40, castor_w = 14) {
    translate([-wheel_distance / 2, drive_axle_y, 0])
        wheel(wheel_d, wheel_w);
    translate([wheel_distance / 2, drive_axle_y, 0])
        wheel(wheel_d, wheel_w);
    translate([0, castor_y, 0])
        castor_wheel(castor_d, castor_w);
}

// Legacy alias — do not use for new layouts
module place_wheels(wheel_distance, drive_axle_y, wheel_d, wheel_w,
                    castor_y, castor_d = 40, castor_w = 14) {
    place_wheels_trike(wheel_distance, drive_axle_y, wheel_d, wheel_w, castor_y, castor_d, castor_w);
}

module wheel_well_cut(x, y, wheel_d, wheel_w, fender_r = 38) {
    translate([x, y, wheel_d / 2])
        rotate([90, 0, 0])
            cylinder(h = wheel_w + 8, d = wheel_d + 14, center = true);
    translate([x, y, wheel_d * 0.55])
        rotate([90, 0, 0])
            cylinder(h = wheel_w + 20, d = fender_r * 2, center = true);
}

module castor_well_cut(x, y, castor_d, castor_w = 14) {
    translate([x, y, castor_d / 2])
        rotate([90, 0, 0])
            cylinder(h = castor_w + 6, d = castor_d + 10, center = true);
}

module wheel_wells_trike(wheel_distance, drive_axle_y, wheel_d, wheel_w,
                         castor_y, castor_d = 40, castor_w = 14) {
    wheel_well_cut(-wheel_distance / 2, drive_axle_y, wheel_d, wheel_w);
    wheel_well_cut(wheel_distance / 2, drive_axle_y, wheel_d, wheel_w);
    castor_well_cut(0, castor_y, castor_d, castor_w);
}

module shell_rounded_cut(wheel_distance, drive_axle_y, wheel_d, wheel_w,
                         castor_y, castor_d = 40, castor_w = 14) {
    wheel_wells_trike(wheel_distance, drive_axle_y, wheel_d, wheel_w, castor_y, castor_d, castor_w);
}

// --- Slot sensors (thin edge windows, not protruding blocks) ---
module slot_sensor_cut(x, y, z, yaw = 0, slot_w = HC_SR04_W, slot_h = 5, depth = 20) {
    translate([x, y, z])
        rotate([0, 0, yaw])
            rounded_box(slot_w + 2, depth, slot_h, 1);
}

module slot_sensor(x, y, z, yaw = 0) {
    color(COL_CHARCOAL)
        translate([x, y, z])
            rotate([0, 0, yaw])
                difference() {
                    rounded_prism_xy(HC_SR04_W + 6, HC_SR04_DEPTH + 4, HC_SR04_H + 4, 2);
                    translate([0, 3, 0])
                        rounded_prism_xy(HC_SR04_W, HC_SR04_DEPTH, HC_SR04_H, 1.5);
                }
    color(COL_SENSOR)
        translate([x, y - 2, z])
            rotate([0, 0, yaw])
                rounded_prism_xy(HC_SR04_W - 6, 8, HC_SR04_H - 6, 1);
}

module slot_sensor_triplet(body_w, body_l, mount_z, inset = 28) {
    slot_sensor(0, body_l / 2 - inset, mount_z, 0);
    slot_sensor(-body_w / 2 + inset, 0, mount_z, 90);
    slot_sensor(body_w / 2 - inset, 0, mount_z, -90);
}

module slot_sensor_triplet_cuts(body_w, body_l, mount_z, inset = 28) {
    slot_sensor_cut(0, body_l / 2 - inset, mount_z, 0);
    slot_sensor_cut(-body_w / 2 + inset, 0, mount_z, 90);
    slot_sensor_cut(body_w / 2 - inset, 0, mount_z, -90);
}

module ultrasonic_triplet(body_w, body_l, mount_z, inset = 28) {
    slot_sensor_triplet(body_w, body_l, mount_z, inset);
}

// --- Pi 5 bay ---
module pi5_bay_cutout(offset_y = 0, deck_bottom = 0, body_h = 0) {
    translate([0, offset_y, deck_bottom + body_h / 2])
        rounded_box(PI5_W + 2 * PI5_CLEARANCE, PI5_L + 2 * PI5_CLEARANCE, body_h + 2, 4);
}

module pi5_stack(x, y, z) {
    color([0.12, 0.45, 0.28, 1])
        translate([x, y, z])
            union() {
                rounded_box(PI5_W, PI5_L, 3, 2);
                translate([0, 0, PI5_STACK_H / 2])
                    rounded_box(PI5_W - 6, PI5_L - 6, PI5_STACK_H - 3, 2);
                for (sx = [-1, 1], sy = [-1, 1])
                    translate([sx * 30, sy * 20, 2])
                        cylinder(h = 6, d = 6, $fn = 16);
            }
}

// --- Flush camera (smart-speaker front circle) ---
module camera_flush(x, y, z, dia = 24, depth = 2) {
    color(COL_LENS)
        translate([x, y, z])
            rotate([90, 0, 0])
                cylinder(h = depth, d = dia, center = true);
    color(COL_CHARCOAL)
        translate([x, y - depth * 0.3, z])
            rotate([90, 0, 0])
                cylinder(h = 1.2, d = dia * 0.55, center = true);
}

module camera_flush_cut(x, y, z, dia = 26, depth = 4) {
    translate([x, y, z])
        rotate([90, 0, 0])
            cylinder(h = depth, d = dia, center = true);
}

// --- LiDAR: architectural oak square column (Variant B) ---
module lidar_column(x, y, z_base, col_size = 30, col_h = 132,
                    puck_d = 68, puck_h = 22, fillet = 3) {
    color(COL_OAK)
        translate([x, y, z_base + col_h / 2])
            rounded_box(col_size, col_size, col_h, fillet);
    color(COL_STONE)
        translate([x, y, z_base + col_h + puck_h / 2])
            cylinder(h = puck_h, d = puck_d, center = true);
    color(COL_CHARCOAL)
        translate([x, y, z_base + col_h + puck_h / 2])
            cylinder(h = puck_h - 6, d = puck_d * 0.35, center = true);
}

// --- Credenza shell (Variant C wide low form) ---
module credenza_shell(body_w, body_l, body_h, fillet, z0, wall_t,
                      wheel_distance, drive_axle_y, wheel_d, wheel_w,
                      castor_y, castor_d = 40, castor_w = 14) {
    difference() {
        zen_slab_stack(body_w, body_l, body_h, fillet, z0);
        zen_slab_hollow(body_w, body_l, body_h, fillet, z0, wall_t);
        shell_rounded_cut(wheel_distance, drive_axle_y, wheel_d, wheel_w, castor_y, castor_d, castor_w);
    }
}

// --- Battery well with oak cover lip (Variant C) ---
module battery_well_cut(w, l, h, x, y, z) {
    translate([x, y, z])
        rounded_box(w, l, h, 6);
}

module battery_well_lip(w, l, lip_t, x, y, z, inset = 6) {
    color(COL_OAK)
        translate([x, y, z + lip_t / 2])
            difference() {
                rounded_box(w + inset, l + inset, lip_t, 4);
                translate([0, 0, -0.5])
                    rounded_box(w - 4, l - 4, lip_t + 2, 3);
            }
}

module battery_pack(w, l, h) {
    color(COL_BATTERY)
        rounded_box(w, l, h, 6);
}

// --- Functional deck features ---
module motor_mount_boss(x, y, z, boss_d = 22, boss_h = 8) {
    color(COL_STONE)
        translate([x, y, z + boss_h / 2])
            cylinder(h = boss_h, d = boss_d, center = true);
}

module motor_mounts_rear_drive(wheel_distance, drive_axle_y, z) {
    motor_mount_boss(-wheel_distance / 2, drive_axle_y, z);
    motor_mount_boss(wheel_distance / 2, drive_axle_y, z);
}

// Legacy name — rear drive pair only (no castor mount)
module motor_mounts_quad(wheel_distance, drive_axle_y, z) {
    motor_mounts_rear_drive(wheel_distance, drive_axle_y, z);
}

module wiring_groove(x1, y1, x2, y2, z, groove_w = 6, groove_d = 2) {
    translate([(x1 + x2) / 2, (y1 + y2) / 2, z - groove_d / 2])
        rotate([0, 0, atan2(y2 - y1, x2 - x1)])
            cube([norm([x2 - x1, y2 - y1]), groove_w, groove_d], center = true);
}

module wiring_grooves_pi(pi_y, z_top) {
    wiring_groove(0, pi_y, -80, pi_y, z_top, 5, 2);
    wiring_groove(80, pi_y, 0, pi_y, z_top, 5, 2);
    wiring_groove(0, pi_y, 0, pi_y + 40, z_top, 5, 2);
}

module japandi_front_lip(body_w, body_l, z_base, lip_h = 6, lip_t = 4) {
    color(COL_STONE)
        translate([0, body_l / 2 - lip_t / 2, z_base + lip_h / 2])
            rounded_box(body_w - 12, lip_t, lip_h, 2);
}

module status_led(x, y, z) {
    color(COL_SENSOR)
        translate([x, y, z])
            cylinder(h = 1.5, d = 6, center = true, $fn = 24);
}

module smartai_assembly() {
    union() {
        children();
    }
}
