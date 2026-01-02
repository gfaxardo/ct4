/**
 * Home - Redirige a dashboard
 */

import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/dashboard')
}
