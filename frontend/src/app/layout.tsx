/**
 * Root layout
 */

import type { Metadata } from 'next'
import { IBM_Plex_Mono, Inter, Space_Grotesk } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter', display: 'swap' })
const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
  weight: ['500', '600', '700'],
})
const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  display: 'swap',
  weight: ['400', '500', '600'],
})

export const metadata: Metadata = {
  title: 'LossGraph - Merchant Risk Intelligence',
  description: 'AI Risk Manager for Merchant Loss Intelligence',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable} ${plexMono.variable}`}>
      <body className="bg-canvas text-ink font-sans antialiased">{children}</body>
    </html>
  )
}
