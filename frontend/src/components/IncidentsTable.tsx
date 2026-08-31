'use client'

import React from 'react'
import { useRouter } from 'next/navigation'
import type { IncidentSummary } from '@/lib/types'
import { actionStyle, confidenceColor, eventTypeLabel, formatDateTime, formatINR } from '@/lib/format'

export function IncidentsTable({ incidents }: { incidents: IncidentSummary[] }) {
  const router = useRouter()

  if (incidents.length === 0) {
    return (
      <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg p-12 text-center">
        <p className="text-gray-600">No loss events for this merchant</p>
        <p className="text-xs text-gray-500 mt-1">Operating normally</p>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
              <th className="px-4 py-3 font-medium">Event</th>
              <th className="px-4 py-3 font-medium">Merchant</th>
              <th className="px-4 py-3 font-medium text-right">Exposure</th>
              <th className="px-4 py-3 font-medium">Confidence</th>
              <th className="px-4 py-3 font-medium text-right">Customers</th>
              <th className="px-4 py-3 font-medium">Detected</th>
              <th className="px-4 py-3 font-medium">Recommended</th>
            </tr>
          </thead>
          <tbody>
            {incidents.map((inc) => {
              const style = actionStyle(inc.recommended_action)
              return (
                <tr
                  key={inc.event_id}
                  onClick={() => router.push(`/incidents/${inc.event_id}`)}
                  className="border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{eventTypeLabel(inc.event_type)}</p>
                    <p className="text-xs text-gray-400">{inc.event_id}</p>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{inc.merchant_name}</td>
                  <td className="px-4 py-3 text-right font-semibold text-gray-900">
                    {formatINR(inc.exposure_estimate)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${confidenceColor(inc.confidence)}`}
                          style={{ width: `${inc.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-600">{(inc.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">{inc.affected_customer_count}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{formatDateTime(inc.detection_time)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${style.bg} ${style.text}`}>
                      {style.label}
                    </span>
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
