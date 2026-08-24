import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import api, { setAccessToken } from '../api/client'
import { User } from '../api/types'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  register: (username: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

interface TokenResponse {
  access_token: string
  user: User
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const refreshTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Schedule a proactive token refresh 5 minutes before expiry (access token = 30 min)
  const scheduleRefresh = useCallback(() => {
    if (refreshTimerRef.current) {
      clearTimeout(refreshTimerRef.current)
    }
    // Refresh 5 minutes before expiry (25 minutes)
    const refreshIn = (30 - 5) * 60 * 1000
    refreshTimerRef.current = setTimeout(async () => {
      try {
        const { data } = await api.post<TokenResponse>('/auth/refresh')
        setAccessToken(data.access_token)
        setUser(data.user)
        scheduleRefresh()
      } catch {
        setUser(null)
        setAccessToken(null)
      }
    }, refreshIn)
  }, [])

  // On mount: attempt to restore session via refresh token cookie
  useEffect(() => {
    const restoreSession = async () => {
      try {
        const { data } = await api.post<TokenResponse>('/auth/refresh')
        setAccessToken(data.access_token)
        setUser(data.user)
        scheduleRefresh()
      } catch {
        // No valid session — that's fine
      } finally {
        setIsLoading(false)
      }
    }
    restoreSession()

    return () => {
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    }
  }, [scheduleRefresh])

  const login = useCallback(
    async (username: string, password: string) => {
      const { data } = await api.post<TokenResponse>('/auth/login', {
        username,
        password,
      })
      setAccessToken(data.access_token)
      setUser(data.user)
      scheduleRefresh()
    },
    [scheduleRefresh]
  )

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      const { data } = await api.post<TokenResponse>('/auth/register', {
        username,
        email,
        password,
      })
      setAccessToken(data.access_token)
      setUser(data.user)
      scheduleRefresh()
    },
    [scheduleRefresh]
  )

  const logout = useCallback(async () => {
    try {
      await api.post('/auth/logout')
    } finally {
      setAccessToken(null)
      setUser(null)
      if (refreshTimerRef.current) clearTimeout(refreshTimerRef.current)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: user !== null,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
