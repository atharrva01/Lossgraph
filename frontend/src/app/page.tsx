/**
 * Home/Dashboard page
 */

'use client'

import React, { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, BarChart3, Eye, ArrowUp } from 'lucide-react'
import { DashboardLayout } from '@/components/DashboardLayout'
import { IncidentCard } from '@/components/IncidentCard'
import { incidentApi, healthApi } from '@/lib/api'

export default function Dashboard() {
  const [incidents, setIncidents] = useState([])
  const [stats, setStats] = useState({
    currentExposure: 0,
    preventableExposure: 0,
    activeIncidents: 0,
    riskAcceleration: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      
      // Check health
      await healthApi.check()
      
      // Load incidents for demo merchant
      const response = await incidentApi.getIncidents('DEMO_MERCHANT_001', 'detected')
      setIncidents(response.data.incidents || [])
      
      // Set demo stats
      setStats({
        currentExposure: 842000,
        preventableExposure: 517000,
        activeIncidents: response.data.active_incidents || 0,
        riskAcceleration: 3.7,
      })
      
      setError(null)
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError('Failed to load dashboard data. Please try again.')
      // Set demo data for development
      setStats({
        currentExposure: 842000,
        preventableExposure: 517000,
        activeIncidents: 4,
        riskAcceleration: 3.7,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <DashboardLayout>
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-gray-600">Current Exposure</p>
            <AlertTriangle className="w-5 h-5 text-red-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            ₹{(stats.currentExposure / 100000).toFixed(2)}L
          </p>
          <p className="text-xs text-gray-500 mt-2">Total at-risk amount</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-gray-600">Preventable Exposure</p>
            <Eye className="w-5 h-5 text-green-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">
            ₹{(stats.preventableExposure / 100000).toFixed(2)}L
          </p>
          <p className="text-xs text-gray-500 mt-2">With optimal intervention</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-gray-600">Active Incidents</p>
            <BarChart3 className="w-5 h-5 text-yellow-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">{stats.activeIncidents}</p>
          <p className="text-xs text-gray-500 mt-2">Ongoing risk events</p>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <p className="text-sm font-medium text-gray-600">Risk Acceleration</p>
            <ArrowUp className="w-5 h-5 text-orange-500" />
          </div>
          <p className="text-3xl font-bold text-gray-900">↑ {stats.riskAcceleration}×</p>
          <p className="text-xs text-gray-500 mt-2">vs. baseline</p>
        </div>
      </div>

      {/* Active Loss Events */}
      <div className="mb-8">
        <h2 className="text-xl font-bold text-gray-900 mb-6">Active Loss Events</h2>
        
        {error && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-yellow-800">{error}</p>
            <p className="text-xs text-yellow-600 mt-2">Showing demo data for development</p>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-12">
            <p className="text-gray-600">Loading incidents...</p>
          </div>
        ) : incidents.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {incidents.map((incident: any) => (
              <IncidentCard
                key={incident.event_id}
                eventId={incident.event_id}
                eventType={incident.event_type}
                exposure={incident.exposure}
                confidence={incident.confidence}
                status={incident.status}
                onClick={() => {
                  // Navigate to incident details
                  console.log('Click incident:', incident.event_id)
                }}
              />
            ))}
          </div>
        ) : (
          <div className="bg-gray-50 border border-dashed border-gray-300 rounded-lg p-12 text-center">
            <p className="text-gray-600">No active incidents detected</p>
            <p className="text-xs text-gray-500 mt-1">Your merchant is operating normally</p>
          </div>
        )}
      </div>

      {/* Demo Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm font-semibold text-blue-900">Demo Mode</p>
        <p className="text-xs text-blue-800 mt-1">
          This dashboard is in development mode. Make sure the backend API is running on http://localhost:8000
        </p>
      </div>
    </DashboardLayout>
  )
}
