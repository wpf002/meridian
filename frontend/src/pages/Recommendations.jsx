import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecommendations } from '../api/client.js'
import { CONVICTION_COLOR, ACTION_COLOR } from '../lib/format.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState, Empty } from '../components/states.jsx'

export default function Recommendations() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    getRecommendations().then(setData).catch(setError)
  }, [])

  if (error) return <ErrorState error={error} />
  if (!data) return <Loading label="Scoring the universe…" />

  const rows = data.recommendations
  if (!rows.length) return <Empty label="No scored assets — provide signals or enable AURORA." />

  return (
    <div>
      <h1 className="text-2xl font-bold mb-1">Recommendations</h1>
      <p className="text-muted mb-6">
        {rows.length} scored · {data.skipped.length} skipped
      </p>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th w-10">#</th>
              <th className="th">Ticker</th>
              <th className="th text-right">ACS</th>
              <th className="th text-center">Tier</th>
              <th className="th">Classification</th>
              <th className="th">Conviction</th>
              <th className="th">Action</th>
              <th className="th">Flags</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.entity}
                onClick={() => navigate(`/asset/${r.entity}`)}
                className="cursor-pointer hover:bg-edge/40"
              >
                <td className="td text-muted">{r.rank}</td>
                <td className="td font-bold font-mono">{r.entity}</td>
                <td className="td text-right font-mono">{r.acs.toFixed(3)}</td>
                <td className="td text-center">{r.tier}</td>
                <td className="td"><Badge value={r.classification} /></td>
                <td className={`td font-mono ${CONVICTION_COLOR[r.conviction] || ''}`}>
                  {r.conviction}
                </td>
                <td className={`td font-mono ${ACTION_COLOR[r.action] || ''}`}>{r.action}</td>
                <td className="td text-tactical text-xs">
                  {r.flags.length ? r.flags.join(', ') : <span className="text-muted">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
