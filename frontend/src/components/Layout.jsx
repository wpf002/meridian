import { NavLink, Outlet } from 'react-router-dom'
import GlobeMark from './GlobeMark.jsx'
import SystemBar from './SystemBar.jsx'

const LINKS = [
  ['/console', 'Console', '>_'],
  ['/', 'Recommendations', '◆'],
  ['/portfolio', 'Portfolio', '◷'],
  ['/scenarios', 'Scenarios', '⚡'],
  ['/status', 'Status', '◉'],
]

export default function Layout() {
  return (
    <div className="flex h-full">
      <aside className="w-60 shrink-0 flex flex-col border-r border-edge/70 bg-panel/60 backdrop-blur">
        <div className="flex items-center gap-3 px-5 py-5 border-b border-edge/70">
          <GlobeMark size={32} spin />
          <div>
            <div className="text-[15px] font-bold tracking-[0.18em] leading-none">MERIDIAN</div>
            <div className="text-[10px] text-muted tracking-[0.22em] mt-1 uppercase">Intelligence Console</div>
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {LINKS.map(([to, label, glyph]) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
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

        <div className="px-5 py-4 border-t border-edge/70 text-[10px] text-faint tracking-widest uppercase">
          ACS Engine · v1.0
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <SystemBar />
        <main className="flex-1 overflow-auto p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
