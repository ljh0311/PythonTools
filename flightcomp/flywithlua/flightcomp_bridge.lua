--[[
  Flightcomp X-Plane 11 / FlyWithLua bridge
  Sends simulator state (position, heading, COM1) to the flightcomp app via UDP.
  Optionally receives ATC messages from flightcomp for on-screen display.

  REQUIREMENTS:
  - FlyWithLua (NG or standard) for X-Plane 11
  - LuaSocket: If your FlyWithLua build does not include socket, you may need
    to add LuaSocket or use the file-based fallback (see README).

  SETUP:
  1. Copy this script to your FlyWithLua Scripts folder, e.g.:
     X-Plane 11/Resources/plugins/FlyWithLua/Scripts/
  2. Ensure flightcomp is running with "Use X-Plane context" enabled (port 49000).
  3. Reload FlyWithLua scripts or restart X-Plane.

  PACKET FORMAT (sent every 2 seconds to 127.0.0.1:49000):
  {"icao":"","lat":0,"lon":0,"hdg":0,"alt_ft":0,"com1_hz":0}
  Set icao in the script if you have a way to get current airport (e.g. from another plugin).
]]

local listen_port = 49000  -- flightcomp listens here
local send_port = 49001    -- flightcomp sends ATC messages here (optional)
local interval_sec = 2.0
local last_send = 0

-- Datarefs (X-Plane 11)
local lat_dr = nil
local lon_dr = nil
local hdg_dr = nil
local alt_dr = nil
local com1_dr = nil

local udp_send = nil
local udp_recv = nil
local socket_ok = false

-- Try to load socket for UDP (LuaSocket)
local socket = nil
if package.loaded["socket"] then
  socket = package.loaded["socket"]
  socket_ok = (socket ~= nil)
else
  local ok, s = pcall(require, "socket")
  if ok and s then
    socket = s
    socket_ok = true
  end
end

local function init_datarefs()
  if lat_dr then return true end
  lat_dr = find_dataref("sim/flightmodel/position/latitude")
  lon_dr = find_dataref("sim/flightmodel/position/longitude")
  hdg_dr = find_dataref("sim/flightmodel/position/psi")  -- true heading rad
  alt_dr = find_dataref("sim/flightmodel/position/elevation")  -- meters MSL
  com1_dr = find_dataref("sim/cockpit/radios/com1_freq_hz")
  return lat_dr and lon_dr and hdg_dr and alt_dr and com1_dr
end

local function to_deg(rad)
  if not rad then return 0 end
  return rad * 180 / 3.14159265359
end

local function meters_to_ft(m)
  if not m then return 0 end
  return m * 3.28084
end

local function send_state()
  if not init_datarefs() then return end
  local lat = lat_dr and lat_dr() or 0
  local lon = lon_dr and lon_dr() or 0
  local hdg_rad = hdg_dr and hdg_dr() or 0
  local alt_m = alt_dr and alt_dr() or 0
  local com1 = com1_dr and com1_dr() or 0
  local icao = ""  -- Set if you have nearest-airport logic
  local tbl = {
    icao = icao,
    lat = lat,
    lon = lon,
    hdg = math.floor(to_deg(hdg_rad) + 0.5),
    alt_ft = math.floor(meters_to_ft(alt_m) + 0.5),
    com1_hz = math.floor(com1 + 0.5)
  }
  local json_str = "{\"icao\":\"" .. tbl.icao .. "\",\"lat\":" .. tbl.lat ..
    ",\"lon\":" .. tbl.lon .. ",\"hdg\":" .. tbl.hdg ..
    ",\"alt_ft\":" .. tbl.alt_ft .. ",\"com1_hz\":" .. tbl.com1_hz .. "}"
  if socket_ok and udp_send then
    udp_send:sendto(json_str, "127.0.0.1", listen_port)
  end
end

local function try_recv_message()
  if not socket_ok or not udp_recv or not socket then return end
  udp_recv:settimeout(0)
  local data, err = udp_recv:receivefrom()
  if data then
    -- Optional: parse JSON and draw on screen (draw_string_Helvetica_18, etc.)
    -- For now we just drain the socket; add draw_text to display ATC messages from flightcomp.
  end
end

function flightcomp_bridge_interval()
  if not socket_ok then return end
  local now = os.clock()
  if now - last_send >= interval_sec then
    last_send = now
    if not udp_send and socket then
      udp_send = socket.udp()
      if udp_send then udp_send:settimeout(0) end
    end
    if not udp_recv and socket then
      udp_recv = socket.udp()
      if udp_recv then
        udp_recv:setsockname("127.0.0.1", send_port)
        udp_recv:settimeout(0)
      end
    end
    if udp_send then send_state() end
    try_recv_message()
  end
end

do_every_frame("flightcomp_bridge_interval()")

if not socket_ok then
  logMsg("Flightcomp bridge: LuaSocket not found. Install LuaSocket or use file-based bridge.")
end
