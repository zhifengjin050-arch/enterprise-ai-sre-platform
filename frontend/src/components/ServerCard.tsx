interface ServerCardProps {
  title: string
  percent: number
  used?: string
  total?: string
  color?: string
}

export default function ServerCard({ title, percent, used, total, color = '#3b82f6' }: ServerCardProps) {
  const barColor = percent > 90 ? '#ef4444' : percent > 75 ? '#f59e0b' : color

  return (
    <div className="card-hover">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-ink-muted">{title}</h3>
        <span className="text-2xl font-bold kpi-value" style={{ color: barColor }}>
          {percent}%
        </span>
      </div>
      <div className="w-full bg-surface-2 rounded-full h-2 mb-2 overflow-hidden border border-line/60">
        <div
          className="h-2 rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(percent, 100)}%`, backgroundColor: barColor }}
        />
      </div>
      {used && total && <p className="text-xs text-ink-muted">{used} / {total}</p>}
    </div>
  )
}
