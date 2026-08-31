'use client'

import React from 'react'
import { CheckCircle2 } from 'lucide-react'
import type { Counterfactual } from '@/lib/types'
import { actionStyle, formatINR } from '@/lib/format'

export function PolicyComparison({ counterfactual }: { counterfactual: Counterfactual }) {
  const sorted = [...counterfactual.simulations].sort((a, b) => b.net_benefit - a.net_benefit)

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b border-gray-200">
            <th className="py-2 pr-4 font-medium">Policy</th>
            <th className="py-2 pr-4 font-medium text-right">Loss Prevented</th>
            <th className="py-2 pr-4 font-medium text-right">Legit Orders Affected</th>
            <th className="py-2 pr-4 font-medium text-right">Operational Cost</th>
            <th className="py-2 pr-4 font-medium text-right">Net Benefit</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((sim) => {
            const isRecommended = sim.action === counterfactual.recommended_action
            const style = actionStyle(sim.action)
            return (
              <tr
                key={sim.action}
                className={`border-b border-gray-100 last:border-0 ${isRecommended ? 'bg-green-50' : ''}`}
              >
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    {isRecommended && <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />}
                    <span className={`text-xs font-semibold px-2 py-1 rounded ${style.bg} ${style.text}`}>
                      {style.label}
                    </span>
                  </div>
                </td>
                <td className="py-3 pr-4 text-right text-gray-700">{formatINR(sim.expected_loss_prevented)}</td>
                <td className="py-3 pr-4 text-right text-gray-700">
                  {sim.expected_legitimate_orders_affected.toFixed(1)}
                </td>
                <td className="py-3 pr-4 text-right text-gray-700">{formatINR(sim.operational_cost)}</td>
                <td className={`py-3 pr-4 text-right font-semibold ${isRecommended ? 'text-green-700' : 'text-gray-900'}`}>
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
