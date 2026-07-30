import type { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'

import { t } from '../i18n/uz'
import { cn } from '../lib/cn'
import { isTelegram } from '../lib/telegram'
import { useNetwork } from '../store/network'
import { Button } from './Button'

interface ScreenProps {
  children: ReactNode
  className?: string
}

export function Screen({ children, className }: ScreenProps) {
  return <div className={cn('mx-auto w-full max-w-2xl px-4 pb-28 pt-3', className)}>{children}</div>
}

interface PageHeaderProps {
  title: string
  subtitle?: string
  back?: boolean | string
  action?: ReactNode
}

export function PageHeader({ title, subtitle, back, action }: PageHeaderProps) {
  const navigate = useNavigate()
  // Telegramda tizim "orqaga" tugmasi ishlaydi, brauzerda o'z tugmamiz kerak.
  const showBack = Boolean(back) && !isTelegram

  return (
    <header className="mb-4 flex items-start gap-3">
      {showBack && (
        <button
          type="button"
          onClick={() => (typeof back === 'string' ? navigate(back) : navigate(-1))}
          aria-label={t.app.back}
          className="tap-scale -ml-1 mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-hint hover:bg-black/5 dark:hover:bg-white/10"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 18l-6-6 6-6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-xl font-bold leading-tight">{title}</h1>
        {subtitle && <p className="mt-0.5 truncate text-sm text-hint">{subtitle}</p>}
      </div>
      {action}
    </header>
  )
}

export function Section({
  title,
  action,
  children,
  className,
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={cn('mb-5', className)}>
      {(title || action) && (
        <div className="mb-2 flex items-center justify-between gap-3 px-1">
          {title && <h2 className="text-sm font-semibold uppercase tracking-wide text-hint">{title}</h2>}
          {action}
        </div>
      )}
      {children}
    </section>
  )
}

export function OfflineBanner() {
  const { online, pending, syncing, sync } = useNetwork()
  if (online && pending === 0) return null

  return (
    <div
      className={cn(
        'sticky top-0 z-40 -mx-4 mb-3 flex items-center justify-between gap-3 px-4 py-2 text-xs font-medium',
        online ? 'bg-warning/15 text-warning' : 'bg-danger/15 text-danger',
      )}
    >
      <span className="flex items-center gap-2">
        <span className={cn('h-2 w-2 rounded-full', online ? 'bg-warning' : 'bg-danger')} />
        {online ? `${t.offline.pending}: ${pending}` : t.offline.banner}
      </span>
      {online && pending > 0 && (
        <Button size="sm" variant="ghost" loading={syncing} onClick={() => void sync()}>
          {syncing ? t.offline.syncing : t.offline.syncNow}
        </Button>
      )}
    </div>
  )
}

interface NavItem {
  to: string
  label: string
  icon: ReactNode
  adminOnly?: boolean
}

const ICON_CLASS = 'h-6 w-6'

const NAV_ITEMS: NavItem[] = [
  {
    to: '/',
    label: t.nav.dashboard,
    icon: (
      <svg viewBox="0 0 24 24" className={ICON_CLASS} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M3 10.5 12 3l9 7.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M5 9.5V21h14V9.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: '/teams',
    label: t.nav.teams,
    adminOnly: true,
    icon: (
      <svg viewBox="0 0 24 24" className={ICON_CLASS} fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="9" cy="8" r="3.2" strokeLinecap="round" />
        <path d="M3.5 19.5c0-3 2.5-5 5.5-5s5.5 2 5.5 5" strokeLinecap="round" />
        <path d="M16 5.5a3 3 0 0 1 0 5.8M17.5 19.5c0-2.2-.9-3.9-2.3-4.7" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/projects',
    label: t.nav.projects,
    icon: (
      <svg viewBox="0 0 24 24" className={ICON_CLASS} fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    to: '/users',
    label: t.nav.users,
    adminOnly: true,
    icon: (
      <svg viewBox="0 0 24 24" className={ICON_CLASS} fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="9" cy="8" r="3.2" />
        <path d="M3.5 20c0-3 2.5-5 5.5-5s5.5 2 5.5 5" strokeLinecap="round" />
        <path d="M16 11.2A3 3 0 0 0 16 5.4M17.5 20c0-2.2-.8-3.9-2-5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    to: '/profile',
    label: t.nav.profile,
    icon: (
      <svg viewBox="0 0 24 24" className={ICON_CLASS} fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="8" r="3.5" />
        <path d="M4.5 20c0-3.6 3.4-6 7.5-6s7.5 2.4 7.5 6" strokeLinecap="round" />
      </svg>
    ),
  },
]

export function BottomNav({ isAdmin }: { isAdmin: boolean }) {
  const items = NAV_ITEMS.filter((item) => !item.adminOnly || isAdmin)

  return (
    <nav
      className="safe-bottom fixed inset-x-0 bottom-0 z-40 border-t backdrop-blur"
      style={{
        background: 'color-mix(in srgb, var(--tg-theme-bg-color) 92%, transparent)',
        borderColor: 'var(--app-border)',
      }}
    >
      <div className="mx-auto flex w-full max-w-2xl items-stretch justify-around px-2 pt-1.5">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              cn(
                'tap-scale flex min-w-16 flex-1 flex-col items-center gap-1 rounded-xl py-1.5 text-[11px] font-medium transition',
                isActive ? 'text-brand-600' : 'text-hint',
              )
            }
          >
            {item.icon}
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
