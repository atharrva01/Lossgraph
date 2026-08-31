/**
 * Incident card component
 */

import React from 'react'
import { AlertTriangle, TrendingUp } from 'lucide-react'

interface IncidentCardProps {
  eventId: string
  eventType: string
  exposure: number
  confidence: number
  status: string
  onClick?: () => void
}

export const IncidentCard: React.FC<IncidentCardProps> = ({
  eventId,
  eventType,
  exposure,
  confidence,
  status,
  onClick,
}) => {
  const statusColors = {
    detected: 'bg-yellow-50 border-yellow-200',
    investigating: 'bg-blue-50 border-blue-200',
    confirmed: 'bg-red-50 border-red-200',
    resolved: 'bg-green-50 border-green-200',
  }

  const statusBadgeColors = {
    detected: 'bg-yellow-100 text-yellow-800',
    investigating: 'bg-blue-100 text-blue-800',
    confirmed: 'bg-red-100 text-red-800',
    resolved: 'bg-green-100 text-green-800',
  }

  return (
    <div
      className={`p-4 border rounded-lg cursor-pointer hover:shadow-md transition-shadow ${
        statusColors[status as keyof typeof statusColors] || 'bg-gray-50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-500" />
          <h3 className="font-semibold text-gray-900">{eventType}</h3>
        </div>
        <span
          className={`text-xs font-semibold px-2 py-1 rounded ${
            statusBadgeColors[status as keyof typeof statusBadgeColors] || 'bg-gray-100'
          }`}
        >
          {status}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-xs text-gray-600">Exposure</p>
          <p className="text-lg font-bold text-gray-900">₹{exposure.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-gray-600">Confidence</p>
          <div className="flex items-center gap-2">
            <div className="w-12 h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-red-500"
                style={{ width: `${confidence * 100}%` }}
              />
            </div>
            <p className="text-sm font-semibold text-gray-900">
              {(confidence * 100).toFixed(0)}%
            </p>
          </div>
        </div>
      </div>

      <p className="text-xs text-gray-600">Event ID: {eventId}</p>
    </div>
  )
}
