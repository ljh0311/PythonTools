# Gemini Image Studio — Frontend

Vite + React + TypeScript UI for local image generation.

## Run

```bash
# from GeminiImageStudio/frontend
npm install
npm run dev
```

Start the FastAPI backend first (port 8765), or use `..\launcher.bat` / `..\scripts\start_api.bat` (they reuse a healthy API instead of failing with WinError 10048).

Open http://127.0.0.1:5173 — Vite proxies `/api` → `http://127.0.0.1:8765`.

## Components

| Import path | Role |
| --- | --- |
| `src/components/PromptComposer.tsx` | prompt, model, aspect |
| `src/components/ReferenceUploader.tsx` | files[], max 14, clear |
| `src/components/GenerateButton.tsx` | loading, error, cost hint |
| `src/components/ResultGallery.tsx` | results + download |

```ts
import {
  PromptComposer,
  ReferenceUploader,
  GenerateButton,
  ResultGallery,
} from './components'
```

## Build

```bash
npm run build
```
