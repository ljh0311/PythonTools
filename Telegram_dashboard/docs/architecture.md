# Architecture

## System overview

```mermaid
flowchart TB
    subgraph client [Client Browser]
        UI[Dashboard UI]
    end

    subgraph server [FastAPI Backend]
        API[REST API]
        WS[WebSocket]
        WH[Webhook Handler]
        BH[Bot Handler]
        AI[AI Services]
        DB[(SQLite)]
    end

    subgraph external [External Services]
        TG[Telegram Bot API]
        GEM[Gemini API]
        OLL[Ollama Local]
    end

    UI <-->|HTTP / WS| API
    UI <-->|HTTP / WS| WS
    TG -->|POST update| WH --> BH --> DB
    BH --> AI
    AI --> GEM
    AI -.->|fallback| OLL
    API --> DB
    API -->|send message| TG
    BH -->|auto-reply| TG
```

---

## Current architecture (Sprint 0)

### Layers

| Layer | Responsibility | Key files |
|-------|----------------|-----------|
| **Presentation** | Dashboard UI, theme, charts | `frontend/` |
| **API** | REST, WebSocket, auth | `backend/routes/api.py` |
| **Ingestion** | Telegram webhook processing | `backend/routes/webhook.py`, `bot_handler.py` |
| **Services** | Telegram API, AI providers | `backend/services/` |
| **Data** | SQLite persistence | `backend/models/store.py` |

### Message flow (current)

1. Telegram sends update → `POST /webhook/telegram`
2. `bot_handler` extracts user, text, chat
3. Message stored in `messages` table
4. `ai_service` generates reply (Gemini → Ollama → built-in)
5. Reply sent via Telegram API and stored as outgoing message
6. WebSocket broadcasts update to dashboard

### AI architecture (current)

```
ai_service
├── GeminiProvider (primary)
├── OllamaProvider (fallback)
└── _fallback_response (built-in commands)
```

AI tools available to the **bot** (not yet the operator dashboard):

- `get_metrics`
- `analyze_command_usage`
- `webhook_notify`

---

## Target architecture (v0.3+)

### New components (planned)

| Component | Sprint | Purpose |
|-----------|--------|---------|
| `MessageQueryService` | 1 | Filtered/paginated message queries |
| `RedactionService` | 2 | Mask sensitive data before AI (D-05) |
| `SummarizationService` | 2 | English summaries + originals (D-04) |
| `ActionSuggestionService` | 2 | Reply drafts and next actions |
| `TopicService` | 3 | User-type + AI-assign modes (D-03) |
| `ReplyModeService` | 3 | Auto / manual / per-chat modes (D-01) |
| `OperatorSettings` | 3 | Presets, preferences |

### Target message flow (operator mode)

```mermaid
sequenceDiagram
    participant TG as Telegram
    participant WH as Webhook
    participant DB as SQLite
    participant UI as Dashboard
    participant AI as AI Services

    TG->>WH: Incoming message
    WH->>DB: Store message (no auto-reply if disabled)
    WH-->>UI: WebSocket push
    UI->>DB: GET /api/messages?filters
    UI->>AI: POST /api/ai/summarize
    AI-->>UI: Summary
    UI->>AI: POST /api/ai/suggest-actions
    AI-->>UI: Suggestions
    UI->>TG: POST /api/send (operator approves)
```

### Target data model additions

```mermaid
erDiagram
    users ||--o{ messages : sends
    messages ||--o{ message_topics : has
    topics ||--o{ message_topics : tagged
    suggestions ||--|| messages : references

    messages {
        int id PK
        int user_id
        int chat_id
        int message_id
        string chat_type
        int reply_to_message_id
        string direction
        string text
        datetime created_at
    }

    topics {
        int id PK
        string name
        string color
    }

    message_topics {
        int message_id FK
        int topic_id FK
    }

    suggestions {
        int id PK
        string type
        json payload
        string status
        datetime created_at
    }

    filter_presets {
        int id PK
        string name
        json filters
    }
```

---

## Technology stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3, FastAPI, httpx, SQLite |
| Frontend | HTML, CSS, vanilla JS (ES modules), Chart.js |
| AI primary | Google Gemini API |
| AI fallback | Ollama (OpenAI-compatible local API) |
| Real-time | WebSocket |
| Telegram | Bot API via webhook + sendMessage |

---

## Security considerations

| Area | Current | Target (v1.0) |
|------|---------|---------------|
| API auth | Static `X-API-Key` header | Session or JWT login |
| Webhook auth | `X-Telegram-Bot-Api-Secret-Token` | Unchanged |
| Secrets | `.env` file | `.env` + not exposed to frontend |
| Message data | Local SQLite | Local SQLite; backup documented |
