import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'

function readWidth(key: string, fallback: number, min: number, max: number) {
  try {
    const n = Number(localStorage.getItem(key))
    if (Number.isFinite(n)) return Math.min(max, Math.max(min, n))
  } catch {
    /* ignore */
  }
  return fallback
}

/** 左右分栏宽度，拖拽方向 invert=true 表示向右拖变窄（右侧栏） */
export function usePanelWidth(key: string, fallback: number, min: number, max: number) {
  const [width, setWidth] = useState(() => readWidth(key, fallback, min, max))
  const drag = useRef<{ startX: number; startW: number; invert: boolean } | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(key, String(Math.round(width)))
    } catch {
      /* ignore */
    }
  }, [key, width])

  useEffect(() => {
    const onMove = (e: PointerEvent) => {
      const d = drag.current
      if (!d) return
      const delta = d.invert ? d.startX - e.clientX : e.clientX - d.startX
      setWidth(Math.min(max, Math.max(min, d.startW + delta)))
    }
    const onUp = () => {
      drag.current = null
      document.body.classList.remove('is-resizing')
    }
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', onUp)
    return () => {
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerup', onUp)
    }
  }, [max, min])

  const startDrag = useCallback(
    (invert: boolean) => (e: ReactPointerEvent) => {
      e.preventDefault()
      drag.current = { startX: e.clientX, startW: width, invert }
      document.body.classList.add('is-resizing')
    },
    [width],
  )

  return { width, startDrag }
}
