import React from 'react'
import type { LucideIcon } from 'lucide-react'

export function StatTile({
  label, value, sublabel, icon: Icon, iconColor,
}: {
  label: string
  value: string
  sublabel: string
  icon: LucideIcon
  iconColor: string
}) {
  return (
    <div className="bg-surface rounded-xl shadow-card p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</p>
        <span className={`w-8 h-8 rounded-lg flex items-center justify-center bg-current/10 ${iconColor}`}>
          <Icon className="w-4 h-4" />
        </span>
      </div>
      <p className="text-2xl font-display font-semibold text-ink tabular-nums">{value}</p>
      <p className="text-xs text-slate-500 mt-2 leading-relaxed">{sublabel}</p>
    </div>
  )
}
