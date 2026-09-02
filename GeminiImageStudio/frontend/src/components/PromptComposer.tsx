import { ASPECT_OPTIONS } from '../types'

export type PromptComposerProps = {
  prompt: string
  model: string
  aspect: string
  disabled?: boolean
  onPromptChange: (value: string) => void
  onModelChange: (value: string) => void
  onAspectChange: (value: string) => void
  onSubmit: () => void
}

export function PromptComposer({
  prompt,
  model,
  aspect,
  disabled = false,
  onPromptChange,
  onModelChange,
  onAspectChange,
  onSubmit,
}: PromptComposerProps) {
  return (
    <section className="composer" aria-label="Prompt">
      <label className="field">
        <span className="field__label">Prompt</span>
        <textarea
          className="field__textarea"
          value={prompt}
          disabled={disabled}
          rows={5}
          placeholder="Describe the image you want…"
          onChange={(e) => onPromptChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              e.preventDefault()
              if (!disabled) onSubmit()
            }
          }}
        />
      </label>

      <div className="composer__row">
        <label className="field field--grow">
          <span className="field__label">Model</span>
          <input
            className="field__input"
            type="text"
            value={model}
            disabled={disabled}
            placeholder="gemini-3.1-flash-image"
            onChange={(e) => onModelChange(e.target.value)}
          />
        </label>

        <label className="field">
          <span className="field__label">Aspect</span>
          <select
            className="field__select"
            value={aspect}
            disabled={disabled}
            onChange={(e) => onAspectChange(e.target.value)}
          >
            {ASPECT_OPTIONS.map((opt) => (
              <option key={opt.value || 'auto'} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>
    </section>
  )
}
