import { useEffect } from 'react'
import type { ReactNode } from 'react'

import { t } from '../i18n/uz'
import { Button } from './Button'

interface SheetProps {
  open: boolean
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

/** Pastdan chiqadigan modal oyna (bir qo'l bilan ishlatishga qulay). */
export function Sheet({ open, title, onClose, children, footer }: SheetProps) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.body.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center" role="dialog" aria-modal="true" aria-label={title}>
      <button
        type="button"
        aria-label={t.app.close}
        onClick={onClose}
        className="absolute inset-0 animate-fade-in bg-black/45"
      />
      <div
        className="relative z-10 max-h-[88vh] w-full max-w-2xl animate-slide-up overflow-y-auto rounded-t-2xl border-t px-4 pb-6 pt-3"
        style={{ background: 'var(--app-card)', borderColor: 'var(--app-border)' }}
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-current opacity-20" />
        <div className="mb-4 flex items-center justify-between gap-3">
          <h2 className="text-lg font-bold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t.app.close}
            className="tap-scale flex h-9 w-9 items-center justify-center rounded-xl text-hint hover:bg-black/5 dark:hover:bg-white/10"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M6 6l12 12M18 6 6 18" strokeLinecap="round" />
            </svg>
          </button>
        </div>
        {children}
        {footer && <div className="mt-5">{footer}</div>}
      </div>
    </div>
  )
}

interface ConfirmProps {
  open: boolean
  title?: string
  message: string
  confirmLabel?: string
  tone?: 'danger' | 'primary'
  loading?: boolean
  onConfirm: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  open,
  title = t.app.confirmTitle,
  message,
  confirmLabel = t.app.delete,
  tone = 'danger',
  loading = false,
  onConfirm,
  onCancel,
}: ConfirmProps) {
  return (
    <Sheet
      open={open}
      title={title}
      onClose={onCancel}
      footer={
        <div className="flex gap-3">
          <Button variant="secondary" fullWidth onClick={onCancel}>
            {t.app.cancel}
          </Button>
          <Button variant={tone === 'danger' ? 'danger' : 'primary'} fullWidth loading={loading} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      }
    >
      <p className="text-[15px] leading-relaxed text-hint">{message}</p>
    </Sheet>
  )
}
