import { useEffect, useState } from 'react'
import { getHealth } from '../api/client.js'

export default function SystemBar() {
  const [online, setOnline] = useState(null)
  const [clock, setClock] = useState('')

  useEffect(() => {
    getHealth().then(() => setOnline(true)).catch(() => setOnline(false))
  }, [])

  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('en-US', { hour12: false }))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="sticky top-0 z-10 flex flex-wrap items-center justify-between gap-2 px-4 sm:px-6 py-2.5
                    border-b border-edge/70 bg-base/80 backdrop-blur">
      <span className={`flex items-center gap-1.5 chip ${online ? 'text-green' : 'text-avoid'}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${online ? 'bg-green shadow-glow' : 'bg-avoid'}`} />
        {online === false ? 'OFFLINE' : 'ONLINE'}
      </span>
      <span className="chip text-muted hidden sm:inline-flex">{clock}</span>
    </div>
  )
}
