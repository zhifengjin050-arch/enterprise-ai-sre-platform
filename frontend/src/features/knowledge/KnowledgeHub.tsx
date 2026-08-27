import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import PageHeader from '../../ui/PageHeader'
import EmptyState from '../../ui/EmptyState'
import StatusBadge from '../../ui/StatusBadge'

/* ── Types ── */
interface KnowledgeSource {
  id: number
  organization_id: number
  type: string
  name: string
  status: string
  last_sync_at: string | null
  last_error: string | null
  created_at: string | null
  upcoming: boolean
}
interface SyncTaskItem {
  id: number
  source_id: number
  trigger: string
  status: string
  stats: Record<string, number>
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}
interface SyncLogItem {
  id: number
  level: string
  external_id: string | null
  message: string
  created_at: string | null
}
interface KnowledgeDoc {
  id: number
  title: string
  source: string
  content_preview: string
  created_at: string
}
interface SearchResult {
  content: string
  score: number
  title?: string
  source?: string
}

const TYPE_LABELS: Record<string, string> = {
  feishu: '飞书 Wiki',
  yuque: '语雀知识库',
  gitlab: 'GitLab Wiki',
  confluence: 'Confluence',
}

const TYPE_ICONS: Record<string, string> = {
  feishu: '🌐',
  yuque: '📖',
  gitlab: '🦊',
  confluence: '📄',
}

/* ── Tabs ── */
type Tab = 'sources' | 'manual' | 'tasks' | 'search'

export default function KnowledgeHub() {
  const navigate = useNavigate()
  const { t } = usePrefs()
  const [tab, setTab] = useState<Tab>('sources')

  /* Sources */
  const [sources, setSources] = useState<KnowledgeSource[]>([])
  const [showForm, setShowForm] = useState(false)
  const [formType, setFormType] = useState('feishu')
  const [formName, setFormName] = useState('')
  const [formAppId, setFormAppId] = useState('')
  const [formAppSecret, setFormAppSecret] = useState('')
  const [formSpaceId, setFormSpaceId] = useState('')
  const [formErr, setFormErr] = useState('')

  /* Tasks */
  const [tasks, setTasks] = useState<SyncTaskItem[]>([])
  const [taskFilter, setTaskFilter] = useState<number | ''>('')
  const [logs, setLogs] = useState<SyncLogItem[]>([])
  const [logsTaskId, setLogsTaskId] = useState<number | null>(null)

  /* Manual upload */
  const [docs, setDocs] = useState<KnowledgeDoc[]>([])
  const [selected, setSelected] = useState<KnowledgeDoc | null>(null)
  const [uploadTitle, setUploadTitle] = useState('')
  const [uploadContent, setUploadContent] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')

  /* Search */
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [err, setErr] = useState('')

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  /* ── Data Loaders ── */
  const loadSources = async () => {
    try {
      const { data } = await api.get('/knowledge/sources')
      setSources(Array.isArray(data) ? data : [])
    } catch { /* ignore */ }
  }
  const loadTasks = async () => {
    try {
      const params = taskFilter ? { source_id: taskFilter } : {}
      const { data } = await api.get('/knowledge/sync/tasks', { params })
      setTasks(Array.isArray(data) ? data : [])
    } catch { /* ignore */ }
  }
  const loadDocs = async () => {
    try {
      const { data } = await api.get('/knowledge')
      setDocs(Array.isArray(data) ? data : [])
    } catch { /* ignore */ }
  }

  useEffect(() => {
    loadSources()
    loadTasks()
    loadDocs()
  }, [])

  useEffect(() => {
    if (tab === 'tasks') loadTasks()
  }, [taskFilter, tab])

  /* ── Source CRUD ── */
  const handleCreateSource = async () => {
    setFormErr('')
    if (!formName.trim()) setFormErr('请输入知识源名称'); return
    try {
      await api.post('/knowledge/sources', {
        type: formType,
        name: formName,
        app_id: formAppId,
        app_secret: formAppSecret,
        space_id: formSpaceId,
      })
      setShowForm(false)
      setFormName('')
      setFormAppId('')
      setFormAppSecret('')
      setFormSpaceId('')
      loadSources()
    } catch (e: any) {
      setFormErr(e?.response?.data?.detail || '创建失败')
    }
  }

  const handleDeleteSource = async (id: number) => {
    if (!confirm('确认删除该知识源？关联文档将停用。')) return
    try {
      await api.delete(`/knowledge/sources/${id}`)
      loadSources()
      loadDocs()
    } catch { setErr('删除失败') }
  }

  const handleTestSource = async (id: number) => {
    try {
      const { data } = await api.post(`/knowledge/sources/${id}/test`)
      setErr(`连接测试：${data.ok ? '✅ ' + data.message : '❌ ' + data.message}`)
      loadSources()
    } catch (e: any) {
      setErr('测试失败：' + (e?.response?.data?.detail || ''))
    }
  }

  const handleSyncSource = async (id: number) => {
    try {
      await api.post(`/knowledge/sources/${id}/sync`)
      setErr('同步任务已排队')
      loadTasks()
      // 轮询任务状态 30s
      if (pollRef.current) clearInterval(pollRef.current)
      pollRef.current = setInterval(() => {
        loadTasks()
      }, 3000)
      setTimeout(() => {
        if (pollRef.current) clearInterval(pollRef.current); pollRef.current = null
      }, 30000)
    } catch (e: any) {
      setErr('触发同步失败：' + (e?.response?.data?.detail || ''))
    }
  }

  const loadLogs = async (taskId: number) => {
    try {
      const { data } = await api.get(`/knowledge/sync/tasks/${taskId}/logs`)
      setLogs(Array.isArray(data) ? data : [])
      setLogsTaskId(taskId)
    } catch { setLogs([]) }
  }

  /* ── Manual upload ── */
  const handleUpload = async () => {
    if (!uploadTitle.trim() || !uploadContent.trim()) return
    setUploading(true)
    setErr('')
    try {
      await api.post('/knowledge/upload', { title: uploadTitle, content: uploadContent })
      setUploadMsg(`已索引：${uploadTitle}`)
      setUploadTitle('')
      setUploadContent('')
      loadDocs()
    } catch { setErr('上传失败') }
    setUploading(false)
  }

  const handleDeleteDoc = async (id: number) => {
    try {
      await api.delete(`/knowledge/${id}`)
      if (selected?.id === id) setSelected(null)
      loadDocs()
    } catch { setErr('删除失败') }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    try {
      const { data } = await api.post('/knowledge/search', { query: searchQuery })
      setSearchResults(Array.isArray(data) ? data : [])
    } catch { setErr('搜索失败') }
  }

  /* ── Render ── */
  return (
    <div>
      <PageHeader title={t('header.knowledge')} subtitle={t('header.knowledgeSub')} />
      {err && <p className="text-sm text-danger mb-3">{err}</p>}
      {uploadMsg && <p className="text-sm text-success mb-3">{uploadMsg}</p>}

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-line pb-1">
        {(['sources', 'tasks', 'manual', 'search'] as Tab[]).map((k) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-2 text-sm rounded-t-md transition ${
              tab === k ? 'bg-primary-500/10 text-primary-700 font-medium border-b-2 border-primary-500' : 'text-ink-muted hover:text-ink'
            }`}
          >
            {k === 'sources' && '数据源'}
            {k === 'tasks' && '同步任务'}
            {k === 'manual' && '本地上传'}
            {k === 'search' && '检索测试'}
          </button>
        ))}
      </div>

      {/* ─── Tab: Sources ─── */}
      {tab === 'sources' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <p className="text-sm text-ink-muted">已连接 {sources.filter(s => s.status === 'connected').length} 个知识源</p>
            <button className="btn-primary text-xs" onClick={() => setShowForm(!showForm)}>
              {showForm ? '取消' : '+ 添加知识源'}
            </button>
          </div>

          {showForm && (
            <div className="card p-4 space-y-3">
              <div className="flex gap-4">
                <select className="input-field flex-1" value={formType} onChange={(e) => setFormType(e.target.value)}>
                  <option value="feishu">飞书 Wiki</option>
                  <option value="yuque">语雀知识库（即将推出）</option>
                  <option value="gitlab">GitLab Wiki（即将推出）</option>
                  <option value="confluence">Confluence（即将推出）</option>
                </select>
                <input className="input-field flex-[2]" placeholder="知识源名称（如：运维 SOP）" value={formName} onChange={(e) => setFormName(e.target.value)} />
              </div>
              {(formType === 'feishu') && (
                <>
                  <input className="input-field" placeholder="飞书 App ID" value={formAppId} onChange={(e) => setFormAppId(e.target.value)} />
                  <input className="input-field" type="password" placeholder="App Secret" value={formAppSecret} onChange={(e) => setFormAppSecret(e.target.value)} />
                  <input className="input-field" placeholder="Wiki Space ID" value={formSpaceId} onChange={(e) => setFormSpaceId(e.target.value)} />
                </>
              )}
              {formErr && <p className="text-xs text-danger">{formErr}</p>}
              <button className="btn-primary text-xs" onClick={handleCreateSource}>创建并连接</button>
            </div>
          )}

          {sources.length === 0 && !showForm && <EmptyState title="暂无知识源" description="添加飞书 Wiki 等企业知识源到统一检索面" />}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sources.map((s) => (
              <div key={s.id} className="card p-4 space-y-2">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{TYPE_ICONS[s.type] || '📁'}</span>
                    <div>
                      <p className="text-sm font-medium">{s.name}</p>
                      <p className="text-xs text-ink-muted">{TYPE_LABELS[s.type] || s.type}</p>
                    </div>
                  </div>
                  <StatusBadge status={s.status} text={s.status === 'connected' ? '已连接' : s.status === 'syncing' ? '同步中' : s.status === 'error' ? '错误' : '未连接'} />
                </div>
                {s.last_sync_at && <p className="text-xs text-ink-muted">上次同步：{new Date(s.last_sync_at).toLocaleString()}</p>}
                {s.last_error && <p className="text-xs text-danger">{s.last_error.slice(0, 200)}</p>}
                {s.upcoming && <p className="text-xs text-warning">该类型知识源即将推出</p>}
                <div className="flex gap-2 pt-1">
                  {!s.upcoming && (
                    <>
                      <button className="btn-ghost text-xs" onClick={() => handleTestSource(s.id)}>测试连接</button>
                      <button className="btn-secondary text-xs" onClick={() => handleSyncSource(s.id)}>同步</button>
                    </>
                  )}
                  <button className="btn-danger text-xs ml-auto" onClick={() => handleDeleteSource(s.id)}>删除</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Tab: Tasks ─── */}
      {tab === 'tasks' && (
        <div className="space-y-4">
          <div className="flex gap-3 items-center">
            <p className="text-sm text-ink-muted">最近 50 条同步任务</p>
            <select className="input-field text-xs w-48" value={taskFilter} onChange={(e) => setTaskFilter(e.target.value ? Number(e.target.value) : '')}>
              <option value="">全部知识源</option>
              {sources.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
            <button className="btn-ghost text-xs" onClick={loadTasks}>刷新</button>
          </div>

          {tasks.length === 0 && <EmptyState title="暂无同步任务" description="添加知识源后触发同步" />}
          <div className="space-y-2">
            {tasks.map((t) => (
              <div key={t.id} className="card p-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={t.status} text={t.status === 'success' ? '成功' : t.status === 'running' ? '运行中' : t.status === 'failed' ? '失败' : '排队中'} />
                    <p className="text-xs text-ink-muted">
                      {sources.find(s => s.id === t.source_id)?.name || `源 #${t.source_id}`}
                      <span className="ml-2">{t.trigger === 'cron' ? '定时' : '手动'}</span>
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button className="btn-ghost text-xs" onClick={() => loadLogs(t.id)}>
                      {logsTaskId === t.id ? '收起日志' : '查看日志'}
                    </button>
                  </div>
                </div>
                {t.stats && Object.keys(t.stats).length > 0 && (
                  <div className="flex gap-3 text-xs text-ink-muted mt-1">
                    <span>获取 {t.stats.fetched ?? 0}</span>
                    <span>索引 {t.stats.upserted ?? 0}</span>
                    <span>跳过 {t.stats.skipped ?? 0}</span>
                    <span>删除 {t.stats.deleted ?? 0}</span>
                    <span>失败 {t.stats.failed ?? 0}</span>
                  </div>
                )}
                {t.started_at && (
                  <p className="text-xs text-ink-muted mt-1">
                    {new Date(t.started_at).toLocaleString()} → {t.finished_at ? new Date(t.finished_at).toLocaleString() : '进行中'}
                  </p>
                )}

                {logsTaskId === t.id && (
                  <div className="mt-2 bg-surface-2 rounded p-2 max-h-48 overflow-y-auto space-y-1">
                    {logs.length === 0 && <p className="text-xs text-ink-muted">暂无日志</p>}
                    {logs.map((l) => (
                      <p key={l.id} className={`text-xs ${l.level === 'warning' ? 'text-warning' : l.level === 'error' ? 'text-danger' : 'text-ink-muted'}`}>
                        <span className="text-ink-muted">[{l.external_id || '-'}]</span> {l.message}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Tab: Manual Upload ─── */}
      {tab === 'manual' && (
        <div className="flex gap-3 min-h-[28rem]">
          {/* 文档列表 */}
          <div className="card p-0 overflow-hidden shrink-0" style={{ width: 260 }}>
            <div className="px-4 py-3 border-b border-line text-xs text-ink-muted">本地上传文档</div>
            <div className="max-h-[32rem] overflow-y-auto">
              {docs.length === 0 && <EmptyState title="知识库为空" description="上传运维文档以构建知识库" />}
              {docs.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelected(doc)}
                  className={`w-full text-left px-4 py-3 border-b border-line/50 ${
                    selected?.id === doc.id ? 'bg-primary-500/10' : 'hover:bg-surface-2'
                  }`}
                >
                  <p className="text-sm">{doc.title}</p>
                  <p className="text-[11px] text-ink-muted">{doc.source}</p>
                </button>
              ))}
            </div>
          </div>

          {/* 预览 / 上传 */}
          <div className="flex-1 card overflow-y-auto max-h-[36rem] min-w-[16rem] p-4">
            {selected ? (
              <div>
                <div className="flex justify-between mb-3">
                  <h3 className="text-sm font-medium">{selected.title}</h3>
                  <button className="btn-danger text-xs" onClick={() => handleDeleteDoc(selected.id)}>删除</button>
                </div>
                <div className="md-body text-sm text-ink-muted max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{selected.content_preview}</ReactMarkdown>
                </div>
                <button
                  className="btn-secondary mt-4 text-xs"
                  onClick={() => navigate(`/ops?q=${encodeURIComponent('根据知识库解释：' + selected.title)}`)}
                >
                  在 Copilot 中提问
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                <input className="input-field" placeholder="文档标题" value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} />
                <textarea
                  className="input-field font-mono min-h-[10rem]"
                  placeholder="粘贴 Markdown / 纯文本"
                  value={uploadContent}
                  onChange={(e) => setUploadContent(e.target.value)}
                />
                <button className="btn-primary" disabled={uploading || !uploadTitle.trim() || !uploadContent.trim()} onClick={handleUpload}>
                  {uploading ? '索引中...' : '上传并索引'}
                </button>
              </div>
            )}
          </div>

          {/* 检索侧栏 */}
          <div className="card shrink-0" style={{ width: 300 }}>
            <p className="section-label p-4 pb-0">检索测试</p>
            <div className="p-4 space-y-3">
              <div className="flex gap-2">
                <input className="input-field" placeholder="搜索知识库..." value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()} />
                <button className="btn-primary" onClick={handleSearch}>搜索</button>
              </div>
              <div className="space-y-2 max-h-[28rem] overflow-y-auto">
                {searchResults.map((r, i) => (
                  <div key={i} className="border border-line rounded-lg p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <StatusBadge status={''} text={`${(r.score * 100).toFixed(1)}%`} />
                      {r.source && <span className="text-xs text-ink-muted">{r.source === 'feishu' ? '飞书' : '本地上传'}</span>}
                    </div>
                    {r.title && <p className="text-xs font-medium mb-1">{r.title}</p>}
                    <p className="text-xs text-ink-muted whitespace-pre-wrap">{r.content}</p>
                    <button className="btn-ghost text-xs mt-2" onClick={() => navigate(`/ops?q=${encodeURIComponent(r.content.slice(0, 120))}`)}>
                      引用到 Copilot
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ─── Tab: Search ─── */}
      {tab === 'search' && (
        <div className="card p-4 max-w-2xl">
          <p className="section-label mb-3">全库检索（本地上传 + 企业知识源）</p>
          <div className="flex gap-2 mb-4">
            <input className="input-field flex-1" placeholder="搜索所有知识库..." value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleSearch()} />
            <button className="btn-primary" onClick={handleSearch}>搜索</button>
          </div>
          <div className="space-y-3">
            {searchResults.map((r, i) => (
              <div key={i} className="border border-line rounded-lg p-3">
                <div className="flex items-center gap-2 mb-1">
                  <StatusBadge status={''} text={`${(r.score * 100).toFixed(1)}%`} />
                  {r.source && <span className="text-xs">{r.source === 'feishu' ? '🌐 飞书' : '📁 本地上传'}</span>}
                </div>
                {r.title && <p className="text-xs font-medium mb-1">{r.title}</p>}
                <p className="text-xs text-ink-muted whitespace-pre-wrap">{r.content}</p>
                <button className="btn-ghost text-xs mt-2" onClick={() => navigate(`/ops?q=${encodeURIComponent(r.content.slice(0, 120))}`)}>
                  引用到 Copilot
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}