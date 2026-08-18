import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  AlertTriangle,
  Server,
  BookOpen,
  GitBranch,
  Activity,
  LogOut,
} from 'lucide-react'
import { useAuth } from '../store/auth'
import { usePrefs } from '../store/prefs'
import type { MessageKey } from '../i18n'

const groups: { label: MessageKey; items: { to: string; label: MessageKey; icon: typeof LayoutDashboard }[] }[] = [
  {
    label: 'nav.operate',
    items: [
      { to: '/overview', label: 'nav.overview', icon: LayoutDashboard },
      { to: '/ops', label: 'nav.copilot', icon: MessageSquare },
      { to: '/incidents', label: 'nav.incidents', icon: AlertTriangle },
    ],
  },
  {
    label: 'nav.platform',
    items: [
      { to: '/infra', label: 'nav.infra', icon: Server },
      { to: '/knowledge', label: 'nav.knowledge', icon: BookOpen },
    ],
  },
  {
    label: 'nav.observe',
    items: [
      { to: '/traces', label: 'nav.traces', icon: GitBranch },
      { to: '/monitor', label: 'nav.monitor', icon: Activity },
    ],
  },
]

export default function Sidebar() {
  const { user, logout } = useAuth()
  const { t } = usePrefs()

  return (
    <aside className="shell-surface w-60 border-r flex flex-col h-full shrink-0">
      <div className="px-4 py-4 border-b border-line anim-rise">
        <p className="text-[11px] uppercase tracking-[0.14em] text-ink-muted">{t('brand.kicker')}</p>
        <h1 className="text-sm font-semibold text-ink mt-0.5">{t('brand.name')}</h1>
        <p className="text-[11px] text-ink-muted mt-0.5">{t('brand.version')}</p>
      </div>

      <nav className="flex-1 py-3 overflow-y-auto">
        {groups.map((group) => (
          <div key={group.label} className="mb-4 stagger-nav">
            <p className="px-4 mb-1 text-[11px] uppercase tracking-wider text-ink-muted">{t(group.label)}</p>
            {group.items.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2.5 mx-2 px-2.5 py-2 text-sm rounded-lg transition-all duration-200 ${
                      isActive
                        ? 'bg-primary-500/10 text-primary-700 font-medium shadow-[inset_2px_0_0_0_rgb(var(--primary))]'
                        : 'text-ink-muted hover:text-ink hover:bg-surface-2 hover:translate-x-0.5'
                    }`
                  }
                >
                  <Icon size={16} strokeWidth={1.75} />
                  {t(item.label)}
                </NavLink>
              )
            })}
          </div>
        ))}
      </nav>

      <div className="p-3 border-t border-line">
        <div className="flex items-center gap-2.5">
          <div className="user-avatar">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-ink truncate">{user?.username || t('nav.guest')}</p>
            <p className="text-[11px] text-ink-muted">{user?.role || '-'}</p>
          </div>
          <button onClick={logout} className="btn-ghost p-1.5" title={t('nav.logout')}>
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  )
}
