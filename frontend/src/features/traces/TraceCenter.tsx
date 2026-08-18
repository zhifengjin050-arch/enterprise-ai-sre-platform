import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import StatusBadge from '../../ui/StatusBadge'
import EmptyState from '../../ui/EmptyState'
import PageHeader from '../../ui/PageHeader'
import ResizeHandle from '../../ui/ResizeHandle'
import { usePanelWidth } from '../../ui/usePanelWidth'
import type { MessageKey } from '../../i18n'

interface Execution {
  id: number
  conversation_id?: number
  status: string
  duration: number
  tools_called: number
  error_message?: string
  created_at?: string
}

interface TraceStep {
  event: string
  content?: string
  tool?: string
  duration?: number
  meta?: Record<string, unknown>
}

const EVENT_LABEL: Record<string, MessageKey> = {
  user_request: 'traces.userRequest',
  agent_start: 'traces.thinking',
  rag_search: 'traces.rag',
  memory_load: 'traces.memory',
  llm_start: 'traces.llm',
  tool_call: 'traces.tool',
  tool_result: 'traces.toolResult',
  final_answer: 'traces.report',
}

function fill(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), template)
}

export default function TraceCenter() {
  const { t } = usePrefs()
  const [params, setParams] = useSearchParams()
  const left = usePanelWidth('sre-traces-left', 256, 160, 560)
  const right = usePanelWidth('sre-traces-right', 320, 220, 720)
  const [runs, setRuns] = useState<Execution[]>([])
  const [conversations, setConversations] = useState<{ id: number; title: string }[]>([])
  const [cid, setCid] = useState(params.get('cid') || '')
  const [steps, setSteps] = useState<TraceStep[]>([])
  const [selected, setSelected] = useState<TraceStep | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/agent/executions', { params: { limit: 40 } }).then((r) => setRuns(Array.isArray(r.data) ? r.data : [])).catch(() => {})
    api.get('/conversations').then((r) => setConversations(Array.isArray(r.data) ? r.data : [])).catch(() => {})
  }, [])

  const load = async (id: string) => {
    if (!id) return
    setError('')
    setCid(id)
    setParams({ cid: id })
    try {
      const res = await api.get(`/agent/traces/${id}`)
      const list = res.data.steps || []
      setSteps(list)
      setSelected(list[0] || null)
    } catch (e: any) {
      setError(e.response?.data?.detail || t('traces.loadFail'))
      setSteps([])
    }
  }

  useEffect(() => {
    if (params.get('cid')) load(params.get('cid')!)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const convTitle = useMemo(() => {
    const n = Number(cid)
    return conversations.find((c) => c.id === n)?.title || (cid ? fill(t('traces.conv'), { id: cid }) : t('traces.unselected'))
  }, [cid, conversations, t])

  const eventLabel = (event: string) => (EVENT_LABEL[event] ? t(EVENT_LABEL[event]) : event)

  return (
    <div className="h-[calc(100vh-6.5rem)] flex gap-3 min-w-0">
      <aside className="relative card overflow-hidden flex flex-col p-0 shrink-0" style={{ width: left.width }}>
        <div className="px-3 py-3 border-b border-line">
          <p className="section-label">{t('traces.runs')}</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversations.map((c) => (
            <button
              key={c.id}
              onClick={() => load(String(c.id))}
              className={`w-full text-left px-3 py-2.5 text-sm border-b border-line/50 ${
                cid === String(c.id) ? 'bg-primary-500/10' : 'hover:bg-surface-2'
              }`}
            >
              <p className="truncate text-ink">{c.title || `#${c.id}`}</p>
              <p className="text-[11px] text-ink-muted">{fill(t('traces.convId'), { id: c.id })}</p>
            </button>
          ))}
          {runs.map((r) => (
            <button
              key={`exec-${r.id}`}
              onClick={() => r.conversation_id && load(String(r.conversation_id))}
              disabled={!r.conversation_id}
              className={`w-full text-left px-3 py-2 text-[11px] border-b border-line/40 ${
                r.conversation_id ? 'text-ink-muted hover:bg-surface-2' : 'text-ink-muted opacity-50 cursor-default'
              }`}
            >
              {fill(t('traces.exec'), { id: r.id, status: r.status, duration: r.duration })}
            </button>
          ))}
        </div>
        <ResizeHandle edge="end" label={t('ops.resize')} onPointerDown={left.startDrag(false)} />
      </aside>

      <section className="flex-1 card overflow-y-auto min-w-[16rem]">
        <PageHeader title={t('traces.waterfall')} subtitle={convTitle} />
        {error && <p className="text-sm text-danger mb-3">{error}</p>}
        {!cid && <EmptyState title={t('traces.emptyTitle')} description={t('traces.emptyDesc')} />}
        <div className="relative pl-4 border-l border-line space-y-4">
          {steps.map((s, i) => (
            <button
              key={i}
              onClick={() => setSelected(s)}
              className={`block w-full text-left -ml-[21px] pl-4 ${selected === s ? 'opacity-100' : 'opacity-80 hover:opacity-100'}`}
            >
              <span className="absolute -ml-[21px] mt-1.5 w-2.5 h-2.5 rounded-full bg-primary-500" />
              <p className="text-sm font-medium text-ink">{eventLabel(s.event)}</p>
              <p className="text-xs text-ink-muted font-mono mt-0.5">
                {s.tool || s.content?.slice(0, 80)}
                {s.duration ? ` · ${s.duration}ms` : ''}
              </p>
            </button>
          ))}
        </div>
      </section>

      <aside className="relative card overflow-y-auto shrink-0" style={{ width: right.width }}>
        <ResizeHandle edge="start" label={t('ops.resize')} onPointerDown={right.startDrag(true)} />
        <p className="section-label mb-3">{t('traces.span')}</p>
        {selected ? (
          <div className="space-y-2 text-sm">
            <StatusBadge status={selected.event} text={eventLabel(selected.event)} />
            {selected.tool && <p className="font-mono text-xs text-ink">{selected.tool}</p>}
            {selected.duration !== undefined && (
              <p className="text-ink-muted">{fill(t('traces.latency'), { n: selected.duration })}</p>
            )}
            <pre className="code-block text-xs font-mono">
              {selected.content}
              {selected.meta ? `\n\n${JSON.stringify(selected.meta, null, 2)}` : ''}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-ink-muted">{t('traces.pickSpan')}</p>
        )}
      </aside>
    </div>
  )
}
