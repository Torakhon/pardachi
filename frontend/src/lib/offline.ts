/**
 * Oflayn qo'llab-quvvatlash.
 *
 * 1. `cache` — oxirgi muvaffaqiyatli GET javoblari (internet yo'qda ko'rsatiladi).
 * 2. `outbox` — yuborilmagan o'zgarishlar navbati. Ulanish tiklanganda ketma-ket
 *    qayta yuboriladi. Yaratish so'rovlari mijoz tomonida UUID bilan yuborilgani
 *    uchun backend ularni idempotent qabul qiladi (takroriy yozuv paydo bo'lmaydi).
 */

const DB_NAME = 'pardachi'
const DB_VERSION = 1
const CACHE_STORE = 'cache'
const OUTBOX_STORE = 'outbox'

export interface OutboxEntry {
  id?: number
  method: 'POST' | 'PATCH' | 'DELETE'
  path: string
  body: unknown | null
  file?: { blob: Blob; filename: string }
  label: string
  createdAt: number
  tries: number
  lastError?: string
}

interface CacheEntry {
  path: string
  data: unknown
  savedAt: number
}

let dbPromise: Promise<IDBDatabase> | null = null

function openDatabase(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise
  dbPromise = new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('IndexedDB mavjud emas'))
      return
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(CACHE_STORE)) {
        db.createObjectStore(CACHE_STORE, { keyPath: 'path' })
      }
      if (!db.objectStoreNames.contains(OUTBOX_STORE)) {
        db.createObjectStore(OUTBOX_STORE, { keyPath: 'id', autoIncrement: true })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('IndexedDB ochilmadi'))
  })
  return dbPromise
}

function runTransaction<T>(
  store: string,
  mode: IDBTransactionMode,
  action: (objectStore: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return openDatabase().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const transaction = db.transaction(store, mode)
        const request = action(transaction.objectStore(store))
        request.onsuccess = () => resolve(request.result)
        request.onerror = () => reject(request.error ?? new Error('IndexedDB xatosi'))
      }),
  )
}

// ------------------------------------------------------------------ kesh

export async function cacheSet(path: string, data: unknown): Promise<void> {
  try {
    const entry: CacheEntry = { path, data, savedAt: Date.now() }
    await runTransaction(CACHE_STORE, 'readwrite', (store) => store.put(entry))
  } catch {
    // Kesh ishlamasa ham ilova ishlashda davom etadi.
  }
}

export async function cacheGet<T>(path: string): Promise<{ data: T; savedAt: number } | null> {
  try {
    const entry = await runTransaction<CacheEntry | undefined>(CACHE_STORE, 'readonly', (store) =>
      store.get(path),
    )
    return entry ? { data: entry.data as T, savedAt: entry.savedAt } : null
  } catch {
    return null
  }
}

export async function cacheClear(): Promise<void> {
  try {
    await runTransaction(CACHE_STORE, 'readwrite', (store) => store.clear())
  } catch {
    // e'tiborsiz
  }
}

// --------------------------------------------------------------- navbat

type Listener = (count: number) => void
const listeners = new Set<Listener>()

export function onQueueChange(listener: Listener): () => void {
  listeners.add(listener)
  void queueSize().then(listener)
  return () => listeners.delete(listener)
}

async function notify(): Promise<void> {
  const count = await queueSize()
  for (const listener of listeners) listener(count)
}

export async function enqueue(entry: Omit<OutboxEntry, 'id' | 'createdAt' | 'tries'>): Promise<number> {
  const record: OutboxEntry = { ...entry, createdAt: Date.now(), tries: 0 }
  const id = await runTransaction<IDBValidKey>(OUTBOX_STORE, 'readwrite', (store) => store.add(record))
  await notify()
  return Number(id)
}

export async function listQueue(): Promise<OutboxEntry[]> {
  try {
    const items = await runTransaction<OutboxEntry[]>(OUTBOX_STORE, 'readonly', (store) =>
      store.getAll(),
    )
    return items.sort((a, b) => a.createdAt - b.createdAt)
  } catch {
    return []
  }
}

export async function queueSize(): Promise<number> {
  try {
    return await runTransaction<number>(OUTBOX_STORE, 'readonly', (store) => store.count())
  } catch {
    return 0
  }
}

export async function dequeue(id: number): Promise<void> {
  await runTransaction(OUTBOX_STORE, 'readwrite', (store) => store.delete(id))
  await notify()
}

export async function markFailure(entry: OutboxEntry, message: string): Promise<void> {
  if (entry.id === undefined) return
  const updated: OutboxEntry = { ...entry, tries: entry.tries + 1, lastError: message }
  await runTransaction(OUTBOX_STORE, 'readwrite', (store) => store.put(updated))
  await notify()
}

export async function clearQueue(): Promise<void> {
  await runTransaction(OUTBOX_STORE, 'readwrite', (store) => store.clear())
  await notify()
}

/** Navbatdagi yozuv 10 martadan ko'p muvaffaqiyatsiz bo'lsa, u tashlab yuboriladi. */
export const MAX_QUEUE_TRIES = 10
