'use client'

import React, { useEffect, useRef } from 'react'
import cytoscape, { type Core, type NodeSingular } from 'cytoscape'
import type { GraphData } from '@/lib/types'

const TYPE_COLOR: Record<string, string> = {
  customer: '#2563eb',
  device: '#dc2626',
  address: '#d97706',
  product: '#7c3aed',
}

export function GraphView({ graph }: { graph: GraphData }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)

  useEffect(() => {
    if (!containerRef.current) return

    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...graph.nodes.map((n) => ({
          data: { id: n.id, label: n.label, type: n.type, segment: n.segment },
        })),
        ...graph.edges.map((e) => ({
          data: {
            id: e.id, source: e.source, target: e.target, type: e.type,
            weight: 1 + e.confidence * 3,
          },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (ele: NodeSingular) => TYPE_COLOR[ele.data('type')] ?? '#6b7280',
            label: 'data(label)',
            'font-size': 8,
            color: '#374151',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: (ele: NodeSingular) => (ele.data('type') === 'customer' ? 22 : 16),
            height: (ele: NodeSingular) => (ele.data('type') === 'customer' ? 22 : 16),
            'border-width': 1,
            'border-color': '#ffffff',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 'data(weight)',
            'line-color': '#cbd5e1',
            'curve-style': 'bezier',
            'target-arrow-shape': 'none',
          },
        },
      ],
      layout: { name: 'cose', animate: false, padding: 24 },
      wheelSensitivity: 0.3,
    })
    cyRef.current = cy

    return () => {
      cy.destroy()
    }
  }, [graph])

  return (
    <div>
      <div ref={containerRef} className="w-full h-96 bg-canvas rounded-xl shadow-card" />
      <div className="flex gap-4 mt-3 text-xs text-slate-500">
        {Object.entries(TYPE_COLOR).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ backgroundColor: color }} />
            <span className="capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
