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
