// Standalone export: service tray only (print separately, bolt to robot top)
// Export: openscad -o service-tray.stl service-tray-standalone.scad

include <service_tray.scad>

/* [Tray] */
tray_w = 260;
tray_l = 260;
bowl_depth = 16;
lip_h = 10;

service_tray(tray_w, tray_l, bowl_depth, lip_h);
