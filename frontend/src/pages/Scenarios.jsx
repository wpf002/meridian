import { useEffect, useState } from 'react'
import { getScenarios, runScenario } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState, PageTitle } from '../components/states.jsx'
import { deltaColor, score, scoreSigned, sleeveLabel, regimeLabel } from '../lib/format.js'

function Banner({ report }) {
  const pb = report.portfolio_baseline_acs
  const ps = report.portfolio_base_acs
  return (
    <div className="card p-5 mb-5 shadow-glow-blue">
      <div className="text-lg font-bold">If this happened: {report.scenario}</div>
      <div className="flex flex-wrap gap-x-8 gap-y-2 mt-3 text-sm">
        <span className="flex items-center gap-2">
          <span className="label">Portfolio score</span>
          <span className="font-mono">{score(pb)} → {score(ps)}</span>
          <span className={`font-mono ${deltaColor(ps - pb)}`}>
            ({scoreSigned(ps - pb)})
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="label">Names that get worse</span>
          <span className="text-avoid font-mono">{report.downgrades}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="label">Market shifts to</span>
          <span className="text-tactical font-mono">{regimeLabel(report.scenario_regime)}</span>
        </span>
      </div>
    </div>
  )
}

export default function Scenarios() {
  const [list, setList] = useState(null)
  const [error, setError] = useState(null)
  const [active, setActive] = useState(null)
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    getScenarios().then((d) => setList(d.scenarios)).catch(setError)
  }, [])

  const run = (scenario) => {
    setActive(scenario)
    setReport(null)
    setError(null)
    setBusy(true)
    runScenario(scenario.slug)
      .then(setReport)
      .catch((e) => setError(e.response?.data?.detail || e.message || String(e)))
      .finally(() => setBusy(false))
  }

  if (error && !list) return <ErrorState error={error} />
  if (!list) return <Loading label="Loading scenarios…" />

  return (
    <div>
      <PageTitle
        title="Scenarios"
        sub="Pick a 'what if' below to see how your names would hold up if the market turned. Lower score = hit harder."
      />

      <div className="flex flex-wrap gap-2 mb-6">
        {list.map((s) => (
          <button
            key={s.slug}
            onClick={() => run(s)}
            title={s.description}
            className={`btn ${active?.slug === s.slug ? 'btn-active' : ''}`}
          >
            {s.name}
          </button>
        ))}
      </div>

      {busy && <Loading label={`Running ${active?.name}…`} />}

      {error && !busy && (
        <div className="card p-4 border-avoid/40 max-w-lg">
          <div className="text-avoid font-medium mb-1">Scenario run failed</div>
          <div className="text-muted text-sm font-mono">{String(error)}</div>
        </div>
      )}

      {report && !busy && (
        <>
          <Banner report={report} />

          <div className="grid lg:grid-cols-[1fr_320px] gap-5">
            <div className="card overflow-x-auto">
              <div className="card-head">How each name holds up</div>
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr>
                    <th className="th">Ticker</th>
                    <th className="th">Bucket</th>
                    <th className="th text-right">Now</th>
                    <th className="th text-right">Stressed</th>
                    <th className="th text-right">Change</th>
                    <th className="th text-right">Best / Worst</th>
                    <th className="th">Tier</th>
                  </tr>
                </thead>
                <tbody>
                  {[...report.entities].sort((a, b) => a.acs_delta - b.acs_delta).map((e) => (
                    <tr key={e.entity} className="hover:bg-raised/50 transition-colors">
                      <td className="td font-mono font-bold">{e.entity}</td>
                      <td className="td text-muted">{sleeveLabel(e.sleeve)}</td>
                      <td className="td text-right font-mono">{score(e.baseline_acs)}</td>
                      <td className="td text-right font-mono">{score(e.base_acs)}</td>
                      <td className={`td text-right font-mono ${deltaColor(e.acs_delta)}`}>
                        {scoreSigned(e.acs_delta)}
                      </td>
                      <td className="td text-right font-mono text-xs">
                        <span className="text-core">{score(e.best_acs)}</span>
                        <span className="text-faint"> / </span>
                        <span className="text-avoid">{score(e.worst_acs)}</span>
                      </td>
                      <td className="td">
                        {e.classification_changed ? (
                          <span className="flex items-center gap-1">
                            <Badge value={e.baseline_classification} />
                            <span className="text-faint">→</span>
                            <Badge value={e.scenario_classification} />
                          </span>
                        ) : (
                          <Badge value={e.baseline_classification} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="card overflow-hidden h-fit self-start lg:sticky lg:top-4">
              <div className="card-head">Worst-case hit by bucket</div>
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th">Bucket</th>
                    <th className="th text-right">Names</th>
                    <th className="th text-right">Worst drop</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sleeve_impacts.map((s) => (
                    <tr key={s.sleeve}>
                      <td className="td">{sleeveLabel(s.sleeve)}</td>
                      <td className="td text-right font-mono">{s.asset_count}</td>
                      <td className={`td text-right font-mono ${deltaColor(s.worst_drawdown)}`}>
                        {scoreSigned(s.worst_drawdown)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
