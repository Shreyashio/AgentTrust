import { useEffect, useState } from 'react'
import { useApi } from '../../lib/api'

interface TimelineEvent {
  timestamp: string
  category: string
  event_type: string
  title: string
  result?: string | null
  reason?: string | null
  details: Record<string, unknown>
}

const categoryColor: Record<string, string> = {
  governance: '#60a5fa',
  campaign: '#c084fc',
  order: '#34d399',
  webhook: '#f472b6',
}

export default function AuditPage() {
  const { apiFetch } = useApi()
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    apiFetch('/audit-log?order=desc')
      .then((res: Response) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: { timeline: TimelineEvent[]; total_events: number }) => {
        if (cancelled) return
        setEvents(Array.isArray(data.timeline) ? data.timeline : [])
        setTotal(typeof data.total_events === 'number' ? data.total_events : 0)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="page-card" style={{ maxWidth: '900px' }}>
      <h2>Audit Trail</h2>
      <p style={{ marginBottom: '1rem' }}>
        Chronological log of every governance decision, campaign event, order, and webhook — {total} total.
      </p>
      {loading && <p style={{ color: '#60a5fa' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}
      {!loading && events.length === 0 && (
        <p style={{ color: 'var(--muted)' }}>No audit events yet. Run the agent or make a purchase.</p>
      )}
      {events.map((e, i) => (
        <div
          key={i}
          style={{
            borderLeft: `3px solid ${categoryColor[e.category] || 'var(--border)'}`,
            background: '#0f172a',
            borderRadius: 8,
            padding: '0.75rem 1rem',
            marginBottom: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
            <strong>{e.title}</strong>
            <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>
              {new Date(e.timestamp).toLocaleString()}
            </span>
          </div>
          {e.reason && <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>{e.reason}</p>}
          <span
            style={{
              color: 'var(--muted)',
              fontSize: '0.72rem',
              textTransform: 'uppercase',
              fontWeight: 700,
            }}
          >
            {e.category} · {e.event_type}
          </span>
        </div>
      ))}
    </div>
  )
}
