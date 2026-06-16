export function Loading({ label = 'Loading…' }) {
  return (
    <div className="flex items-center gap-2 text-muted text-sm">
      <span className="w-1.5 h-1.5 rounded-full bg-green animate-pulse" />
      <span className="font-mono">{label}</span>
    </div>
  )
}

export function ErrorState({ error }) {
  return (
    <div className="card p-4 border-avoid/40 max-w-lg">
      <div className="text-avoid font-medium mb-1">Couldn’t reach the engine</div>
      <div className="text-muted text-sm font-mono">{String(error)}</div>
      <div className="text-faint text-xs mt-2">
        Is the API running? <code className="text-ink">python -m api</code>
      </div>
    </div>
  )
}

export function Empty({ label = 'Nothing to show.' }) {
  return <div className="text-muted text-sm">{label}</div>
}

export function PageTitle({ title, sub, right }) {
  return (
    <div className="flex items-end justify-between mb-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {sub && <p className="text-muted text-sm mt-1">{sub}</p>}
      </div>
      {right}
    </div>
  )
}
