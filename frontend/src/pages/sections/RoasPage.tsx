import { useEffect, useState } from 'react'
import { useApi } from '../../lib/api'

interface CampaignROAS {
  campaign_id: number
  campaign_name: string
  product_name?: string | null
  cost: number
  human_revenue: number
  agent_revenue: number
  total_revenue: number
  human_roas: number
  agent_roas: number
  total_roas: number
  orders_count: { human: number; agent: number; total: number }
}

interface ROASReport {
  summary: {
    total_cost: number
    total_revenue: number
    human_revenue: number
    agent_revenue: number
    human_roas: number
    agent_roas: number
    total_roas: number
    orders_count: { human: number; agent: number; total: number }
  }
  campaigns: CampaignROAS[]
}

export default function RoasPage() {
  const { apiFetch } = useApi()
  const [report, setReport] = useState<ROASReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    apiFetch('/analytics/roas')
      .then((res: Response) => (res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`))))
      .then((data: ROASReport) => {
        if (!cancelled) setReport(data)
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
    <div className="page-card" style={{ maxWidth: '1000px' }}>
      <h2>ROAS Report</h2>
      <p style={{ marginBottom: '1rem' }}>
        Return on ad spend split by human vs agent purchases, per campaign and overall.
      </p>
      {loading && <p style={{ color: '#60a5fa' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}

      {report && (
        <>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '0.75rem',
              marginBottom: '1.5rem',
            }}
          >
            <Stat label="Total cost" value={`₹${report.summary.total_cost.toLocaleString('en-IN')}`} />
            <Stat label="Total revenue" value={`₹${report.summary.total_revenue.toLocaleString('en-IN')}`} />
            <Stat label="Total ROAS" value={`${report.summary.total_roas.toFixed(2)}x`} />
            <Stat label="Human ROAS" value={`${report.summary.human_roas.toFixed(2)}x`} />
            <Stat label="Agent ROAS" value={`${report.summary.agent_roas.toFixed(2)}x`} />
          </div>

          <h3 style={{ margin: '0 0 0.5rem 0' }}>Per Campaign</h3>
          {report.campaigns.length === 0 && (
            <p style={{ color: 'var(--muted)' }}>No campaigns with spend yet.</p>
          )}
          {report.campaigns.map((c) => (
            <div
              key={c.campaign_id}
              style={{
                background: '#0f172a',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '0.75rem 1rem',
                marginBottom: '0.5rem',
              }}
            >
              <strong>
                {c.campaign_name} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>({c.product_name})</span>
              </strong>
              <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>
                Cost ₹{c.cost.toLocaleString('en-IN')} · Revenue ₹{c.total_revenue.toLocaleString('en-IN')} · ROAS{' '}
                <strong style={{ color: '#60a5fa' }}>{c.total_roas.toFixed(2)}x</strong>
              </p>
              <p style={{ color: 'var(--muted)', fontSize: '0.8rem', margin: 0 }}>
                human: {`${c.human_roas.toFixed(2)}x (₹${c.human_revenue.toLocaleString('en-IN')})`} · agent:{' '}
                {`${c.agent_roas.toFixed(2)}x (₹${c.agent_revenue.toLocaleString('en-IN')})`} · orders:{' '}
                {c.orders_count.total}
              </p>
            </div>
          ))}
        </>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ background: '#0f172a', border: '1px solid var(--border)', borderRadius: 10, padding: '1rem' }}>
      <div style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{label}</div>
      <div style={{ fontSize: '1.3rem', fontWeight: 700, color: '#fff' }}>{value}</div>
    </div>
  )
}
