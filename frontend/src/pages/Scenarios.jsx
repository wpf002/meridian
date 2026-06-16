import { useEffect, useState } from 'react'
import { getScenarios, runScenario } from '../api/client.js'
import Badge from '../components/Badge.jsx'
import { Loading, ErrorState, PageTitle } from '../components/states.jsx'
import { deltaColor, titleCase } from '../lib/format.js'

function Banner({ report }) {
  const pb = report.portfolio_baseline_acs
  const ps = report.portfolio_base_acs
  return (
    <div className="card p-5 mb-5 shadow-glow-blue">
      <div className="text-lg font-bold">{report.scenario}</div>
      <div className="flex flex-wrap gap-x-8 gap-y-2 mt-3 text-sm">
        <span className="flex items-center gap-2">
          <span className="label">Stressed Regime</span>
          <span className="text-tactical font-mono">{report.scenario_regime}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="label">Current Regime</span>
          <span className="text-blue font-mono">{report.current_regime}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="label">Portfolio ACS</span>
          <span className="font-mono">{pb.toFixed(3)} → {ps.toFixed(3)}</span>
          <span className={`font-mono ${deltaColor(ps - pb)}`}>
            ({ps - pb >= 0 ? '+' : ''}{(ps - pb).toFixed(3)})
          </span>
        </span>
        <span className="flex items-center gap-2">
          <span className="label">Downgrades</span>
          <span className="text-avoid font-mono">{report.downgrades}</span>
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
    setBusy(true)
    runScenario(scenario.slug).then(setReport).catch((e) => setError(e)).finally(() => setBusy(false))
  }

  if (error && !list) return <ErrorState error={error} />
  if (!list) return <Loading label="Loading scenarios…" />

  return (
    <div>
      <PageTitle title="Scenarios" sub="Stress-test the universe against a macro shock." />

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

      {report && !busy && (
        <>
          <Banner report={report} />

          <div className="grid lg:grid-cols-[1fr_320px] gap-5">
            <div className="card overflow-x-auto">
              <div className="card-head">Per-Asset Impact</div>
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr>
                    <th className="th">Ticker</th>
                    <th className="th">Sleeve</th>
                    <th className="th text-right">Base</th>
                    <th className="th text-right">Scenario</th>
                    <th className="th text-right">Δ</th>
                    <th className="th text-right">Best / Worst</th>
                    <th className="th">Class</th>
                  </tr>
                </thead>
                <tbody>
                  {[...report.entities].sort((a, b) => a.acs_delta - b.acs_delta).map((e) => (
                    <tr key={e.entity} className="hover:bg-raised/50 transition-colors">
                      <td className="td font-mono font-bold">{e.entity}</td>
                      <td className="td text-muted">{titleCase(e.sleeve)}</td>
                      <td className="td text-right font-mono">{e.baseline_acs.toFixed(3)}</td>
                      <td className="td text-right font-mono">{e.base_acs.toFixed(3)}</td>
                      <td className={`td text-right font-mono ${deltaColor(e.acs_delta)}`}>
                        {e.acs_delta >= 0 ? '+' : ''}{e.acs_delta.toFixed(3)}
                      </td>
                      <td className="td text-right font-mono text-xs">
                        <span className="text-core">{e.best_acs.toFixed(2)}</span>
                        <span className="text-faint"> / </span>
                        <span className="text-avoid">{e.worst_acs.toFixed(2)}</span>
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

            <div className="card overflow-hidden h-fit">
              <div className="card-head">Sleeve Drawdown · Worst Case</div>
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="th">Sleeve</th>
                    <th className="th text-right">Assets</th>
                    <th className="th text-right">Worst Δ</th>
                  </tr>
                </thead>
                <tbody>
                  {report.sleeve_impacts.map((s) => (
                    <tr key={s.sleeve}>
                      <td className="td">{titleCase(s.sleeve)}</td>
                      <td className="td text-right font-mono">{s.asset_count}</td>
                      <td className={`td text-right font-mono ${deltaColor(s.worst_drawdown)}`}>
                        {s.worst_drawdown >= 0 ? '+' : ''}{s.worst_drawdown.toFixed(3)}
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
