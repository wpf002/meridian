import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getRecommendations } from '../api/client.js'
import { CONVICTION_COLOR, ACTION_COLOR, humanize } from '../lib/format.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState, Empty, PageTitle } from '../components/states.jsx'

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
      <PageTitle
        title="Recommendations"
        sub={`${rows.length} scored · ${data.skipped.length} without signals`}
      />

      <div className="card overflow-x-auto">
        <table className="w-full min-w-[680px]">
          <thead>
            <tr>
              <th className="th w-12 text-center">#</th>
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
                className="cursor-pointer hover:bg-raised/50 transition-colors"
              >
                <td className="td text-center text-faint font-mono">{r.rank}</td>
                <td className="td font-bold font-mono text-ink">{r.entity}</td>
                <td className="td text-right font-mono">{r.acs.toFixed(3)}</td>
                <td className="td text-center font-mono text-muted">{r.tier}</td>
                <td className="td"><Badge value={r.classification} /></td>
                <td className={`td font-mono text-xs ${CONVICTION_COLOR[r.conviction] || ''}`}>
                  {r.conviction}
                </td>
                <td className={`td font-mono text-xs ${ACTION_COLOR[r.action] || ''}`}>{r.action}</td>
                <td className="td text-tactical text-xs">
                  {r.flags.length ? r.flags.map(humanize).join(', ') : <span className="text-faint">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
