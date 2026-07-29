import type { ReactNode } from 'react'

import { t } from '../i18n/uz'
import { cn } from '../lib/cn'
import { Button } from './Button'

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        'inline-block h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent',
        className,
      )}
      role="status"
      aria-label={t.app.loading}
    />
  )
}

export function FullScreenLoader({ message = t.app.loading }: { message?: string }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3">
      <Spinner className="h-8 w-8" />
      <p className="text-sm text-hint">{message}</p>
    </div>
  )
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton h-4 w-full', className)} />
}

export function CardSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, index) => (
        <div key={index} className="card space-y-3 p-4">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-4 w-1/3" />
        </div>
      ))}
    </div>
  )
}

interface EmptyStateProps {
  icon?: string
  title: string
  description?: string
  action?: ReactNode
}

export function EmptyState({ icon = '📭', title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-12 text-center">
      <span className="text-5xl" aria-hidden>
        {icon}
      </span>
      <h3 className="text-base font-semibold">{title}</h3>
      {description && <p className="max-w-xs text-sm text-hint">{description}</p>}
      {action}
    </div>
  )
}

interface ErrorStateProps {
  message: string
  onRetry?: () => void
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <EmptyState
      icon="⚠️"
      title={t.app.somethingWrong}
      description={message}
      action={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {t.app.retry}
          </Button>
        ) : undefined
      }
    />
  )
}

const STATUS_STYLES: Record<string, string> = {
  draft: 'bg-slate-500/15 text-slate-500 dark:text-slate-300',
  in_progress: 'bg-warning/15 text-warning',
  completed: 'bg-success/15 text-success',
  cancelled: 'bg-danger/15 text-danger',
}

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold',
        STATUS_STYLES[status] ?? STATUS_STYLES.draft,
      )}
    >
      {label ?? t.status[status] ?? status}
    </span>
  )
}

export function Chip({ children, tone = 'default' }: { children: ReactNode; tone?: 'default' | 'brand' }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium',
        tone === 'brand' ? 'bg-brand-600/12 text-brand-600' : 'bg-black/5 text-hint dark:bg-white/10',
      )}
    >
      {children}
    </span>
  )
}
