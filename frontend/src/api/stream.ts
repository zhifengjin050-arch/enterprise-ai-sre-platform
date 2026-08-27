export interface StreamEvent {
  type: string
  content?: string
  tool?: string
  status?: string
  query?: string
  result_count?: number
  result?: string
  duration_ms?: number
  model?: string
  message?: string
  report?: string
  trace?: unknown[]
  conversation_id?: number
  args?: string
}

export async function streamChat(
  payload: { message: string; session_id?: string; conversation_id?: number },
  onEvent: (event: StreamEvent) => void,
  token?: string | null,
  signal?: AbortSignal,
): Promise<StreamEvent> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch('/api/chat/stream', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      message: payload.message,
      session_id: payload.session_id || 'web-console',
      conversation_id: payload.conversation_id,
    }),
    signal,
  })

  if (!res.ok || !res.body) {
    throw new Error(`SSE 请求失败 (${res.status})`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let lastComplete: StreamEvent = { type: 'complete' }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() || ''
    for (const chunk of chunks) {
      const line = chunk
        .split('\n')
        .filter((l) => l.startsWith('data:'))
        .map((l) => l.slice(5).trim())
        .join('')
      if (!line) continue
      try {
        const event = JSON.parse(line) as StreamEvent
        onEvent(event)
        if (event.report) lastComplete = { ...lastComplete, ...event, report: event.report }
        if (event.type === 'final_answer' && event.content) {
          lastComplete = { ...lastComplete, ...event, report: event.content }
        }
        if (event.type === 'complete' || event.type === 'error') {
          lastComplete = { ...lastComplete, ...event }
        }
      } catch {
        // ignore malformed heartbeat
      }
    }
  }
  return lastComplete
}
