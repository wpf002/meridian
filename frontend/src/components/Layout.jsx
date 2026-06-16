import { NavLink, Outlet } from 'react-router-dom'

const LINKS = [
  ['/', 'Recommendations'],
  ['/portfolio', 'Portfolio'],
  ['/scenarios', 'Scenarios'],
  ['/status', 'Status'],
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 bg-panel border-r border-edge p-5">
        <div className="mb-8">
          <div className="text-xl font-bold tracking-tight">MERIDIAN</div>
          <div className="text-xs text-muted">financial intelligence</div>
        </div>
        <nav className="space-y-1">
          {LINKS.map(([to, label]) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm ${
                  isActive ? 'bg-edge text-ink' : 'text-muted hover:text-ink hover:bg-edge/40'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 p-8 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
