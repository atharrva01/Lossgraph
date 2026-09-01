'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertOctagon, ShieldCheck, ShieldQuestion } from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { StatTile } from '@/components/StatTile'
import { Badge } from '@/components/Badge'
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
        <h1 className="text-2xl font-display font-semibold text-ink tracking-tight">Chargeback Responder</h1>
        <p className="text-sm text-slate-500 mt-1.5 max-w-2xl">
          Evidence-assembled dispute cases, cross-checked against this system&apos;s own loss-event detection
          before recommending a response.{' '}
          <Link href="/how-it-works" className="text-brand-600 font-medium hover:underline">How is this computed?</Link>
        </p>
      </div>

      {error && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-sm text-amber-800">{error}</p>
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8">
            <StatTile
              label="Contest"
              value={String(data.recommendation_counts.CONTEST ?? 0)}
              sublabel="Evidence supports the merchant"
              icon={ShieldCheck}
              iconColor="text-brand-600"
            />
            <StatTile
              label="Accept"
              value={String(data.recommendation_counts.ACCEPT ?? 0)}
              sublabel="Independently flagged as real loss -- contesting would contradict our own finding"
              icon={AlertOctagon}
              iconColor="text-risk-500"
            />
            <StatTile
              label="Escalate"
              value={String(data.recommendation_counts.ESCALATE ?? 0)}
              sublabel="Contradiction or thin evidence -- needs manual review"
              icon={ShieldQuestion}
              iconColor="text-amber-500"
            />
          </div>

          <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
            <div className="flex gap-2">
              {['ALL', 'CONTEST', 'ACCEPT', 'ESCALATE'].map((r) => (
                <button
                  key={r}
                  onClick={() => setFilter(r)}
                  className={`text-xs font-medium px-3 py-1.5 rounded-full border transition-colors ${
                    filter === r ? 'bg-ink text-white border-ink' : 'bg-surface text-slate-600 border-line hover:border-slate-300'
                  }`}
                >
                  {r === 'ALL' ? 'All' : recommendationStyle(r).label}
                </button>
              ))}
            </div>
            <p className="text-xs text-slate-400">{data.cases.length} of {data.total_cases} cases</p>
          </div>

          <div className="bg-surface rounded-xl shadow-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-canvas/70 border-b border-line text-left text-[11px] text-slate-500 uppercase tracking-wider">
                    <th className="px-4 py-3 font-semibold">Case</th>
                    <th className="px-4 py-3 font-semibold">Merchant</th>
                    <th className="px-4 py-3 font-semibold">Reason</th>
                    <th className="px-4 py-3 font-semibold text-right">Amount</th>
                    <th className="px-4 py-3 font-semibold">Disputed</th>
                    <th className="px-4 py-3 font-semibold">Linked Event</th>
                    <th className="px-4 py-3 font-semibold">Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {data.cases.map((c) => {
                    const style = recommendationStyle(c.recommendation)
                    return (
                      <tr
                        key={c.case_id}
                        onClick={() => router.push(`/chargebacks/${c.case_id}`)}
                        className="border-b border-line last:border-0 hover:bg-brand-50/40 cursor-pointer transition-colors"
                      >
                        <td className="px-4 py-3.5">
                          <p className="font-medium text-ink font-mono text-xs">{c.case_id}</p>
                          {c.has_contradictions && <p className="text-xs text-amber-600 mt-0.5">⚠ contradiction</p>}
                        </td>
                        <td className="px-4 py-3.5 text-slate-600">{c.merchant_name}</td>
                        <td className="px-4 py-3.5 text-slate-600">{reasonCodeLabel(c.reason_code)}</td>
                        <td className="px-4 py-3.5 text-right font-semibold text-ink tabular-nums">{formatINR(c.amount)}</td>
                        <td className="px-4 py-3.5 text-slate-500 text-xs">{formatDateTime(c.disputed_at)}</td>
                        <td className="px-4 py-3.5 text-xs">
                          {c.linked_loss_event ? (
                            <span className="text-violet-700 font-mono">{c.linked_loss_event.event_id}</span>
                          ) : (
                            <span className="text-slate-300">--</span>
                          )}
                        </td>
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
        </>
      )}
    </DashboardLayout>
  )
}
