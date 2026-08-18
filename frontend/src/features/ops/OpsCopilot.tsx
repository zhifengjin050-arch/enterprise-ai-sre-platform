import { useEffect, useMemo, useRef, useState, type MouseEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Plus, Send, GitBranch, Trash2, Download, FileJson } from 'lucide-react'
import api from '../../api/client'
import { streamChat, StreamEvent } from '../../api/stream'
import { useAuth } from '../../store/auth'
import { usePrefs } from '../../store/prefs'
import EmptyState from '../../ui/EmptyState'
import PrefsToggles from '../../ui/PrefsToggles'
import ResizeHandle from '../../ui/ResizeHandle'
import { usePanelWidth } from '../../ui/usePanelWidth'
import type { MessageKey } from '../../i18n'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Conversation {
  id: number
  title: string
  updated_at?: string
  message_count?: number
}

interface LiveStep {
  id: string
  type: string
  status: 'running' | 'completed' | 'failed'
  detail?: string
}

const STORAGE_KEY = 'chat_messages'
const PIPELINE: { type: string; label: MessageKey }[] = [
  { type: 'agent_start', label: 'ops.thinking' },
  { type: 'rag_search', label: 'ops.rag' },
  { type: 'memory_load', label: 'ops.memory' },
  { type: 'llm_start', label: 'ops.llm' },
  { type: 'tool_call', label: 'ops.tool' },
  { type: 'final_answer', label: 'ops.report' },
]

function loadLocal(): Message[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function fill(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), template)
}

function downloadBlob(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function toMarkdown(title: string, messages: Message[], you: string, agent: string) {
  const lines = [`# ${title}`, '', `_${new Date().toISOString()}_`, '']
  for (const m of messages) {
    lines.push(`## ${m.role === 'user' ? you : agent}`, '', m.content, '')
  }
  return lines.join('\n')
}

export default function OpsCopilot() {
  const { token } = useAuth()
  const { t } = usePrefs()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const preset = params.get('q') || ''
  const left = usePanelWidth('sre-ops-left', 224, 140, 640)
  const right = usePanelWidth('sre-ops-right', 320, 200, 720)

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>(loadLocal)
  const [input, setInput] = useState(preset)
  const [loading, setLoading] = useState(false)
  const [live, setLive] = useState<LiveStep[]>([])
  const [approvalToken, setApprovalToken] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadConversations = () => {
    api
      .get('/conversations')
      .then((r) => setConversations(Array.isArray(r.data) ? r.data : []))
      .catch(() => {})
  }

  useEffect(() => {
    loadConversations()
  }, [])

  useEffect(() => {
    if (preset) setInput(preset)
  }, [preset])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch {
      /* ignore */
    }
  }, [messages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, live])

  const fetchMessages = async (id: number): Promise<Message[]> => {
    const res = await api.get(`/conversations/${id}`)
    return (res.data.messages || []).map((m: { role: string; content: string }) => ({
      role: m.role === 'user' ? 'user' : 'assistant',
      content: m.content,
    }))
  }

  const openConversation = async (id: number) => {
    setActiveId(id)
    try {
      setMessages(await fetchMessages(id))
    } catch {
      /* keep local */
    }
  }

  const newChat = () => {
    setActiveId(null)
    setMessages([])
    setLive([])
    localStorage.removeItem(STORAGE_KEY)
  }

  const deleteConversation = async (c: Conversation, e: MouseEvent) => {
    e.stopPropagation()
    const title = c.title || fill(t('ops.untitled'), { id: c.id })
    if (!window.confirm(fill(t('ops.deleteConfirm'), { title }))) return
    try {
      await api.delete(`/conversations/${c.id}`)
      setConversations((prev) => prev.filter((x) => x.id !== c.id))
      if (activeId === c.id) newChat()
    } catch {
      /* ignore */
    }
  }

  const exportConversation = async (c: Conversation, format: 'md' | 'json', e: MouseEvent) => {
    e.stopPropagation()
    const title = c.title || fill(t('ops.untitled'), { id: c.id })
    let msgs = messages
    if (activeId !== c.id) {
      try {
        msgs = await fetchMessages(c.id)
      } catch {
        return
      }
    }
    const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
    const safe = title.replace(/[\\/:*?"<>|]/g, '_').slice(0, 40)
    if (format === 'json') {
      downloadBlob(`${safe}-${stamp}.json`, JSON.stringify({ id: c.id, title, messages: msgs }, null, 2), 'application/json')
    } else {
      downloadBlob(`${safe}-${stamp}.md`, toMarkdown(title, msgs, t('ops.you'), t('ops.agent')), 'text/markdown;charset=utf-8')
    }
  }

  const applyEvent = (event: StreamEvent) => {
    setLive((prev) => {
      const next = [...prev]
      const upsert = (type: string, status: LiveStep['status'], detail?: string) => {
        const idx = next.findIndex((s) => s.type === type && (type !== 'tool_call' || s.detail === detail))
        const step: LiveStep = { id: `${type}-${next.length}`, type, status, detail }
        if (idx >= 0) next[idx] = { ...next[idx], status, detail: detail || next[idx].detail }
        else next.push(step)
      }
      if (event.type === 'agent_start' || event.type === 'thinking') {
        upsert('agent_start', 'running', event.content)
      } else if (event.type === 'rag_search') {
        upsert('rag_search', event.status === 'failed' ? 'failed' : 'completed', fill(t('ops.hits'), { n: event.result_count ?? 0 }))
      } else if (event.type === 'memory_load') {
        upsert('memory_load', 'completed', event.content)
      } else if (event.type === 'llm_start') {
        upsert('llm_start', event.status === 'completed' ? 'completed' : 'running', event.model || event.content)
      } else if (event.type === 'tool_call') {
        upsert('tool_call', 'running', event.tool)
      } else if (event.type === 'tool_result') {
        upsert('tool_call', event.status === 'failed' ? 'failed' : 'completed', event.tool)
      } else if (event.type === 'final_answer' || event.type === 'complete') {
        upsert('final_answer', 'completed')
        next.forEach((s) => {
          if (s.status === 'running') s.status = 'completed'
        })
      } else if (event.type === 'error') {
        upsert('error', 'failed', event.message)
      }
      return next
    })
    if (event.content && event.content.includes('approval') && /token/i.test(event.content)) {
      const m = event.content.match(/[A-Za-z0-9_-]{8,}/)
      if (m) setApprovalToken(m[0])
    }
  }

  const send = async () => {
    if (!input.trim() || loading) return
    const msg = input.trim()
    setInput('')
    setLoading(true)
    setLive([])
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    try {
      const complete = await streamChat(
        { message: msg, session_id: activeId ? String(activeId) : 'web-console', conversation_id: activeId || undefined },
        applyEvent,
        token,
      )
      const report =
        complete.report ||
        (complete.type === 'final_answer' ? complete.content : '') ||
        t('ops.noReport')
      setMessages((prev) => [...prev, { role: 'assistant', content: report }])
      if (complete.conversation_id) {
        setActiveId(complete.conversation_id)
        loadConversations()
      }
    } catch (err: any) {
      try {
        const res = await api.post('/chat', {
          message: msg,
          session_id: activeId ? String(activeId) : 'web-console',
          conversation_id: activeId,
        })
        setMessages((prev) => [...prev, { role: 'assistant', content: res.data.report }])
        if (res.data.conversation_id) setActiveId(res.data.conversation_id)
      } catch (e: any) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: `${t('ops.errorPrefix')}: ${e.response?.data?.detail || err.message || t('ops.failed')}` },
        ])
      }
    } finally {
      setLoading(false)
    }
  }

  const approve = async (ok: boolean) => {
    if (!approvalToken) return
    try {
      await api.post(ok ? '/repair/approve' : '/repair/reject', { token: approvalToken })
      setApprovalToken('')
    } catch {
      /* ignore */
    }
  }

  const pipelineView = useMemo(() => {
    return PIPELINE.map((p) => {
      const found = [...live].reverse().find((s) => s.type === p.type)
      return { ...p, status: found?.status, detail: found?.detail }
    })
  }, [live])

  return (
    <div className="theme-canvas h-full flex">
      <aside className="theme-chrome relative border-r border-line flex flex-col shrink-0" style={{ width: left.width }}>
        <div className="p-3 flex items-center justify-between border-b border-line">
          <span className="text-xs font-medium text-ink-muted tracking-wider">{t('ops.conversations')}</span>
          <button className="btn-ghost p-1" onClick={newChat} title={t('ops.newChat')}>
            <Plus size={14} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group relative border-b border-line/60 ${
                activeId === c.id ? 'bg-primary-500/10 text-ink' : 'text-ink-muted hover:bg-surface-2'
              }`}
            >
              <button onClick={() => openConversation(c.id)} className="w-full text-left px-3 py-2.5 pr-20 text-sm">
                <p className="truncate">{c.title || fill(t('ops.untitled'), { id: c.id })}</p>
                <p className="text-[11px] text-ink-muted mt-0.5">{fill(t('ops.msgs'), { n: c.message_count || 0 })}</p>
              </button>
              <div className={`absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5 ${activeId === c.id ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 focus-within:opacity-100'}`}>
                <button
                  type="button"
                  className="btn-ghost p-1"
                  title={t('ops.exportMd')}
                  onClick={(e) => exportConversation(c, 'md', e)}
                >
                  <Download size={13} />
                </button>
                <button
                  type="button"
                  className="btn-ghost p-1"
                  title={t('ops.exportJson')}
                  onClick={(e) => exportConversation(c, 'json', e)}
                >
                  <FileJson size={13} />
                </button>
                <button
                  type="button"
                  className="btn-ghost p-1"
                  title={t('ops.delete')}
                  onClick={(e) => deleteConversation(c, e)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
        <ResizeHandle edge="end" label={t('ops.resize')} onPointerDown={left.startDrag(false)} />
      </aside>

      <section className="theme-canvas flex-1 flex flex-col min-w-0">
        <div className="px-4 py-2.5 border-b border-line flex items-center justify-end shrink-0">
          <PrefsToggles compact />
        </div>
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {messages.length === 0 && <EmptyState title={t('ops.emptyTitle')} description={t('ops.emptyDesc')} />}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 text-sm text-ink ${
                  m.role === 'user'
                    ? 'bg-primary-500/10 border border-primary-500/25'
                    : 'theme-chrome border border-line'
                }`}
              >
                <p className="text-[11px] text-ink-muted mb-1">{m.role === 'user' ? t('ops.you') : t('ops.agent')}</p>
                {m.role === 'assistant' ? (
                  <div className="md-body text-sm leading-relaxed [&_pre]:p-3 [&_pre]:rounded-lg [&_pre]:border [&_pre]:border-line [&_code]:font-mono">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <div className="whitespace-pre-wrap text-ink">{m.content}</div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <div className="p-4 border-t border-line flex gap-2">
          <input
            className="input-field flex-1"
            placeholder={t('ops.inputPh')}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            disabled={loading}
          />
          <button className="btn-primary inline-flex items-center gap-1.5" onClick={send} disabled={loading}>
            <Send size={14} />
            {loading ? t('ops.running') : t('ops.send')}
          </button>
        </div>
      </section>

      <aside className="theme-chrome relative border-l border-line flex flex-col shrink-0" style={{ width: right.width }}>
        <ResizeHandle edge="start" label={t('ops.resize')} onPointerDown={right.startDrag(true)} />
        <div className="px-4 py-3 border-b border-line flex items-center justify-between">
          <h3 className="text-xs font-medium text-ink-muted tracking-wider">{t('ops.live')}</h3>
          {activeId && (
            <button className="btn-ghost text-xs inline-flex items-center gap-1" onClick={() => navigate(`/traces?cid=${activeId}`)}>
              <GitBranch size={12} /> {t('ops.trace')}
            </button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {pipelineView.map((p) => (
            <div key={p.type} className="flex gap-3">
              <div
                className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
                  p.status === 'completed'
                    ? 'bg-success'
                    : p.status === 'failed'
                      ? 'bg-danger'
                      : p.status === 'running'
                        ? 'bg-primary-500 animate-pulse'
                        : 'bg-line'
                }`}
              />
              <div>
                <p className="text-sm text-ink">{t(p.label)}</p>
                {p.detail && <p className="text-[11px] text-ink-muted font-mono mt-0.5">{p.detail}</p>}
              </div>
            </div>
          ))}
          {approvalToken && (
            <div className="mt-4 p-3 border border-warning/30 rounded-lg bg-warning/5">
              <p className="text-xs text-warning mb-2">{t('ops.approval')}</p>
              <div className="flex gap-2">
                <button className="btn-primary text-xs" onClick={() => approve(true)}>
                  {t('ops.approve')}
                </button>
                <button className="btn-secondary text-xs" onClick={() => approve(false)}>
                  {t('ops.reject')}
                </button>
              </div>
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
