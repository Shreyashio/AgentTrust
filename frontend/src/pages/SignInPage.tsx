import { SignIn } from '@clerk/clerk-react'
import { Link } from 'react-router-dom'
import '../auth.css'

export default function SignInPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">AgentTrust</h1>
        <p className="auth-subtitle">Sign in to your merchant account</p>
        <SignIn />
        <p className="auth-switch">
          New here? <Link to="/sign-up">Create an account</Link>
        </p>
      </div>
    </div>
  )
}