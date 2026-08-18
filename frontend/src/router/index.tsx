import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../store/auth'
import Layout from '../components/Layout'
import Login from '../pages/Login'
import Dashboard from '../pages/Dashboard'
import Chat from '../pages/Chat'
import Trace from '../pages/Trace'
import Knowledge from '../pages/Knowledge'
import InfraExplorer from '../features/infra/InfraExplorer'
import Incidents from '../features/incidents/Incidents'
import MonitorCenter from '../features/monitor/MonitorCenter'
import Servers from '../pages/Servers'
import Kubernetes from '../pages/Kubernetes'
import Monitoring from '../pages/Monitoring'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function AppRouter() {
  const { isAuthenticated } = useAuth()

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to="/overview" replace /> : <Login />} />
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<Dashboard />} />
        <Route path="ops" element={<Chat />} />
        <Route path="infra" element={<InfraExplorer />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="knowledge" element={<Knowledge />} />
        <Route path="traces" element={<Trace />} />
        <Route path="monitor" element={<MonitorCenter />} />
        <Route path="dashboard" element={<Navigate to="/overview" replace />} />
        <Route path="chat" element={<Navigate to="/ops" replace />} />
        <Route path="servers" element={<Navigate to="/infra" replace />} />
        <Route path="kubernetes" element={<Navigate to="/infra" replace />} />
        <Route path="monitoring" element={<Navigate to="/monitor" replace />} />
        <Route path="trace" element={<Navigate to="/traces" replace />} />
        <Route path="legacy/servers" element={<Servers />} />
        <Route path="legacy/kubernetes" element={<Kubernetes />} />
        <Route path="legacy/monitoring" element={<Monitoring />} />
      </Route>
      <Route path="*" element={<Navigate to={isAuthenticated ? '/overview' : '/login'} replace />} />
    </Routes>
  )
}
