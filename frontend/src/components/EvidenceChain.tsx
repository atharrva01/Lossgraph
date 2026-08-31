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
          <div key={item.id} className="border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setExpanded(isOpen ? null : item.id)}
              className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-50"
            >
              {isOpen ? (
                <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
              )}
              <span className="text-xs font-mono text-gray-400 shrink-0">{item.id}</span>
              <span className="text-sm text-gray-800">{item.claim}</span>
            </button>
            {isOpen && (
              <div className="px-4 pb-3 pl-10">
                <pre className="text-xs bg-gray-50 rounded p-3 overflow-x-auto text-gray-600">
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
