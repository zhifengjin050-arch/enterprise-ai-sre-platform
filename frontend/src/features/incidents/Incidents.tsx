import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import PageHeader from '../../ui/PageHeader'
import StatusBadge from '../../ui/StatusBadge'
import SeverityChip from '../../ui/SeverityChip'
import EmptyState from '../../ui/EmptyState'
import ResizeHandle from '../../ui/ResizeHandle'
import { usePanelWidth } from '../../ui/usePanelWidth'

interface AlertItem {
  id: number
  level: string
  title: string
  message: string
  source: string
  status: string
  created_at?: string
}

interface Execution {
  id: number
  status: string
  duration: number
  tools_called: number
  error_message?: string
  created_at?: string
}

type Incident = {
  key: string
  kind: 'alert' | 'run'
  severity: string
  status: string
  title: string
  source: string
  created_at?: string
  detail: string
}

export default function Incidents() {
  const navigate = useNavigate()
  const { t } = usePrefs()
  const left = usePanelWidth('sre-inc-left', 280, 180, 560)
  const right = usePanelWidth('sre-inc-right', 300, 220, 640)
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [runs, setRuns] = useState<Execution[]>([])
  const [selected, setSelected] = useState<Incident | null>(null)
  const [token, setToken] = useState('')
  const [actionMsg, setActionMsg] = useState('')

  useEffect(() => {
    api.get('/alerts', { params: { limit: 50 } }).then((r) => setAlerts(Array.isArray(r.data) ? r.data : [])).catch(() => {})
    api.get('/agent/executions', { params: { limit: 30 } }).then((r) => setRuns(Array.isArray(r.data) ? r.data : [])).catch(() => {})
  }, [])

  const incidents = useMemo<Incident[]>(() => {
    const fromAlerts: Incident[] = alerts.map((a) => ({
      key: `alert-${a.id}`,
      kind: 'alert',
      severity: a.level || 'warning',
      status: a.status || 'firing',
      title: a.title,
      source: a.source || 'alert',
      created_at: a.created_at,
      detail: a.message,
    }))
    const fromRuns: Incident[] = runs
      .filter((r) => String(r.status).toLowerCase() === 'failed')
      .map((r) => ({
        key: `run-${r.id}`,
        kind: 'run',
        severity: 'critical',
        status: 'failed',
        title: `Agent execution #${r.id} failed`,
        source: 'agent',
        created_at: r.created_at,
        detail: r.error_message || `duration ${r.duration}s · tools ${r.tools_called}`,
      }))
    return [...fromAlerts, ...fromRuns]
  }, [alerts, runs])

  const approve = async (ok: boolean) => {
    if (!token.trim()) return
    try {
      const res = await api.post(ok ? '/repair/approve' : '/repair/reject', { token: token.trim() })
      setActionMsg(JSON.stringify(res.data))
    } catch (e: any) {
      setActionMsg(e.response?.data?.detail || '审批失败')
    }
  }

  return (
    <div>
      <PageHeader
        title={t('header.incidents')}
        subtitle={t('header.incidentsSub')}
      />
      <div className="flex gap-3 min-h-[28rem]">
        <div className="relative card p-0 overflow-hidden shrink-0" style={{ width: left.width }}>
          <div className="px-4 py-3 border-b border-line text-xs text-ink-muted tracking-wider">
            列表 · {incidents.length}
          </div>
          <div className="overflow-y-auto max-h-[32rem]">
            {incidents.length === 0 && (
              <EmptyState title="暂无 Incident" description="告警与失败执行为空" />
            )}
            {incidents.map((inc) => (
              <button
                key={inc.key}
                onClick={() => setSelected(inc)}
                className={`w-full text-left px-4 py-3 border-b border-line/50 ${
                  selected?.key === inc.key ? 'bg-primary-500/10' : 'hover:bg-surface-2'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <SeverityChip level={inc.severity} />
                  <StatusBadge status={inc.status} />
                </div>
                <p className="text-sm text-ink">{inc.title}</p>
                <p className="text-[11px] text-ink-muted mt-0.5">
                  {inc.source} · {inc.created_at ? new Date(inc.created_at).toLocaleString() : ''}
                </p>
              </button>
            ))}
          </div>
          <ResizeHandle edge="end" label={t('ops.resize')} onPointerDown={left.startDrag(false)} />
        </div>

        <div className="flex-1 card min-w-[16rem]">
          <p className="section-label mb-3">时间线 / 根因</p>
          {selected ? (
            <div className="space-y-3 text-sm">
              <p className="font-medium">{selected.title}</p>
              <p className="text-ink-muted whitespace-pre-wrap">{selected.detail}</p>
              <div className="border-l border-line pl-3 space-y-2 text-xs text-ink-muted">
                <p>Detected · {selected.source}</p>
                <p>AI 分析：将上下文交给 Copilot 生成根因与修复计划</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-ink-muted">选择一条 Incident</p>
          )}
        </div>

        <div className="relative card shrink-0" style={{ width: right.width }}>
          <ResizeHandle edge="start" label={t('ops.resize')} onPointerDown={right.startDrag(true)} />
          <p className="section-label mb-3">修复方案 / 审批</p>
          {selected ? (
            <div className="space-y-3">
              <button
                className="btn-primary w-full"
                onClick={() =>
                  navigate(`/ops?q=${encodeURIComponent(`分析并给出修复方案：${selected.title}。${selected.detail}`)}`)
                }
              >
                交给 Agent
              </button>
              <input
                className="input-field"
                placeholder="审批令牌"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
              <div className="flex gap-2">
                <button className="btn-primary flex-1" onClick={() => approve(true)}>
                  批准
                </button>
                <button className="btn-secondary flex-1" onClick={() => approve(false)}>
                  驳回
                </button>
              </div>
              {actionMsg && <p className="text-xs text-ink-muted font-mono break-all">{actionMsg}</p>}
            </div>
          ) : (
            <p className="text-sm text-ink-muted">选择 Incident 后可审批危险操作</p>
          )}
        </div>
      </div>
    </div>
  )
}
