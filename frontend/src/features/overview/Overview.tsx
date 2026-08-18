import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ArrowUpRight } from 'lucide-react'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import PageHeader from '../../ui/PageHeader'
import StatusBadge from '../../ui/StatusBadge'
import EmptyState from '../../ui/EmptyState'
import HealthRing from '../../ui/HealthRing'
import ServerCard from '../../components/ServerCard'
import { useCountUp } from '../../ui/useCountUp'

function KpiValue({ value }: { value: number }) {
  const shown = useCountUp(Number(value))
  return <span className="kpi-value text-2xl font-semibold mt-3 block">{shown}</span>
}

interface OverviewData {
  health_score: number
  sla_percent: number
  risk_count: number
  executions_24h: number
  repair_count: number
  time_saved_hours: number
  health: {
    status: string
    version: string
    environment: string
    services: Record<string, string>
    servers_managed?: number
  }
  resources: {
    cpu: { percent: number; cores: number }
    memory: { percent: number; total_gb: number; used_gb: number }
    disks: { percent: number; total_gb: number; used_gb: number }[]
  }
  stats: {
    total_conversations: number
    total_messages: number
    total_servers: number
    total_executions: number
    success_executions: number
    tools_available: number
  }
  trend: { day: string; success: number; failed: number }[]
  incidents: { id: number; level: string; title: string; status: string; created_at?: string }[]
  recent_runs: { id: number; status: string; duration: number; tools_called: number; created_at?: string }[]
}

function useChartColors() {
  const { theme } = usePrefs()
  const [colors, setColors] = useState({ tick: '#8C9AAE', bg: '#141C2A', line: '#2A364A' })
  useEffect(() => {
    const s = getComputedStyle(document.documentElement)
    const rgb = (name: string) => `rgb(${s.getPropertyValue(name).trim()})`
    setColors({
      tick: rgb('--ink-muted'),
      bg: rgb('--surface'),
      line: rgb('--line'),
    })
  }, [theme])
  return colors
}

export default function Overview() {
  const navigate = useNavigate()
  const { t } = usePrefs()
  const chartColors = useChartColors()
  const [data, setData] = useState<OverviewData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false

    const emptyResources = {
      cpu: { percent: 0, cores: 0 },
      memory: { percent: 0, total_gb: 0, used_gb: 0 },
      disks: [] as OverviewData['resources']['disks'],
    }
    const emptyStats = {
      total_conversations: 0,
      total_messages: 0,
      total_servers: 0,
      total_executions: 0,
      success_executions: 0,
      tools_available: 0,
    }

    async function loadFallback(): Promise<OverviewData> {
      const healthRes = await fetch('/health')
        .then(async (r) => {
          if (!r.ok) throw new Error(`health ${r.status}`)
          return r.json()
        })
        .catch(() => ({
          status: 'unknown',
          version: '—',
          environment: '—',
          services: { api: 'unknown', database: 'unknown', llm: 'unknown', monitoring: 'unknown' },
          servers_managed: 0,
        }))

      const [statusRes, statsRes, alertsRes, runsRes] = await Promise.all([
        api.get('/server/status').catch(() => ({ data: emptyResources })),
        api.get('/agent/stats').catch(() => ({ data: emptyStats })),
        api.get('/alerts', { params: { limit: 10 } }).catch(() => ({ data: [] })),
        api.get('/agent/executions', { params: { limit: 8 } }).catch(() => ({ data: [] })),
      ])

      const stats = { ...emptyStats, ...(statsRes.data || {}) }
      const alerts = Array.isArray(alertsRes.data) ? alertsRes.data : []
      const runs = Array.isArray(runsRes.data) ? runsRes.data : []
      const resources = statusRes.data?.cpu ? statusRes.data : emptyResources
      const sla =
        stats.total_executions > 0
          ? Math.round((stats.success_executions / stats.total_executions) * 100)
          : 100
      const risk = alerts.filter((a: { status?: string }) => a.status === 'firing').length

      return {
        health_score: Math.max(40, sla - risk * 8),
        sla_percent: sla,
        risk_count: risk,
        executions_24h: stats.total_executions || 0,
        repair_count: 0,
        time_saved_hours: Number((((stats.success_executions || 0) * 0.25)).toFixed(1)),
        health: healthRes,
        resources,
        stats,
        trend: [],
        incidents: alerts,
        recent_runs: runs,
      }
    }

    async function load() {
      setLoading(true)
      setError('')
      try {
        const r = await api.get('/overview')
        if (!cancelled) {
          setData(r.data)
          setError('')
        }
        // #region agent log
        fetch('http://127.0.0.1:7421/ingest/ef51d3f6-500c-4df2-9cf3-d971502cfbd2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'c5f825'},body:JSON.stringify({sessionId:'c5f825',runId:'v32-debug',hypothesisId:'H3',location:'Overview.tsx:load',message:'overview primary ok',data:{hasData:!!r.data,score:r.data?.health_score},timestamp:Date.now()})}).catch(()=>{});
        // #endregion
      } catch {
        try {
          const fallback = await loadFallback()
          if (!cancelled) {
            setData(fallback)
            setError('')
          }
          // #region agent log
          fetch('http://127.0.0.1:7421/ingest/ef51d3f6-500c-4df2-9cf3-d971502cfbd2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'c5f825'},body:JSON.stringify({sessionId:'c5f825',runId:'v32-debug',hypothesisId:'H3',location:'Overview.tsx:load',message:'overview fallback',data:{hasData:!!fallback,score:fallback?.health_score},timestamp:Date.now()})}).catch(()=>{});
          // #endregion
        } catch {
          if (!cancelled) {
            setData(null)
            setError(t('overview.loadError'))
          }
          // #region agent log
          fetch('http://127.0.0.1:7421/ingest/ef51d3f6-500c-4df2-9cf3-d971502cfbd2',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'c5f825'},body:JSON.stringify({sessionId:'c5f825',runId:'v32-debug',hypothesisId:'H3',location:'Overview.tsx:load',message:'overview failed',data:{ok:false},timestamp:Date.now()})}).catch(()=>{});
          // #endregion
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
    // reloadKey 触发重试；不把 t 放进依赖，避免切语言/主题时误取消请求
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey])

  if (loading && !data) {
    return <div className="text-sm text-ink-muted anim-rise">{t('overview.loading')}</div>
  }
  if (error && !data) {
    return (
      <EmptyState
        title={t('overview.loadFail')}
        description={error}
        action={
          <button type="button" className="btn-primary" onClick={() => setReloadKey((k) => k + 1)}>
            {t('overview.retry')}
          </button>
        }
      />
    )
  }
  if (!data) return null

  const health = data.health
  const serverStatus = data.resources
  const stats = data.stats
  const kpis = [
    { label: t('overview.risk'), value: data.risk_count, to: '/incidents' },
    { label: t('overview.executions'), value: data.executions_24h, to: '/traces' },
    { label: t('overview.repairs'), value: data.repair_count, to: '/incidents' },
    { label: t('overview.timeSaved'), value: data.time_saved_hours, to: '/traces' },
  ]

  return (
    <div className="overview-ambient space-y-6">
      <div className="anim-rise-scale">
        <PageHeader
          title={t('overview.title')}
          subtitle={t('overview.subtitle')}
          actions={
            <button className="btn-primary" onClick={() => navigate('/ops')}>
              {t('overview.askAgent')}
            </button>
          }
        />
        <div className="shimmer-line mt-1" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-6 gap-4 stagger">
        <div className="card lg:col-span-2">
          <HealthRing value={data.health_score} label={t('overview.healthScore')} hint={t('overview.healthHint')} />
        </div>
        {kpis.map((kpi) => (
          <button
            key={kpi.label}
            className="card card-lift text-left"
            onClick={() => navigate(kpi.to)}
          >
            <p className="section-label">{kpi.label}</p>
            <KpiValue value={Number(kpi.value)} />
          </button>
        ))}
      </div>

      <div className="anim-rise" style={{ animationDelay: '180ms' }}>
        <h3 className="section-label mb-3">{t('overview.healthStatus')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger">
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.api')}</p>
            <StatusBadge status={health.services?.api || 'unknown'} pulse />
            <p className="text-xs text-ink-muted mt-2">v{health.version}</p>
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.database')}</p>
            <StatusBadge status={health.services?.database || 'unknown'} />
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.llm')}</p>
            <StatusBadge status={health.services?.llm || 'unknown'} />
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.sla')}</p>
            <p className="text-2xl font-semibold kpi-value">{data.sla_percent}%</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 card anim-rise-scale" style={{ animationDelay: '220ms' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="section-label">{t('overview.trend')}</h3>
            <span className="text-xs text-ink-muted">{t('overview.trendLegend')}</span>
          </div>
          {data.trend?.length ? (
            <div className="h-48 chart-fade">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.trend}>
                  <XAxis dataKey="day" tick={{ fill: chartColors.tick, fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: chartColors.tick, fontSize: 11 }} axisLine={false} tickLine={false} width={28} />
                  <Tooltip
                    contentStyle={{
                      background: chartColors.bg,
                      border: `1px solid ${chartColors.line}`,
                      fontSize: 12,
                      color: chartColors.tick,
                    }}
                  />
                  <Area type="monotone" dataKey="success" stroke="#22C55E" fill="#22C55E22" />
                  <Area type="monotone" dataKey="failed" stroke="#EF4444" fill="#EF444422" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-sm text-ink-muted py-8 text-center">{t('overview.trendEmpty')}</p>
          )}
        </div>
        <div className="card anim-rise-scale" style={{ animationDelay: '280ms' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="section-label">{t('overview.openIncidents')}</h3>
            <button className="btn-ghost text-xs" onClick={() => navigate('/incidents')}>
              {t('overview.all')} <ArrowUpRight size={12} className="inline" />
            </button>
          </div>
          {data.incidents?.length ? (
            <div className="row-rise">
              {data.incidents.slice(0, 5).map((inc) => (
                <div
                  key={inc.id}
                  className="flex items-start justify-between gap-2 py-2 border-b border-line last:border-0 transition-colors hover:bg-surface-2/60 rounded-md px-1"
                >
                  <div>
                    <p className="text-sm text-ink">{inc.title}</p>
                    <p className="text-[11px] text-ink-muted">{inc.level}</p>
                  </div>
                  <StatusBadge status={inc.status} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-ink-muted">{t('overview.noIncidents')}</p>
          )}
        </div>
      </div>

      <div className="anim-rise" style={{ animationDelay: '300ms' }}>
        <h3 className="section-label mb-3">{t('overview.hostStatus')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 stagger">
          <ServerCard
            title={t('overview.cpu')}
            percent={serverStatus?.cpu?.percent || 0}
            total={`${serverStatus?.cpu?.cores || 0} ${t('overview.cores')}`}
          />
          <ServerCard
            title={t('overview.memory')}
            percent={serverStatus?.memory?.percent || 0}
            used={`${serverStatus?.memory?.used_gb?.toFixed?.(1) || serverStatus?.memory?.used_gb || 0} GB`}
            total={`${serverStatus?.memory?.total_gb?.toFixed?.(1) || serverStatus?.memory?.total_gb || 0} GB`}
            color="#3b82f6"
          />
          <ServerCard
            title={t('overview.disk')}
            percent={serverStatus?.disks?.[0]?.percent || 0}
            used={`${serverStatus?.disks?.[0]?.used_gb?.toFixed?.(1) || serverStatus?.disks?.[0]?.used_gb || 0} GB`}
            total={`${serverStatus?.disks?.[0]?.total_gb?.toFixed?.(1) || serverStatus?.disks?.[0]?.total_gb || 0} GB`}
            color="#22c55e"
          />
        </div>
      </div>

      <div className="anim-rise" style={{ animationDelay: '340ms' }}>
        <h3 className="section-label mb-3">{t('overview.agentStats')}</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 stagger">
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.conversations')}</p>
            <p className="text-2xl font-bold kpi-value">{stats?.total_conversations ?? 0}</p>
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.messages')}</p>
            <p className="text-2xl font-bold kpi-value">{stats?.total_messages ?? 0}</p>
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.servers')}</p>
            <p className="text-2xl font-bold kpi-value">{stats?.total_servers ?? 0}</p>
          </div>
          <div className="card-hover">
            <p className="text-xs text-ink-muted mb-1">{t('overview.tools')}</p>
            <p className="text-2xl font-bold kpi-value">{stats?.tools_available ?? 0}</p>
          </div>
        </div>
      </div>

      <div className="card anim-rise-scale" style={{ animationDelay: '380ms' }}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="section-label">{t('overview.recentRuns')}</h3>
          <button className="btn-ghost text-xs" onClick={() => navigate('/traces')}>
            {t('overview.traceCenter')}
          </button>
        </div>
        {data.recent_runs?.length ? (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-ink-muted text-left border-b border-line">
                <th className="py-2 font-medium">{t('overview.colId')}</th>
                <th className="py-2 font-medium">{t('overview.colStatus')}</th>
                <th className="py-2 font-medium">{t('overview.colDuration')}</th>
                <th className="py-2 font-medium">{t('overview.colTools')}</th>
              </tr>
            </thead>
            <tbody className="row-rise">
              {data.recent_runs.map((run) => (
                <tr key={run.id} className="border-b border-line/60 hover:bg-surface-2/50 transition-colors">
                  <td className="py-2 font-mono text-xs">#{run.id}</td>
                  <td className="py-2">
                    <StatusBadge status={run.status} />
                  </td>
                  <td className="py-2 text-ink-muted">{run.duration}s</td>
                  <td className="py-2 text-ink-muted">{run.tools_called}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="text-sm text-ink-muted">{t('overview.noRuns')}</p>
        )}
      </div>
    </div>
  )
}
