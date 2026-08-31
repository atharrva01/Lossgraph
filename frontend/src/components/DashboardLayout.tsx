/**
 * Main dashboard layout
 */

'use client'

import React from 'react'
import Link from 'next/link'
import { Shield } from 'lucide-react'

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-3">
              <Shield className="w-7 h-7 text-red-500" />
              <h1 className="text-xl font-bold text-gray-900">LossGraph</h1>
            </Link>
            <p className="text-sm text-gray-500 ml-2 hidden sm:block">
              AI Risk Manager for Merchant Loss Intelligence
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
