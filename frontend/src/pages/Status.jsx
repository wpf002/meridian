import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { getStatus, getAlerts, ackAlert } from '../api/client.js'
import { Loading, ErrorState } from '../components/states.jsx'
import { pct } from '../lib/format.js'

const SEVERITY = {
  high: 'border-avoid/50 text-avoid',
  medium: 'border-tactical/50 text-tactical',
  low: 'border-edge text-muted',
}
const WEIGHT_COLOR = {
  macro: '#34d399', tactical: '#22d3ee', sentiment: '#7c93ff', structural_risk: '#f87171',
}

function AlertsPanel() {
  const [alerts, setAlerts] = useState(null)
  const load = () => getAlerts().then((d) => setAlerts(d.alerts)).catch(() => setAlerts([]))
  useEffect(() => { load() }, [])

  const ack = (id) => ackAlert(id).then(load)

  if (!alerts) return <Loading label="Loading alerts…" />
  return (
    <div className="card overflow-hidden">
      <div className="px-4 py-2 border-b border-edge font-medium flex justify-between">
        <span>Active alerts</span>
        <span className="text-muted text-sm">{alerts.length}</span>
      </div>
      {alerts.length === 0 ? (
        <div className="px-4 py-3 text-core text-sm">No active alerts.</div>
      ) : (
        <ul className="divide-y divide-edge/60">
          {alerts.map((a) => (
            <li key={a.id} className="px-4 py-3 flex items-start gap-3">
              <span className={`text-xs font-mono border rounded px-2 py-0.5 ${SEVERITY[a.severity] || ''}`}>
                {a.severity.toUpperCase()}
              </span>
              <div className="flex-1">
                <div className="text-sm">{a.message}</div>
                <div className="text-xs text-muted">{a.alert_type} · {a.entity || '—'}</div>
              </div>
              <button
                onClick={() => ack(a.id)}
                className="text-xs px-2 py-1 rounded border border-edge text-muted hover:text-ink"
              >
                ack
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="px-4 py-2 text-xs text-muted border-t border-edge">
        Alerts are evaluated when a daily brief runs.
      </div>
    </div>
  )
}

export default function Status() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getStatus().then(setData).catch(setError)
  }, [])

  if (error) return <ErrorState error={error} />
  if (!data) return <Loading label="Loading status…" />

  const weights = Object.entries(data.weights).map(([name, value]) => ({ name, value }))
  const accuracy = Object.entries(data.accuracy || {})

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Status</h1>
      <p className="text-muted mb-6">
        Model <span className="font-mono text-ink">v{data.model_version}</span> · signal source{' '}
        <span className={`font-mono ${data.signal_source === 'AURORA' ? 'text-core' : 'text-ink'}`}>
          {data.signal_source}
        </span>
      </p>

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <div className="font-medium mb-3">Scoring weights</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={weights} layout="vertical" margin={{ left: 24 }}>
              <XAxis type="number" domain={[0, 0.5]} stroke="#8a93a6" fontSize={12} />
              <YAxis type="category" dataKey="name" stroke="#8a93a6" width={90} fontSize={11} />
              <Tooltip
                cursor={{ fill: '#222a3955' }}
                contentStyle={{ background: '#121722', border: '1px solid #222a39', borderRadius: 8 }}
                formatter={(v) => v.toFixed(2)}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {weights.map((w) => (
                  <Cell key={w.name} fill={WEIGHT_COLOR[w.name] || '#8a93a6'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <div className="font-medium mb-3">Accuracy by classification</div>
          {accuracy.length === 0 ? (
            <div className="text-muted text-sm">
              No resolved outcomes yet — resolve returns to populate this.
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr>
                  <th className="th">Class</th>
                  <th className="th text-right">Accuracy</th>
                  <th className="th text-right">Resolved</th>
                  <th className="th text-right">Avg return</th>
                </tr>
              </thead>
              <tbody>
                {accuracy.map(([cls, s]) => (
                  <tr key={cls}>
                    <td className="td font-mono">{cls}</td>
                    <td className="td text-right font-mono">{pct(s.accuracy)}</td>
                    <td className="td text-right font-mono">{s.correct}/{s.total}</td>
                    <td className="td text-right font-mono">
                      {s.avg_return >= 0 ? '+' : ''}{(s.avg_return * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card overflow-hidden">
          <div className="px-4 py-2 border-b border-edge font-medium">Model version history</div>
          <ul className="divide-y divide-edge/60">
            {data.model_history.map((m, i) => (
              <li key={i} className="px-4 py-2 text-sm">
                <span className="font-mono font-bold">v{m.version}</span>
                <span className="text-muted ml-2">{m.notes}</span>
              </li>
            ))}
          </ul>
        </div>

        <AlertsPanel />
      </div>
    </div>
  )
}
