const map: Record<string, string> = {
  critical: 'badge-danger',
  high: 'badge-danger',
  warning: 'badge-warning',
  medium: 'badge-warning',
  info: 'badge-info',
  low: 'badge-info',
  success: 'badge-success',
}

export default function SeverityChip({ level }: { level: string }) {
  const cls = map[level.toLowerCase()] || 'badge-info'
  return <span className={cls}>{level}</span>
}
