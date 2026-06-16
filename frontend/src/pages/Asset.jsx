import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan, getUniverse, compareAssets } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import AcsComponentsChart from '../components/AcsComponentsChart.jsx'
import { Loading, ErrorState } from '../components/states.jsx'
import { CONVICTION_COLOR, ACTION_COLOR, deltaColor, humanize } from '../lib/format.js'

function Stat({ label, value, className = '' }) {
  return (
    <div className="card px-4 py-3">
      <div className="label">{label}</div>
      <div className={`text-lg font-mono mt-1 ${className}`}>{value}</div>
    </div>
  )
}

function ComparePanel({ ticker }) {
  const [tickers, setTickers] = useState([])
  const [other, setOther] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getUniverse()
      .then((d) => setTickers(d.assets.map((a) => a.ticker).filter((t) => t !== ticker)))
      .catch(() => {})
  }, [ticker])

  const run = () => {
    if (!other) return
    setBusy(true)
    compareAssets(ticker, other).then(setResult).catch(() => setResult(null)).finally(() => setBusy(false))
  }

  const rows = result
    ? [
        ['ACS', result.a.acs, result.b.acs, result.delta.acs],
        ['Macro', result.a.components.mas, result.b.components.mas, result.delta.mas],
        ['Tactical', result.a.components.tas, result.b.components.tas, result.delta.tas],
        ['Sentiment', result.a.components.sas, result.b.components.sas, result.delta.sas],
        ['Structural Risk', result.a.components.srs, result.b.components.srs, result.delta.srs],
      ]
    : []

  return (
    <div className="card p-5">
      <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">Compare</div>
      <div className="flex items-center gap-2 mb-4">
        <select
          value={other}
          onChange={(e) => setOther(e.target.value)}
          className="bg-base border border-edge rounded px-2 py-1.5 text-sm font-mono focus:border-green/60 outline-none"
        >
          <option value="">Select asset…</option>
          {tickers.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <button onClick={run} disabled={!other || busy} className="btn">
          {busy ? 'Comparing…' : 'Compare'}
        </button>
      </div>

      {result && (
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Component</th>
              <th className="th text-right font-mono">{result.a.entity}</th>
              <th className="th text-right font-mono">{result.b.entity}</th>
              <th className="th text-right">Δ</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, a, b, d]) => (
              <tr key={label}>
                <td className="td text-muted">{label}</td>
                <td className="td text-right font-mono">{a.toFixed(3)}</td>
                <td className="td text-right font-mono">{b.toFixed(3)}</td>
                <td className={`td text-right font-mono ${deltaColor(d)}`}>
                  {d >= 0 ? '+' : ''}{d.toFixed(3)}
                </td>
              </tr>
            ))}
            <tr>
              <td className="td text-muted">Classification</td>
              <td className="td text-right"><Badge value={result.a.classification} /></td>
              <td className="td text-right"><Badge value={result.b.classification} /></td>
              <td className="td" />
            </tr>
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function Asset() {
  const { ticker } = useParams()
  const [scan, setScan] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setScan(null)
    setError(null)
    getScan(ticker).then(setScan).catch(setError)
  }, [ticker])

  return (
    <div>
      <Link to="/" className="text-muted text-sm hover:text-green font-mono">← Recommendations</Link>

      {error ? (
        <div className="mt-4"><ErrorState error={error.response?.data?.detail || error} /></div>
      ) : !scan ? (
        <div className="mt-4"><Loading label={`Scoring ${ticker}…`} /></div>
      ) : (
        <>
          <div className="flex flex-wrap items-center gap-4 mt-3 mb-6">
            <h1 className="text-3xl font-bold font-mono tracking-tight">{scan.entity}</h1>
            <Badge value={scan.classification} />
            <span className="chip text-muted">Tier {scan.tier}</span>
            <span className={`chip ${ACTION_COLOR[scan.action] || ''}`}>{scan.action}</span>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <Stat label="ACS" value={scan.acs.toFixed(3)} className="text-2xl text-green" />
            <Stat label="Conviction" value={scan.conviction} className={CONVICTION_COLOR[scan.conviction]} />
            <Stat label="Confidence" value={scan.confidence.toFixed(2)} />
            <Stat label="Signals" value={scan.signal_count} />
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div className="card p-5">
              <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">ACS Components</div>
              <AcsComponentsChart components={scan.components} weights={scan.weights} />
            </div>

            <div className="card p-5">
              <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">Signals & Flags</div>
              <dl className="text-sm space-y-2.5">
                <div className="flex justify-between">
                  <dt className="text-muted">Signal Agreement</dt>
                  <dd className="font-mono">{scan.signal_agreement.toFixed(2)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted">Model</dt>
                  <dd className="font-mono">v{scan.model_version}</dd>
                </div>
                <div>
                  <dt className="text-muted mb-1.5">Flags</dt>
                  <dd className="flex flex-wrap gap-1.5">
                    {scan.flags.length ? (
                      scan.flags.map((f) => (
                        <span key={f} className="chip text-tactical border-tactical/40">{humanize(f)}</span>
                      ))
                    ) : (
                      <span className="text-faint text-xs">None</span>
                    )}
                  </dd>
                </div>
                {scan.override_reason && (
                  <div>
                    <dt className="text-muted">Override</dt>
                    <dd className="text-sm">{scan.override_reason}</dd>
                  </div>
                )}
              </dl>
            </div>
          </div>

          {scan.notes?.length > 0 && (
            <div className="card p-4 mb-6 text-sm text-muted">
              {scan.notes.map((n, i) => <div key={i}>· {n}</div>)}
            </div>
          )}

          <div className="card p-4 mb-6">
            <div className="label mb-1.5">Rationale</div>
            <div className="text-sm font-mono text-ink/90">{scan.rationale}</div>
          </div>

          <ComparePanel ticker={scan.entity} />
        </>
      )}
    </div>
  )
}
