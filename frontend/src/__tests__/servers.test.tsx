import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import Servers from '../pages/Servers'
import { createWrapper, mockUser } from '../test-utils'

vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

import api from '../api/client'

const mockServers = [
  { id: 1, name: 'web-prod-01', host: '192.168.1.10', port: 22, username: 'root', auth_type: 'password', description: 'Production web server', is_active: true, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
  { id: 2, name: 'db-master', host: '192.168.1.20', port: 22, username: 'admin', auth_type: 'key', description: 'Database master', is_active: false, created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

describe('服务器列表', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValue({ data: mockServers })
  })

  it('渲染服务器列表', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Servers />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('web-prod-01')).toBeDefined()
      expect(screen.getByText('db-master')).toBeDefined()
      expect(screen.getByText('192.168.1.10:22')).toBeDefined()
      expect(screen.getByText('192.168.1.20:22')).toBeDefined()
    })
  })

  it('显示服务器数量', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Servers />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('共 2 台服务器')).toBeDefined()
    })
  })

  it('点击添加按钮显示表单', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Servers />, { wrapper })

    await waitFor(() => {
      fireEvent.click(screen.getByText('+ 添加服务器'))
      expect(screen.getByText('新增服务器')).toBeDefined()
    })
  })
})

describe('空服务器列表', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const mockGet = vi.mocked(api.get)
    mockGet.mockResolvedValue({ data: [] })
  })

  it('空列表显示提示信息', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Servers />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('暂无服务器，请添加一台服务器开始使用。')).toBeDefined()
    })
  })
})