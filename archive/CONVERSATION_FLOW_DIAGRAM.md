# Battery Monitor Conversation Flow

## Visual Flow Diagram

```mermaid
flowchart TD
    Start[Start convo_mode] --> Init[Initialize:<br/>turn_count = 1<br/>api_message_history = empty<br/>conversation_history = empty]
    Init --> Display[Display Initial Question<br/>from talker2 Student]
    Display --> AddInit[Add to histories:<br/>role: user<br/>speaker: talker2]
    AddInit --> Loop{Enter While Loop}
    
    Loop --> CheckLimit{turn_count >= max_turns?}
    CheckLimit -->|Yes| EndLimit[Print Reached Limit<br/>Break Loop]
    CheckLimit -->|No| GetLastRole[Get last_role from<br/>api_message_history]
    
    GetLastRole --> CheckRole{last_role == user?}
    
    CheckRole -->|Yes| SetTalker1[Set responder:<br/>talker1 Battery Assistant<br/>role: assistant<br/>🔋]
    CheckRole -->|No| SetTalker2[Set responder:<br/>talker2 Student<br/>role: user<br/>🎮]
    
    SetTalker1 --> DebugOutput[Print DEBUG info:<br/>Turn, API History, Speaker]
    SetTalker2 --> DebugOutput
    
    DebugOutput --> BatteryCheck{API History == 1?}
    BatteryCheck -->|Yes| AddBattery[Include battery_data<br/>in context]
    BatteryCheck -->|No| NoBattery[No battery context]
    
    AddBattery --> SendAPI[Call send_chat_message with:<br/>- api_message_history<br/>- personality<br/>- battery_context]
    NoBattery --> SendAPI
    
    SendAPI --> APIError{API Error?}
    APIError -->|Yes| PrintError[Print detailed error<br/>with traceback<br/>Break Loop]
    APIError -->|No| CheckResponse{Response empty?}
    
    CheckResponse -->|Yes| NoResponse[Print No Response<br/>Break Loop]
    CheckResponse -->|No| DisplayResp[Display Response with:<br/>Icon, Speaker Label]
    
    DisplayResp --> AddToHistory[Add response to:<br/>api_message_history<br/>conversation_history<br/>turn_count++]
    
    AddToHistory --> DebugNext[Print DEBUG:<br/>Turn count, API length,<br/>Next expected speaker]
    
    DebugNext --> UserPrompt[Prompt user:<br/>Enter continue OR<br/>exit save export]
    
    UserPrompt --> UserChoice{User Input?}
    UserChoice -->|Enter| Continue[Print DEBUG:<br/>User pressed Enter<br/>Sleep 0.5s]
    UserChoice -->|exit| ExitUser[Print Exiting<br/>Break Loop]
    UserChoice -->|save| SaveConvo[Save conversation<br/>Continue Loop]
    UserChoice -->|export| ExportExit[Save and export<br/>Break Loop]
    UserChoice -->|Ctrl+C| Interrupt[Print Interrupted<br/>Break Loop]
    
    Continue --> Separator[Print visual separator:<br/>Continuing Turn N]
    SaveConvo --> Separator
    
    Separator --> Loop
    
    EndLimit --> Finally[Display Summary:<br/>Total turns, Duration]
    ExitUser --> Finally
    ExportExit --> Finally
    PrintError --> Finally
    NoResponse --> Finally
    Interrupt --> Finally
    
    Finally --> OfferSave{Conversation saved?}
    OfferSave -->|No| AskSave[Ask user to save]
    OfferSave -->|Yes| End[End]
    AskSave --> End
```

## Key Points

### Alternating Logic
The conversation alternates based on the **last role** in `api_message_history`:
- If last role is `"user"` → talker1 (assistant) responds
- If last role is `"assistant"` → talker2 (user) responds

### Turn Sequence
```
Turn 1: 🎮 talker2 asks (user)
  ↓ [User presses Enter]
Turn 2: 🔋 talker1 responds (assistant)
  ↓ [User presses Enter]
Turn 3: 🎮 talker2 follows up (user)
  ↓ [User presses Enter]
Turn 4: 🔋 talker1 responds (assistant)
  ↓ [Continues...]
```

### API Message History Structure
After Turn 3, the `api_message_history` looks like:
```python
[
    {"role": "user", "content": "Initial question from talker2"},      # Turn 1
    {"role": "assistant", "content": "Response from talker1"},         # Turn 2
    {"role": "user", "content": "Follow-up from talker2"}             # Turn 3
]
```

### Personality Injection
Each call to `send_chat_message()` includes:
1. **System message**: Either `talker1_personality` or `talker2_personality`
2. **Message history**: Full conversation up to this point
3. **Battery context**: Only included in Turn 2 (first assistant response)

### Why It Should Work Now

The debug output now clearly shows:
1. **Before each turn**: Who is about to speak and why
2. **After each turn**: What was added and who should speak next
3. **On errors**: Detailed information about what went wrong and when
4. **User actions**: Confirmation of what the user typed

This visibility makes it easy to:
- Verify the alternating pattern is correct
- Identify if/when the loop breaks unexpectedly
- See if Ollama is failing for a specific speaker
- Confirm the conversation continues past Turn 2
