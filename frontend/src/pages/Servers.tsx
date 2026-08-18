import { useState, useEffect } from 'react'
import api from '../api/client'

interface Server {
  id: number
  name: string
  host: string
  port: number
  username: string
  auth_type: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function Servers() {
  const [servers, setServers] = useState<Server[]>([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [testingId, setTestingId] = useState<number | null>(null)
  const [testResult, setTestResult] = useState<{ [key: number]: string }>({})
  const [form, setForm] = useState({ name: '', host: '', port: 22, username: '', auth_type: 'password', auth_credential: '', description: '' })

  const loadServers = () => {
    setLoading(true)
    api.get('/servers').then(r => setServers(Array.isArray(r.data) ? r.data : [])).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { loadServers() }, [])

  const addServer = async () => {
    try {
      await api.post('/servers', form)
      setShowAdd(false)
      setForm({ name: '', host: '', port: 22, username: '', auth_type: 'password', auth_credential: '', description: '' })
      loadServers()
    } catch (err: any) {
      alert(err.response?.data?.detail || '添加失败')
    }
  }

  const deleteServer = async (id: number) => {
    if (!confirm('确定删除该服务器？')) return
    try {
      await api.delete(`/servers/${id}`)
      loadServers()
    } catch (err: any) {
      alert(err.response?.data?.detail || '删除失败')
    }
  }

  const testConnection = async (id: number) => {
    setTestingId(id)
    try {
      const res = await api.post(`/servers/${id}/test-connection`)
      setTestResult(prev => ({ ...prev, [id]: res.data.success ? '✅ 连接成功' : `❌ ${res.data.output?.substring(0, 100)}` }))
    } catch {
      setTestResult(prev => ({ ...prev, [id]: '❌ 测试失败' }))
    } finally {
      setTestingId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-sm text-ink-muted">共 {servers.length} 台服务器</p>
        <button className="btn-primary" onClick={() => setShowAdd(!showAdd)}>
          {showAdd ? '取消' : '+ 添加服务器'}
        </button>
      </div>

      {showAdd && (
        <div className="card">
          <h3 className="text-sm font-medium mb-4">新增服务器</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <input className="input-field" placeholder="名称（如 web-prod-01）" value={form.name} onChange={e => setForm({...form, name: e.target.value})} />
            <input className="input-field" placeholder="IP 或域名" value={form.host} onChange={e => setForm({...form, host: e.target.value})} />
            <input className="input-field" type="number" placeholder="SSH 端口" value={form.port} onChange={e => setForm({...form, port: parseInt(e.target.value) || 22})} />
            <input className="input-field" placeholder="SSH 用户名" value={form.username} onChange={e => setForm({...form, username: e.target.value})} />
            <select className="input-field" value={form.auth_type} onChange={e => setForm({...form, auth_type: e.target.value})}>
              <option value="password">密码认证</option>
              <option value="key">密钥认证</option>
            </select>
            <input className="input-field" type="password" placeholder="密码或密钥内容" value={form.auth_credential} onChange={e => setForm({...form, auth_credential: e.target.value})} />
          </div>
          <input className="input-field mb-4" placeholder="描述（可选）" value={form.description} onChange={e => setForm({...form, description: e.target.value})} />
          <button className="btn-primary" onClick={addServer}>确认添加</button>
        </div>
      )}

      {loading ? (
        <div className="card text-ink-muted text-sm">加载中...</div>
      ) : servers.length === 0 ? (
        <div className="card text-ink-muted text-sm text-center py-12">暂无服务器，请添加一台服务器开始使用。</div>
      ) : (
        <div className="space-y-3">
          {servers.map(s => (
            <div key={s.id} className="card-hover flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <h4 className="text-sm font-medium text-ink">{s.name}</h4>
                  <span className={`text-xs px-2 py-0.5 rounded ${s.is_active ? 'bg-success/20 text-success' : 'bg-danger/20 text-danger'}`}>
                    {s.is_active ? '活跃' : '停用'}
                  </span>
                </div>
                <div className="flex gap-4 mt-1 text-xs text-ink-muted">
                  <span>{s.host}{s.port ? `:${s.port}` : ''}</span>
                  <span>{s.username}</span>
                  <span>{s.auth_type === 'local' ? '本机' : s.auth_type === 'password' ? '密码' : '密钥'}</span>
                </div>
                {s.description && <p className="text-xs text-ink-muted mt-1">{s.description}</p>}
                {testResult[s.id] && <p className="text-xs mt-1">{testResult[s.id]}</p>}
              </div>
              <div className="flex gap-2">
                {s.id !== -1 && (
                  <>
                    <button className="btn-secondary text-xs" onClick={() => testConnection(s.id)} disabled={testingId === s.id}>
                      {testingId === s.id ? '测试中...' : '测试连接'}
                    </button>
                    <button className="btn-danger text-xs" onClick={() => deleteServer(s.id)}>删除</button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}