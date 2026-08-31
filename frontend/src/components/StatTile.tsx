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
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-gray-600">{label}</p>
        <Icon className={`w-5 h-5 ${iconColor}`} />
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-2">{sublabel}</p>
    </div>
  )
}
