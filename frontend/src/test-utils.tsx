import React, { ReactNode } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { AuthContext } from './store/auth'
import { PrefsProvider } from './store/prefs'

// 模拟用户数据
export const mockUser = {
  id: 1,
  username: 'admin',
  email: 'admin@example.com',
  role: 'admin',
}

// 创建包装组件
export function createWrapper({ user = null, token = null }: { user?: any; token?: string | null }) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <BrowserRouter>
        <PrefsProvider>
          <AuthContext.Provider
            value={{
              user,
              token,
              login: async () => {},
              register: async () => {},
              logout: () => {},
              isAuthenticated: !!token,
            }}
          >
            {children}
          </AuthContext.Provider>
        </PrefsProvider>
      </BrowserRouter>
    )
  }
}