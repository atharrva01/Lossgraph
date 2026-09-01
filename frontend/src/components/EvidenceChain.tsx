'use client'

import React, { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { EvidenceItem } from '@/lib/types'

export function EvidenceChain({ evidence }: { evidence: EvidenceItem[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)

  return (
    <div className="space-y-2">
      {evidence.map((item) => {
        const isOpen = expanded === item.id
        return (
          <div
            key={item.id}
            className={`bg-surface rounded-lg overflow-hidden transition-shadow ${isOpen ? 'shadow-card' : 'shadow-sm shadow-slate-200/60'}`}
          >
            <button
              onClick={() => setExpanded(isOpen ? null : item.id)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-canvas/70"
            >
              <span className="w-6 h-6 rounded-full bg-brand-50 text-brand-700 text-[11px] font-mono font-semibold flex items-center justify-center shrink-0">
                {item.id}
              </span>
              <span className="text-sm text-ink flex-1">{item.claim}</span>
              {isOpen ? (
                <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
              )}
            </button>
            {isOpen && (
              <div className="px-4 pb-3">
                <pre className="text-xs font-mono bg-canvas rounded-lg p-3 overflow-x-auto text-slate-600 ml-9">
                  {JSON.stringify(item.data, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
