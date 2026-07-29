/** Ma'lumot yuklash uchun yengil hook (kesh va qayta yuklash bilan). */

import { useCallback, useEffect, useRef, useState } from 'react'

import { getCached } from '../lib/api'

interface ResourceState<T> {
  data: T | null
  loading: boolean
  error: string | null
  fromCache: boolean
  savedAt?: number
}

export interface Resource<T> extends ResourceState<T> {
  reload: () => Promise<void>
  setData: (updater: T | ((previous: T | null) => T | null)) => void
}

export function useResource<T>(path: string | null, deps: unknown[] = []): Resource<T> {
  const [state, setState] = useState<ResourceState<T>>({
    data: null,
    loading: Boolean(path),
    error: null,
    fromCache: false,
  })
  const controllerRef = useRef<AbortController | null>(null)

  const load = useCallback(async () => {
    if (!path) {
      setState({ data: null, loading: false, error: null, fromCache: false })
      return
    }
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller

    setState((previous) => ({ ...previous, loading: true, error: null }))
    try {
      const result = await getCached<T>(path, controller.signal)
      if (controller.signal.aborted) return
      setState({
        data: result.data,
        loading: false,
        error: null,
        fromCache: result.fromCache,
        savedAt: result.savedAt,
      })
    } catch (error) {
      if (controller.signal.aborted) return
      setState({
        data: null,
        loading: false,
        error: error instanceof Error ? error.message : 'Xatolik yuz berdi',
        fromCache: false,
      })
    }
  }, [path])

  useEffect(() => {
    void load()
    return () => controllerRef.current?.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])

  const setData = useCallback((updater: T | ((previous: T | null) => T | null)) => {
    setState((previous) => ({
      ...previous,
      data:
        typeof updater === 'function'
          ? (updater as (value: T | null) => T | null)(previous.data)
          : updater,
    }))
  }, [])

  return { ...state, reload: load, setData }
}
