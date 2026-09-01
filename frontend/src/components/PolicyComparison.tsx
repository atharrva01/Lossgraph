'use client'

import React from 'react'
import { CheckCircle2 } from 'lucide-react'
import type { Counterfactual } from '@/lib/types'
import { actionStyle, formatINR } from '@/lib/format'
import { Badge } from './Badge'

export function PolicyComparison({ counterfactual }: { counterfactual: Counterfactual }) {
  const sorted = [...counterfactual.simulations].sort((a, b) => b.net_benefit - a.net_benefit)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] text-slate-500 uppercase tracking-wider border-b border-line">
            <th className="py-2.5 pr-4 font-semibold">Policy</th>
            <th className="py-2.5 pr-4 font-semibold text-right">Loss Prevented</th>
            <th className="py-2.5 pr-4 font-semibold text-right">Legit Orders Affected</th>
            <th className="py-2.5 pr-4 font-semibold text-right">Operational Cost</th>
            <th className="py-2.5 pr-4 font-semibold text-right">Net Benefit</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((sim) => {
            const isRecommended = sim.action === counterfactual.recommended_action
            const style = actionStyle(sim.action)
            return (
              <tr
                key={sim.action}
                className={`border-b border-line last:border-0 ${isRecommended ? 'bg-success/[0.06]' : ''}`}
              >
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    {isRecommended && <CheckCircle2 className="w-4 h-4 text-success shrink-0" />}
                    <Badge tone={style} />
                  </div>
                </td>
                <td className="py-3 pr-4 text-right text-slate-700 tabular-nums">{formatINR(sim.expected_loss_prevented)}</td>
                <td className="py-3 pr-4 text-right text-slate-700 tabular-nums">
                  {sim.expected_legitimate_orders_affected.toFixed(1)}
                </td>
                <td className="py-3 pr-4 text-right text-slate-700 tabular-nums">{formatINR(sim.operational_cost)}</td>
                <td className={`py-3 pr-4 text-right font-semibold tabular-nums ${isRecommended ? 'text-success' : 'text-ink'}`}>
                  {formatINR(sim.net_benefit)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
