// Classification → Tailwind text/border color classes (terminal-matched palette).
export const CLASS_COLOR = {
  CORE: 'text-core border-core/50',
  'HIGH-ASYMMETRY': 'text-asym border-asym/50',
  TACTICAL: 'text-tactical border-tactical/50',
  AVOID: 'text-avoid border-avoid/50',
}

export const CONVICTION_COLOR = {
  HIGH: 'text-core',
  MEDIUM: 'text-tactical',
  LOW: 'text-avoid',
}

export const ACTION_COLOR = {
  ESCALATE: 'text-core',
  MONITOR: 'text-tactical',
  RESTRICT: 'text-avoid',
  LOG: 'text-muted',
}

export const pct = (x) => `${(x * 100).toFixed(1)}%`
export const signed = (x) => `${x >= 0 ? '+' : ''}${x.toFixed(3)}`
export const deltaColor = (x) =>
  x > 0.0005 ? 'text-core' : x < -0.0005 ? 'text-avoid' : 'text-muted'
