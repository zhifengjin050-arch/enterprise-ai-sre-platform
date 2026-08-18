import { useEffect, useState } from 'react'

/** Count-up for KPI numbers; decimals supported when target has fraction. */
export function useCountUp(target: number, duration = 700) {
  const [value, setValue] = useState(0)
  const decimals = Number.isInteger(target) ? 0 : 1

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
      const next = target * eased
      setValue(decimals ? Number(next.toFixed(decimals)) : Math.round(next))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, decimals])

  return value
}
