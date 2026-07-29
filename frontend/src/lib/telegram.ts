/** Telegram WebApp SDK ustidan yupqa qatlam (SDK bo'lmasa ham ilova ishlaydi). */

interface TelegramThemeParams {
  bg_color?: string
  secondary_bg_color?: string
  text_color?: string
  hint_color?: string
  link_color?: string
  button_color?: string
  button_text_color?: string
  section_separator_color?: string
}

interface TelegramLocationManager {
  init: (callback: () => void) => void
  getLocation: (callback: (location: { latitude: number; longitude: number; horizontal_accuracy?: number } | null) => void) => void
  isInited: boolean
  isLocationAvailable: boolean
  isAccessGranted: boolean
  openSettings: () => void
}

export interface TelegramWebApp {
  initData: string
  initDataUnsafe: { user?: { id: number; first_name: string; username?: string }; start_param?: string }
  version: string
  platform: string
  colorScheme: 'light' | 'dark'
  themeParams: TelegramThemeParams
  isExpanded: boolean
  viewportStableHeight: number
  ready: () => void
  expand: () => void
  close: () => void
  enableClosingConfirmation: () => void
  disableVerticalSwipes?: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  onEvent: (event: string, handler: () => void) => void
  offEvent: (event: string, handler: () => void) => void
  openLink: (url: string, options?: { try_instant_view?: boolean }) => void
  openTelegramLink: (url: string) => void
  showPopup?: (params: { title?: string; message: string; buttons?: unknown[] }, cb?: (id: string) => void) => void
  showConfirm?: (message: string, cb: (confirmed: boolean) => void) => void
  showAlert?: (message: string, cb?: () => void) => void
  HapticFeedback?: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void
    selectionChanged: () => void
  }
  BackButton: {
    isVisible: boolean
    show: () => void
    hide: () => void
    onClick: (cb: () => void) => void
    offClick: (cb: () => void) => void
  }
  MainButton: {
    text: string
    isVisible: boolean
    isActive: boolean
    showProgress: (leaveActive?: boolean) => void
    hideProgress: () => void
    setParams: (params: { text?: string; color?: string; text_color?: string; is_active?: boolean; is_visible?: boolean }) => void
    show: () => void
    hide: () => void
    onClick: (cb: () => void) => void
    offClick: (cb: () => void) => void
  }
  LocationManager?: TelegramLocationManager
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
  }
}

export const webApp: TelegramWebApp | undefined =
  typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export const isTelegram = Boolean(webApp?.initData)

/** Ilovani ishga tayyorlaydi: to'liq ekran, mavzu, vertikal svaypni o'chirish. */
export function initTelegram(): void {
  if (!webApp) return
  webApp.ready()
  webApp.expand()
  webApp.disableVerticalSwipes?.()
  applyTheme()
  webApp.onEvent('themeChanged', applyTheme)
}

/** Telegram mavzusidagi ranglarni CSS o'zgaruvchilarga ko'chiradi. */
export function applyTheme(): void {
  const root = document.documentElement
  const params = webApp?.themeParams ?? {}
  const map: Record<string, string | undefined> = {
    '--tg-theme-bg-color': params.bg_color,
    '--tg-theme-secondary-bg-color': params.secondary_bg_color,
    '--tg-theme-text-color': params.text_color,
    '--tg-theme-hint-color': params.hint_color,
    '--tg-theme-link-color': params.link_color,
    '--tg-theme-button-color': params.button_color,
    '--tg-theme-button-text-color': params.button_text_color,
    '--tg-theme-section-separator-color': params.section_separator_color,
  }

  const scheme = resolveScheme()
  root.classList.toggle('dark', scheme === 'dark')

  if (getStoredTheme() !== 'auto' || !webApp) {
    // Qo'lda tanlangan mavzuda Telegram ranglari qo'llanilmaydi (index.css standartlari ishlaydi).
    for (const key of Object.keys(map)) root.style.removeProperty(key)
  } else {
    for (const [key, value] of Object.entries(map)) {
      if (value) root.style.setProperty(key, value)
    }
    if (params.bg_color) {
      webApp.setHeaderColor?.(params.bg_color)
      webApp.setBackgroundColor?.(params.secondary_bg_color ?? params.bg_color)
    }
  }
}

export type ThemePreference = 'auto' | 'light' | 'dark'

const THEME_KEY = 'pardachi.theme'

export function getStoredTheme(): ThemePreference {
  const value = localStorage.getItem(THEME_KEY)
  return value === 'light' || value === 'dark' ? value : 'auto'
}

export function setStoredTheme(preference: ThemePreference): void {
  localStorage.setItem(THEME_KEY, preference)
  applyTheme()
}

function resolveScheme(): 'light' | 'dark' {
  const preference = getStoredTheme()
  if (preference !== 'auto') return preference
  if (webApp?.colorScheme) return webApp.colorScheme
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/** Tebranish (haptic) signallari. */
export const haptic = {
  tap(): void {
    webApp?.HapticFeedback?.impactOccurred('light')
  },
  success(): void {
    webApp?.HapticFeedback?.notificationOccurred('success')
  },
  error(): void {
    webApp?.HapticFeedback?.notificationOccurred('error')
  },
  warning(): void {
    webApp?.HapticFeedback?.notificationOccurred('warning')
  },
  select(): void {
    webApp?.HapticFeedback?.selectionChanged()
  },
}

/** Telegram orqasiga qaytish tugmasini boshqaradi. */
export function setBackButton(visible: boolean, handler?: () => void): () => void {
  if (!webApp?.BackButton) return () => undefined
  const button = webApp.BackButton
  if (visible && handler) {
    button.onClick(handler)
    button.show()
    return () => {
      button.offClick(handler)
      button.hide()
    }
  }
  button.hide()
  return () => undefined
}

export interface GeoResult {
  latitude: number
  longitude: number
  accuracy?: number
  source: 'telegram' | 'browser'
}

/** Lokatsiyani avval Telegramdan, bo'lmasa brauzerdan oladi. */
export function getCurrentLocation(timeoutMs = 12000): Promise<GeoResult> {
  const manager = webApp?.LocationManager
  if (manager) {
    return new Promise<GeoResult>((resolve, reject) => {
      const request = () => {
        manager.getLocation((location) => {
          if (location) {
            resolve({
              latitude: location.latitude,
              longitude: location.longitude,
              accuracy: location.horizontal_accuracy,
              source: 'telegram',
            })
          } else {
            browserLocation(timeoutMs).then(resolve).catch(reject)
          }
        })
      }
      if (manager.isInited) request()
      else manager.init(request)
    }).catch(() => browserLocation(timeoutMs))
  }
  return browserLocation(timeoutMs)
}

function browserLocation(timeoutMs: number): Promise<GeoResult> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('Geolokatsiya qo‘llab-quvvatlanmaydi'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (position) =>
        resolve({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          source: 'browser',
        }),
      (error) => reject(new Error(error.message)),
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 30000 },
    )
  })
}

/** Havolani Telegram ichida yoki yangi oynada ochadi. */
export function openExternal(url: string): void {
  if (webApp?.openLink) webApp.openLink(url)
  else window.open(url, '_blank', 'noopener,noreferrer')
}

/** Telegramning tasdiqlash oynasi (bo'lmasa brauzer confirm). */
export function confirmDialog(message: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (webApp?.showConfirm) webApp.showConfirm(message, resolve)
    else resolve(window.confirm(message))
  })
}
