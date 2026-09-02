// SmartAI service tray — removable drink/food carrier
// Units: mm. Mounts on zen slab oak top plate (Variant A default).
// Design goals: easy to clean (smooth bowl, drain slope), easy to integrate (bolt flange).

// --- Defaults (Customizer when included from service-tray-standalone.scad) ---
TRAY_W = 260;
TRAY_L = 260;
BOWL_DEPTH = 16;
LIP_H = 10;
FLANGE_T = 4;
DRAIN_SLOPE = 0.018;  // ~1° toward rear-left for spill runoff
LIP_THICK = 3;
BOWL_FILLET = 12;

// Mount: 4× M3 clearance on square pattern
MOUNT_HOLE_D = 3.4;
MOUNT_SPREAD_W = 220;
MOUNT_SPREAD_L = 220;

module tray_bowl_interior(w, l, depth, fillet) {
  // Smooth rounded cavity — no sharp corners (easy to wipe)
  translate([0, 0, -depth / 2])
    hull() {
      for (sx = [-1, 1], sy = [-1, 1])
        translate([sx * (w / 2 - fillet), sy * (l / 2 - fillet), 0])
          sphere(r = fillet);
      translate([0, 0, -depth + fillet])
        scale([1, 1, 0.35])
          sphere(r = fillet);
    }
}

module service_tray(
  w = TRAY_W,
  l = TRAY_L,
  bowl_depth = BOWL_DEPTH,
  lip_h = LIP_H,
  flange_t = FLANGE_T,
  drain_slope = DRAIN_SLOPE
) {
  color([0.92, 0.90, 0.86, 1])  // warm off-white — food-safe print material hint
    union() {
      // Mounting flange (sits on oak top plate)
      translate([0, 0, flange_t / 2])
        linear_extrude(height = flange_t, center = true)
          offset(r = 6)
            square([w + 8, l + 8], center = true);

      // Lip ring
      translate([0, 0, flange_t + lip_h / 2])
        difference() {
          linear_extrude(height = lip_h, center = true)
            offset(r = 4)
              square([w + 4, l + 4], center = true);
          translate([0, 0, -1])
            linear_extrude(height = lip_h + 2)
              square([w - LIP_THICK, l - LIP_THICK], center = true);
        }

      // Bowl (sloped floor: rear-left lowest)
      translate([0, 0, flange_t + bowl_depth / 2])
        rotate([atan(drain_slope * l), -atan(drain_slope * w), 0])
          difference() {
            linear_extrude(height = bowl_depth, center = true, convexity = 8)
              offset(r = 8)
                square([w - 16, l - 16], center = true);
            tray_bowl_interior(w - 20, l - 20, bowl_depth - 2, BOWL_FILLET);
          }
    }

  // Drain well at lowest corner (rear-left, -X -Y)
  color([0.75, 0.75, 0.78, 1])
    translate([-w / 2 + 18, -l / 2 + 18, flange_t + 2])
      cylinder(h = 4, d = 8, $fn = 24);
}

module service_tray_mount_holes(
  spread_w = MOUNT_SPREAD_W,
  spread_l = MOUNT_SPREAD_L,
  hole_d = MOUNT_HOLE_D,
  z = 0
) {
  for (sx = [-1, 1], sy = [-1, 1])
    translate([sx * spread_w / 2, sy * spread_l / 2, z])
      cylinder(h = 20, d = hole_d, center = true, $fn = 20);
}

// Integrate on robot: flange bottom flush with oak top
module service_tray_on_robot(z_top, w = TRAY_W, l = TRAY_L) {
  translate([0, 0, z_top + FLANGE_T / 2])
    service_tray(w, l);
}

// Cut bolt holes through oak top + slab (call from variant difference())
module service_tray_mount_cuts(z_top, spread_w = MOUNT_SPREAD_W, spread_l = MOUNT_SPREAD_L) {
  service_tray_mount_holes(spread_w, spread_l, MOUNT_HOLE_D, z_top);
}
