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

The mod writes `config/ollamamod.json` in your Minecraft config directory on first run. Edit the file and restart the game to apply changes.

### Connection

| Key | Default | Description |
|-----|---------|-------------|
| `ollamaUrl` | `http://localhost:11434` | Ollama server URL |
| `defaultModel` | `llama2` | Model name passed to Ollama |
| `timeoutSeconds` | `30` | HTTP timeout for AI requests |

### Chat & UI

| Key | Default | Description |
|-----|---------|-------------|
| `enableChatCommand` | `true` | Register `/ollama` client commands |
| `enableGui` | `true` | Allow the chat GUI (keybinding) |
| `enableChatTrigger` | `true` | Intercept chat messages starting with the trigger |
| `chatTrigger` | `@ai` | Prefix that routes chat to the AI |
| `enableWorldContext` | `true` | Include position, biome, and health in prompts |
| `overseerPersonality` | `Assistant` | AI persona name in prompts |
| `maxContextMessages` | `20` | Conversation turns kept per player (`0` = unlimited) |

### Command execution

| Key | Default | Description |
|-----|---------|-------------|
| `enableCommandExecution` | `true` | Allow AI-suggested commands to run (see `/ollama do`) |
| `confirmBeforeExecute` | `true` | Block destructive commands (`kill`, `ban`, `stop`, etc.) |
| `commandExecutionWhitelist` | `[]` | When non-empty, only listed command roots may run |
| `commandExecutionBlacklist` | `[]` | Additional blocked command roots |
| `enableCommandLearning` | `true` | Record command success/failure for prompts |
| `enableFailureAnalysis` | `true` | Analyze failed commands |
| `maxCommandLearningEntries` | `500` | Cap on stored learning entries |

### Daily summary & stats

| Key | Default | Description |
|-----|---------|-------------|
| `enableDailySummary` | `true` | Track per-player daily stats |
| `showDistanceStats` | `true` | Include travel distance in summaries |
| `showCombatStats` | `true` | Include combat stats |
| `showMiningStats` | `true` | Include mining stats |
| `showPlaytimeStats` | `true` | Include play time |
| `showFoodStats` | `true` | Include hunger/food stats |
| `foodTrackingInterval` | `100` | Ticks between stat samples (20 TPS; 100 = 5 s) |
| `foodRecommendationSafetyMultiplier` | `1.5` | Safety margin for food recommendations |
| `enableMiningTracking` | `true` | Track blocks mined |
| `showMinerType` | `true` | Show inferred miner type in summary |
| `showOreProbabilities` | `true` | Show ore share in summary |
| `minBlocksForAnalysis` | `10` | Minimum blocks before miner-type analysis |

### Recording & limits

| Key | Default | Description |
|-----|---------|-------------|
| `enableActionRecording` | `true` | Record player actions for learning |
| `recordingInterval` | `1` | Ticks between action samples |
| `patternLearningThreshold` | `5` | Repetitions before a pattern is learned |
| `maxPatterns` | `100` | Stored behavior patterns |
| `maxLearningEntries` | `1000` | Stored learning entries |
| `maxRecordingQueueSize` | `1000` | Action recording queue size |

## Usage

### GUI

Press `O` (default keybinding) to open the Ollama chat GUI. Type your message and press Enter or click Send.

### Commands

- `/ollama <message>` — Send a message to the AI
- `/ollama_clear` — Clear your conversation history

You can also type `@ai <message>` in chat when `enableChatTrigger` is on.

## Architecture

This mod uses Architectury API to support both Fabric and Forge with minimal code duplication:

- `common/` — Shared code that works on both loaders
- `fabric/` — Fabric-specific implementations
- `forge/` — Forge-specific implementations

## License

MIT License — see LICENSE file for details

## Credits

- Thanks to the Ollama team for the amazing AI platform
- Built with Architectury API for multi-loader support
