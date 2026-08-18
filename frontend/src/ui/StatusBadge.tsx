import type { ReactNode } from 'react'

interface StatusBadgeProps {
  status: string
  pulse?: boolean
  text?: string
  children?: ReactNode
}

export default function StatusBadge({ status, pulse, text, children }: StatusBadgeProps) {
  const normalized = (status || '').toLowerCase()

  let variant: 'success' | 'warning' | 'danger' | 'info' = 'info'
  if (['healthy', 'ok', 'running', 'ready', 'online', 'true', 'connected', 'available', 'success', 'resolved'].includes(normalized)) {
    variant = 'success'
  } else if (['warning', 'pending', 'degraded', 'unknown', 'firing'].includes(normalized)) {
    variant = 'warning'
  } else if (['error', 'failed', 'notready', 'crashloopbackoff', 'unhealthy', 'offline', 'false', 'critical', 'danger'].includes(normalized)) {
    variant = 'danger'
  }

  const badgeClass = {
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    info: 'badge-info',
  }[variant]

  return (
    <span className={`${badgeClass} ${pulse ? 'animate-pulse' : ''}`}>
      {children ?? text ?? status}
    </span>
  )
}
