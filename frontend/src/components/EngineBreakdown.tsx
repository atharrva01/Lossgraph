'use client'

import React from 'react'
import { ArrowRight } from 'lucide-react'
import type { EngineBreakdown as EngineBreakdownData } from '@/lib/types'

const ROWS: { key: keyof Omit<EngineBreakdownData, 'fused'>; label: string; blurb: string; color: string }[] = [
  {
    key: 'transaction_model',
    label: 'Transaction risk model',
    blurb: 'LightGBM, scored at authorization time from this customer/device history alone',
    color: 'bg-blue-500',
  },
  {
    key: 'graph_engine',
    label: 'Entity graph engine',
    blurb: 'How suspicious the shared-device/address cluster looks (0 if this customer is not in a cluster)',
    color: 'bg-violet-500',
  },
  {
    key: 'anomaly_engine',
    label: 'Temporal anomaly engine',
    blurb: "This merchant's daily return/dispute rate, compared to its own recent baseline",
    color: 'bg-amber-500',
  },
]

export function EngineBreakdown({ data }: { data: EngineBreakdownData }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="text-sm font-semibold text-gray-900 mb-1">How the confidence score was computed</h3>
      <p className="text-xs text-gray-500 mb-4">
        Three independent engines each score this event; they are combined (not averaged -- any one strong
        signal can dominate) into the fused confidence shown above.
      </p>
      <div className="space-y-3">
        {ROWS.map((row) => {
          const value = data[row.key]
          return (
            <div key={row.key}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-gray-700">{row.label}</span>
                <span className="text-xs font-semibold text-gray-900">{(value * 100).toFixed(0)}%</span>
              </div>
              <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                <div className={`h-full rounded-full ${row.color}`} style={{ width: `${value * 100}%` }} />
              </div>
              <p className="text-xs text-gray-400 mt-1">{row.blurb}</p>
            </div>
          )
        })}
      </div>
      <div className="flex items-center justify-center gap-2 mt-4 pt-4 border-t border-gray-100">
        <span className="text-xs text-gray-500">combined via noisy-OR</span>
        <ArrowRight className="w-3.5 h-3.5 text-gray-400" />
        <span className="text-sm font-bold text-gray-900">{(data.fused * 100).toFixed(0)}% fused confidence</span>
      </div>
    </div>
  )
}
