import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { runCommand, COMMAND_GROUPS } from '../lib/commands.js'
import Badge from '../components/Badge.jsx'
import {
  humanize, pct, deltaColor, titleCase, CONVICTION_COLOR, ACTION_COLOR,
  score, scoreSigned, actionLabel, sleeveLabel, regimeLabel,
} from '../lib/format.js'

const GREEN = 'text-green'
const MUT = 'text-muted'

// --- output renderers (terminal-styled) ------------------------------------

function Help() {
  return (
    <div className="columns-1 sm:columns-2 gap-8">
      {COMMAND_GROUPS.map((g) => (
        <div key={g.title} className="mb-3 break-inside-avoid">
          <div className="text-blue text-xs uppercase tracking-wider mb-1">{g.title}</div>
          {g.items.map(([c, d]) => (
            <div key={c} className="flex gap-3 leading-relaxed">
              <span className={`${GREEN} font-mono whitespace-nowrap w-40 shrink-0`}>{c}</span>
              <span className={`${MUT} text-xs self-center`}>{d}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

function ScanOut({ d }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-mono font-bold text-ink">{d.entity}</span>
        <span className="font-mono">Score <span className={GREEN}>{score(d.acs)}</span></span>
        <Badge value={d.classification} />
        <span className={`font-mono text-xs ${ACTION_COLOR[d.action]}`}>{actionLabel(d.action)}</span>
        <span className={`font-mono text-xs ${CONVICTION_COLOR[d.conviction]}`}>{titleCase(d.conviction)}</span>
      </div>
      <div className={`font-mono text-xs ${MUT}`}>
        Macro {score(d.components.mas)} · Price Trend {score(d.components.tas)} ·
        News {score(d.components.sas)} · Risk {score(d.components.srs)}
      </div>
      {d.flags.length > 0 && (
        <div className="text-xs text-tactical">⚑ {d.flags.map(humanize).join(' · ')}</div>
      )}
    </div>
  )
}

function RecommendOut({ d }) {
  return (
    <div className="font-mono text-sm">
      {d.recommendations.map((r) => (
        <div key={r.entity} className="flex gap-3">
          <span className={`${MUT} w-6 text-right`}>{r.rank}</span>
          <Link to={`/asset/${r.entity}`} className="text-ink hover:text-green w-16">{r.entity}</Link>
          <span className="w-12 text-right">{score(r.acs)}</span>
          <span className="w-36"><Badge value={r.classification} /></span>
          <span className={`${ACTION_COLOR[r.action]} text-xs self-center w-14`}>{actionLabel(r.action)}</span>
          <span className={`${CONVICTION_COLOR[r.conviction]} text-xs self-center`}>{titleCase(r.conviction)}</span>
        </div>
      ))}
      <div className={`${MUT} text-xs mt-1`}>{d.skipped.length} without enough data</div>
    </div>
  )
}

function PortfolioOut({ d }) {
  return (
    <div className="space-y-1 font-mono text-sm">
      {Object.entries(d.sleeves).map(([name, s]) => (
        <div key={name} className="flex gap-3">
          <span className="w-24 text-blue">{sleeveLabel(name)}</span>
          <span className="w-16 text-right">{pct(s.weight)}</span>
          <span className={MUT}>{s.holdings.map((h) => h.ticker).join(' ') || '—'}</span>
        </div>
      ))}
      <div className={`${MUT} text-xs`}>Total {pct(d.total_weight)}</div>
      {d.warnings.map((w, i) => <div key={i} className="text-tactical text-xs">⚠ {w}</div>)}
    </div>
  )
}

function ScenariosOut({ d }) {
  return (
    <div className="space-y-1">
      {d.scenarios.map((s) => (
        <div key={s.slug} className="flex gap-2 text-sm">
          <span className={`${GREEN} font-mono`}>{s.name}</span>
          <span className={MUT}>— {s.description}</span>
        </div>
      ))}
      <div className={`${MUT} text-xs mt-1`}>Run with: scenario &lt;name&gt;</div>
    </div>
  )
}

function ScenarioOut({ d }) {
  const delta = d.portfolio_base_acs - d.portfolio_baseline_acs
  const movers = [...d.entities].sort((a, b) => a.acs_delta - b.acs_delta).slice(0, 6)
  return (
    <div className="space-y-1">
      <div className="font-mono text-sm flex flex-wrap gap-x-4">
        <span className="font-bold text-ink">{d.scenario}</span>
        <span className="text-tactical">{regimeLabel(d.scenario_regime)}</span>
        <span>Score {score(d.portfolio_baseline_acs)} → {score(d.portfolio_base_acs)}
          <span className={deltaColor(delta)}> ({scoreSigned(delta)})</span>
        </span>
        <span className="text-avoid">{d.downgrades} get worse</span>
      </div>
      <div className="font-mono text-xs space-y-0.5">
        {movers.map((e) => (
          <div key={e.entity} className="flex gap-3">
            <span className="w-14 text-ink">{e.entity}</span>
            <span className="w-28 text-right">{score(e.baseline_acs)} → {score(e.base_acs)}</span>
            <span className={`w-16 text-right ${deltaColor(e.acs_delta)}`}>
              {scoreSigned(e.acs_delta)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function CompareOut({ d }) {
  const rows = [
    ['Score', d.a.acs, d.b.acs, d.delta.acs],
    ['Macro', d.a.components.mas, d.b.components.mas, d.delta.mas],
    ['Price Trend', d.a.components.tas, d.b.components.tas, d.delta.tas],
    ['News', d.a.components.sas, d.b.components.sas, d.delta.sas],
    ['Risk', d.a.components.srs, d.b.components.srs, d.delta.srs],
  ]
  return (
    <div className="font-mono text-sm">
      <div className="flex gap-3 text-xs text-muted">
        <span className="w-32" /><span className="w-16 text-right">{d.a.entity}</span>
        <span className="w-16 text-right">{d.b.entity}</span><span className="w-16 text-right">Δ</span>
      </div>
      {rows.map(([l, a, b, dd]) => (
        <div key={l} className="flex gap-3">
          <span className={`w-32 ${MUT}`}>{l}</span>
          <span className="w-16 text-right">{score(a)}</span>
          <span className="w-16 text-right">{score(b)}</span>
          <span className={`w-16 text-right ${deltaColor(dd)}`}>{scoreSigned(dd)}</span>
        </div>
      ))}
    </div>
  )
}

function BriefOut({ d }) {
  return (
    <div>
      <div className="font-mono text-xs text-muted mb-1">
        Regime <span className="text-blue">{d.regime}</span> · {d.alerts_fired} alerts fired
      </div>
      <pre className="font-mono text-xs text-ink/90 whitespace-pre-wrap leading-relaxed">{d.brief}</pre>
    </div>
  )
}

const WEIGHT_LABEL = {
  macro: 'Macro', tactical: 'Price Trend', sentiment: 'News', structural_risk: 'Risk',
}

function StatusOut({ d }) {
  return (
    <div className="font-mono text-sm space-y-1">
      <div className={MUT}>Live data source: <span className="text-blue">{d.signal_source}</span></div>
      <div className={MUT}>
        Score recipe: {Object.entries(d.weights).map(([k, v]) => `${WEIGHT_LABEL[k] || k} ${v}`).join(' · ')}
      </div>
    </div>
  )
}

function TextOut({ d }) {
  if (Array.isArray(d)) {
    return (
      <div className="font-mono text-sm space-y-0.5">
        {d.map((line, i) => (
          <div key={i} className={i === 0 ? 'text-ink' : 'text-muted'}>{line}</div>
        ))}
      </div>
    )
  }
  return <div className="text-green font-mono text-sm">{d}</div>
}

function AlertsOut({ d }) {
  if (!d.alerts.length) return <div className={GREEN}>No active alerts.</div>
  return (
    <div className="space-y-0.5 text-sm">
      {d.alerts.map((a) => (
        <div key={a.id} className="flex gap-2">
          <span className={a.severity === 'high' ? 'text-avoid' : a.severity === 'medium' ? 'text-tactical' : MUT}>
            [{a.severity.toUpperCase()}]
          </span>
          <span>{a.message}</span>
        </div>
      ))}
    </div>
  )
}

function UniverseOut({ d }) {
  return (
    <div className="font-mono text-sm text-ink/90">
      <span className={`${MUT} text-xs`}>{d.assets.length} assets · </span>
      {d.assets.map((a) => a.ticker).join('  ')}
    </div>
  )
}

function Result({ r }) {
  switch (r.type) {
    case 'help': return <Help />
    case 'text': return <TextOut d={r.data} />
    case 'error': return <div className="text-avoid">✕ {r.text}</div>
    case 'scan': return <ScanOut d={r.data} />
    case 'recommend': return <RecommendOut d={r.data} />
    case 'portfolio': return <PortfolioOut d={r.data} />
    case 'scenarios': return <ScenariosOut d={r.data} />
    case 'scenario': return <ScenarioOut d={r.data} />
    case 'compare': return <CompareOut d={r.data} />
    case 'brief': return <BriefOut d={r.data} />
    case 'status': return <StatusOut d={r.data} />
    case 'alerts': return <AlertsOut d={r.data} />
    case 'universe': return <UniverseOut d={r.data} />
    default: return null
  }
}

// --- the terminal ----------------------------------------------------------

const WELCOME = {
  input: null,
  result: { type: 'help' },
  banner: "MERIDIAN CONSOLE — type a command, or 'help'. Data is pulled live from the engine.",
}

export default function Console() {
  const [entries, setEntries] = useState([WELCOME])
  const [value, setValue] = useState('')
  const [history, setHistory] = useState([])
  const [hIdx, setHIdx] = useState(-1)
  const [busy, setBusy] = useState(false)
  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight })
  }, [entries, busy])

  const submit = async (e) => {
    e?.preventDefault()
    const input = value.trim()
    if (!input || busy) return
    setValue('')
    setHistory((h) => [...h, input])
    setHIdx(-1)

    if (input.toLowerCase() === 'clear') {
      setEntries([])
      return
    }

    setBusy(true)
    const result = await runCommand(input)
    setBusy(false)
    if (result?.type === 'clear') {
      setEntries([])
      return
    }
    setEntries((prev) => [...prev, { input, result }])
  }

  const onKey = (e) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (!history.length) return
      const idx = hIdx < 0 ? history.length - 1 : Math.max(0, hIdx - 1)
      setHIdx(idx)
      setValue(history[idx])
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (hIdx < 0) return
      const idx = hIdx + 1
      if (idx >= history.length) { setHIdx(-1); setValue('') }
      else { setHIdx(idx); setValue(history[idx]) }
    }
  }

  return (
    <div className="h-[calc(100dvh-12rem)] md:h-[calc(100vh-9.5rem)] min-h-[440px] flex flex-col card overflow-hidden">
      <div className="card-head flex items-center justify-between shrink-0">
        <span>Console</span>
        <span className="text-faint normal-case tracking-normal text-xs font-mono">
          scan · recommend · portfolio · scenario · brief · status
        </span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-auto px-4 py-3 space-y-4 text-sm" onClick={() => inputRef.current?.focus()}>
        {entries.map((entry, i) => (
          <div key={i}>
            {entry.banner && <div className="text-muted text-xs mb-2">{entry.banner}</div>}
            {entry.input != null && (
              <div className="font-mono text-sm mb-1">
                <span className="text-green">meridian&gt;</span> <span className="text-ink">{entry.input}</span>
              </div>
            )}
            {entry.result && <div className="pl-0"><Result r={entry.result} /></div>}
          </div>
        ))}
        {busy && <div className="font-mono text-xs text-muted caret">running</div>}
      </div>

      <form onSubmit={submit} className="shrink-0 flex items-center gap-2 border-t border-edge/70 px-4 py-3">
        <span className="text-green font-mono">meridian&gt;</span>
        <input
          ref={inputRef}
          autoFocus
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKey}
          spellCheck={false}
          autoComplete="off"
          placeholder="type a command…"
          className="flex-1 bg-transparent outline-none font-mono text-ink placeholder:text-faint"
        />
      </form>
    </div>
  )
}
