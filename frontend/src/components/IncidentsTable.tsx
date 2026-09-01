'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import type { IncidentSummary } from '@/lib/types'
import { actionStyle, eventTypeLabel, formatDateTime, formatINR } from '@/lib/format'
import { Badge } from './Badge'

function confidenceBarColor(confidence: number): string {
  if (confidence >= 0.8) return 'linear-gradient(90deg, #FB6672, #DC1F31)'
  if (confidence >= 0.5) return 'linear-gradient(90deg, #FCD34D, #D97706)'
  return 'linear-gradient(90deg, #CBD5E1, #94A3B8)'
}

export function IncidentsTable({ incidents }: { incidents: IncidentSummary[] }) {
  const router = useRouter()

  if (incidents.length === 0) {
    return (
      <div className="bg-surface border border-dashed border-line rounded-xl p-12 text-center">
        <p className="text-slate-600">No loss events for this merchant</p>
        <p className="text-xs text-slate-500 mt-1">Operating normally</p>
      </div>
    )
  }

  return (
    <div className="bg-surface rounded-xl shadow-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-canvas/70 border-b border-line text-left text-[11px] text-slate-500 uppercase tracking-wider">
              <th className="px-4 py-3 font-semibold">Event</th>
              <th className="px-4 py-3 font-semibold">Merchant</th>
              <th className="px-4 py-3 font-semibold text-right">Exposure</th>
              <th className="px-4 py-3 font-semibold">Confidence</th>
              <th className="px-4 py-3 font-semibold text-right">Customers</th>
              <th className="px-4 py-3 font-semibold">Detected</th>
              <th className="px-4 py-3 font-semibold">Recommended</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => {
              const style = actionStyle(inc.recommended_action)
              return (
                <tr
                  key={inc.event_id}
                  onClick={() => router.push(`/incidents/${inc.event_id}`)}
                  className="border-b border-line last:border-0 hover:bg-brand-50/40 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3.5">
                    <p className="font-medium text-ink">{eventTypeLabel(inc.event_type)}</p>
                    <p className="text-xs text-slate-400 font-mono">{inc.event_id}</p>
                  </td>
                  <td className="px-4 py-3.5 text-slate-600">{inc.merchant_name}</td>
                  <td className="px-4 py-3.5 text-right font-semibold text-ink tabular-nums">
                    {formatINR(inc.exposure_estimate)}
                  </td>
                  <td className="px-4 py-3.5">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{ width: `${inc.confidence * 100}%`, background: confidenceBarColor(inc.confidence) }}
                        />
                      </div>
                      <span className="text-xs text-slate-600 tabular-nums">{(inc.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3.5 text-right text-slate-600 tabular-nums">{inc.affected_customer_count}</td>
                  <td className="px-4 py-3.5 text-slate-500 text-xs">{formatDateTime(inc.detection_time)}</td>
                  <td className="px-4 py-3.5">
                    <Badge tone={style} />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
