import { useCallback, useEffect, useState } from 'react'
import {
  GenerateButton,
  PromptComposer,
  ReferenceUploader,
  ResultGallery,
} from './components'
import { fetchHealth, fetchOutputs, generateImage, toGalleryItem } from './api'
import type { GalleryItem } from './types'
import './App.css'

export default function App() {
  const [prompt, setPrompt] = useState('')
  const [model, setModel] = useState('')
  const [aspect, setAspect] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [items, setItems] = useState<GalleryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [healthNote, setHealthNote] = useState<string | null>(null)
  const [defaultModel, setDefaultModel] = useState('gemini-3.1-flash-image')

  const loadOutputs = useCallback(async () => {
    try {
      const list = await fetchOutputs(50)
      setItems(list)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load outputs')
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const health = await fetchHealth()
        if (cancelled) return
        setDefaultModel(health.default_model || 'gemini-3.1-flash-image')
        if (!health.has_api_key) {
          setHealthNote(
            'API key missing on the server. Set GEMINI_API_KEY in GeminiImageStudio/.env before generating.',
          )
        } else {
          setHealthNote(null)
        }
      } catch {
        if (!cancelled) {
          setHealthNote(
            'Cannot reach API at /api (proxy → 127.0.0.1:8765). Start the backend first.',
          )
        }
      }
      if (!cancelled) await loadOutputs()
    })()
    return () => {
      cancelled = true
    }
  }, [loadOutputs])

  async function handleGenerate() {
    const trimmed = prompt.trim()
    if (!trimmed) {
      setError('Enter a prompt before generating.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const result = await generateImage({
        prompt: trimmed,
        model: model || undefined,
        aspect: aspect || undefined,
        files,
      })
      const item = toGalleryItem(result.image)
      setItems((prev) => [item, ...prev.filter((x) => x.id !== item.id)])
      if (result.estimated_cost_usd != null) {
        setHealthNote(
          `Last generate ≈ $${Number(result.estimated_cost_usd).toFixed(3)} (${result.model})`,
        )
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Generate failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = Boolean(prompt.trim()) && !loading

  return (
    <div className="app">
      <div className="app__atmosphere" aria-hidden />
      <header className="app__brand">
        <div className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect
              x="4"
              y="8"
              width="40"
              height="32"
              rx="4"
              stroke="currentColor"
              strokeWidth="2"
            />
            <circle cx="16" cy="20" r="4" fill="currentColor" opacity="0.85" />
            <path
              d="M8 32l10-8 8 6 14-14"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
        <div className="brand-copy">
          <p className="brand-eyebrow">Local · Nano Banana</p>
          <h1 className="brand">
            <span className="brand__accent">Gemini</span>{' '}
            <span className="brand__name">Image Studio</span>
          </h1>
          <p className="lede">Local Gemini image generation — entirely on your machine.</p>
          <ul className="brand-features" aria-label="Capabilities">
            <li className="brand-feature">Prompt</li>
            <li className="brand-feature">References</li>
            <li className="brand-feature">Preview</li>
          </ul>
        </div>
      </header>

      {(healthNote || error) && (
        <div className="app__status" role="status">
          {healthNote && <p className="status status--info">{healthNote}</p>}
        </div>
      )}

      <main className="app__layout">
        <aside className="app__controls">
          <PromptComposer
            prompt={prompt}
            model={model}
            aspect={aspect}
            disabled={loading}
            onPromptChange={setPrompt}
            onModelChange={setModel}
            onAspectChange={setAspect}
            onSubmit={handleGenerate}
          />
          <ReferenceUploader
            files={files}
            disabled={loading}
            onChange={setFiles}
            onClear={() => setFiles([])}
          />
          <GenerateButton
            loading={loading}
            disabled={!canSubmit}
            error={error}
            onClick={handleGenerate}
          />
          <p className="muted tiny">
            Default model: {defaultModel}. Ctrl/Cmd+Enter to generate.
          </p>
        </aside>

        <div className="app__results">
          <ResultGallery items={items} loading={loading} />
        </div>
      </main>
    </div>
  )
}
