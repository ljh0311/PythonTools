import { DEFAULT_COST_HINT } from '../types'

export type GenerateButtonProps = {
  loading?: boolean
  disabled?: boolean
  error?: string | null
  costHintUsd?: number
  onClick: () => void
}

export function GenerateButton({
  loading = false,
  disabled = false,
  error = null,
  costHintUsd = DEFAULT_COST_HINT,
  onClick,
}: GenerateButtonProps) {
  return (
    <div className="generate">
      <button
        type="button"
        className="btn btn--primary"
        disabled={disabled || loading}
        onClick={onClick}
      >
        {loading ? 'Generating…' : 'Generate'}
      </button>
      <p className="generate__hint muted">
        ~${costHintUsd.toFixed(3)} / image for the default model
      </p>
      {error && (
        <p className="generate__error" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
