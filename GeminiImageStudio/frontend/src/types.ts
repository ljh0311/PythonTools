export type GalleryItem = {
  id: string
  url: string
  prompt: string | null
  createdAt: string
  filename?: string
  model?: string | null
}

export type HealthResponse = {
  status: string
  has_api_key: boolean
  default_model: string
}

export type GenerateImageMeta = {
  id: string
  filename: string
  url: string
  mime_type?: string
  prompt?: string | null
  model?: string | null
  created_at?: string
  size_bytes?: number
}

export type GenerateResponse = {
  ok: boolean
  image: GenerateImageMeta
  model: string
  model_text?: string | null
  estimated_cost_usd?: number | null
  reference_count?: number
}

export type OutputsResponse = {
  items: GenerateImageMeta[]
  count: number
}

export const ASPECT_OPTIONS = [
  { value: '', label: 'Auto' },
  { value: '1:1', label: '1:1' },
  { value: '16:9', label: '16:9' },
  { value: '9:16', label: '9:16' },
  { value: '4:3', label: '4:3' },
  { value: '3:4', label: '3:4' },
] as const

export const DEFAULT_COST_HINT = 0.085
export const MAX_REFERENCES = 14
