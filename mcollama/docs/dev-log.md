# Dev log

## 2026-09-02 — Beta 1.0.0-beta.1

### Progress
- Recovered mod from non-building state to shippable Fabric + Forge jars.
- Added player-facing paths: `@ai`, GUI (`O`), commands, startup check, config JSON.
- Added headless verification (JUnit + `smoke_test_mcollama.py`).
- Open PR: https://github.com/ljh0311/PythonTools/pull/6

### Feature state
| Feature | Status |
|---------|--------|
| AI chat (`@ai`, `/ollama`, GUI) | Beta — needs in-game + Ollama QA |
| `config/ollamamod.json` | Working |
| World context in prompts | Wired |
| `/ollama summary` | Wired; some stat counters still zero |
| `/ollama do` command assist | Opt-in, whitelist, singleplayer-focused |
| Headless smoke tests | Passing |

### Gaps before stable
- Fix Forge keybind registration (mod event bus).
- Mod Menu / in-game config screen.
- Update default model recommendation.
- In-game playtest on Fabric and Forge.

### Verification
```bat
cd mcollama
run_smoke_test.bat
gradlew.bat build
package-beta.bat
```
