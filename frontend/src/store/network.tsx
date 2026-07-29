/** Tarmoq holati va oflayn navbatni boshqarish. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { syncOutbox } from '../lib/api'
import { onQueueChange } from '../lib/offline'
import { t } from '../i18n/uz'
import { useToast } from './toast'

interface NetworkContextValue {
  online: boolean
  pending: number
  syncing: boolean
  sync: () => Promise<void>
}

const NetworkContext = createContext<NetworkContextValue | null>(null)

export function NetworkProvider({ children }: { children: ReactNode }) {
  const [online, setOnline] = useState(navigator.onLine)
  const [pending, setPending] = useState(0)
  const [syncing, setSyncing] = useState(false)
  const toast = useToast()

  const sync = useCallback(async () => {
    if (!navigator.onLine || syncing) return
    setSyncing(true)
    try {
      const result = await syncOutbox()
      if (result.sent > 0 && result.failed === 0) toast.success(t.offline.synced)
      if (result.failed > 0) toast.warning(t.offline.failedItems)
    } finally {
      setSyncing(false)
    }
  }, [syncing, toast])

  useEffect(() => onQueueChange(setPending), [])

  useEffect(() => {
    const goOnline = () => {
      setOnline(true)
      void sync()
    }
    const goOffline = () => setOnline(false)

    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)

    // Ilova ochilganda va har 60 soniyada navbatni tekshiramiz.
    void sync()
    const interval = window.setInterval(() => void sync(), 60_000)

    return () => {
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
      window.clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const value = useMemo<NetworkContextValue>(
    () => ({ online, pending, syncing, sync }),
    [online, pending, syncing, sync],
  )

  return <NetworkContext.Provider value={value}>{children}</NetworkContext.Provider>
}

export function useNetwork(): NetworkContextValue {
  const context = useContext(NetworkContext)
  if (!context) throw new Error('useNetwork faqat NetworkProvider ichida ishlaydi')
  return context
}
