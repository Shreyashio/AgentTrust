import { useEffect, useState } from 'react'
import { useUser } from '@clerk/clerk-react'
import { useApi } from '../../lib/api'

interface Product {
  id: number
  name: string
  stock_count: number
  price: number
  margin: number
  staleness_status: string
}

export default function OverviewPage() {
  const { user } = useUser()
  const { apiFetch } = useApi()
  const [products, setProducts] = useState<Product[] | null>(null)
  const [msg, setMsg] = useState('Checking backend connection…')

  useEffect(() => {
    apiFetch('/products')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data) => {
        const list = Array.isArray(data) ? data : []
        setProducts(list)
        setMsg(`Backend connected on port 8000 — ${list.length} product(s) returned.`)
      })
      .catch(() => setMsg('Backend not running. Start it on port 8000.'))
  }, [])

  const totalStock = products ? products.reduce((s, p) => s + p.stock_count, 0) : 0
  const totalValue = products ? products.reduce((s, p) => s + p.price * p.stock_count, 0) : 0
  const staleCount = products ? products.filter((p) => p.staleness_status === 'stale').length : 0

  return (
    <div className="page-card">
      <h2>Welcome, {user?.firstName || 'merchant'}</h2>
      <p style={{ marginTop: '0.5rem' }}>
        This is your merchant dashboard. Use the sidebar to manage your inventory, run the agent, review
        governance, watch orders, and track ROAS.
      </p>
      <p style={{ marginTop: '1rem', color: '#60a5fa' }}>{msg}</p>

      {products && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '1rem',
            marginTop: '1.5rem',
          }}
        >
          <Stat label="Products" value={String(products.length)} />
          <Stat label="Total stock units" value={String(totalStock)} />
          <Stat label="Inventory value" value={`₹${totalValue.toLocaleString('en-IN')}`} />
          <Stat label="Stale SKUs" value={String(staleCount)} warn={staleCount > 0} />
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div style={{ background: '#0f172a', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem' }}>
      <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{label}</div>
      <div style={{ fontSize: '1.4rem', fontWeight: 700, color: warn ? '#facc15' : '#fff' }}>{value}</div>
    </div>
  )
}
