# FlyWithLua bridge for flightcomp

This folder contains a sample **FlyWithLua** script that sends X-Plane 11 simulator state to the flightcomp application over UDP.

## Requirements

- **X-Plane 11**
- **FlyWithLua** (standard or NG) installed in `X-Plane 11/Resources/plugins/FlyWithLua/`
- **LuaSocket** (if not already included in your FlyWithLua build) for UDP support

## Setup

1. Copy `flightcomp_bridge.lua` into your FlyWithLua Scripts folder:
   - **Windows**: `X-Plane 11\Resources\plugins\FlyWithLua\Scripts\`
   - **macOS**: `X-Plane 11/Resources/plugins/FlyWithLua/Scripts/`
   - **Linux**: `X-Plane 11/Resources/plugins/FlyWithLua/Scripts/`

2. Start X-Plane 11 and (if needed) reload FlyWithLua scripts (Plugins → FlyWithLua → Reload all Lua script files).

3. In flightcomp, enable **Use X-Plane context** (ATC: checkbox in the header; Pilot: Simulator menu).

## Packet format (Lua → flightcomp)

The script sends a JSON UDP packet to `127.0.0.1:49000` every 2 seconds:

```json
{"icao":"","lat":41.98,"lon":-87.90,"hdg":270,"alt_ft":1200,"com1_hz":121900}
```

- **icao**: Current airport ICAO (optional; leave empty if unknown).
- **lat**, **lon**: Latitude and longitude (degrees).
- **hdg**: Heading (degrees).
- **alt_ft**: Altitude (feet MSL).
- **com1_hz**: COM1 frequency (Hz, e.g. 121900 for 121.90 MHz).

If **icao** is set and matches an airport in flightcomp, the ATC window can automatically switch to that airport.

## Receiving messages from flightcomp (optional)

flightcomp can send ATC messages to FlyWithLua on UDP port **49001** for on-screen display. The script binds a receive socket to that port; you can extend `try_recv_message()` to parse the JSON and use FlyWithLua’s drawing API (e.g. `draw_string_Helvetica_18`) to show the text in the sim.

## If LuaSocket is not available

Some FlyWithLua builds do not include LuaSocket. Options:

1. Use a FlyWithLua build that includes LuaSocket, or add LuaSocket to your Lua path.
2. **File-based fallback**: Use a Lua script that writes simulator state to a JSON file (e.g. in a shared folder) every 1–2 seconds, and run a small Python helper that reads the file and forwards the data to flightcomp over UDP or that flightcomp polls. This is not included here but can be implemented if needed.

## Troubleshooting

- **“LuaSocket not found”**: Install or enable LuaSocket for FlyWithLua (see FlyWithLua documentation).
- **flightcomp not updating**: Ensure flightcomp is running and **Use X-Plane context** is enabled; check that no firewall is blocking UDP on port 49000.
- **Port already in use**: Change `listen_port` in the Lua script and set `xplane_bridge_listen_port` in flightcomp config to match.
