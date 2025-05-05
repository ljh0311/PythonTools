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

## Installation

1. Clone this repository
2. Install required dependencies:

```
pip install -r requirements.txt
```

## Usage

Run the application:

```
python main.py
```

Or on Windows, you can simply double-click:

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

## Development

This application is structured with clear separation of responsibilities:
- `models/` - Data models
- `utils/` - Utility functions and modules
- `views/` - User interface components

## License

MIT
