import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cn } from '../lib/cn'
import { haptic } from '../lib/telegram'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  fullWidth?: boolean
  icon?: ReactNode
}

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 active:bg-brand-700 shadow-sm',
  secondary: 'card text-app hover:opacity-90',
  ghost: 'bg-transparent text-brand-600 hover:bg-brand-50 dark:hover:bg-white/5',
  danger: 'bg-danger text-white hover:opacity-90',
  success: 'bg-success text-white hover:opacity-90',
}

const SIZES: Record<Size, string> = {
  sm: 'h-9 px-3 text-sm rounded-lg gap-1.5',
  md: 'h-12 px-4 text-[15px] rounded-xl gap-2',
  lg: 'h-14 px-5 text-base rounded-2xl gap-2.5',
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = false,
  icon,
  className,
  children,
  disabled,
  onClick,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      onClick={(event) => {
        haptic.tap()
        onClick?.(event)
      }}
      className={cn(
        'tap-scale inline-flex items-center justify-center font-semibold transition disabled:cursor-not-allowed disabled:opacity-50',
        VARIANTS[variant],
        SIZES[size],
        fullWidth && 'w-full',
        className,
      )}
    >
      {loading ? (
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : (
        icon
      )}
      {children}
    </button>
  )
}

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string
  tone?: 'default' | 'danger'
}

export function IconButton({ label, tone = 'default', className, onClick, children, ...rest }: IconButtonProps) {
  return (
    <button
      {...rest}
      aria-label={label}
      title={label}
      onClick={(event) => {
        haptic.tap()
        onClick?.(event)
      }}
      className={cn(
        'tap-scale inline-flex h-10 w-10 items-center justify-center rounded-xl transition',
        tone === 'danger' ? 'text-danger hover:bg-danger/10' : 'text-hint hover:bg-black/5 dark:hover:bg-white/10',
        className,
      )}
    >
      {children}
    </button>
  )
}

/** Sahifa pastida turadigan katta harakat tugmasi (bir qo'l bilan ishlash uchun). */
export function StickyAction({ children }: { children: ReactNode }) {
  return (
    <div
      className="sticky bottom-[4.75rem] -mx-4 mt-6 rounded-2xl border px-4 py-3 backdrop-blur"
      style={{
        background: 'color-mix(in srgb, var(--tg-theme-secondary-bg-color) 92%, transparent)',
        borderColor: 'var(--app-border)',
      }}
    >
      {children}
    </div>
  )
}
