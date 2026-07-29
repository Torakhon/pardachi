/** Backend bilan ishlovchi HTTP klient (JWT, oflayn navbat va kesh bilan). */

import type { ApiErrorBody, TokenResponse } from '../types'
import {
  MAX_QUEUE_TRIES,
  cacheGet,
  cacheSet,
  dequeue,
  enqueue,
  listQueue,
  markFailure,
} from './offline'

const API_BASE = `${(import.meta.env.VITE_API_BASE_URL as string | undefined) ?? ''}/api/v1`

const ACCESS_KEY = 'pardachi.access_token'
const REFRESH_KEY = 'pardachi.refresh_token'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly fields: Record<string, string>

  constructor(status: number, code: string, message: string, fields: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

/** Internet yo'qligi sababli so'rov navbatga qo'yilganda tashlanadi. */
export class QueuedError extends Error {
  readonly queued = true

  constructor(message = 'Internet yo‘q. Ma’lumot telefonda saqlandi.') {
    super(message)
    this.name = 'QueuedError'
  }
}

export const tokens = {
  get access(): string | null {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY)
  },
  save(data: TokenResponse): void {
    localStorage.setItem(ACCESS_KEY, data.access_token)
    localStorage.setItem(REFRESH_KEY, data.refresh_token)
  },
  clear(): void {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

interface RequestOptions {
  /** Autentifikatsiya sarlavhasini qo'shmaslik uchun */
  anonymous?: boolean
  /** Oflayn holatda navbatga qo'yish (POST/PATCH/DELETE uchun) */
  queueOffline?: boolean
  /** Navbatdagi yozuv uchun ko'rinadigan nom */
  label?: string
  /** Fayl yuborish */
  file?: { blob: Blob; filename: string }
  signal?: AbortSignal
}

let refreshPromise: Promise<boolean> | null = null

async function refreshTokens(): Promise<boolean> {
  if (refreshPromise) return refreshPromise
  const refreshToken = tokens.refresh
  if (!refreshToken) return false

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!response.ok) {
        tokens.clear()
        return false
      }
      tokens.save((await response.json()) as TokenResponse)
      return true
    } catch {
      return false
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

function buildHeaders(options: RequestOptions, hasJsonBody: boolean): Headers {
  const headers = new Headers()
  if (hasJsonBody) headers.set('Content-Type', 'application/json')
  if (!options.anonymous && tokens.access) headers.set('Authorization', `Bearer ${tokens.access}`)
  return headers
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = `http_${response.status}`
  let message = 'Xatolik yuz berdi. Qayta urinib ko‘ring.'
  let fields: Record<string, string> = {}
  try {
    const body = (await response.json()) as ApiErrorBody
    if (body?.error) {
      code = body.error.code ?? code
      message = body.error.message ?? message
      fields = (body.error.details?.fields as Record<string, string>) ?? {}
    }
  } catch {
    // JSON emas — standart xabar qoladi
  }
  return new ApiError(response.status, code, message, fields)
}

async function rawFetch(
  method: Method,
  path: string,
  body: unknown,
  options: RequestOptions,
  retry = true,
): Promise<Response> {
  let payload: BodyInit | undefined
  let hasJsonBody = false

  if (options.file) {
    const form = new FormData()
    form.append('file', options.file.blob, options.file.filename)
    payload = form
  } else if (body !== undefined && body !== null) {
    payload = JSON.stringify(body)
    hasJsonBody = true
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: buildHeaders(options, hasJsonBody),
    body: payload,
    signal: options.signal,
    credentials: 'omit',
  })

  if (response.status === 401 && retry && !options.anonymous && tokens.refresh) {
    if (await refreshTokens()) {
      return rawFetch(method, path, body, options, false)
    }
  }
  return response
}

async function parse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const text = await response.text()
  return text ? (JSON.parse(text) as T) : (undefined as T)
}

function isNetworkError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof DOMException && error.name === 'AbortError')
}

async function request<T>(
  method: Method,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  try {
    const response = await rawFetch(method, path, body, options)
    if (!response.ok) throw await toApiError(response)
    const data = await parse<T>(response)
    if (method === 'GET') void cacheSet(path, data)
    return data
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (!isNetworkError(error)) throw error

    // Tarmoq xatosi
    if (method !== 'GET' && options.queueOffline) {
      await enqueue({
        method,
        path,
        body: body ?? null,
        file: options.file,
        label: options.label ?? path,
      })
      throw new QueuedError()
    }
    throw new ApiError(0, 'internet_yoq', 'Internetga ulanish yo‘q.')
  }
}

export interface CachedResult<T> {
  data: T
  fromCache: boolean
  savedAt?: number
}

/** GET so'rovi: internet bo'lmasa oxirgi saqlangan nusxani qaytaradi. */
export async function getCached<T>(path: string, signal?: AbortSignal): Promise<CachedResult<T>> {
  try {
    const data = await request<T>('GET', path, undefined, { signal })
    return { data, fromCache: false }
  } catch (error) {
    const cached = await cacheGet<T>(path)
    if (cached && (error instanceof ApiError ? error.status === 0 : true)) {
      return { data: cached.data, fromCache: true, savedAt: cached.savedAt }
    }
    throw error
  }
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal): Promise<T> =>
    request<T>('GET', path, undefined, { signal }),

  post: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    request<T>('POST', path, body, { queueOffline: true, ...options }),

  patch: <T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> =>
    request<T>('PATCH', path, body, { queueOffline: true, ...options }),

  delete: <T>(path: string, options: RequestOptions = {}): Promise<T> =>
    request<T>('DELETE', path, undefined, { queueOffline: true, ...options }),

  upload: <T>(path: string, blob: Blob, filename: string, label?: string): Promise<T> =>
    request<T>('POST', path, undefined, { file: { blob, filename }, queueOffline: true, label }),

  anonymous: {
    post: <T>(path: string, body: unknown): Promise<T> =>
      request<T>('POST', path, body, { anonymous: true, queueOffline: false }),
  },
}

export interface SyncResult {
  sent: number
  failed: number
}

let syncing = false

/** Navbatdagi barcha o'zgarishlarni ketma-ket yuboradi. */
export async function syncOutbox(): Promise<SyncResult> {
  if (syncing || !navigator.onLine) return { sent: 0, failed: 0 }
  syncing = true
  let sent = 0
  let failed = 0

  try {
    const queue = await listQueue()
    for (const entry of queue) {
      if (entry.id === undefined) continue
      try {
        const response = await rawFetch(entry.method, entry.path, entry.body, {
          file: entry.file,
        })
        if (response.ok || response.status === 404 || response.status === 409) {
          // 404/409 — yozuv allaqachon o'chirilgan yoki yaratilgan: navbatdan olib tashlaymiz.
          await dequeue(entry.id)
          sent += 1
        } else if (response.status >= 400 && response.status < 500) {
          const error = await toApiError(response)
          await markFailure(entry, error.message)
          if (entry.tries + 1 >= MAX_QUEUE_TRIES) await dequeue(entry.id)
          failed += 1
        } else {
          await markFailure(entry, `Server xatosi (${response.status})`)
          failed += 1
        }
      } catch (error) {
        await markFailure(entry, error instanceof Error ? error.message : 'Tarmoq xatosi')
        failed += 1
        break // internet yana uzildi — keyingi urinishgacha to'xtatamiz
      }
    }
  } finally {
    syncing = false
  }

  return { sent, failed }
}

export { API_BASE }
