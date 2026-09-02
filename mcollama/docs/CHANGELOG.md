# Changelog

All notable changes to Ollama Mod are documented here.

## [1.0.0-beta.1] - 2026-09-02

### Added
- `@ai` chat trigger, `/ollama`, `/ollama summary`, `/ollama do`, `/ollama_clear`
- Config file `config/ollamamod.json` (created on first run)
- Startup connection check with actionable errors
- Headless smoke test (`run_smoke_test.bat`) and JUnit unit tests
- World context in AI prompts (position, biome, health)
- Daily mining/food summary via `/ollama summary`

### Fixed
- Mod builds and packages common code into Fabric and Forge jars
- Chat GUI widgets render correctly (`addRenderableWidget`)
- Command execution gated behind `/ollama do`, off by default, whitelist-only
- Commands run on the main server thread

### Known limitations (beta)
- Forge `O` keybind may not appear in Controls menu
- No in-game config UI (edit JSON and restart)
- Default model is `llama2` — pull it or change `defaultModel` in config
- Combat/distance stats in summary may show zero (not all events wired)
- Live AI not verified in automated CI from every environment

### Install
1. Download `ollamamod-fabric-1.0.0-beta.1.jar` or `ollamamod-forge-1.0.0-beta.1.jar` from GitHub Releases.
2. Place in your Minecraft `mods` folder (MC 1.20.1).
3. Start Ollama (`ollama serve`) and pull your model (`ollama pull llama2` or edit config).
4. In-game: `@ai hello` or press `O`.

### Verify without Minecraft
```bat
cd mcollama
run_smoke_test.bat
```
