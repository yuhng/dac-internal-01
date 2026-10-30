import type { ReactNode } from 'react'

export function Badge({ className, children }: { className: string; children: ReactNode }) {
  return <span className={`inline-block rounded-full px-[9px] py-0.5 text-xs font-semibold ${className}`}>{children}</span>
}

export function SimulatedBadge({ children }: { children: ReactNode }) {
  return <Badge className="border border-dashed border-line bg-surface-2 text-muted">{children}</Badge>
}

export function PageHead({ title, subtitle, actions }: { title: string; subtitle: string; actions?: ReactNode }) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-[650]">{title}</h1>
        <p className="mt-1 text-muted">{subtitle}</p>
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function EmptyState({ icon, title, children }: { icon?: string; title: string; children: ReactNode }) {
  return (
    <div className="px-5 py-12 text-center text-muted">
      {icon && <div className="mx-auto mb-3 grid size-12 place-items-center rounded-xl bg-surface-2 text-[22px]">{icon}</div>}
      <h3 className="mb-1.5 text-base font-semibold text-ink">{title}</h3>
      {children}
    </div>
  )
}

export function ErrorAlert({ children }: { children: ReactNode }) {
  return <div role="alert" className="rounded-lg bg-danger-weak px-3 py-2.5 text-sm text-danger">{children}</div>
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-[13px] font-medium">{label} {hint}</span>
      {children}
    </label>
  )
}
