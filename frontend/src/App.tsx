import { Routes, Route, Navigate } from 'react-router-dom'
import { GuestOnly, RequireAuth } from './components/AuthGuards'
import SignInPage from './pages/SignInPage'
import SignUpPage from './pages/SignUpPage'
import Dashboard from './pages/Dashboard'

export default function App() {
  return (
    <Routes>
      {/* The dashboard handles its own redirect: signed-out users get sent to /sign-in. */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/sign-in" element={<GuestOnly><SignInPage /></GuestOnly>} />
      <Route path="/sign-up" element={<GuestOnly><SignUpPage /></GuestOnly>} />
      <Route path="/dashboard/*" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}