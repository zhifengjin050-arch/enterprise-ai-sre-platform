import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import PageHeader from '../../ui/PageHeader'
import StatusBadge from '../../ui/StatusBadge'
import EmptyState from '../../ui/EmptyState'

interface MonitoringData {
  cpu: { percent: number; cores: number }
  memory: { percent: number; used_gb: number; total_gb: number }
  disks: { mount: string; percent: number }[]
}

interface AlertItem {
  id: number
  level: string
  title: string
  message: string
  status: string
  created_at?: string
}

function fill(template: string, vars: Record<string, string | number>) {
  return Object.entries(vars).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, String(v)), template)
}

function Bar({ label, percent }: { label: string; percent: number }) {
  const color = percent > 90 ? '#EF4444' : percent > 75 ? '#F59E0B' : '#22C55E'
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-ink-muted mb-1">
        <span>{label}</span>
        <span>{percent.toFixed(1)}%</span>
      </div>
      <div className="h-1.5 bg-surface-2 rounded-full">
        <div className="h-1.5 rounded-full" style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: color }} />
      </div>
    </div>
  )
}

export default function MonitorCenter() {
  const navigate = useNavigate()
  const { t, theme } = usePrefs()
  const [monitoring, setMonitoring] = useState<MonitoringData | null>(null)
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [metrics, setMetrics] = useState('')
  const [grafanaOk, setGrafanaOk] = useState<boolean | null>(null)
  const [error, setError] = useState('')

  const fetchData = useCallback(async () => {
    setError('')
    try {
      const [mon, al] = await Promise.all([
        api.get('/monitoring/current'),
        api.get('/alerts', { params: { limit: 20 } }),
      ])
      setMonitoring(mon.data)
      setAlerts(Array.isArray(al.data) ? al.data : [])
    } catch (e: any) {
      setError(e.response?.data?.detail || t('monitor.noData'))
    }
    fetch('/metrics')
      .then((r) => r.text())
      .then((txt) => setMetrics(txt.split('\n').filter((l) => l && !l.startsWith('#')).slice(0, 24).join('\n')))
      .catch(() => setMetrics(''))
    fetch('http://localhost:3000/api/health')
      .then((r) => setGrafanaOk(r.ok))
      .catch(() => setGrafanaOk(false))
  }, [t])

  useEffect(() => {
    fetchData()
    const timer = setInterval(fetchData, 30000)
    return () => clearInterval(timer)
  }, [fetchData])

  const grafanaSrc = `http://localhost:3000/?theme=${theme === 'day' ? 'light' : 'dark'}`
  const firing = alerts.filter((a) => a.status === 'firing').length

  return (
    <div className="space-y-5">
      <PageHeader
        title={t('monitor.title')}
        subtitle={t('monitor.subtitle')}
        actions={
          <button className="btn-secondary" onClick={fetchData}>
            {t('monitor.refresh')}
          </button>
        }
      />
      {error && <div className="text-sm text-danger">{error}</div>}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="card">
          <p className="section-label mb-3">{t('monitor.cpu')}</p>
          {monitoring && (
            <>
              <p className="text-2xl font-semibold mb-2">{monitoring.cpu.percent.toFixed(1)}%</p>
              <p className="text-xs text-ink-muted mb-3">{fill(t('monitor.cores'), { n: monitoring.cpu.cores })}</p>
              <Bar label={t('monitor.usage')} percent={monitoring.cpu.percent} />
            </>
          )}
        </div>
        <div className="card">
          <p className="section-label mb-3">{t('monitor.memory')}</p>
          {monitoring && (
            <>
              <p className="text-2xl font-semibold mb-2">{monitoring.memory.percent.toFixed(1)}%</p>
              <p className="text-xs text-ink-muted mb-3">
                {monitoring.memory.used_gb}G / {monitoring.memory.total_gb}G
              </p>
              <Bar label={t('monitor.usage')} percent={monitoring.memory.percent} />
            </>
          )}
        </div>
        <div className="card">
          <p className="section-label mb-3">{t('monitor.disk')}</p>
          {monitoring?.disks?.length ? (
            monitoring.disks.map((d) => <Bar key={d.mount} label={d.mount} percent={d.percent} />)
          ) : (
            <p className="text-sm text-ink-muted">{t('monitor.noData')}</p>
          )}
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <p className="section-label">{t('monitor.alerts')}</p>
          <StatusBadge
            status={firing ? 'warning' : 'success'}
            text={firing ? fill(t('monitor.firing'), { n: firing }) : t('monitor.allClear')}
          />
        </div>
        {alerts.length === 0 ? (
          <p className="text-sm text-ink-muted">{t('monitor.noAlerts')}</p>
        ) : (
          <div className="space-y-2">
            {alerts.slice(0, 10).map((alert) => (
              <div key={alert.id} className="flex items-center justify-between py-2 border-b border-line/50">
                <div>
                  <p className="text-sm">{alert.title}</p>
                  <p className="text-xs text-ink-muted">{alert.message?.slice(0, 100)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={alert.level} text={alert.level} />
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => navigate(`/ops?q=${encodeURIComponent('分析告警：' + alert.title)}`)}
                  >
                    {t('monitor.askAgent')}
                  </button>
                  <button className="btn-ghost text-xs" onClick={() => navigate('/incidents')}>
                    {t('monitor.incident')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-0 overflow-hidden min-h-[280px]">
          <div className="px-4 py-3 border-b border-line text-xs text-ink-muted">{t('monitor.grafana')}</div>
          {grafanaOk ? (
            <iframe title="Grafana" src={grafanaSrc} className="w-full h-72 border-0 bg-surface-2" />
          ) : (
            <div className="h-72 flex items-center theme-canvas">
              <EmptyState title={t('monitor.grafanaOff')} description={t('monitor.grafanaHint')} />
            </div>
          )}
        </div>
        <div className="card">
          <p className="section-label mb-3">{t('monitor.metrics')}</p>
          <pre className="code-block text-[11px] font-mono text-ink-muted max-h-72 overflow-auto">
            {metrics || t('monitor.metricsFail')}
          </pre>
        </div>
      </div>
    </div>
  )
}
