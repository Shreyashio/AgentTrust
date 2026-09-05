import { useEffect, useState } from 'react'
import { useApi } from '../../lib/api'

interface Order {
  id: number
  payment_link_id: string
  payment_id?: string | null
  product_name: string
  amount: number
  status: string
  source: string
  user_agent?: string | null
  referer?: string | null
  click_delay_seconds?: number | null
  classification_method: string
  created_at: string
}

export default function OrdersPage() {
  const { apiFetch } = useApi()
  const [orders, setOrders] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    apiFetch('/payments/orders')
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: Order[]) => {
        if (!cancelled) setOrders(Array.isArray(data) ? data : [])
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="page-card" style={{ maxWidth: '1000px' }}>
      <h2>Orders</h2>
      <p style={{ marginBottom: '1rem' }}>
        Purchases created via payment links, tagged human vs agent with their technical fingerprint signals.
      </p>
      {loading && <p style={{ color: '#60a5fa' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}
      {!loading && orders.length === 0 && (
        <p style={{ color: 'var(--muted)' }}>
          No orders yet. Use the storefront to make a test purchase, then check back here.
        </p>
      )}
      {orders.map((o) => (
        <div
          key={o.id}
          style={{
            background: '#0f172a',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '0.75rem 1rem',
            marginBottom: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap' }}>
            <strong>
              #{o.id} · {o.product_name}
            </strong>
            <span style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <span
                style={{
                  color: o.source === 'agent' ? '#facc15' : '#22c55e',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                }}
              >
                {o.source}
              </span>
              <span
                style={{
                  color: o.status === 'captured' ? '#22c55e' : o.status === 'created' ? '#60a5fa' : '#ef4444',
                  textTransform: 'uppercase',
                }}
              >
                {o.status}
              </span>
            </span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>
            ₹{o.amount.toLocaleString('en-IN')} · {new Date(o.created_at).toLocaleString()} ·{' '}
            {o.classification_method}
          </p>
          <p style={{ color: 'var(--muted)', fontSize: '0.75rem', margin: 0 }}>
            {o.user_agent && <>UA: {o.user_agent.slice(0, 60)} · </>}
            {o.click_delay_seconds != null && <>click delay: {o.click_delay_seconds}s · </>}
            link: {o.payment_link_id}
          </p>
        </div>
      ))}
    </div>
  )
}
