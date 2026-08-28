import { useEffect, useRef, useState } from 'react'
import type { GalleryItem } from '../types'

export type ResultGalleryProps = {
  items: GalleryItem[]
  loading?: boolean
  emptyMessage?: string
}

function downloadHref(item: GalleryItem): string {
  return item.url
}

function labelFor(item: GalleryItem): string {
  return item.prompt || item.filename || item.id
}

function formatRelativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return '—'
  const sec = Math.floor((Date.now() - then) / 1000)
  if (sec < 60) return 'just now'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m ago`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}h ago`
  const day = Math.floor(hr / 24)
  if (day < 30) return `${day}d ago`
  return new Date(iso).toLocaleDateString()
}

export function ResultGallery({
  items,
  loading = false,
  emptyMessage = 'Generated images will appear here.',
}: ResultGalleryProps) {
  const lastFirstId = useRef<string | undefined>(undefined)
  const historyInit = useRef(false)
  const [featuredId, setFeaturedId] = useState<string | undefined>()
  const [historyOpen, setHistoryOpen] = useState(false)

  useEffect(() => {
    if (items.length === 0) {
      setFeaturedId(undefined)
      lastFirstId.current = undefined
      historyInit.current = false
      setHistoryOpen(false)
      return
    }

    if (!historyInit.current) {
      setHistoryOpen(items.length <= 5)
      historyInit.current = true
    }

    const newFirst = items[0].id
    if (lastFirstId.current !== newFirst) {
      setFeaturedId(newFirst)
      lastFirstId.current = newFirst
      return
    }

    setFeaturedId((prev) => {
      if (prev && items.some((item) => item.id === prev)) return prev
      return newFirst
    })
  }, [items])

  const featured = items.find((item) => item.id === featuredId) ?? items[0]

  function handleView(id: string) {
    setFeaturedId(id)
  }

  return (
    <section className="gallery" aria-label="Results">
      <div className="gallery__stage">
        {loading && !featured && (
          <div className="gallery__placeholder">
            <span className="spinner" aria-hidden />
            <p>Generating image…</p>
          </div>
        )}
        {!loading && !featured && (
          <div className="gallery__placeholder">
            <p>{emptyMessage}</p>
          </div>
        )}
        {featured && (
          <figure className="gallery__featured">
            <div className="gallery__featured-frame">
              <img src={featured.url} alt={labelFor(featured)} />
            </div>
            <figcaption className="gallery__caption">
              <span className="gallery__prompt">{labelFor(featured)}</span>
              <a
                className="btn btn--ghost"
                href={downloadHref(featured)}
                download={featured.filename || featured.id}
              >
                Download
              </a>
            </figcaption>
          </figure>
        )}
        {loading && featured && (
          <div className="gallery__overlay" aria-live="polite">
            <span className="spinner" aria-hidden />
            Generating…
          </div>
        )}
      </div>

      {items.length > 0 && (
        <details
          className="gallery__history"
          open={historyOpen}
          onToggle={(event) => setHistoryOpen(event.currentTarget.open)}
        >
          <summary className="gallery__history-summary">
            Generation history ({items.length})
          </summary>
          <ul className="gallery__history-list">
            {items.map((item) => {
              const isFeatured = item.id === featured?.id
              return (
                <li
                  key={item.id}
                  className={
                    isFeatured
                      ? 'gallery__history-row gallery__history-row--active'
                      : 'gallery__history-row'
                  }
                >
                  <img
                    className="gallery__history-thumb"
                    src={item.url}
                    alt=""
                    loading="lazy"
                  />
                  <span
                    className="gallery__history-prompt"
                    title={labelFor(item)}
                  >
                    {labelFor(item)}
                  </span>
                  <time
                    className="gallery__history-time"
                    dateTime={item.createdAt}
                  >
                    {formatRelativeTime(item.createdAt)}
                  </time>
                  <button
                    type="button"
                    className="btn btn--tiny gallery__history-view"
                    disabled={isFeatured}
                    onClick={() => handleView(item.id)}
                  >
                    View
                  </button>
                  <a
                    className="gallery__history-dl"
                    href={downloadHref(item)}
                    download={item.filename || item.id}
                  >
                    Download
                  </a>
                </li>
              )
            })}
          </ul>
        </details>
      )}
    </section>
  )
}
