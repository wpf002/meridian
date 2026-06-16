import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { getStatus, getAlerts, ackAlert } from '../api/client.js'
import { Loading, ErrorState, PageTitle } from '../components/states.jsx'
import { pct, humanize, SEVERITY_COLOR } from '../lib/format.js'

const WEIGHT_COLOR = {
  macro: '#26e3a0', tactical: '#39b6f6', sentiment: '#8ad0ff', structural_risk: '#ff6b7a',
}

function AlertsPanel() {
  const [alerts, setAlerts] = useState(null)
  const load = () => getAlerts().then((d) => setAlerts(d.alerts)).catch(() => setAlerts([]))
  useEffect(() => { load() }, [])
  const ack = (id) => ackAlert(id).then(load)

  if (!alerts) return <Loading label="Loading alerts…" />
  return (
    <div className="card overflow-hidden">
      <div className="card-head flex justify-between">
        <span>Active Alerts</span>
        <span className="text-muted">{alerts.length}</span>
      </div>
      {alerts.length === 0 ? (
        <div className="px-4 py-3 text-green text-sm">No active alerts.</div>
      ) : (
        <ul className="divide-y divide-edge/50">
          {alerts.map((a) => (
            <li key={a.id} className="px-4 py-3 flex items-start gap-3">
              <span className={`chip ${SEVERITY_COLOR[a.severity] || ''}`}>{a.severity.toUpperCase()}</span>
              <div className="flex-1">
                <div className="text-sm">{a.message}</div>
                <div className="text-xs text-muted">{humanize(a.alert_type)} · {a.entity || '—'}</div>
              </div>
              <button onClick={() => ack(a.id)} className="btn py-1 text-xs">Ack</button>
            </li>
          ))}
        </ul>
      )}
      <div className="px-4 py-2 text-xs text-faint border-t border-edge/70">
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
      <PageTitle title="Status" sub="Model, scoring weights, accuracy & alerts." />

      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div className="card p-5">
          <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">Scoring Weights</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={weights} layout="vertical" margin={{ left: 36 }}>
              <XAxis type="number" domain={[0, 0.5]} stroke="#5d7689" fontSize={12} />
              <YAxis
                type="category"
                dataKey="name"
                stroke="#5d7689"
                width={104}
                fontSize={11}
                tickFormatter={humanize}
              />
              <Tooltip
                cursor={{ fill: '#0b192540' }}
                contentStyle={{ background: '#08111a', border: '1px solid #15303d', borderRadius: 8 }}
                formatter={(v) => v.toFixed(2)}
                labelFormatter={humanize}
              />
              <Bar dataKey="value" radius={[0, 3, 3, 0]}>
                {weights.map((w) => (
                  <Cell key={w.name} fill={WEIGHT_COLOR[w.name] || '#5d7689'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-5">
          <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">Accuracy by Classification</div>
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
                  <th className="th text-right">Avg Return</th>
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
          <div className="card-head">Model Version History</div>
          <ul className="divide-y divide-edge/50">
            {data.model_history.map((m, i) => (
              <li key={i} className="px-4 py-2.5 text-sm">
                <span className="font-mono font-bold text-green">v{m.version}</span>
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
