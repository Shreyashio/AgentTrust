import { useEffect, useState } from 'react'
import { useApi } from '../../lib/api'

interface Product {
  id: number
  name: string
  stock_count: number
  price: number
  margin: number
  last_updated: string
  staleness_status: string
  hours_since_update: number
}

export default function InventoryPage() {
  const { apiFetch } = useApi()
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [seeding, setSeeding] = useState(false)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/products')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as Product[]
      setProducts(Array.isArray(data) ? data : [])
    } catch (e) {
      setError((e as Error).message || 'Failed to load inventory')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function seedDemo() {
    setSeeding(true)
    try {
      const res = await apiFetch('/products/seed-demo', { method: 'POST' })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      await load()
    } catch (e) {
      setError((e as Error).message || 'Failed to seed demo inventory')
    } finally {
      setSeeding(false)
    }
  }

  const inr = (n: number) => `₹${n.toLocaleString('en-IN')}`

  return (
    <div className="page-card">
      <h2>Inventory</h2>
      <p style={{ marginBottom: '1rem' }}>
        Your merchant's product SKUs with live stock, price, margin, and staleness status. Fresh = updated
        within the last 24h.
      </p>
      {loading && <p style={{ color: '#60a5fa' }}>Loading inventory…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}
      {!loading && !error && products.length === 0 && (
        <div>
          <p style={{ color: '#facc15' }}>
            No products found for your account yet. Click below to seed sample products + campaigns so you can
            test the agent, governance, and ROAS.
          </p>
          <button
            onClick={seedDemo}
            disabled={seeding}
            style={{ marginTop: '0.5rem', padding: '0.6rem 1rem', fontWeight: 700, cursor: 'pointer' }}
          >
            {seeding ? 'Seeding…' : 'Seed my demo inventory'}
          </button>
        </div>
      )}
      {products.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
          <thead>
            <tr style={{ textAlign: 'left', color: 'var(--muted)' }}>
              <th style={{ padding: '0.5rem' }}>Name</th>
              <th style={{ padding: '0.5rem' }}>Stock</th>
              <th style={{ padding: '0.5rem' }}>Price</th>
              <th style={{ padding: '0.5rem' }}>Margin</th>
              <th style={{ padding: '0.5rem' }}>Status</th>
              <th style={{ padding: '0.5rem' }}>Updated (hrs ago)</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.id} style={{ borderTop: '1px solid var(--border)' }}>
                <td style={{ padding: '0.5rem' }}>{p.name}</td>
                <td style={{ padding: '0.5rem' }}>{p.stock_count}</td>
                <td style={{ padding: '0.5rem' }}>{inr(p.price)}</td>
                <td style={{ padding: '0.5rem' }}>{(p.margin * 100).toFixed(0)}%</td>
                <td style={{ padding: '0.5rem' }}>
                  <span
                    style={{
                      color: p.staleness_status === 'fresh' ? 'var(--green, #22c55e)' : '#ef4444',
                      textTransform: 'uppercase',
                      fontSize: '0.75rem',
                      fontWeight: 700,
                    }}
                  >
                    {p.staleness_status}
                  </span>
                </td>
                <td style={{ padding: '0.5rem' }}>{p.hours_since_update.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
