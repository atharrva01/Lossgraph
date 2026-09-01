'use client'

import React, { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertOctagon, ShieldCheck, ShieldQuestion } from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { StatTile } from '@/components/StatTile'
import { chargebackApi } from '@/lib/api'
import { formatDateTime, formatINR, reasonCodeLabel, recommendationStyle } from '@/lib/format'
import type { ChargebackListResponse } from '@/lib/types'

export default function ChargebacksPage() {
  const router = useRouter()
  const [data, setData] = useState<ChargebackListResponse | null>(null)
  const [filter, setFilter] = useState('ALL')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    chargebackApi
      .list(filter)
      .then((res) => {
        setData(res.data)
        setError(null)
      })
      .catch((err) => setError(err?.response?.data?.detail ?? 'Could not reach the LossGraph API.'))
  }, [filter])

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Chargeback Responder</h1>
        <p className="text-sm text-gray-500 mt-1">
          Evidence-assembled dispute cases, cross-checked against this system&apos;s own loss-event detection
          before recommending a response
        </p>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-yellow-800">{error}</p>
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <StatTile
              label="Contest"
              value={String(data.recommendation_counts.CONTEST ?? 0)}
              sublabel="Evidence supports the merchant"
              icon={ShieldCheck}
              iconColor="text-blue-500"
            />
            <StatTile
              label="Accept"
              value={String(data.recommendation_counts.ACCEPT ?? 0)}
              sublabel="Independently flagged as real loss -- contesting would contradict our own finding"
              icon={AlertOctagon}
              iconColor="text-red-500"
            />
            <StatTile
              label="Escalate"
              value={String(data.recommendation_counts.ESCALATE ?? 0)}
              sublabel="Contradiction or thin evidence -- needs manual review"
              icon={ShieldQuestion}
              iconColor="text-amber-500"
            />
          </div>

          <div className="flex items-center justify-between mb-4">
            <div className="flex gap-2">
              {['ALL', 'CONTEST', 'ACCEPT', 'ESCALATE'].map((r) => (
                <button
                  key={r}
                  onClick={() => setFilter(r)}
                  className={`text-xs font-medium px-3 py-1.5 rounded-full border ${
                    filter === r ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-600 border-gray-300'
                  }`}
                >
                  {r === 'ALL' ? 'All' : recommendationStyle(r).label}
                </button>
              ))}
            </div>
            <p className="text-xs text-gray-400">{data.cases.length} of {data.total_cases} cases</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200 text-left text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3 font-medium">Case</th>
                    <th className="px-4 py-3 font-medium">Merchant</th>
                    <th className="px-4 py-3 font-medium">Reason</th>
                    <th className="px-4 py-3 font-medium text-right">Amount</th>
                    <th className="px-4 py-3 font-medium">Disputed</th>
                    <th className="px-4 py-3 font-medium">Linked Event</th>
                    <th className="px-4 py-3 font-medium">Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cases.map((c) => {
                    const style = recommendationStyle(c.recommendation)
                    return (
                      <tr
                        key={c.case_id}
                        onClick={() => router.push(`/chargebacks/${c.case_id}`)}
                        className="border-b border-gray-100 last:border-0 hover:bg-gray-50 cursor-pointer"
                      >
                        <td className="px-4 py-3">
                          <p className="font-medium text-gray-900">{c.case_id}</p>
                          {c.has_contradictions && <p className="text-xs text-amber-600">⚠ contradiction</p>}
                        </td>
                        <td className="px-4 py-3 text-gray-600">{c.merchant_name}</td>
                        <td className="px-4 py-3 text-gray-600">{reasonCodeLabel(c.reason_code)}</td>
                        <td className="px-4 py-3 text-right font-semibold text-gray-900">{formatINR(c.amount)}</td>
                        <td className="px-4 py-3 text-gray-500 text-xs">{formatDateTime(c.disputed_at)}</td>
                        <td className="px-4 py-3 text-xs">
                          {c.linked_loss_event ? (
                            <span className="text-violet-700">{c.linked_loss_event.event_id}</span>
                          ) : (
                            <span className="text-gray-300">--</span>
                          )}
                        </td>
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
        </>
      )}
    </DashboardLayout>
  )
}
