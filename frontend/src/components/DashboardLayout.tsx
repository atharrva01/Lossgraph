/**
 * Main dashboard layout
 */

'use client'

import React from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { BookOpen, Gauge, Receipt, Shield } from 'lucide-react'

const NAV_LINKS = [
  { href: '/', label: 'Command Center', icon: Gauge },
  { href: '/chargebacks', label: 'Chargebacks', icon: Receipt },
  { href: '/how-it-works', label: 'How It Works', icon: BookOpen },
]

export const DashboardLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const pathname = usePathname()

  return (
    <div className="min-h-screen bg-canvas">
      <header className="bg-surface border-b border-line sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link href="/" className="flex items-center gap-3">
              <span className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center shrink-0">
                <Shield className="w-4 h-4 text-white" />
              </span>
              <div className="hidden sm:block leading-none">
                <p className="font-display font-semibold text-[15px] text-ink">LossGraph</p>
                <p className="text-[11px] text-slate-400 mt-0.5">Merchant Loss Intelligence</p>
              </div>
            </Link>

            <nav className="flex items-center gap-1">
              {NAV_LINKS.map((link) => {
                const active = link.href === '/' ? pathname === '/' : pathname.startsWith(link.href)
                const Icon = link.icon
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      active ? 'bg-brand-50 text-brand-700' : 'text-slate-500 hover:text-ink hover:bg-canvas'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="hidden md:inline">{link.label}</span>
                  </Link>
                )
              })}
            </nav>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 lg:px-8 py-10">
        {children}
      </main>
    </div>
  )
}
