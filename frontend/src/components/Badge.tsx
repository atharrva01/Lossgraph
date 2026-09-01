import React from 'react'

export interface BadgeTone {
  bg: string
  text: string
  dot: string
  label: string
}

export function Badge({
  tone, label, dotted = true,
}: {
  tone: BadgeTone
  label?: string
  dotted?: boolean
}) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${tone.bg} ${tone.text}`}>
      {dotted && <span className={`w-1.5 h-1.5 rounded-full ${tone.dot}`} />}
      {label ?? tone.label}
    </span>
  )
}
