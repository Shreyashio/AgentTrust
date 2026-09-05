import { useEffect, useState } from 'react'
import { useApi } from '../../lib/api'

interface PolicyLog {
  id: number
  action: string
  details: string
  result: string
  reason: string
  timestamp: string
}

const resultColor: Record<string, string> = {
  approved: '#22c55e',
  needs_approval: '#facc15',
  blocked: '#ef4444',
}

export default function GovernancePage() {
  const { apiFetch } = useApi()
  const [logs, setLogs] = useState<PolicyLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Manual policy check form
  const [action, setAction] = useState('launch_campaign')
  const [budget, setBudget] = useState('1500')
  const [checkResult, setCheckResult] = useState<string | null>(null)
  const [checkReason, setCheckReason] = useState('')

  async function load() {
    setLoading(true)
    try {
      const res = await apiFetch('/governance/logs')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = (await res.json()) as PolicyLog[]
      setLogs(Array.isArray(data) ? data : [])
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function runCheck() {
    setCheckResult(null)
    setCheckReason('')
    try {
      const res = await apiFetch('/governance/check', {
        method: 'POST',
        body: JSON.stringify({
          action,
          details: { budget: Number(budget), campaign_name: 'Manual Check' },
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setCheckResult(data.result)
      setCheckReason(data.reason)
      load()
    } catch (e) {
      setCheckReason((e as Error).message)
    }
  }

  return (
    <div className="page-card" style={{ maxWidth: '900px' }}>
      <h2>Governance</h2>
      <p style={{ marginBottom: '1rem' }}>
        Manually evaluate an action against the policy engine, then review every decision the agent has
        triggered.
      </p>

      <div
        style={{
          display: 'flex',
          gap: '0.5rem',
          alignItems: 'center',
          flexWrap: 'wrap',
          marginBottom: '1rem',
        }}
      >
        <select
          value={action}
          onChange={(e) => setAction(e.target.value)}
          style={{
            background: '#0f172a',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '0.5rem',
          }}
        >
          <option value="launch_campaign">launch_campaign</option>
          <option value="adjust_ad_budget">adjust_ad_budget</option>
        </select>
        <input
          type="number"
          value={budget}
          onChange={(e) => setBudget(e.target.value)}
          style={{
            background: '#0f172a',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '0.5rem',
            width: 120,
          }}
        />
        <button onClick={runCheck} style={{ padding: '0.5rem 1rem', fontWeight: 700, cursor: 'pointer' }}>
          Check
        </button>
      </div>

      {checkResult && (
        <p style={{ margin: '0 0 1rem 0' }}>
          <strong style={{ color: resultColor[checkResult] || 'var(--text)', textTransform: 'uppercase' }}>
            {checkResult}
          </strong>{' '}
          <span style={{ color: 'var(--muted)' }}>{checkReason}</span>
        </p>
      )}

      <h3 style={{ margin: '1rem 0 0.5rem 0' }}>Decision Log</h3>
      {loading && <p style={{ color: '#60a5fa' }}>Loading…</p>}
      {error && <p style={{ color: '#ef4444' }}>{error}</p>}
      {!loading && logs.length === 0 && (
        <p style={{ color: 'var(--muted)' }}>
          No governance decisions yet. Run the agent or use the check form above.
        </p>
      )}
      {logs.map((l) => (
        <div
          key={l.id}
          style={{
            background: '#0f172a',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '0.75rem 1rem',
            marginBottom: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <strong>{l.action}</strong>
            <span style={{ color: resultColor[l.result] || 'var(--text)', fontWeight: 700, textTransform: 'uppercase' }}>
              {l.result}
            </span>
          </div>
          <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>{l.reason}</p>
          <p style={{ color: 'var(--muted)', fontSize: '0.75rem', margin: 0 }}>
            {new Date(l.timestamp).toLocaleString()} · details: {l.details}
          </p>
        </div>
      ))}
    </div>
  )
}
