import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import api from '../api/client'
import { usePrefs } from '../store/prefs'
import PrefsToggles from '../ui/PrefsToggles'
import type { MessageKey } from '../i18n'

const pageKeys: Record<string, { title: MessageKey; subtitle?: MessageKey }> = {
  '/overview': { title: 'header.overview', subtitle: 'header.overviewSub' },
  '/ops': { title: 'header.ops', subtitle: 'header.opsSub' },
  '/infra': { title: 'header.infra', subtitle: 'header.infraSub' },
  '/incidents': { title: 'header.incidents', subtitle: 'header.incidentsSub' },
  '/knowledge': { title: 'header.knowledge', subtitle: 'header.knowledgeSub' },
  '/traces': { title: 'header.traces', subtitle: 'header.tracesSub' },
  '/monitor': { title: 'header.monitor', subtitle: 'header.monitorSub' },
  '/dashboard': { title: 'header.overview', subtitle: 'header.overviewSub' },
  '/chat': { title: 'header.ops' },
  '/servers': { title: 'header.infra' },
  '/kubernetes': { title: 'header.infra' },
  '/monitoring': { title: 'header.monitor' },
  '/trace': { title: 'header.traces' },
}

export default function Header() {
  const location = useLocation()
  const navigate = useNavigate()
  const { t } = usePrefs()
  const keys = pageKeys[location.pathname]
  const [env, setEnv] = useState('development')
  const [openIncidents, setOpenIncidents] = useState(0)

  useEffect(() => {
    fetch('/health')
      .then((r) => r.json())
      .then((d) => setEnv(d.environment || 'development'))
      .catch(() => {})
    api
      .get('/alerts', { params: { limit: 50 } })
      .then((r) => {
        const list = Array.isArray(r.data) ? r.data : []
        setOpenIncidents(list.filter((a: { status?: string }) => a.status === 'firing').length)
      })
      .catch(() => {})
  }, [location.pathname])

  const hideChrome = location.pathname === '/ops' || location.pathname === '/chat'

  if (hideChrome) return null

  return (
    <header className="shell-surface h-14 border-b flex items-center justify-between px-5 shrink-0 anim-rise">
      <div className="anim-rise" style={{ animationDelay: '60ms' }}>
        <h2 className="text-sm font-semibold text-ink">{keys ? t(keys.title) : t('header.fallback')}</h2>
        {keys?.subtitle && <p className="text-[11px] text-ink-muted">{t(keys.subtitle)}</p>}
      </div>
      <div className="flex items-center gap-3 anim-rise" style={{ animationDelay: '120ms' }}>
        <PrefsToggles />
        <span className="badge-info">{env}</span>
        <button
          className="relative btn-ghost"
          onClick={() => navigate('/incidents')}
          title={t('header.incidentsHint')}
        >
          <Bell size={16} />
          {openIncidents > 0 && (
            <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-danger text-[10px] text-white flex items-center justify-center">
              {openIncidents}
            </span>
          )}
        </button>
      </div>
    </header>
  )
}
