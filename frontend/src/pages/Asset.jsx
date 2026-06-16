import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getScan, getUniverse, compareAssets, addAsset, removeAsset } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import AcsComponentsChart from '../components/AcsComponentsChart.jsx'
import { Loading, ErrorState } from '../components/states.jsx'
import { CONVICTION_COLOR, ACTION_COLOR, deltaColor, humanize, titleCase, score, scoreSigned, actionLabel } from '../lib/format.js'

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
        ['Score', result.a.acs, result.b.acs, result.delta.acs],
        ['Macro', result.a.components.mas, result.b.components.mas, result.delta.mas],
        ['Price trend', result.a.components.tas, result.b.components.tas, result.delta.tas],
        ['News', result.a.components.sas, result.b.components.sas, result.delta.sas],
        ['Risk', result.a.components.srs, result.b.components.srs, result.delta.srs],
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
                <td className="td text-right font-mono">{score(a)}</td>
                <td className="td text-right font-mono">{score(b)}</td>
                <td className={`td text-right font-mono ${deltaColor(d)}`}>
                  {scoreSigned(d)}
                </td>
              </tr>
            ))}
            <tr>
              <td className="td text-muted">Tier</td>
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

function WatchlistButton({ ticker }) {
  const [inList, setInList] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getUniverse()
      .then((d) => setInList(d.assets.some((a) => a.ticker === ticker.toUpperCase())))
      .catch(() => setInList(false))
  }, [ticker])

  const toggle = () => {
    setBusy(true)
    const action = inList ? removeAsset(ticker) : addAsset(ticker)
    action.then(() => setInList(!inList)).finally(() => setBusy(false))
  }

  if (inList === null) return null
  return (
    <button onClick={toggle} disabled={busy} className={`btn ml-auto ${inList ? 'btn-active' : ''}`}>
      {inList ? '✓ In watchlist' : '+ Add to watchlist'}
    </button>
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
            <span className={`chip ${ACTION_COLOR[scan.action] || ''}`}>{actionLabel(scan.action)}</span>
            <WatchlistButton ticker={scan.entity} />
          </div>

          <div className="grid grid-cols-3 gap-3 mb-6">
            <Stat label="Score / 100" value={score(scan.acs)} className="text-2xl text-green" />
            <Stat label="Confidence" value={titleCase(scan.conviction)} className={CONVICTION_COLOR[scan.conviction]} />
            <Stat label="Signals used" value={scan.signal_count} />
          </div>

          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <div className="card p-5">
              <div className="card-head -mx-5 -mt-5 mb-4 rounded-t-lg">What drives the Score</div>
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
            <div className="text-sm font-mono text-ink/90">{scan.rationale.replace(/_/g, ' ')}</div>
          </div>

          <ComparePanel ticker={scan.entity} />
        </>
      )}
    </div>
  )
}
