import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Dashboard from '../pages/Dashboard'
import { createWrapper, mockUser } from '../test-utils'

// Mock axios
vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
  api: {
    get: vi.fn(),
    post: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  },
}))

import api from '../api/client'

const mockHealth = {
  status: 'healthy',
  version: '1.1.0',
  environment: 'test',
  services: { api: 'healthy', database: 'connected', llm: 'available' },
  servers_managed: 5,
}

const mockServerStatus = {
  cpu: { percent: 45, cores: 8 },
  memory: { percent: 62, total_gb: 32, used_gb: 19.8, free_gb: 12.2 },
  disks: [{ mount: '/', percent: 71, total_gb: 256, used_gb: 182 }],
}

const mockStats = {
  total_conversations: 42,
  total_messages: 580,
  total_servers: 5,
  tools_available: 12,
}

describe('Dashboard加载', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        json: () => Promise.resolve(mockHealth),
      }),
    )
    const mockGet = vi.mocked(api.get)
    mockGet.mockImplementation((url: string) => {
      if (url === '/overview') {
        return Promise.resolve({
          data: {
            health_score: 88,
            sla_percent: 99,
            risk_count: 0,
            executions_24h: 12,
            repair_count: 1,
            time_saved_hours: 3,
            health: mockHealth,
            resources: mockServerStatus,
            stats: mockStats,
            trend: [],
            incidents: [],
            recent_runs: [],
          },
        })
      }
      if (url === '/server/status') return Promise.resolve({ data: mockServerStatus })
      if (url === '/agent/stats') return Promise.resolve({ data: mockStats })
      return Promise.reject(new Error('not found'))
    })
  })

  it('Dashboard渲染健康状态卡片', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('healthy')).toBeDefined()
      expect(screen.getByText('connected')).toBeDefined()
      expect(screen.getByText('available')).toBeDefined()
    })
  })

  it('Dashboard渲染服务器状态进度条', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('45%')).toBeDefined()
      expect(screen.getByText('62%')).toBeDefined()
    })
  })

  it('Dashboard渲染Agent统计', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('42')).toBeDefined()
      expect(screen.getByText('580')).toBeDefined()
      expect(screen.getByText('12')).toBeDefined()
    })
  })

  it('Dashboard显示系统标题', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Dashboard />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('系统健康状态')).toBeDefined()
      expect(screen.getByText('本机服务器状态')).toBeDefined()
      expect(screen.getByText('Agent 运行统计')).toBeDefined()
    })
  })
})