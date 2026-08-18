import React, { useEffect, useState, useCallback } from 'react';
import api from '../api/client';
import StatusBadge from '../components/StatusBadge';

interface CpuInfo {
  percent: number;
  cores: number;
}

interface MemoryInfo {
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

interface DiskInfo {
  mount: string;
  total_gb: number;
  used_gb: number;
  free_gb: number;
  percent: number;
}

interface MonitoringData {
  cpu: CpuInfo;
  memory: MemoryInfo;
  disks: DiskInfo[];
}

interface AlertItem {
  id: number;
  level: string;
  title: string;
  message: string;
  source: string;
  status: string;
  created_at: string;
  resolved_at: string | null;
}

interface AgentStats {
  total_conversations: number;
  total_messages: number;
  total_servers: number;
  total_executions: number;
  success_executions: number;
  tools_available: number;
}

function ProgressBar({ label, percent, color }: { label: string; percent: number; color?: string }) {
  const barColor = color || (percent > 90 ? '#ef4444' : percent > 75 ? '#f59e0b' : '#22c55e');
  return (
    <div className="mb-4">
      <div className="flex justify-between mb-1">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className="text-sm font-medium text-gray-400">{percent.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-gray-700 rounded-full h-2.5">
        <div
          className="h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: barColor }}
        />
      </div>
    </div>
  );
}

export default function Monitoring() {
  const [monitoring, setMonitoring] = useState<MonitoringData | null>(null);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [agentStats, setAgentStats] = useState<AgentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [monRes, alertRes, statsRes] = await Promise.all([
        api.get('/monitoring/current'),
        api.get('/alerts', { params: { limit: 20 } }),
        api.get('/agent/stats'),
      ]);
      setMonitoring(monRes.data);
      setAlerts(alertRes.data || []);
      setAgentStats(statsRes.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || '获取监控数据失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const timer = setInterval(fetchData, 30000);
    return () => clearInterval(timer);
  }, [fetchData]);

  const levelColor = (level: string) => {
    switch (level) {
      case 'critical': return 'danger';
      case 'warning': return 'warning';
      default: return 'info';
    }
  };

  if (loading && !monitoring) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-100">系统监控</h1>
        <button
          onClick={fetchData}
          className="px-4 py-2 bg-gray-700 text-gray-200 rounded-lg hover:bg-gray-600 transition-colors"
        >
          刷新
        </button>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700 text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      {/* 实时指标 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* CPU */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">CPU</h3>
          {monitoring && (
            <>
              <div className="text-3xl font-bold text-gray-100 mb-2">{monitoring.cpu.percent.toFixed(1)}%</div>
              <div className="text-sm text-gray-400 mb-4">{monitoring.cpu.cores} 核心</div>
              <ProgressBar label="使用率" percent={monitoring.cpu.percent} />
            </>
          )}
        </div>

        {/* 内存 */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">内存</h3>
          {monitoring && (
            <>
              <div className="text-3xl font-bold text-gray-100 mb-2">{monitoring.memory.percent.toFixed(1)}%</div>
              <div className="text-sm text-gray-400 mb-4">
                {monitoring.memory.used_gb}G / {monitoring.memory.total_gb}G
              </div>
              <ProgressBar label="使用率" percent={monitoring.memory.percent} />
            </>
          )}
        </div>

        {/* 磁盘 */}
        <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold text-gray-200 mb-4">磁盘</h3>
          {monitoring && monitoring.disks.length > 0 ? (
            monitoring.disks.map((disk) => (
              <ProgressBar key={disk.mount} label={disk.mount} percent={disk.percent} />
            ))
          ) : (
            <div className="text-gray-500">暂无数据</div>
          )}
        </div>
      </div>

      {/* Agent 运行统计 */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold text-gray-200 mb-4">AI Agent 运行统计</h3>
        {agentStats ? (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="bg-gray-700/50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-400">{agentStats.total_executions}</div>
              <div className="text-xs text-gray-400 mt-1">总执行次数</div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-400">{agentStats.success_executions}</div>
              <div className="text-xs text-gray-400 mt-1">成功次数</div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-400">
                {agentStats.total_executions > 0
                  ? ((agentStats.success_executions / agentStats.total_executions) * 100).toFixed(0)
                  : 'N/A'}%
              </div>
              <div className="text-xs text-gray-400 mt-1">成功率</div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-400">{agentStats.total_conversations}</div>
              <div className="text-xs text-gray-400 mt-1">会话数</div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-indigo-400">{agentStats.tools_available}</div>
              <div className="text-xs text-gray-400 mt-1">可用工具</div>
            </div>
          </div>
        ) : (
          <div className="text-gray-500">加载中...</div>
        )}
      </div>

      {/* 告警列表 */}
      <div className="bg-gray-800 rounded-xl p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-200">告警列表</h3>
          <StatusBadge status={alerts.filter(a => a.status === 'firing').length > 0 ? 'warning' : 'success'}
            text={alerts.filter(a => a.status === 'firing').length > 0 ? `${alerts.filter(a => a.status === 'firing').length} 个活跃` : '全部已解决'} />
        </div>
        {alerts.length === 0 ? (
          <div className="text-gray-500 text-center py-8">暂无告警</div>
        ) : (
          <div className="space-y-3">
            {alerts.slice(0, 10).map((alert) => (
              <div key={alert.id} className="flex items-center justify-between bg-gray-700/30 rounded-lg p-4">
                <div className="flex items-center space-x-3">
                  <StatusBadge status={levelColor(alert.level)} text={alert.level} />
                  <div>
                    <div className="text-sm font-medium text-gray-200">{alert.title}</div>
                    <div className="text-xs text-gray-400 mt-1">{alert.message.slice(0, 100)}</div>
                  </div>
                </div>
                <div className="text-right">
                  <StatusBadge status={alert.status === 'firing' ? 'warning' : 'success'} text={alert.status} />
                  <div className="text-xs text-gray-500 mt-1">
                    {alert.created_at ? new Date(alert.created_at).toLocaleString() : ''}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}