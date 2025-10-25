import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import axios from '@/utils/axios'

export interface User {
  id: number
  username: string
  email: string
  created_at: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<boolean>
  register: (username: string, email: string, password: string) => Promise<boolean>
  logout: () => void
  refreshToken: () => Promise<boolean>
  setToken: (token: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          const response = await axios.post('/api/auth/login', {
            username,
            password,
          })

          const { access_token, user } = response.data
          
          set({
            user,
            token: access_token,
            isAuthenticated: true,
          })

          // 设置axios默认header
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return true
        } catch (error) {
          console.error('登录失败:', error)
          return false
        }
      },

      register: async (username: string, email: string, password: string) => {
        try {
          await axios.post('/api/auth/register', {
            username,
            email,
            password,
          })
          return true
        } catch (error) {
          console.error('注册失败:', error)
          return false
        }
      },

      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
        
        // 清除axios默认header
        delete axios.defaults.headers.common['Authorization']
      },

      refreshToken: async () => {
        try {
          const { token } = get()
          if (!token) return false

          const response = await axios.post('/api/auth/refresh', {}, {
            headers: { Authorization: `Bearer ${token}` }
          })

          const { access_token } = response.data
          
          set({ token: access_token })
          axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

          return true
        } catch (error) {
          console.error('刷新token失败:', error)
          get().logout()
          return false
        }
      },

      setToken: (token: string) => {
        set({ token, isAuthenticated: true })
        axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // 恢复时设置axios header
        if (state?.token) {
          axios.defaults.headers.common['Authorization'] = `Bearer ${state.token}`
        }
      },
    }
  )
)