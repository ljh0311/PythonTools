import { useRef } from 'react'
import { MAX_REFERENCES } from '../types'

export type ReferenceUploaderProps = {
  files: File[]
  max?: number
  disabled?: boolean
  onChange: (files: File[]) => void
  onClear: () => void
}

export function ReferenceUploader({
  files,
  max = MAX_REFERENCES,
  disabled = false,
  onChange,
  onClear,
}: ReferenceUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  function mergeFiles(incoming: FileList | File[]) {
    const next = [...files]
    for (const file of Array.from(incoming)) {
      if (!file.type.startsWith('image/')) continue
      if (next.length >= max) break
      const dup = next.some(
        (f) => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified,
      )
      if (!dup) next.push(file)
    }
    onChange(next.slice(0, max))
  }

  return (
    <section className="refs" aria-label="Reference images">
      <div className="refs__header">
        <span className="field__label">
          References <span className="muted">({files.length}/{max})</span>
        </span>
        {files.length > 0 && (
          <button
            type="button"
            className="btn btn--ghost"
            disabled={disabled}
            onClick={onClear}
          >
            Clear
          </button>
        )}
      </div>

      <div
        className={`refs__drop${disabled ? ' is-disabled' : ''}`}
        onDragOver={(e) => {
          e.preventDefault()
          e.stopPropagation()
        }}
        onDrop={(e) => {
          e.preventDefault()
          if (disabled) return
          if (e.dataTransfer.files?.length) mergeFiles(e.dataTransfer.files)
        }}
        onClick={() => {
          if (!disabled) inputRef.current?.click()
        }}
      >
        <p>Drop images here or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          multiple
          hidden
          disabled={disabled}
          onChange={(e) => {
            if (e.target.files?.length) mergeFiles(e.target.files)
            e.target.value = ''
          }}
        />
      </div>

      {files.length > 0 && (
        <ul className="refs__list">
          {files.map((file, i) => (
            <li key={`${file.name}-${file.lastModified}-${i}`} className="refs__item">
              <span className="refs__name" title={file.name}>
                {file.name}
              </span>
              <button
                type="button"
                className="btn btn--ghost btn--tiny"
                disabled={disabled}
                aria-label={`Remove ${file.name}`}
                onClick={() => onChange(files.filter((_, idx) => idx !== i))}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
