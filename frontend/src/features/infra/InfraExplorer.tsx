import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Servers from '../../pages/Servers'
import Kubernetes from '../../pages/Kubernetes'
import EmptyState from '../../ui/EmptyState'
import PageHeader from '../../ui/PageHeader'
import { usePrefs } from '../../store/prefs'

const tabs = [
  { id: 'hosts', label: 'Hosts' },
  { id: 'docker', label: 'Docker' },
  { id: 'kubernetes', label: 'Kubernetes' },
] as const

export default function InfraExplorer() {
  const { t } = usePrefs()
  const [tab, setTab] = useState<(typeof tabs)[number]['id']>('hosts')
  const navigate = useNavigate()

  return (
    <div>
      <PageHeader title={t('header.infra')} subtitle={t('header.infraSub')} />
      <div className="flex gap-1 mb-5 border-b border-line">
        {tabs.map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id)}
            className={`px-4 py-2 text-sm -mb-px border-b-2 ${
              tab === item.id ? 'border-primary-500 text-ink' : 'border-transparent text-ink-muted hover:text-ink'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>
      {tab === 'hosts' && <Servers />}
      {tab === 'docker' && (
        <EmptyState
          title="Docker 尚未接入独立 API"
          description="可在 Copilot 中让 Agent 检查容器状态。"
          action={
            <button className="btn-primary" onClick={() => navigate('/ops?q=检查 Docker 容器状态')}>
              让 Agent 检查容器
            </button>
          }
        />
      )}
      {tab === 'kubernetes' && <Kubernetes />}
    </div>
  )
}
