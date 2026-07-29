/** Shartli CSS klasslarni birlashtirish. */
export function cn(...values: (string | false | null | undefined)[]): string {
  return values.filter(Boolean).join(' ')
}
