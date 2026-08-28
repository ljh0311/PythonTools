import type {
  GenerateResponse,
  GalleryItem,
  HealthResponse,
  OutputsResponse,
  GenerateImageMeta,
} from './types'

const API_BASE = ''

function detailFromErrorBody(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail
        .map((d) =>
          typeof d === 'object' && d && 'msg' in d
            ? String((d as { msg: unknown }).msg)
            : JSON.stringify(d),
        )
        .join('; ')
    }
  }
  return fallback
}

async function parseJsonOrThrow<T>(res: Response, fallback: string): Promise<T> {
  let body: unknown = null
  const text = await res.text()
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = text
    }
  }
  if (!res.ok) {
    const msg =
      typeof body === 'string' && body
        ? body
        : detailFromErrorBody(body, fallback)
    throw new Error(msg || `${fallback} (${res.status})`)
  }
  return body as T
}

export function toGalleryItem(meta: GenerateImageMeta): GalleryItem {
  return {
    id: meta.id || meta.filename,
    url: meta.url,
    prompt: meta.prompt ?? null,
    createdAt: meta.created_at ?? new Date().toISOString(),
    filename: meta.filename,
    model: meta.model ?? null,
  }
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE}/api/health`)
  return parseJsonOrThrow<HealthResponse>(res, 'Health check failed')
}

export async function fetchOutputs(limit = 50): Promise<GalleryItem[]> {
  const res = await fetch(`${API_BASE}/api/outputs?limit=${limit}`)
  const data = await parseJsonOrThrow<OutputsResponse>(res, 'Failed to load outputs')
  return (data.items ?? []).map(toGalleryItem)
}

export async function generateImage(params: {
  prompt: string
  model?: string
  aspect?: string
  files: File[]
}): Promise<GenerateResponse> {
  const form = new FormData()
  form.append('prompt', params.prompt)
  if (params.model?.trim()) form.append('model', params.model.trim())
  if (params.aspect?.trim()) form.append('aspect', params.aspect.trim())
  for (const file of params.files) {
    form.append('files', file)
  }

  const res = await fetch(`${API_BASE}/api/generate`, {
    method: 'POST',
    body: form,
  })
  return parseJsonOrThrow<GenerateResponse>(res, 'Generate failed')
}
