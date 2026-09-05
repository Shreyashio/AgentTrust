import { useAuth } from '@clerk/clerk-react'

// Your FastAPI backend. Override with a VITE_API_URL variable in frontend/.env if needed.
// In a production build the dashboard is served by the backend itself, so we default
// to same-origin (''); in local dev the Vite server differs from the API, so default
// to localhost:8000.
export const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.PROD ? '' : 'http://localhost:8000')

// Returns an apiFetch() function that:
//   1. grabs your Clerk session token (a JWT),
//   2. sends it as "Authorization: Bearer <token>" on every request,
//   3. bounces to /sign-in if the backend says the token is invalid (401).
export function useApi() {
  const { getToken } = useAuth()

  async function apiFetch(path: string, options: RequestInit = {}) {
    // Our Clerk session token, signed for us by Clerk.
    const token = await getToken()

    const headers = new Headers(options.headers)
    headers.set('Authorization', `Bearer ${token}`)

    // Automatically send JSON bodies with the right Content-Type.
    if (options.body && !headers.has('Content-Type')) {
      headers.set('Content-Type', 'application/json')
    }

    const res = await fetch(`${API_BASE_URL}${path}`, { ...options, headers })

    // Expired or invalid token -> ask the merchant to sign in again.
    if (res.status === 401) {
      window.location.href = '/sign-in'
      throw new Error('Your session expired. Please sign in again.')
    }

    return res
  }

  return { apiFetch }
}