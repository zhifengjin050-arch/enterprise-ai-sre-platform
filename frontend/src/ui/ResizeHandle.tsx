import type { PointerEvent as ReactPointerEvent } from 'react'

type Props = {
  onPointerDown: (e: ReactPointerEvent) => void
  label: string
  edge: 'start' | 'end'
}

export default function ResizeHandle({ onPointerDown, label, edge }: Props) {
  return (
    <button
      type="button"
      className={`resize-handle ${edge === 'start' ? 'resize-handle--start' : 'resize-handle--end'}`}
      aria-label={label}
      title={label}
      onPointerDown={onPointerDown}
    />
  )
}
