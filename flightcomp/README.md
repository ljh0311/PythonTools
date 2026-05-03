# Aviation Operations Assistant

A comprehensive Python-based tool designed to assist both pilots and air traffic controllers with aviation communications and operations.

## Features

### For Pilots:
- **ATC Instructions**: Get examples and guidance on common ATC instructions
- **Readback Generator**: Get proper readback formats for various instructions
- **ATIS Decoder**: Parse and display ATIS information in an easy-to-read format
- **Configurable**: Adjusts complexity based on pilot experience and aircraft type

### For Air Traffic Controllers:
- **Ground Operations**: Manage aircraft on taxiways and ramp areas
- **Tower Control**: Handle departures and arrivals
- **Approach/Departure Control**: Manage aircraft in terminal airspace
- **Aircraft Sequencing**: Organize and prioritize aircraft movements
- **ATIS Management**: Create and update ATIS information
- **AI-Powered Responses**: Intelligent ATC responses using Ollama integration

## Installation

1. Clone this repository
2. Install required dependencies:

```
pip install -r requirements.txt
```

### AI Features Setup (Optional)

For AI-powered ATC responses, you'll need to install and configure Ollama:

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Start Ollama: `ollama serve`
3. Download a model: `ollama pull llama2`
4. Test the integration: `python test_ollama_standalone.py`
5. See [OLLAMA_SETUP.md](OLLAMA_SETUP.md) for detailed instructions

#### Testing Ollama Integration

The application includes several ways to test Ollama integration:

- **Standalone Test**: Run `python test_ollama_standalone.py` to test Ollama independently
- **Application Test**: Run `python test_ollama.py` to test within the application context
- **UI Integration**: Use "Check AI Status" from the Tools menu in the role selection screen
- **Automatic Check**: The application automatically checks Ollama availability on startup

## Usage

Run the application from the **project root** (the `flightcomp` directory) so that config and data paths resolve correctly:

```
python main.py
```

Or run as a module from the parent directory:

```
cd PythonTools && python -m flightcomp
```

On Windows you can also double-click:

```
run_aviation_assistant.bat
```

Upon starting, you can choose your role (Pilot or ATC) to access specialized tools.

## Configuration

The application can be configured based on:

### Pilot Settings:
- Pilot experience level (Student, Private, Commercial, ATP)
- Aircraft type (Single Engine, Multi Engine, Jet, etc.)
- Regional ATC phraseology (US, ICAO, UK, etc.)

### ATC Settings:
- Airport information
- Runway configurations
- Controller callsigns
- Frequencies

### X-Plane / FlyWithLua (optional)
- `xplane_bridge_enabled`: Enable UDP bridge to receive sim context from X-Plane 11.
- `xplane_bridge_listen_port`: Port for receiving dataref updates (default 49000).
- `xplane_bridge_send_port`: Port for sending ATC messages to FlyWithLua for on-screen display (default 49001).

## X-Plane 11 / FlyWithLua integration

You can connect the assistant to **X-Plane 11** using the **FlyWithLua** plugin so that the sim drives airport/context and (optionally) displays training messages in the cockpit.

1. **In flightcomp**: Enable **Use X-Plane context** (Pilot: Simulator menu; ATC: checkbox in the airport header). The app will listen on UDP port 49000 for simulator state.
2. **In X-Plane 11**: Install [FlyWithLua](https://github.com/X-Friese/FlyWithLua) and copy the provided Lua script into the FlyWithLua Scripts folder (see `flywithlua/` below).
3. **LuaSocket**: The script uses UDP. If your FlyWithLua build does not include LuaSocket, you may need to add it or use a file-based fallback (see `flywithlua/README.md`).

When the bridge is active, the ATC window can auto-switch the current airport from the sim’s position/ICAO, and the status bar shows **Live: ICAO** when data is received.

See **flywithlua/README.md** and **flywithlua/flightcomp_bridge.lua** for script setup and packet format.

## Development

This application is structured with clear separation of responsibilities:
- `models/` - Data models
- `utils/` - Utility functions and modules
- `views/` - User interface components

## License

MIT
