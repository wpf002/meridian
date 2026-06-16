import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import GlobeMark from './GlobeMark.jsx'
import SystemBar from './SystemBar.jsx'

const LINKS = [
  ['/console', 'Console', '>_'],
  ['/', 'Recommendations', '◆'],
  ['/portfolio', 'Portfolio', '◷'],
  ['/scenarios', 'Scenarios', '⚡'],
  ['/status', 'Status', '◉'],
  ['/help', 'How to Use', '?'],
]

function Brand({ size = 38 }) {
  return (
    <div className="flex items-center gap-3">
      <GlobeMark size={size} spin />
      <div>
        <div className="text-[15px] font-bold tracking-[0.18em] leading-none">MERIDIAN</div>
        <div className="text-[10px] text-muted tracking-[0.22em] mt-1 uppercase">Intelligence Console</div>
      </div>
    </div>
  )
}

function Nav({ onNavigate }) {
  return (
    <nav className="flex-1 px-3 py-4 space-y-0.5">
      {LINKS.map(([to, label, glyph]) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          onClick={onNavigate}
          className={({ isActive }) =>
            `group flex items-center gap-3 px-3 py-2.5 rounded text-sm transition-colors ${
              isActive
                ? 'bg-raised/70 text-green border-l-2 border-green'
                : 'text-muted hover:text-ink hover:bg-raised/40 border-l-2 border-transparent'
            }`
          }
        >
          <span className="font-mono text-[13px] w-4 text-center opacity-80">{glyph}</span>
          <span className="tracking-wide">{label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)

  return (
    <div className="flex h-full">
      {/* mobile drawer scrim */}
      {open && (
        <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm md:hidden" onClick={() => setOpen(false)} />
      )}

      {/* sidebar: off-canvas drawer on mobile, static on md+ */}
      <aside
        className={`fixed md:static z-40 h-full w-64 md:w-60 shrink-0 flex flex-col
                    border-r border-edge/70 bg-panel/95 md:bg-panel/60 backdrop-blur
                    transition-transform duration-200
                    ${open ? 'translate-x-0' : '-translate-x-full'} md:translate-x-0`}
      >
        <div className="px-5 py-5 border-b border-edge/70">
          <Brand />
        </div>
        <Nav onNavigate={() => setOpen(false)} />
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        {/* mobile top bar with menu toggle */}
        <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-edge/70 bg-base/80 backdrop-blur">
          <button
            onClick={() => setOpen(true)}
            aria-label="Open menu"
            className="flex flex-col gap-[3px] p-1.5 rounded border border-edge/70"
          >
            <span className="w-4 h-0.5 bg-ink" />
            <span className="w-4 h-0.5 bg-ink" />
            <span className="w-4 h-0.5 bg-ink" />
          </button>
          <GlobeMark size={26} spin />
          <span className="text-sm font-bold tracking-[0.18em]">MERIDIAN</span>
        </div>

        <SystemBar />
        <main className="flex-1 overflow-auto p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
