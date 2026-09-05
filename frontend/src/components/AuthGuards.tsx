import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '@clerk/clerk-react'

// Used for pages that need a logged-in merchant.
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth()

  // Clerk is still checking the session token — show a quick loader.
  if (!isLoaded) {
    return <div className="loading">Loading…</div>
  }

  // Not logged in → send to the sign-in page.
  if (!isSignedIn) {
    return <Navigate to="/sign-in" replace />
  }

  return children
}

// Used for pages like /sign-in that only make sense for signed-out users.
export function GuestOnly({ children }: { children: ReactNode }) {
  const { isLoaded, isSignedIn } = useAuth()

  if (!isLoaded) {
    return <div className="loading">Loading…</div>
  }

  // Already logged in → send to the dashboard.
  if (isSignedIn) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}