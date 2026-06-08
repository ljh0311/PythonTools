# Ollama Mod for Minecraft 1.20.1

A multi-loader Minecraft mod (Fabric & Forge) that integrates with Ollama AI to provide in-game AI chat capabilities.

## Features

- **AI Chat Integration**: Chat with Ollama AI models directly in-game
- **GUI Interface**: Beautiful chat interface accessible via keybinding
- **Command Support**: `/ollama` command for quick AI interactions
- **Conversation Management**: Maintains conversation context per player
- **World Context**: AI can understand your current world state
- **Action Recording**: Learn and analyze player behavior patterns
- **Behavior Analysis**: Advanced analytics on player actions
- **Multi-Loader Support**: Works on both Fabric and Forge 1.20.1

## Requirements

- Minecraft 1.20.1
- Fabric Loader 0.14.22+ or Forge 47.2.0+
- Ollama server running (default: http://localhost:11434)
- Java 17+

## Setup

### Building

1. Clone this repository
2. Run `./gradlew build` (or `gradlew.bat build` on Windows)
3. Find the mod JARs in `fabric/build/libs/` and `forge/build/libs/`

### Running Ollama

1. Install Ollama from https://ollama.ai
2. Start the Ollama server
3. Pull a model: `ollama pull llama2`
4. Configure the mod to use your model in the config file

## Configuration

The mod creates a config file in your Minecraft config directory. Key settings:

- `ollamaUrl`: URL of your Ollama server (default: http://localhost:11434)
- `defaultModel`: Model to use for AI responses (default: llama2)
- `enableGui`: Enable/disable the chat GUI
- `enableChatCommand`: Enable/disable the /ollama command
- `enableWorldContext`: Include world information in AI context

## Usage

### GUI

Press `O` (default keybinding) to open the Ollama chat GUI. Type your message and press Enter or click Send.

### Commands

- `/ollama <message>` - Send a message to the AI
- `/ollama_clear` - Clear your conversation history

## Architecture

This mod uses Architectury API to support both Fabric and Forge with minimal code duplication:

- `common/` - Shared code that works on both loaders
- `fabric/` - Fabric-specific implementations
- `forge/` - Forge-specific implementations

## License

MIT License - see LICENSE file for details

## Credits

- Thanks to the Ollama team for the amazing AI platform
- Built with Architectury API for multi-loader support
