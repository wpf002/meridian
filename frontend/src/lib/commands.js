import {
  getScan, getRecommendations, getPortfolio, getScenarios, runScenario,
  getBrief, getRegime, getStatus, getAlerts, ackAlert, getUniverse,
  compareAssets, addAsset, removeAsset,
} from '../api/client.js'

// Commands grouped for the `help` screen. Every command here is runnable.
export const COMMAND_GROUPS = [
  {
    title: 'Find & rank',
    items: [
      ['recommend', 'Rank everything you track, best first'],
      ['top [N]', 'The best N names (default 5)'],
      ['bottom [N]', 'The weakest N names'],
      ['buys', 'Only the names flagged Buy'],
      ['watch', 'Names worth keeping an eye on'],
      ['avoid', 'Names flagged Avoid'],
      ['tier1', 'Only Tier 1 (strongest) names'],
      ['tier2', 'Only Tier 2 names'],
      ['tier3', 'Only Tier 3 names'],
      ['flagged', 'Names carrying a risk flag'],
      ['sectors', 'Your watchlist broken down by sector'],
      ['sector <name>', 'Names in one sector (e.g. sector tech)'],
    ],
  },
  {
    title: 'Dig into a stock',
    items: [
      ['scan <TICKER>', 'Full score & breakdown for one stock'],
      ['score <TICKER>', 'Quick one-line score for a stock'],
      ['why <TICKER>', "Plain-English reason for the stock's score"],
      ['flags <TICKER>', 'Risk flags on one stock'],
      ['compare <A> vs <B>', 'Put two stocks side by side'],
    ],
  },
  {
    title: 'Your watchlist',
    items: [
      ['watchlist', 'List the stocks you track'],
      ['count', 'How many stocks you track'],
      ['add <TICKER>', 'Add a stock to your watchlist'],
      ['remove <TICKER>', 'Remove a stock from your watchlist'],
    ],
  },
  {
    title: 'Build a portfolio',
    items: [
      ['portfolio', 'Suggested mix across the four buckets'],
      ['sleeve <name>', 'Holdings in one bucket (e.g. sleeve growth)'],
      ['foundation', 'Just the Foundation bucket'],
      ['growth', 'Just the Growth bucket'],
      ['protection', 'Just the Protection bucket'],
      ['short-term', 'Just the Short-term bucket'],
      ['warnings', 'Diversification heads-up on the mix'],
    ],
  },
  {
    title: 'Stress test',
    items: [
      ['scenarios', 'List the "what if" market scenarios'],
      ['scenario <name>', 'Run one and see who gets hit'],
    ],
  },
  {
    title: 'Market & health',
    items: [
      ['brief', 'Plain-English summary of the whole book'],
      ['regime', "What kind of market we're in today"],
      ['status', "How the score is built & how it's done"],
      ['weights', 'What the score is made of'],
      ['accuracy', 'Track record by tier'],
      ['alerts', 'Anything that needs attention'],
      ['ack <id>', 'Dismiss an alert'],
      ['source', 'Where the live data comes from'],
      ['health', 'Is the engine online?'],
    ],
  },
  {
    title: 'Console',
    items: [
      ['help [command]', 'List commands, or details for one'],
      ['examples', 'A few things to try'],
      ['about', 'What Meridian is'],
      ['clear', 'Clear the console'],
    ],
  },
]

// Flat lookup of usage/description for `help <command>`.
export const COMMANDS = COMMAND_GROUPS.flatMap((g) => g.items)

const ok = (type, data) => ({ type, data })
const err = (text) => ({ type: 'error', text })
const text = (data) => ({ type: 'text', data })

// plain bucket name -> engine sleeve key
const SLEEVE_KEY = {
  foundation: 'core', core: 'core',
  growth: 'growth',
  protection: 'defensive', defensive: 'defensive',
  'short-term': 'tactical', shortterm: 'tactical', short: 'tactical', tactical: 'tactical',
}

// reuse the recommend renderer for any filtered subset of the ranked list
const asList = (data, rows) => ok('recommend', { recommendations: rows, skipped: data.skipped || [] })

async function filterRecommend(predicate) {
  const data = await getRecommendations()
  return asList(data, data.recommendations.filter(predicate))
}

async function showSleeve(name) {
  const key = SLEEVE_KEY[(name || '').toLowerCase()]
  if (!key) return err(`Unknown bucket "${name}". Try: foundation, growth, protection, short-term`)
  const data = await getPortfolio()
  const s = data.sleeves[key]
  if (!s) return err(`No holdings in that bucket.`)
  return ok('portfolio', { ...data, sleeves: { [key]: s } })
}

export async function runCommand(raw) {
  const input = raw.trim()
  if (!input) return null
  const parts = input.split(/\s+/)
  const cmd = parts[0].toLowerCase()
  const arg = parts[1]
  const T = () => (arg || '').toUpperCase()

  try {
    switch (cmd) {
      // --- console -------------------------------------------------------
      case 'help':
        if (arg) {
          const hit = COMMANDS.find(([c]) => c.split(/[ <[]/)[0] === arg.toLowerCase())
          return hit ? text(`${hit[0]} — ${hit[1]}`) : err(`No command "${arg}". Type 'help'.`)
        }
        return ok('help')
      case 'commands':
        return ok('help')
      case 'clear':
        return { type: 'clear' }
      case 'about':
        return text([
          'MERIDIAN — a stock screening console.',
          'It scores every name you track 0–100 by blending the macro backdrop,',
          'price trend, news sentiment and risk, then ranks them and suggests a mix.',
          'Not financial advice — a tool to focus your own research. Type "help".',
        ])
      case 'examples':
        return text([
          'top 10            → your ten best names',
          'scan NVDA         → full breakdown for one stock',
          'buys              → everything flagged Buy',
          'sector tech       → just the technology names',
          'scenario recession→ stress-test the whole book',
          'compare NVDA vs AMD',
        ])

      // --- find & rank ---------------------------------------------------
      case 'recommend':
      case 'recommendations':
        return ok('recommend', await getRecommendations())
      case 'top': {
        const n = Math.max(1, parseInt(arg, 10) || 5)
        const data = await getRecommendations()
        return asList(data, data.recommendations.slice(0, n))
      }
      case 'bottom':
      case 'worst': {
        const n = Math.max(1, parseInt(arg, 10) || 5)
        const data = await getRecommendations()
        return asList(data, data.recommendations.slice(-n).reverse())
      }
      case 'buys':
      case 'buy':
        return filterRecommend((r) => r.action === 'ESCALATE')
      case 'watch':
      case 'watching':
        return filterRecommend((r) => r.action === 'MONITOR')
      case 'avoid':
        return filterRecommend((r) => r.classification === 'AVOID' || r.action === 'RESTRICT')
      case 'tier1':
        return filterRecommend((r) => r.classification === 'CORE')
      case 'tier2':
        return filterRecommend((r) => r.classification === 'HIGH-ASYMMETRY')
      case 'tier3':
        return filterRecommend((r) => r.classification === 'TACTICAL')
      case 'flagged':
      case 'risky':
        return filterRecommend((r) => r.flags && r.flags.length > 0)

      case 'sectors': {
        const u = await getUniverse()
        const counts = {}
        for (const a of u.assets) counts[a.sector || 'Unknown'] = (counts[a.sector || 'Unknown'] || 0) + 1
        const lines = Object.entries(counts)
          .sort((a, b) => b[1] - a[1])
          .map(([s, n]) => `${s} — ${n}`)
        return text(['Your watchlist by sector:', ...lines])
      }
      case 'sector': {
        if (!arg) return err('Usage: sector <name>  (e.g. sector technology)')
        const q = parts.slice(1).join(' ').toLowerCase()
        const u = await getUniverse()
        const map = {}
        for (const a of u.assets) map[a.ticker] = a.sector || ''
        const data = await getRecommendations()
        const rows = data.recommendations.filter((r) => (map[r.entity] || '').toLowerCase().includes(q))
        if (!rows.length) return err(`No tracked names in a sector matching "${q}".`)
        return asList(data, rows)
      }

      // --- dig into a stock ---------------------------------------------
      case 'scan':
      case 'open':
        if (!arg) return err('Usage: scan <TICKER>')
        return ok('scan', await getScan(T()))
      case 'score': {
        if (!arg) return err('Usage: score <TICKER>')
        const d = await getScan(T())
        const tier = { CORE: 'Tier 1', 'HIGH-ASYMMETRY': 'Tier 2', TACTICAL: 'Tier 3', AVOID: 'Avoid' }[d.classification] || d.classification
        const act = { ESCALATE: 'Buy', MONITOR: 'Watch', RESTRICT: 'Avoid', LOG: 'Neutral' }[d.action] || d.action
        return text(`${d.entity} — Score ${Math.round(d.acs * 100)}/100 · ${tier} · ${act}`)
      }
      case 'why': {
        if (!arg) return err('Usage: why <TICKER>')
        const d = await getScan(T())
        return text(`${d.entity}: ${d.rationale.replace(/_/g, ' ')}`)
      }
      case 'flags': {
        if (!arg) return err('Usage: flags <TICKER>')
        const d = await getScan(T())
        if (!d.flags.length) return text(`${d.entity}: no risk flags.`)
        return text([`${d.entity} flags:`, ...d.flags.map((f) => `· ${f.replace(/[_/]/g, ' ')}`)])
      }
      case 'compare': {
        const rest = input.slice('compare'.length).trim()
        const m = rest.split(/\s+vs\s+/i)
        if (m.length !== 2) return err('Usage: compare <A> vs <B>')
        return ok('compare', await compareAssets(m[0].trim().toUpperCase(), m[1].trim().toUpperCase()))
      }

      // --- watchlist -----------------------------------------------------
      case 'watchlist':
      case 'universe':
        return ok('universe', await getUniverse())
      case 'count': {
        const u = await getUniverse()
        return text(`You track ${u.assets.length} stocks.`)
      }
      case 'add':
        if (!arg) return err('Usage: add <TICKER>')
        await addAsset(T())
        return text(`Added ${T()} to your watchlist.`)
      case 'remove':
      case 'rm':
        if (!arg) return err('Usage: remove <TICKER>')
        await removeAsset(T())
        return text(`Removed ${T()} from your watchlist.`)

      // --- portfolio -----------------------------------------------------
      case 'portfolio':
        return ok('portfolio', await getPortfolio())
      case 'build':
        if ((arg || '').toLowerCase() === 'portfolio') return ok('portfolio', await getPortfolio())
        return err("Did you mean 'build portfolio'?")
      case 'sleeve':
      case 'bucket':
        return showSleeve(parts.slice(1).join('-'))
      case 'foundation':
      case 'growth':
      case 'protection':
      case 'short-term':
        return showSleeve(cmd)
      case 'warnings': {
        const d = await getPortfolio()
        if (!d.warnings.length) return text('No warnings — the mix looks well balanced.')
        return text(['Heads-up on the current mix:', ...d.warnings.map((w) => `⚠ ${w}`)])
      }

      // --- scenarios -----------------------------------------------------
      case 'scenarios':
        return ok('scenarios', await getScenarios())
      case 'scenario':
      case 'stress': {
        const q = input.slice(cmd.length).trim()
        if (!q) return ok('scenarios', await getScenarios())
        const { scenarios } = await getScenarios()
        const ql = q.toLowerCase()
        const slugged = ql.replace(/[^a-z0-9]+/g, '_')
        const match =
          scenarios.find((s) => s.slug === ql || s.name.toLowerCase() === ql) ||
          scenarios.find((s) => s.slug.includes(slugged) || s.name.toLowerCase().includes(ql))
        if (!match) return err(`No scenario matching "${q}". Try: scenarios`)
        return ok('scenario', await runScenario(match.slug))
      }

      // --- market & health ----------------------------------------------
      case 'brief':
        return ok('brief', await getBrief())
      case 'regime': {
        const d = await getRegime()
        const r = String(d.regime || '').split('-').map((w) => w[0] + w.slice(1).toLowerCase()).join(' ')
        return text(`Today's market looks like: ${r}.`)
      }
      case 'status':
        return ok('status', await getStatus())
      case 'weights': {
        const d = await getStatus()
        const L = { macro: 'Macro', tactical: 'Price trend', sentiment: 'News', structural_risk: 'Risk' }
        const lines = Object.entries(d.weights).map(([k, v]) => `${L[k] || k} — ${Math.round(v * 100)}%`)
        return text(['What the score is made of:', ...lines])
      }
      case 'accuracy': {
        const d = await getStatus()
        const rows = Object.entries(d.accuracy || {})
        if (!rows.length) return text('Nothing graded yet — this fills in as past calls play out.')
        const tier = { CORE: 'Tier 1', 'HIGH-ASYMMETRY': 'Tier 2', TACTICAL: 'Tier 3', AVOID: 'Avoid' }
        return text(['Track record by tier:', ...rows.map(([c, s]) =>
          `${tier[c] || c} — ${Math.round(s.accuracy * 100)}% (${s.correct}/${s.total})`)])
      }
      case 'alerts':
        return ok('alerts', await getAlerts())
      case 'ack':
        if (!arg) return err('Usage: ack <id>')
        await ackAlert(arg)
        return text(`Dismissed alert ${arg}.`)
      case 'source': {
        const d = await getStatus()
        return text(`Live data source: ${d.signal_source}.`)
      }
      case 'health': {
        const d = await getStatus().catch(() => null)
        return text(d ? `Engine online · data source: ${d.signal_source}.` : 'Engine not reachable.')
      }

      default:
        return err(`Unknown command: ${cmd}. Type 'help'.`)
    }
  } catch (e) {
    return err(e.response?.data?.detail || e.message || 'Request failed')
  }
}
