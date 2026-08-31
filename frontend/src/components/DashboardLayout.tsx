/**
 * Main dashboard layout
 */

'use client'

import React from 'react'
import { AlertTriangle, TrendingUp, BarChart3, Shield } from 'lucide-react'

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-red-500" />
              <h1 className="text-2xl font-bold text-gray-900">LossGraph</h1>
              <p className="text-sm text-gray-600 ml-4">
                AI Risk Manager for Merchant Loss Intelligence
              </p>
            </div>
            <div className="flex items-center gap-4">
              <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">
                Settings
              </button>
              <button className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700">
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200 sticky top-16 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex gap-8">
            <a
              href="/dashboard"
              className="px-4 py-4 text-sm font-medium text-gray-700 border-b-2 border-red-500 hover:text-gray-900"
            >
              Dashboard
            </a>
            <a
              href="/incidents"
              className="px-4 py-4 text-sm font-medium text-gray-600 border-b-2 border-transparent hover:text-gray-900 hover:border-gray-300"
            >
              Incidents
            </a>
            <a
              href="/investigation"
              className="px-4 py-4 text-sm font-medium text-gray-600 border-b-2 border-transparent hover:text-gray-900 hover:border-gray-300"
            >
              Investigation
            </a>
            <a
              href="/chargebacks"
              className="px-4 py-4 text-sm font-medium text-gray-600 border-b-2 border-transparent hover:text-gray-900 hover:border-gray-300"
            >
              Chargebacks
            </a>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
