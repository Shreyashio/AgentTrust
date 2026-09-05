import { useState } from 'react'
import { useApi } from '../../lib/api'

interface Step {
  tool: string
  input: Record<string, unknown>
  governance_result?: string | null
  governance_reason?: string | null
  output: Record<string, unknown>
}

interface AgentResult {
  instruction: string
  status: string
  steps: Step[]
  final_summary: string
}

const EXAMPLES = [
  'Increase the budget of campaign 1 to 500',
  'Create an ad and launch a campaign for Wireless Noise-Cancelling Headphones',
  'Check inventory of the Mechanical Gaming Keyboard RGB',
]

const statusColor: Record<string, string> = {
  approved_and_executed: '#22c55e',
  held_for_approval: '#facc15',
  blocked_due_to_stale_data: '#ef4444',
}

export default function AgentPage() {
  const { apiFetch } = useApi()
  const [instruction, setInstruction] = useState('')
  const [result, setResult] = useState<AgentResult | null>(null)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')

  async function run(inst: string) {
    setRunning(true)
    setError('')
    setResult(null)
    try {
      const res = await apiFetch('/agent/act', {
        method: 'POST',
        body: JSON.stringify({ instruction: inst }),
      })
      if (!res.ok) {
        const body = await res.text()
        throw new Error(`HTTP ${res.status}${body ? ` — ${body}` : ''}`)
      }
      setResult(await res.json())
    } catch (e) {
      setError((e as Error).message || 'Failed to run agent')
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="page-card" style={{ maxWidth: '900px' }}>
      <h2>AI Agent</h2>
      <p style={{ marginBottom: '1rem' }}>
        Give your AI agent a natural-language instruction. It decides which tools to call and automatically
        runs them through the governance policy engine.
      </p>

      <textarea
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        placeholder="e.g. Increase the budget of campaign 1 to 500"
        style={{
          width: '100%',
          minHeight: '80px',
          background: '#0f172a',
          color: 'var(--text)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '0.75rem',
          fontFamily: 'inherit',
          resize: 'vertical',
        }}
      />
      <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
        <button
          onClick={() => run(instruction)}
          disabled={running || !instruction.trim()}
          style={{ padding: '0.6rem 1rem', fontWeight: 700, cursor: 'pointer' }}
        >
          {running ? 'Running…' : 'Run Agent'}
        </button>
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            onClick={() => {
              setInstruction(ex)
              run(ex)
            }}
            disabled={running}
            style={{
              background: 'transparent',
              color: 'var(--accent)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '0.5rem 0.75rem',
              cursor: 'pointer',
              fontSize: '0.85rem',
            }}
          >
            {ex}
          </button>
        ))}
      </div>

      {error && <p style={{ color: '#ef4444', marginTop: '1rem' }}>{error}</p>}

      {result && (
        <div style={{ marginTop: '1.5rem' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              marginBottom: '0.75rem',
            }}
          >
            <span style={{ fontWeight: 700 }}>Status:</span>
            <span
              style={{
                color: statusColor[result.status] || 'var(--text)',
                fontWeight: 700,
                textTransform: 'capitalize',
              }}
            >
              {result.status.replace(/_/g, ' ')}
            </span>
          </div>

          {result.steps.map((step, i) => (
            <div
              key={i}
              style={{
                background: '#0f172a',
                border: '1px solid var(--border)',
                borderRadius: 10,
                padding: '1rem',
                marginBottom: '0.75rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>
                  {i + 1}. {step.tool}
                </strong>
                <span
                  style={{
                    color:
                      step.governance_result === 'approved'
                        ? '#22c55e'
                        : step.governance_result === 'blocked'
                          ? '#ef4444'
                          : '#facc15',
                    fontWeight: 600,
                  }}
                >
                  {step.governance_result || 'n/a'}
                </span>
              </div>
              {step.governance_reason && (
                <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: '0.25rem 0' }}>
                  {step.governance_reason}
                </p>
              )}
              <pre
                style={{
                  whiteSpace: 'pre-wrap',
                  background: '#111827',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '0.5rem',
                  fontSize: '0.8rem',
                  maxHeight: 160,
                  overflow: 'auto',
                  color: '#cbd5e1',
                }}
              >
                {JSON.stringify(step.output, null, 2)}
              </pre>
            </div>
          ))}

          {result.final_summary && (
            <p style={{ color: 'var(--text)', marginTop: '1rem' }}>
              <strong>Summary:</strong> {result.final_summary}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
