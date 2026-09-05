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
  const [importing, setImporting] = useState(false)
  const [simulating, setSimulating] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/payments/orders')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as Order[]
      setOrders(Array.isArray(data) ? data : [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function importDemo() {
    setImporting(true)
    try {
      const res = await apiFetch('/payments/orders/adopt-demo', { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await load()
    } catch (e) {
      setError((e as Error).message || 'Failed to import demo orders')
    } finally {
      setImporting(false)
    }
  }

  async function simulateCapture(order: Order) {
    setSimulating(order.id)
    setError('')
    try {
      const res = await apiFetch('/payments/simulate-payment', {
        method: 'POST',
        body: JSON.stringify({ order_id: order.id }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await load()
    } catch (e) {
      setError((e as Error).message || 'Failed to simulate payment')
    } finally {
      setSimulating(null)
    }
  }

  return (
    <div className="page-card" style={{ maxWidth: '1000px' }}>
      <h2>Orders</h2>
      <p style={{ marginBottom: '1rem' }}>
        Purchases created via payment links, tagged human vs agent with their technical fingerprint signals.
      </p>
      {loading && <p style={{ color: '#60a5fa' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}
      {!loading && orders.length === 0 && (
        <div>
          <p style={{ color: 'var(--muted)' }}>
            No orders yet for your account. Buy from the Demo Storefront (opened from the top bar) or run the
            robot, then check back here — demo storefront purchases appear automatically.
          </p>
          <button
            onClick={importDemo}
            disabled={importing}
            style={{ marginTop: '0.5rem', padding: '0.6rem 1rem', fontWeight: 700, cursor: 'pointer' }}
          >
            {importing ? 'Importing…' : 'Import demo storefront orders'}
          </button>
        </div>
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
          {o.status === 'created' && (
            <button
              onClick={() => simulateCapture(o)}
              disabled={simulating === o.id}
              style={{
                marginTop: '0.5rem',
                background: 'transparent',
                color: '#22c55e',
                border: '1px solid #22c55e',
                borderRadius: 8,
                padding: '0.35rem 0.75rem',
                cursor: 'pointer',
                fontSize: '0.8rem',
                fontWeight: 600,
              }}
            >
              {simulating === o.id ? 'Simulating…' : 'Simulate payment.captured webhook'}
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
