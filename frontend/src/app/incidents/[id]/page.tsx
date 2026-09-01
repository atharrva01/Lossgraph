'use client'

import React, { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { AlertTriangle, ArrowLeft, Clock, FlaskConical, Target, Users } from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { EngineBreakdown } from '@/components/EngineBreakdown'
import { EvidenceChain } from '@/components/EvidenceChain'
import { GraphView } from '@/components/GraphView'
import { InvestigationPanel } from '@/components/InvestigationPanel'
import { PolicyComparison } from '@/components/PolicyComparison'
import { StatTile } from '@/components/StatTile'
import { incidentApi } from '@/lib/api'
import { actionStyle, eventTypeLabel, formatDateTime, formatINR } from '@/lib/format'
import type { GraphData, IncidentDetail } from '@/lib/types'

export default function IncidentDetailPage() {
  const params = useParams<{ id: string }>()
  const [incident, setIncident] = useState<IncidentDetail | null>(null)
  const [graph, setGraph] = useState<GraphData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    incidentApi
      .getIncidentDetails(params.id)
      .then((res) => setIncident(res.data))
      .catch(() => setError('Incident not found, or the API is unreachable.'))
    incidentApi
      .getIncidentGraph(params.id)
      .then((res) => setGraph(res.data))
      .catch(() => setGraph(null))
  }, [params.id])

  if (error) {
    return (
      <DashboardLayout>
        <p className="text-sm text-red-600">{error}</p>
      </DashboardLayout>
    )
  }
  if (!incident) {
    return (
      <DashboardLayout>
        <p className="text-sm text-gray-500">Loading...</p>
      </DashboardLayout>
    )
  }

  const style = actionStyle(incident.counterfactual.recommended_action)
  const gt = incident.ground_truth

  return (
    <DashboardLayout>
      <div className="flex items-center justify-between mb-4">
        <Link href="/" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800">
          <ArrowLeft className="w-4 h-4" /> Back to Command Center
        </Link>
        <Link href="/how-it-works" className="text-sm text-blue-600 hover:underline">
          New here? See how this page is computed →
        </Link>
      </div>

      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{eventTypeLabel(incident.event_type)}</h1>
            <span className={`text-xs font-semibold px-2 py-1 rounded ${style.bg} ${style.text}`}>
              Recommended: {style.label}
            </span>
          </div>
          <p className="text-sm text-gray-500">
            {incident.event_id} &middot; {incident.merchant_name} &middot;{' '}
            {incident.source === 'cluster' ? 'Graph-clustered event' : 'Temporal anomaly event'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatTile
          label="Exposure"
          value={formatINR(incident.exposure_estimate)}
          sublabel={`${formatINR(incident.gross_amount_at_risk)} gross amount at risk`}
          icon={AlertTriangle}
          iconColor="text-red-500"
        />
        <StatTile
          label="Confidence"
          value={`${(incident.confidence * 100).toFixed(0)}%`}
          sublabel="Fused across engines"
          icon={Target}
          iconColor="text-amber-500"
        />
        <StatTile
          label="Affected"
          value={String(incident.affected_customer_count)}
          sublabel={`${incident.affected_transaction_count} transactions, ${incident.affected_entity_count} shared entities`}
          icon={Users}
          iconColor="text-blue-500"
        />
        <StatTile
          label="Detected"
          value={formatDateTime(incident.detection_time)}
          sublabel={`started ${formatDateTime(incident.start_time)}`}
          icon={Clock}
          iconColor="text-gray-500"
        />
      </div>

      <div className="mb-8">
        <EngineBreakdown data={incident.engine_breakdown} />
      </div>

      {incident.investigation && (
        <section className="mb-8">
          <InvestigationPanel investigation={incident.investigation} />
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        <section>
          <h2 className="text-lg font-bold text-gray-900 mb-1">Why was this detected?</h2>
          <p className="text-xs text-gray-500 mb-3">
            Every claim below is machine-checked to trace back to a real number -- click to expand.
          </p>
          <EvidenceChain evidence={incident.evidence} />
        </section>

        <section>
          <h2 className="text-lg font-bold text-gray-900 mb-1">Entity Graph</h2>
          <p className="text-xs text-gray-500 mb-3">
            Blue = customer, red = device, orange = address. An edge means that customer used that
            device/address. This is what the graph engine's score above is measuring.
          </p>
          {graph && graph.nodes.length > 0 ? (
            <GraphView graph={graph} />
          ) : (
            <div className="h-96 bg-gray-50 rounded-lg border border-dashed border-gray-300 flex items-center justify-center text-center px-8">
              <p className="text-sm text-gray-500">
                No qualifying shared-entity cluster -- this event was detected from the merchant-day
                anomaly signal alone, not a device/address graph pattern.
              </p>
            </div>
          )}
        </section>
      </div>

      {incident.linked_chargebacks.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-bold text-gray-900 mb-3">
            Linked Chargebacks ({incident.linked_chargebacks.length})
          </h2>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <p className="text-sm text-gray-600 mb-3">
              These disputes trace back to this Loss Event -- detected independently, before any of them arrived.
            </p>
            <div className="flex flex-wrap gap-2">
              {incident.linked_chargebacks.slice(0, 30).map((cb) => (
                <Link
                  key={cb.case_id}
                  href={`/chargebacks/${cb.case_id}`}
                  className="text-xs font-medium px-2.5 py-1 rounded-full bg-violet-50 text-violet-700 border border-violet-200 hover:bg-violet-100"
                >
                  {cb.case_id}
                </Link>
              ))}
              {incident.linked_chargebacks.length > 30 && (
                <span className="text-xs text-gray-400 self-center">
                  +{incident.linked_chargebacks.length - 30} more --{' '}
                  <Link href="/chargebacks" className="underline">view all</Link>
                </span>
              )}
            </div>
          </div>
        </section>
      )}

      <section className="mb-8">
        <h2 className="text-lg font-bold text-gray-900 mb-1">Simulate Intervention</h2>
        <p className="text-xs text-gray-500 mb-3">
          For each possible action, the estimated Rupee cost/benefit if the merchant took it right now.
          The highlighted row (green) is whichever has the highest net benefit -- not necessarily the
          most aggressive one.
        </p>
        <div className="bg-white border border-gray-200 rounded-lg p-4">
          <PolicyComparison counterfactual={incident.counterfactual} />
        </div>
      </section>

      <section className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <FlaskConical className="w-4 h-4 text-indigo-600" />
          <p className="text-sm font-semibold text-indigo-900">Ground Truth (evaluation only)</p>
        </div>
        <p className="text-xs text-indigo-800">
          This synthetic dataset carries injected ground-truth labels so detection quality can be
          measured honestly. A production deployment would not have this panel -- it exists here to
          show the system's calibration: {gt.purity >= 0.8
            ? `${(gt.purity * 100).toFixed(0)}% of the flagged transactions are genuinely part of ${
                gt.dominant_true_scenario ?? 'a real loss scenario'
              }.`
            : `only ${(gt.purity * 100).toFixed(0)}% of the flagged transactions are true loss -- ${
                gt.n_edge_case
              } are a legitimate-but-unusual pattern the model correctly assigned lower confidence to.`}
        </p>
      </section>
    </DashboardLayout>
  )
}
