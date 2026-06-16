import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { getPortfolio } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState, PageTitle } from '../components/states.jsx'
import { pct, titleCase } from '../lib/format.js'

const SLEEVE_COLOR = {
  core: '#26e3a0', growth: '#39b6f6', defensive: '#8a7dff', tactical: '#f5b53d',
}
const SLEEVE_ORDER = ['core', 'growth', 'defensive', 'tactical']

export default function Portfolio() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getPortfolio().then(setData).catch(setError)
  }, [])

  if (error) return <ErrorState error={error.response?.data?.detail || error} />
  if (!data) return <Loading label="Constructing portfolio…" />

  const sleeves = Object.entries(data.sleeves).sort(
    (a, b) => SLEEVE_ORDER.indexOf(a[0]) - SLEEVE_ORDER.indexOf(b[0]),
  )
  const pie = sleeves.map(([name, s]) => ({ name, value: s.weight }))

  return (
    <div>
      <PageTitle title="Portfolio" sub={`Four-sleeve allocation · ${pct(data.total_weight)} allocated`} />

      <div className="grid md:grid-cols-[280px_1fr] gap-6">
        <div className="card p-5 h-fit">
          <ResponsiveContainer width="100%" height={210}>
            <PieChart>
              <Pie data={pie} dataKey="value" nameKey="name" innerRadius={56} outerRadius={92} paddingAngle={2}>
                {pie.map((d) => (
                  <Cell key={d.name} fill={SLEEVE_COLOR[d.name] || '#5d7689'} stroke="#04070b" strokeWidth={2} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#08111a', border: '1px solid #15303d', borderRadius: 8 }}
                formatter={(v, n) => [pct(v), titleCase(n)]}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-1.5 mt-3">
            {sleeves.map(([name, s]) => (
              <div key={name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: SLEEVE_COLOR[name] }} />
                  <span>{titleCase(name)}</span>
                </span>
                <span className="font-mono text-muted">{pct(s.weight)}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="space-y-4">
          {sleeves.map(([name, s]) => (
            <div key={name} className="card overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-edge/70">
                <span className="font-semibold tracking-wide" style={{ color: SLEEVE_COLOR[name] }}>
                  {titleCase(name)}
                </span>
                <span className="font-mono text-sm text-muted">{pct(s.weight)}</span>
              </div>
              {s.holdings.length ? (
                <table className="w-full">
                  <tbody>
                    {s.holdings.map((h) => (
                      <tr key={h.ticker} className="hover:bg-raised/50 transition-colors">
                        <td className="td">
                          <Link to={`/asset/${h.ticker}`} className="font-mono font-bold hover:text-green">
                            {h.ticker}
                          </Link>
                        </td>
                        <td className="td"><Badge value={h.classification} /></td>
                        <td className="td text-right font-mono text-muted">{h.acs.toFixed(3)}</td>
                        <td className="td text-right font-mono">{pct(h.weight)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="px-4 py-3 text-faint text-sm">Empty</div>
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
