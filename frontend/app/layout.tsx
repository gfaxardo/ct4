import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import Topbar from '@/components/Topbar'
import { Providers } from './providers'

export const metadata: Metadata = {
  title: 'CT4 Identity System',
  description: 'Sistema de Identidad Canónica',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" className="antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className="font-sans" suppressHydrationWarning>
        <Providers>
          <Sidebar />
          <Topbar />
          <main className="ml-64 mt-16 min-h-[calc(100vh-4rem)]">
            <div className="p-6 animate-fade-in">
              {children}
            </div>
          </main>
        </Providers>
      </body>
    </html>
  )
}
