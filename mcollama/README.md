# Ollama Mod for Minecraft 1.20.1

A multi-loader Minecraft mod (Fabric & Forge) that integrates with Ollama AI to provide in-game AI chat capabilities.

## Features

- **AI Chat Integration**: Chat with Ollama via `@ai` in chat, `/ollama`, or the GUI (key `O`)
- **World Context**: Position, biome, dimension, and health are included in prompts when enabled
- **Daily Summary**: `/ollama summary` reports mining, hunger, and play-time stats
- **Command Assistance**: `/ollama do` can run whitelisted server commands from AI replies (opt-in, off by default)
- **Conversation Memory**: Keeps recent turns per player (`maxContextMessages`)
- **Multi-Loader Support**: Fabric and Forge 1.20.1

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
| `enableCommandExecution` | `false` | Allow `/ollama do` to run server commands from AI replies |
| `blockDestructiveCommands` | `true` | Refuse commands like `kill`, `ban`, `stop` |
| `commandExecutionWhitelist` | see below | Only these command roots may run when execution is enabled |
| `commandExecutionBlacklist` | `[]` | Additional blocked command roots |
| `enableCommandLearning` | `true` | Record command success/failure for prompts |
| `enableFailureAnalysis` | `true` | Analyze failed commands |
| `maxCommandLearningEntries` | `500` | Cap on stored learning entries |

Default whitelist: `give`, `tp`, `teleport`, `gamemode`, `time`, `weather`, `say`, `me`, `tell`, `msg`, `w`, `seed`, `list`, `help`.

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

## Usage

### GUI

Press `O` (default keybinding) to open the Ollama chat GUI. Type your message and press Enter or click Send.

### Commands

- `/ollama <message>` — Send a message to the AI
- `/ollama do <request>` — Ask the AI for a command and run it (requires `enableCommandExecution`)
- `/ollama summary` — Show today's activity summary
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
