import { useEffect, useState } from 'react'

function useCountUp(target: number, duration = 800) {
  const [value, setValue] = useState(0)

  useEffect(() => {
    const reduced =
      typeof window !== 'undefined' &&
      typeof window.matchMedia === 'function' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduced) {
      setValue(target)
      return
    }
    const start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - p, 3)
      setValue(Math.round(target * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration])

  return value
}

function scoreStroke(n: number) {
  if (n >= 85) return 'rgb(var(--success))'
  if (n >= 70) return 'rgb(var(--warning))'
  return 'rgb(var(--danger))'
}

export default function HealthRing({
  value,
  label,
  hint,
}: {
  value: number
  label: string
  hint: string
}) {
  const shown = useCountUp(Math.round(value))
  const r = 42
  const c = 2 * Math.PI * r
  const clamped = Math.min(100, Math.max(0, value))
  const offset = c * (1 - clamped / 100)
  const color = scoreStroke(value)

  return (
    <div className="flex items-center gap-5">
      <div className="health-ring-wrap shrink-0">
        <svg width="112" height="112" viewBox="0 0 112 112">
          <circle cx="56" cy="56" r={r} fill="none" stroke="rgb(var(--line))" strokeWidth="8" />
          <circle
            cx="56"
            cy="56"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            transform="rotate(-90 56 56)"
            className="health-ring-stroke"
            style={{ ['--ring-len' as string]: c }}
          />
          <text
            x="56"
            y="56"
            textAnchor="middle"
            dominantBaseline="central"
            fill="rgb(var(--ink))"
            style={{ fontSize: 28, fontWeight: 600 }}
          >
            {shown}
          </text>
        </svg>
      </div>
      <div className="anim-rise" style={{ animationDelay: '120ms' }}>
        <p className="section-label">{label}</p>
        <p className="text-xs text-ink-muted mt-2 max-w-[12rem] leading-relaxed">{hint}</p>
      </div>
    </div>
  )
}
