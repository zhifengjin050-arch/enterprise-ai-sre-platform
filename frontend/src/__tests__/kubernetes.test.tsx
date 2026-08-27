import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import Kubernetes from '../pages/Kubernetes'
import { createWrapper, mockUser } from '../test-utils'

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

const mockNodes = {
  nodes: [
    { name: 'node-1', status: 'Ready', role: 'control-plane', cpu: '4', memory: '8Gi', kubelet_version: 'v1.28' },
    { name: 'node-2', status: 'Ready', role: 'worker', cpu: '8', memory: '32Gi', kubelet_version: 'v1.28' },
  ],
}

const mockPods = {
  pods: [
    { namespace: 'default', name: 'nginx-abc123', status: 'Running', ready: '1/1', restarts: 0 },
    { namespace: 'default', name: 'redis-def456', status: 'CrashLoopBackOff', ready: '0/1', restarts: 5 },
    { namespace: 'kube-system', name: 'coredns-xyz789', status: 'Running', ready: '1/1', restarts: 0 },
  ],
}

describe('Kubernetes页面', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const mockGet = vi.mocked(api.get)
    mockGet.mockImplementation((url: string) => {
      if (url === '/k8s/nodes') return Promise.resolve({ data: mockNodes })
      if (url === '/k8s/pods') return Promise.resolve({ data: mockPods })
      return Promise.reject(new Error('not found'))
    })
  })

  it('渲染节点列表', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Kubernetes />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('node-1')).toBeDefined()
      expect(screen.getByText('node-2')).toBeDefined()
    })
  })

  it('渲染Pod列表', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Kubernetes />, { wrapper })

    await waitFor(() => {
      expect(screen.getByText('nginx-abc123')).toBeDefined()
      expect(screen.getByText('redis-def456')).toBeDefined()
      expect(screen.getByText('coredns-xyz789')).toBeDefined()
    })
  })

  it('Pod状态显示颜色标记', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Kubernetes />, { wrapper })

    await waitFor(() => {
      // Running should show green badge
      const runningBadges = screen.getAllByText('Running')
      expect(runningBadges.length).toBeGreaterThan(0)
      // CrashLoopBackOff should show red badge
      expect(screen.getByText('CrashLoopBackOff')).toBeDefined()
    })
  })

  it('显示Pod诊断输入框', async () => {
    const wrapper = createWrapper({ user: mockUser, token: 'test-token' })
    render(<Kubernetes />, { wrapper })

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Pod 名称')).toBeDefined()
      expect(screen.getByPlaceholderText('命名空间')).toBeDefined()
      expect(screen.getByText('诊断')).toBeDefined()
    })
  })
})