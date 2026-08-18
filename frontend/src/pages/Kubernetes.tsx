import { useState, useEffect } from 'react'
import api from '../api/client'
import StatusBadge from '../components/StatusBadge'

interface Pod {
  namespace: string
  name: string
  status: string
  ready: string
  restarts: number
}

interface Node {
  name: string
  status: string
  role: string
  cpu: string
  memory: string
  kubelet_version: string
}

export default function Kubernetes() {
  const [pods, setPods] = useState<Pod[]>([])
  const [nodes, setNodes] = useState<Node[]>([])
  const [loading, setLoading] = useState(true)
  const [namespace, setNamespace] = useState('')
  const [diagnosisPod, setDiagnosisPod] = useState('')
  const [diagnosisNs, setDiagnosisNs] = useState('default')
  const [diagnosisResult, setDiagnosisResult] = useState<any>(null)
  const [diagnosisLoading, setDiagnosisLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [podsRes, nodesRes] = await Promise.all([
        api.get('/k8s/pods', { params: { namespace } }),
        api.get('/k8s/nodes'),
      ])
      if (podsRes.data?.pods) setPods(podsRes.data.pods)
      if (nodesRes.data?.nodes) setNodes(nodesRes.data.nodes)
    } catch {
      // K8S 可能未启用
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [namespace])

  const diagnosePod = async () => {
    if (!diagnosisPod) return
    setDiagnosisLoading(true)
    setDiagnosisResult(null)
    try {
      const res = await api.post('/k8s/diagnose-pod', { pod_name: diagnosisPod, namespace: diagnosisNs })
      setDiagnosisResult(res.data)
    } catch (err: any) {
      setDiagnosisResult({ error: err.response?.data?.detail || '诊断失败' })
    } finally {
      setDiagnosisLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* 节点列表 */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">集群节点</h3>
        {nodes.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {nodes.map(n => (
              <div key={n.name} className="card-hover">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="text-sm font-medium text-gray-200">{n.name}</h4>
                  <StatusBadge status={n.status} />
                </div>
                <div className="text-xs text-gray-500 space-y-1">
                  <p>角色: {n.role}</p>
                  <p>CPU: {n.cpu} | 内存: {n.memory}</p>
                  <p>Kubelet: {n.kubelet_version}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="card text-gray-500 text-sm">{loading ? '加载中...' : 'Kubernetes 未启用或无法连接'}</div>
        )}
      </div>

      {/* Pod 列表 */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider">Pod 列表</h3>
          <div className="flex gap-2">
            <input
              className="input-field w-40 text-sm"
              placeholder="命名空间 (默认全部)"
              value={namespace}
              onChange={e => setNamespace(e.target.value)}
            />
          </div>
        </div>
        {pods.length > 0 ? (
          <div className="card overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-500 border-b border-dark-300">
                  <th className="text-left py-2 px-3">命名空间</th>
                  <th className="text-left py-2 px-3">名称</th>
                  <th className="text-left py-2 px-3">状态</th>
                  <th className="text-center py-2 px-3">就绪</th>
                  <th className="text-center py-2 px-3">重启次数</th>
                </tr>
              </thead>
              <tbody>
                {pods.map((p, i) => (
                  <tr key={i} className="border-b border-dark-300/50 hover:bg-dark-300/50">
                    <td className="py-2 px-3 text-gray-400">{p.namespace}</td>
                    <td className="py-2 px-3 text-gray-200">{p.name}</td>
                    <td className="py-2 px-3"><StatusBadge status={p.status} /></td>
                    <td className="py-2 px-3 text-center text-gray-400">{p.ready}</td>
                    <td className="py-2 px-3 text-center text-gray-400">{p.restarts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="card text-gray-500 text-sm">{loading ? '加载中...' : '暂无 Pod 数据'}</div>
        )}
      </div>

      {/* Pod AI 诊断 */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">Pod AI 诊断</h3>
        <div className="card">
          <div className="flex gap-2 mb-4">
            <input className="input-field flex-1" placeholder="Pod 名称" value={diagnosisPod} onChange={e => setDiagnosisPod(e.target.value)} />
            <input className="input-field w-32" placeholder="命名空间" value={diagnosisNs} onChange={e => setDiagnosisNs(e.target.value)} />
            <button className="btn-primary" onClick={diagnosePod} disabled={diagnosisLoading || !diagnosisPod}>
              {diagnosisLoading ? '诊断中...' : '诊断'}
            </button>
          </div>

          {diagnosisResult && (
            <div className="bg-dark-300 rounded-lg p-4">
              {diagnosisResult.error ? (
                <p className="text-danger text-sm">{diagnosisResult.error}</p>
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-400">Pod:</span>
                    <span className="text-sm text-gray-200">{diagnosisResult.pod_name}</span>
                    <span className="text-sm text-gray-400">状态:</span>
                    <StatusBadge status={diagnosisResult.phase || 'Unknown'} />
                  </div>
                  
                  {diagnosisResult.has_issues && (
                    <div>
                      <p className="text-sm font-medium text-danger mb-2">发现异常:</p>
                      {diagnosisResult.issues?.map((issue: any, i: number) => (
                        <div key={i} className="bg-danger/5 border border-danger/10 rounded-lg p-3 mb-2">
                          <div className="flex items-center gap-2">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                              issue.severity === 'critical' ? 'bg-danger/20 text-danger' : issue.severity === 'high' ? 'bg-warning/20 text-warning' : 'bg-info/20 text-info'
                            }`}>
                              {issue.severity === 'critical' ? '严重' : issue.severity === 'high' ? '高' : '警告'}
                            </span>
                            <span className="text-sm text-gray-200">{issue.type}</span>
                            {issue.container && <span className="text-xs text-gray-500">容器: {issue.container}</span>}
                          </div>
                          <p className="text-xs text-gray-400 mt-1">{issue.message}</p>
                        </div>
                      ))}
                    </div>
                  )}

                  {diagnosisResult.containers && (
                    <div>
                      <p className="text-sm text-gray-400 mb-2">容器状态:</p>
                      {diagnosisResult.containers.map((c: any, i: number) => (
                        <div key={i} className="text-xs text-gray-500 flex gap-4 py-1">
                          <span className="text-gray-300">{c.name}</span>
                          <span>状态: {c.state}</span>
                          <span>就绪: {c.ready ? '✅' : '❌'}</span>
                          <span>重启: {c.restart_count}次</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {!diagnosisResult.has_issues && (
                    <p className="text-xs text-success">✅ 未检测到异常</p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}