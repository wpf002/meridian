import { useEffect, useState } from 'react'
import { getStatus } from '../api/client.js'

function Chip({ label, value, color = 'text-ink' }) {
  return (
    <span className="chip">
      <span className="text-muted">{label}</span>
      <span className={color}>{value}</span>
    </span>
  )
}

export default function SystemBar() {
  const [status, setStatus] = useState(null)
  const [online, setOnline] = useState(null)
  const [clock, setClock] = useState('')

  useEffect(() => {
    getStatus()
      .then((s) => { setStatus(s); setOnline(true) })
      .catch(() => setOnline(false))
  }, [])

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('en-US', { hour12: false }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="sticky top-0 z-10 flex items-center justify-between gap-3 px-6 py-2.5
                    border-b border-edge/70 bg-base/80 backdrop-blur">
      <div className="flex items-center gap-2 text-xs">
        <span className={`flex items-center gap-1.5 chip ${online ? 'text-green' : 'text-avoid'}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-green shadow-glow' : 'bg-avoid'}`} />
          {online === false ? 'OFFLINE' : 'ONLINE'}
        </span>
      </div>
      <div className="flex items-center gap-2 text-xs">
        {status && <Chip label="MODEL" value={`v${status.model_version}`} />}
        {status && (
          <Chip
            label="SOURCE"
            value={status.signal_source}
            color={status.signal_source === 'AURORA' ? 'text-green' : 'text-blue'}
          />
        )}
        <span className="chip text-muted">{clock}</span>
      </div>
    </div>
  )
}
