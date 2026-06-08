# MTR Ollama Integration Instructions

## Integration Steps

To integrate Ollama into the MTR mod, you need to:

### 1. Add Integration Call to Init.java

In `org/mtr/mod/Init.java`, add the following import at the top:

```java
import org.mtr.ollama.MTROllamaIntegration;
```

Then, in the `init()` method, add this line after the other initialization calls (around line 142, after `SoundEvents.init();`):

```java
MTROllamaIntegration.init();
```

### 2. Update mods.toml

The mods.toml file should be updated to include information about the Ollama integration. Add a note in the description about AI-powered train management.

### 3. Build the Modified JAR

1. Compile all the new Java files in `src/main/java/org/mtr/ollama/`
2. Package them into the MTR JAR file
3. Ensure all dependencies (Gson) are included

### 4. Dependencies

Make sure the following dependencies are available:
- Google Gson library (for JSON parsing)
- Java 11+ (for HTTP client)

## Files Created

- `org/mtr/ollama/OllamaClient.java` - HTTP client for Ollama API
- `org/mtr/ollama/OllamaConfig.java` - Configuration system
- `org/mtr/ollama/MTRWorldContext.java` - MTR-specific context gathering
- `org/mtr/ollama/MTROllamaCommands.java` - Command handlers
- `org/mtr/ollama/MTROllamaIntegration.java` - Main integration class

## Usage

After integration, players can use:
- `/mtr ollama chat <message>` - Chat with AI about trains
- `/mtr ollama status` - Check Ollama server status
- `/mtr ollama analyze` - Analyze train network
- `/mtr ollama optimize` - Get route optimization suggestions
- `/mtr ollama help` - Show help

## Configuration

Configuration file: `config/mtr-ollama-common.toml`

Key settings:
- `ollamaUrl` - Ollama server URL (default: http://localhost:11434)
- `defaultModel` - AI model to use (default: llama2)
- `enableChatCommand` - Enable chat command
- `enableWorldContext` - Enable MTR context gathering
- `enableRouteOptimization` - Enable route optimization
- `enableNetworkAnalysis` - Enable network analysis
