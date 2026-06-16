// --- Text humanization (no underscores in displayed values) ----------------

const ACRONYMS = new Set(['acs', 'mas', 'tas', 'sas', 'srs', 'ai', 'esg'])

export function titleCase(word) {
  if (!word) return word
  if (ACRONYMS.has(word.toLowerCase())) return word.toUpperCase()
  return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()
}

// "HIGH_STRUCTURAL_RISK" -> "High Structural Risk"
// "MACRO/TACTICAL_DIVERGENCE" -> "Macro / Tactical Divergence"
// "structural_risk" -> "Structural Risk"
export function humanize(value) {
  if (value == null) return ''
  return String(value)
    .replace(/\//g, ' / ')
    .split(/[\s_]+/)
    .map((w) => (w === '/' ? '/' : titleCase(w)))
    .join(' ')
    .replace(/ \/ /g, ' / ')
    .trim()
}

// --- Color maps (green/blue console theme) ---------------------------------

export const CLASS_COLOR = {
  CORE: 'text-core border-core/50',
  'HIGH-ASYMMETRY': 'text-asym border-asym/50',
  TACTICAL: 'text-tactical border-tactical/50',
  AVOID: 'text-avoid border-avoid/50',
}

// Display the engine's internal classifications as plain tier labels. The
// values above stay as-is in the API/engine (the portfolio constructor routes
// sleeves off them); this is presentation only.
export const TIER_LABEL = {
  CORE: 'Tier 1',
  'HIGH-ASYMMETRY': 'Tier 2',
  TACTICAL: 'Tier 3',
  AVOID: 'Avoid',
}

export const tierLabel = (classification) => TIER_LABEL[classification] || classification

// The engine works in 0–1; users read 0–100. One place to convert.
export const score = (acs) => Math.round((acs ?? 0) * 100)
export const scoreSigned = (d) => `${d >= 0 ? '+' : ''}${Math.round(d * 100)}`

// Action verbs the user understands (engine keeps ESCALATE/MONITOR/RESTRICT/LOG).
export const ACTION_LABEL = {
  ESCALATE: 'Buy', MONITOR: 'Watch', RESTRICT: 'Avoid', LOG: 'Neutral',
}
export const actionLabel = (action) => ACTION_LABEL[action] || titleCase(action)

// Plain portfolio-bucket names (engine keeps core/growth/defensive/tactical).
export const SLEEVE_LABEL = {
  core: 'Foundation', growth: 'Growth', defensive: 'Protection', tactical: 'Short-term',
}
export const sleeveLabel = (name) => SLEEVE_LABEL[name] || titleCase(name)

// "LIQUIDITY-CONTRACTION" -> "Liquidity Contraction"
export const regimeLabel = (regime) =>
  String(regime || '').split('-').map(titleCase).join(' ')

export const CONVICTION_COLOR = { HIGH: 'text-core', MEDIUM: 'text-tactical', LOW: 'text-avoid' }
export const ACTION_COLOR = {
  ESCALATE: 'text-core',
  MONITOR: 'text-tactical',
  RESTRICT: 'text-avoid',
  LOG: 'text-muted',
}
export const SEVERITY_COLOR = {
  high: 'text-avoid border-avoid/50',
  medium: 'text-tactical border-tactical/50',
  low: 'text-muted border-edge',
}

// --- Numeric formatting -----------------------------------------------------

export const pct = (x) => `${(x * 100).toFixed(1)}%`
export const signed = (x) => `${x >= 0 ? '+' : ''}${x.toFixed(3)}`
export const deltaColor = (x) =>
  x > 0.0005 ? 'text-core' : x < -0.0005 ? 'text-avoid' : 'text-muted'
