/**
 * Command Center -- main dashboard
 */

'use client'

import React, { useEffect, useState } from 'react'
import { AlertTriangle, ShieldCheck, Siren, TrendingUp } from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { IncidentsTable } from '@/components/IncidentsTable'
import { StatTile } from '@/components/StatTile'
import { incidentApi, merchantApi } from '@/lib/api'
import { formatINR } from '@/lib/format'
import type { CommandCenterResponse, Merchant } from '@/lib/types'

export default function CommandCenterPage() {
  const [merchants, setMerchants] = useState<Merchant[]>([])
  const [selectedMerchant, setSelectedMerchant] = useState('ALL')
  const [data, setData] = useState<CommandCenterResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    merchantApi.list().then((res) => setMerchants(res.data)).catch(() => setMerchants([]))
  }, [])

  useEffect(() => {
    setLoading(true)
    incidentApi
      .getCommandCenter(selectedMerchant)
      .then((res) => {
        setData(res.data)
        setError(null)
      })
      .catch((err) => {
        const detail = err?.response?.data?.detail
        setError(
          detail ??
            'Could not reach the LossGraph API. Is the backend running on http://localhost:8000?'
        )
        setData(null)
      })
      .finally(() => setLoading(false))
  }, [selectedMerchant])

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Merchant Risk Command Center</h1>
          <p className="text-sm text-gray-500 mt-1">
            Loss events detected on the held-out test split of the synthetic merchant ecosystem
          </p>
        </div>
        <select
          value={selectedMerchant}
          onChange={(e) => setSelectedMerchant(e.target.value)}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm bg-white"
        >
          <option value="ALL">All Merchants</option>
          {merchants.map((m) => (
            <option key={m.merchant_id} value={m.merchant_id}>
              {m.name} ({m.incident_count})
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-yellow-800">{error}</p>
        </div>
      )}

      {loading ? (
        <div className="py-16 text-center text-gray-500 text-sm">Loading...</div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <StatTile
              label="Current Exposure"
              value={formatINR(data.current_exposure)}
              sublabel="Probability-weighted amount at risk"
              icon={AlertTriangle}
              iconColor="text-red-500"
            />
            <StatTile
              label="Preventable Exposure"
              value={formatINR(data.preventable_exposure)}
              sublabel="Loss prevented by recommended actions"
              icon={ShieldCheck}
              iconColor="text-green-500"
            />
            <StatTile
              label="Active Incidents"
              value={String(data.active_incidents)}
              sublabel={`of ${data.total_incidents} total events`}
              icon={Siren}
              iconColor="text-amber-500"
            />
            <StatTile
              label="Net Benefit"
              value={formatINR(data.net_benefit_vs_allow)}
              sublabel="vs. allowing every transaction"
              icon={TrendingUp}
              iconColor="text-blue-500"
            />
          </div>

          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Loss Events</h2>
            <p className="text-xs text-gray-400">Click a row to investigate</p>
          </div>
          <IncidentsTable incidents={data.incidents} />
        </>
      ) : null}
    </DashboardLayout>
  )
}
