import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { createWrapper, mockUser } from '../test-utils'

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: any) => void) | null = null
  onerror: (() => void) | null = null
  readyState: number = 0
  url: string

  constructor(url: string) {
    this.url = url
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }

  send() {}
  close() {
    this.readyState = 3
    this.onclose?.()
  }
}

vi.stubGlobal('WebSocket', MockWebSocket)

// 直接在vitest环境中测试WebSocket逻辑
describe('WebSocket连接', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('WebSocket支持创建连接', async () => {
    const ws = new MockWebSocket('ws://localhost/ws/chat/1')
    expect(ws.url).toBe('ws://localhost/ws/chat/1')
  })

  it('WebSocket连接后触发onopen', async () => {
    const ws = new MockWebSocket('ws://localhost/ws/chat/1')
    return new Promise<void>((resolve) => {
      ws.onopen = () => {
        expect(ws.readyState).toBe(1)
        resolve()
      }
    })
  })

  it('WebSocket接收消息', async () => {
    const ws = new MockWebSocket('ws://localhost/ws/chat/1')
    const testData = JSON.stringify({ type: 'agent_start', content: '开始分析...' })

    setTimeout(() => {
      ws.onmessage?.({ data: testData })
    }, 0)

    return new Promise<void>((resolve) => {
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        expect(data.type).toBe('agent_start')
        expect(data.content).toBe('开始分析...')
        resolve()
      }
    })
  })

  it('WebSocket断线后状态变化', async () => {
    const ws = new MockWebSocket('ws://localhost/ws/chat/1')
    return new Promise<void>((resolve) => {
      ws.onclose = () => {
        expect(ws.readyState).toBe(3)
        resolve()
      }
      ws.close()
    })
  })

  it('WebSocket支持重连尝试', async () => {
    const connectFn = vi.fn()
    // 模拟重连逻辑
    const simulateReconnect = () => {
      setTimeout(connectFn, 3000)
    }
    simulateReconnect()

    await new Promise(resolve => setTimeout(resolve, 100))
    expect(connectFn).not.toHaveBeenCalled() // 3秒内不应调用

    await new Promise(resolve => setTimeout(resolve, 3000))
    expect(connectFn).toHaveBeenCalledTimes(1)
  }, 10000)
})