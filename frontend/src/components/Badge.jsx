import { CLASS_COLOR, tierLabel } from '../lib/format.js'

export default function Badge({ value }) {
  const color = CLASS_COLOR[value] || 'text-muted border-edge'
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded border text-[11px] font-mono tracking-wide whitespace-nowrap ${color}`}
    >
      {tierLabel(value)}
    </span>
  )
}
