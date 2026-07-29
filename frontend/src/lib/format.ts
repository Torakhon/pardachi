/** Formatlash yordamchilari (sana, telefon, o'lcham) — o'zbek tilida. */

const MONTHS = [
  'yanvar',
  'fevral',
  'mart',
  'aprel',
  'may',
  'iyun',
  'iyul',
  'avgust',
  'sentabr',
  'oktabr',
  'noyabr',
  'dekabr',
]

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return `${date.getDate()}-${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const time = `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  return `${formatDate(value)}, ${time}`
}

export function formatRelative(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  const diffMs = Date.now() - date.getTime()
  const minutes = Math.round(diffMs / 60000)
  if (minutes < 1) return 'hozir'
  if (minutes < 60) return `${minutes} daqiqa oldin`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours} soat oldin`
  const days = Math.round(hours / 24)
  if (days === 1) return 'kecha'
  if (days < 7) return `${days} kun oldin`
  return formatDate(value)
}

/** `+998901234567` -> `+998 90 123 45 67` */
export function formatPhone(value: string | null | undefined): string {
  if (!value) return '—'
  const digits = value.replace(/\D/g, '')
  if (digits.length === 12 && digits.startsWith('998')) {
    return `+${digits.slice(0, 3)} ${digits.slice(3, 5)} ${digits.slice(5, 8)} ${digits.slice(8, 10)} ${digits.slice(10)}`
  }
  return value
}

/** Telefon maydonidagi jonli formatlash uchun */
export function maskPhoneInput(value: string): string {
  const digits = value.replace(/\D/g, '').replace(/^998/, '').slice(0, 9)
  const parts = [digits.slice(0, 2), digits.slice(2, 5), digits.slice(5, 7), digits.slice(7, 9)].filter(
    Boolean,
  )
  return parts.length ? `+998 ${parts.join(' ')}` : ''
}

export function phoneToApi(value: string): string {
  const digits = value.replace(/\D/g, '')
  if (digits.length === 9) return `+998${digits}`
  if (digits.startsWith('998')) return `+${digits}`
  return value.trim()
}

/** `150.00` -> `150`, `150.50` -> `150.5` */
export function formatCm(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const numeric = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(numeric)) return String(value)
  return String(Number(numeric.toFixed(2)))
}

export function formatSize(width: string | null, height: string | null): string {
  if (!width || !height) return '—'
  return `${formatCm(width)} × ${formatCm(height)} sm`
}

export function pluralUz(count: number, word: string): string {
  return `${count} ${word}`
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2)
  return parts.map((part) => part[0]?.toUpperCase() ?? '').join('') || '?'
}
