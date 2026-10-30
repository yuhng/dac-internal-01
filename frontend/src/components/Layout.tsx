import type { ReactNode } from 'react'
import { NavLink, Outlet } from 'react-router-dom'

const NAV: { to: string; label: string; icon: ReactNode }[] = [
  { to: '/', label: 'Overview', icon: <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" /> },
  { to: '/score', label: 'Score', icon: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></> },
  { to: '/improve', label: 'Improve CV', icon: <path d="M4 20h4L19 9l-4-4L4 16z" /> },
  { to: '/assistant', label: 'Assistant', icon: <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z" /> },
  { to: '/tracker', label: 'Tracker', icon: <><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 10h18M9 4v16" /></> },
]

export function Layout() {
  return (
    <div className="grid min-h-screen grid-cols-1 md:grid-cols-[236px_1fr]">
      <aside className="sticky top-0 z-20 flex items-center gap-3 border-b border-line bg-surface px-4 py-2.5 md:h-screen md:flex-col md:items-stretch md:gap-[22px] md:border-r md:border-b-0 md:px-3.5 md:py-5">
        <div className="flex items-center gap-2.5 text-base font-bold md:px-2">
          <span className="grid size-[30px] place-items-center rounded-lg bg-primary text-sm text-on-primary">AA</span>
          <span className="hidden md:inline">MyCareerAI</span>
        </div>
        <nav aria-label="Main" className="flex gap-0.5 overflow-x-auto md:flex-col">
          {NAV.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-2.5 py-[9px] font-medium whitespace-nowrap ${isActive ? 'bg-primary-weak text-primary' : 'text-muted hover:bg-surface-2 hover:text-ink'}`
              }
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true" className="hidden size-[18px] flex-none md:block">
                {icon}
              </svg>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto hidden rounded-lg bg-surface-2 p-3 text-xs text-muted md:block">
          <b>Prototype v0.1</b>
          <br />
          All analysis runs locally in your browser. No data leaves this page.
        </div>
      </aside>

      <main className="min-w-0">
        <div role="note" className="border-b border-line bg-warn-weak px-4 py-2 text-[13px] text-warn md:px-7">
          <b>Demo mode:</b> scores, rewrites and chat replies come from rule-based heuristics in your browser. No AI model or server is used.
        </div>
        <div className="max-w-[1280px] px-4 py-5 md:p-7">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
