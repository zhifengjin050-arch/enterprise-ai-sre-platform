import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import api from '../../api/client'
import { usePrefs } from '../../store/prefs'
import PageHeader from '../../ui/PageHeader'
import EmptyState from '../../ui/EmptyState'
import ResizeHandle from '../../ui/ResizeHandle'
import { usePanelWidth } from '../../ui/usePanelWidth'

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
  metadata: Record<string, unknown>
}

export default function KnowledgeCenter() {
  const navigate = useNavigate()
  const { t } = usePrefs()
  const left = usePanelWidth('sre-kb-left', 280, 180, 560)
  const right = usePanelWidth('sre-kb-right', 320, 220, 640)
  const [docs, setDocs] = useState<KnowledgeDoc[]>([])
  const [selected, setSelected] = useState<KnowledgeDoc | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [uploading, setUploading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [error, setError] = useState('')
  const [indexed, setIndexed] = useState('')

  const loadDocs = async () => {
    try {
      const { data } = await api.get('/knowledge')
      setDocs(Array.isArray(data) ? data : [])
    } catch {
      setError('加载知识库失败')
    }
  }

  useEffect(() => {
    loadDocs()
  }, [])

  const handleUpload = async () => {
    if (!title.trim() || !content.trim()) return
    setUploading(true)
    setError('')
    try {
      await api.post('/knowledge/upload', { title, content })
      setIndexed(`已索引：${title}`)
      setTitle('')
      setContent('')
      loadDocs()
    } catch {
      setError('上传失败')
    }
    setUploading(false)
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    try {
      const { data } = await api.post('/knowledge/search', { query: searchQuery })
      setSearchResults(Array.isArray(data) ? data : [])
    } catch {
      setError('搜索失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await api.delete(`/knowledge/${id}`)
      if (selected?.id === id) setSelected(null)
      loadDocs()
    } catch {
      setError('删除失败')
    }
  }

  return (
    <div>
      <PageHeader title={t('header.knowledge')} subtitle={t('header.knowledgeSub')} />
      {error && <p className="text-sm text-danger mb-3">{error}</p>}
      {indexed && <p className="text-sm text-success mb-3">{indexed}</p>}
      <div className="flex gap-3 min-h-[28rem]">
        <div className="relative card p-0 overflow-hidden shrink-0" style={{ width: left.width }}>
          <div className="px-4 py-3 border-b border-line text-xs text-ink-muted">文档列表</div>
          <div className="max-h-[32rem] overflow-y-auto">
            {docs.length === 0 && <EmptyState title="知识库为空" description="上传运维文档以构建企业知识库" />}
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
          <ResizeHandle edge="end" label={t('ops.resize')} onPointerDown={left.startDrag(false)} />
        </div>

        <div className="flex-1 card overflow-y-auto max-h-[36rem] min-w-[16rem]">
          <p className="section-label mb-3">预览 / 上传</p>
          {selected ? (
            <div>
              <div className="flex justify-between mb-3">
                <h3 className="text-sm font-medium">{selected.title}</h3>
                <button className="btn-danger text-xs" onClick={() => handleDelete(selected.id)}>删除</button>
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
              <input className="input-field" placeholder="文档标题" value={title} onChange={(e) => setTitle(e.target.value)} />
              <textarea
                className="input-field font-mono min-h-[10rem]"
                placeholder="粘贴 Markdown / 纯文本"
                value={content}
                onChange={(e) => setContent(e.target.value)}
              />
              <button className="btn-primary" disabled={uploading || !title.trim() || !content.trim()} onClick={handleUpload}>
                {uploading ? '索引中...' : '上传并索引'}
              </button>
            </div>
          )}
        </div>

        <div className="relative card shrink-0" style={{ width: right.width }}>
          <ResizeHandle edge="start" label={t('ops.resize')} onPointerDown={right.startDrag(true)} />
          <p className="section-label mb-3">检索测试</p>
          <div className="flex gap-2 mb-3">
            <input
              className="input-field"
              placeholder="搜索知识库..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            />
            <button className="btn-primary" onClick={handleSearch}>搜索</button>
          </div>
          <div className="space-y-3 max-h-[28rem] overflow-y-auto">
            {searchResults.map((r, i) => (
              <div key={i} className="border border-line rounded-lg p-3">
                <p className="text-xs text-success font-mono mb-1">{(r.score * 100).toFixed(1)}%</p>
                <p className="text-xs text-ink-muted whitespace-pre-wrap">{r.content}</p>
                <button
                  className="btn-ghost text-xs mt-2"
                  onClick={() => navigate(`/ops?q=${encodeURIComponent(r.content.slice(0, 120))}`)}
                >
                  引用到 Copilot
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
