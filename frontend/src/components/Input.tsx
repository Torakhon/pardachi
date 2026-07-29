import { useId } from 'react'
import type {
  InputHTMLAttributes,
  ReactNode,
  Ref,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from 'react'

import { cn } from '../lib/cn'

interface FieldProps {
  label: string
  hint?: string
  error?: string
  required?: boolean
  suffix?: ReactNode
  children: (id: string) => ReactNode
}

export function Field({ label, hint, error, required, children }: FieldProps) {
  const id = useId()
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="flex items-center gap-1 text-sm font-medium">
        {label}
        {required && <span className="text-danger">*</span>}
      </label>
      {children(id)}
      {error ? (
        <p className="text-xs font-medium text-danger">{error}</p>
      ) : hint ? (
        <p className="text-xs text-hint">{hint}</p>
      ) : null}
    </div>
  )
}

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  label: string
  hint?: string
  error?: string
  suffix?: string
  inputRef?: Ref<HTMLInputElement>
}

export function Input({ label, hint, error, required, suffix, className, inputRef, ...rest }: InputProps) {
  return (
    <Field label={label} hint={hint} error={error} required={required}>
      {(id) => (
        <div className="relative">
          <input
            {...rest}
            ref={inputRef}
            id={id}
            required={required}
            className={cn('field', error && 'field-error', suffix && 'pr-14', className)}
          />
          {suffix && (
            <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm text-hint">
              {suffix}
            </span>
          )}
        </div>
      )}
    </Field>
  )
}

interface NumberInputProps extends Omit<InputProps, 'type' | 'inputMode'> {
  unit?: string
}

/** Katta raqamli maydon — o'lchov kiritish uchun (mobil klaviaturada raqamlar). */
export function NumberInput({ unit = 'sm', className, ...rest }: NumberInputProps) {
  return (
    <Input
      {...rest}
      type="text"
      inputMode="decimal"
      autoComplete="off"
      suffix={unit}
      className={cn('h-14 text-lg font-semibold tabular-nums', className)}
    />
  )
}

interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label: string
  hint?: string
  error?: string
}

export function TextArea({ label, hint, error, required, className, ...rest }: TextAreaProps) {
  return (
    <Field label={label} hint={hint} error={error} required={required}>
      {(id) => (
        <textarea
          {...rest}
          id={id}
          rows={rest.rows ?? 3}
          className={cn('field resize-none', error && 'field-error', className)}
        />
      )}
    </Field>
  )
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string
  hint?: string
  error?: string
  options: { value: string; label: string }[]
  placeholder?: string
}

export function Select({ label, hint, error, options, placeholder, required, className, ...rest }: SelectProps) {
  return (
    <Field label={label} hint={hint} error={error} required={required}>
      {(id) => (
        <select {...rest} id={id} className={cn('field appearance-none pr-10', error && 'field-error', className)}>
          {placeholder && <option value="">{placeholder}</option>}
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      )}
    </Field>
  )
}

interface ComboboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'list'> {
  label: string
  hint?: string
  error?: string
  suggestions: string[]
}

/** Tanlash + erkin yozish (mato turi, model, rang uchun). */
export function Combobox({ label, hint, error, suggestions, className, ...rest }: ComboboxProps) {
  const listId = useId()
  return (
    <Field label={label} hint={hint} error={error}>
      {(id) => (
        <>
          <input {...rest} id={id} list={listId} className={cn('field', error && 'field-error', className)} />
          <datalist id={listId}>
            {suggestions.map((suggestion) => (
              <option key={suggestion} value={suggestion} />
            ))}
          </datalist>
        </>
      )}
    </Field>
  )
}

interface SegmentedProps<T extends string> {
  label?: string
  value: T
  options: { value: T; label: string; icon?: string }[]
  onChange: (value: T) => void
}

/** Ikki-uch variantli tanlov (Oyna / Eshik kabi). */
export function Segmented<T extends string>({ label, value, options, onChange }: SegmentedProps<T>) {
  return (
    <div className="space-y-1.5">
      {label && <span className="text-sm font-medium">{label}</span>}
      <div className="card flex gap-1 p-1">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={cn(
              'tap-scale flex-1 rounded-lg px-3 py-2.5 text-sm font-semibold transition',
              value === option.value ? 'bg-brand-600 text-white shadow-sm' : 'text-hint',
            )}
          >
            {option.icon && <span className="mr-1">{option.icon}</span>}
            {option.label}
          </button>
        ))}
      </div>
    </div>
  )
}
