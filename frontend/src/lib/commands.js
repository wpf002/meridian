import {
  getScan, getRecommendations, getPortfolio, getScenarios, runScenario,
  getBrief, getStatus, getAlerts, getUniverse, compareAssets, addAsset, removeAsset,
} from '../api/client.js'

export const COMMANDS = [
  ['help', 'List every command'],
  ['scan <TICKER>', 'Score one stock (0–100) with Buy / Watch / Avoid'],
  ['recommend', 'Rank everything you track, best first'],
  ['top [N]', 'Show just the top N names (default 5)'],
  ['portfolio', 'Build a suggested mix across the four buckets'],
  ['scenarios', 'List the "what if" market scenarios'],
  ['scenario <name>', 'Run a scenario and see who gets hit'],
  ['compare <A> vs <B>', 'Put two stocks side by side'],
  ['add <TICKER>', 'Add a stock to your watchlist'],
  ['remove <TICKER>', 'Remove a stock from your watchlist'],
  ['watchlist', 'List the stocks you track'],
  ['brief', 'Plain-English summary of the whole book'],
  ['status', 'How the score is built & how it has done'],
  ['alerts', 'Anything that needs attention'],
  ['clear', 'Clear the console'],
]

const ok = (type, data) => ({ type, data })
const err = (text) => ({ type: 'error', text })

export async function runCommand(raw) {
  const input = raw.trim()
  if (!input) return null
  const parts = input.split(/\s+/)
  const cmd = parts[0].toLowerCase()

  try {
    switch (cmd) {
      case 'help':
        return ok('help')
      case 'clear':
        return { type: 'clear' }

      case 'scan':
        if (!parts[1]) return err('Usage: scan <TICKER>')
        return ok('scan', await getScan(parts[1].toUpperCase()))

      case 'recommend':
      case 'recommendations':
        return ok('recommend', await getRecommendations())

      case 'top': {
        const n = Math.max(1, parseInt(parts[1], 10) || 5)
        const data = await getRecommendations()
        return ok('recommend', { ...data, recommendations: data.recommendations.slice(0, n) })
      }

      case 'add':
      case 'watch':
        if (!parts[1]) return err('Usage: add <TICKER>')
        await addAsset(parts[1].toUpperCase())
        return ok('text', `Added ${parts[1].toUpperCase()} to your watchlist.`)

      case 'remove':
      case 'rm':
        if (!parts[1]) return err('Usage: remove <TICKER>')
        await removeAsset(parts[1].toUpperCase())
        return ok('text', `Removed ${parts[1].toUpperCase()} from your watchlist.`)

      case 'portfolio':
        return ok('portfolio', await getPortfolio())
      case 'build':
        if ((parts[1] || '').toLowerCase() === 'portfolio')
          return ok('portfolio', await getPortfolio())
        return err("Did you mean 'build portfolio'?")

      case 'scenarios':
        return ok('scenarios', await getScenarios())

      case 'scenario': {
        const q = input.slice('scenario'.length).trim()
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

      case 'compare': {
        const rest = input.slice('compare'.length).trim()
        const m = rest.split(/\s+vs\s+/i)
        if (m.length !== 2) return err('Usage: compare <A> vs <B>')
        return ok('compare', await compareAssets(m[0].trim().toUpperCase(), m[1].trim().toUpperCase()))
      }

      case 'brief':
        return ok('brief', await getBrief())
      case 'status':
        return ok('status', await getStatus())
      case 'alerts':
        return ok('alerts', await getAlerts())
      case 'universe':
      case 'watchlist':
        return ok('universe', await getUniverse())

      default:
        return err(`Unknown command: ${cmd}. Type 'help'.`)
    }
  } catch (e) {
    return err(e.response?.data?.detail || e.message || 'Request failed')
  }
}
