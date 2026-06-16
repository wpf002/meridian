import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { getPortfolio } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState } from '../components/states.jsx'
import { pct } from '../lib/format.js'

const SLEEVE_COLOR = {
  core: '#34d399', growth: '#22d3ee', defensive: '#7c93ff', tactical: '#fbbf24',
}
const SLEEVE_ORDER = ['core', 'growth', 'defensive', 'tactical']

export default function Portfolio() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getPortfolio().then(setData).catch(setError)
  }, [])

  if (error) return <ErrorState error={error.response?.data?.detail || error} />
  if (!data) return <Loading label="Building portfolio…" />

  const sleeves = Object.entries(data.sleeves).sort(
    (a, b) => SLEEVE_ORDER.indexOf(a[0]) - SLEEVE_ORDER.indexOf(b[0]),
  )
  const pie = sleeves.map(([name, s]) => ({ name, value: s.weight }))

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Portfolio</h1>
      <p className="text-muted mb-6">Total allocated {pct(data.total_weight)}</p>

      <div className="grid md:grid-cols-[260px_1fr] gap-6">
        <div className="card p-4">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" innerRadius={55} outerRadius={90} paddingAngle={2}>
                {pie.map((d) => (
                  <Cell key={d.name} fill={SLEEVE_COLOR[d.name] || '#8a93a6'} stroke="#0b0e14" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#121722', border: '1px solid #222a39', borderRadius: 8 }}
                formatter={(v, n) => [pct(v), n]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1 mt-2">
            {sleeves.map(([name, s]) => (
              <div key={name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: SLEEVE_COLOR[name] }} />
                  <span className="capitalize">{name}</span>
                </span>
                <span className="font-mono text-muted">{pct(s.weight)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {sleeves.map(([name, s]) => (
            <div key={name} className="card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2 border-b border-edge">
                <span className="font-medium capitalize" style={{ color: SLEEVE_COLOR[name] }}>
                  {name}
                </span>
                <span className="font-mono text-sm text-muted">{pct(s.weight)}</span>
              </div>
              {s.holdings.length ? (
                <table className="w-full">
                  <tbody>
                    {s.holdings.map((h) => (
                      <tr key={h.ticker} className="hover:bg-edge/40">
                        <td className="td">
                          <Link to={`/asset/${h.ticker}`} className="font-mono font-bold hover:text-accent">
                            {h.ticker}
                          </Link>
                        </td>
                        <td className="td"><Badge value={h.classification} /></td>
                        <td className="td text-right font-mono">{h.acs.toFixed(3)}</td>
                        <td className="td text-right font-mono">{pct(h.weight)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="px-4 py-3 text-muted text-sm">empty</div>
              )}
            </div>
          ))}

          {data.warnings.length > 0 && (
            <div className="card p-4 border-tactical/40">
              {data.warnings.map((w, i) => (
                <div key={i} className="text-tactical text-sm">⚠ {w}</div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
