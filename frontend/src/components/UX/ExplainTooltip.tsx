import { useState, useRef, useEffect } from 'react'
import { Info } from 'lucide-react'
import clsx from 'clsx'

interface ExplainTooltipProps {
  text: string
  className?: string
}

export function ExplainTooltip({ text, className }: ExplainTooltipProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <span className={clsx('relative inline-flex', className)} ref={ref}>
      <button
        type="button"
        className="text-gray-400 hover:text-gray-600 transition-colors"
        onClick={() => setOpen((v) => !v)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        aria-label="More info"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-50 mb-2 -translate-x-1/2 whitespace-normal rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs text-gray-600 shadow-lg max-w-[220px] w-max"
        >
          {text}
        </span>
      )}
    </span>
  )
}
