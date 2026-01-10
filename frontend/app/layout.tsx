import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import Topbar from '@/components/Topbar'

export const metadata: Metadata = {
  title: 'CT4 Identity System',
  description: 'Sistema de Identidad Canónica',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Note: Suspense boundary needed for useSearchParams in client components
  return (
    <html lang="es">
      <body>
        <Sidebar />
        <Topbar />
        <main className="ml-64 mt-16 p-6">
          {children}
        </main>
      </body>
    </html>
  )
}
