// Small shared loading / error / empty placeholders.

export function Loading({ label = 'Loading…' }) {
  return <div className="text-muted text-sm animate-pulse">{label}</div>
}

export function ErrorState({ error }) {
  return (
    <div className="card p-4 border-avoid/40">
      <div className="text-avoid font-medium mb-1">Couldn’t reach the API</div>
      <div className="text-muted text-sm">{String(error)}</div>
      <div className="text-muted text-xs mt-2">
        Is the backend running? <code className="text-ink">python -m api</code>
      </div>
    </div>
  )
}

export function Empty({ label = 'Nothing to show.' }) {
  return <div className="text-muted text-sm">{label}</div>
}
