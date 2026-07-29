/** Autentifikatsiya konteksti: Telegram initData -> JWT. */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { ApiError, api, tokens } from '../lib/api'
import { isTelegram, webApp } from '../lib/telegram'
import type { TokenResponse, User } from '../types'

type Status = 'loading' | 'authenticated' | 'unauthenticated'

interface AuthState {
  status: Status
  user: User | null
  error: string | null
}

interface AuthContextValue extends AuthState {
  isAdmin: boolean
  signIn: () => Promise<void>
  devSignIn: (role: 'admin' | 'measurer') => Promise<void>
  signOut: () => void
  setUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading', user: null, error: null })

  const authenticate = useCallback(async () => {
    setState((previous) => ({ ...previous, status: 'loading', error: null }))

    // 1. Amaldagi token bo'lsa — profilni olamiz.
    if (tokens.access) {
      try {
        const user = await api.get<User>('/auth/me')
        setState({ status: 'authenticated', user, error: null })
        return
      } catch (error) {
        if (error instanceof ApiError && error.status === 403) {
          tokens.clear()
          setState({ status: 'unauthenticated', user: null, error: error.message })
          return
        }
        if (error instanceof ApiError && error.status !== 401) {
          // Internet yo'q — mavjud token bilan davom etamiz (oflayn rejim).
          const cachedUser = readCachedUser()
          if (cachedUser) {
            setState({ status: 'authenticated', user: cachedUser, error: null })
            return
          }
        }
        tokens.clear()
      }
    }

    // 2. Telegram ichida — initData orqali kiramiz.
    if (isTelegram && webApp?.initData) {
      try {
        const response = await api.anonymous.post<TokenResponse>('/auth/telegram', {
          init_data: webApp.initData,
        })
        tokens.save(response)
        cacheUser(response.user)
        setState({ status: 'authenticated', user: response.user, error: null })
        return
      } catch (error) {
        setState({
          status: 'unauthenticated',
          user: null,
          error: error instanceof Error ? error.message : 'Kirishda xatolik',
        })
        return
      }
    }

    setState({ status: 'unauthenticated', user: null, error: null })
  }, [])

  const devSignIn = useCallback(async (role: 'admin' | 'measurer') => {
    setState((previous) => ({ ...previous, status: 'loading', error: null }))
    try {
      const response = await api.anonymous.post<TokenResponse>('/auth/dev-login', {
        secret: (import.meta.env.VITE_DEV_LOGIN_SECRET as string | undefined) ?? 'dev-secret',
        telegram_id: role === 'admin' ? 900000001 : 900000002,
        first_name: role === 'admin' ? 'Admin' : 'O‘lchovchi',
        role,
      })
      tokens.save(response)
      cacheUser(response.user)
      setState({ status: 'authenticated', user: response.user, error: null })
    } catch (error) {
      setState({
        status: 'unauthenticated',
        user: null,
        error: error instanceof Error ? error.message : 'Kirishda xatolik',
      })
    }
  }, [])

  const signOut = useCallback(() => {
    tokens.clear()
    localStorage.removeItem('pardachi.user')
    setState({ status: 'unauthenticated', user: null, error: null })
  }, [])

  const setUser = useCallback((user: User) => {
    cacheUser(user)
    setState((previous) => ({ ...previous, user }))
  }, [])

  useEffect(() => {
    void authenticate()
  }, [authenticate])

  const value = useMemo<AuthContextValue>(
    () => ({
      ...state,
      isAdmin: state.user?.role === 'admin',
      signIn: authenticate,
      devSignIn,
      signOut,
      setUser,
    }),
    [state, authenticate, devSignIn, signOut, setUser],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth faqat AuthProvider ichida ishlaydi')
  return context
}

function cacheUser(user: User): void {
  try {
    localStorage.setItem('pardachi.user', JSON.stringify(user))
  } catch {
    // localStorage to'lgan bo'lishi mumkin — e'tiborsiz
  }
}

function readCachedUser(): User | null {
  try {
    const raw = localStorage.getItem('pardachi.user')
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    return null
  }
}
