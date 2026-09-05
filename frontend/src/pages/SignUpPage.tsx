import { SignUp } from '@clerk/clerk-react'
import { Link } from 'react-router-dom'
import '../auth.css'

export default function SignUpPage() {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1 className="auth-title">AgentTrust</h1>
        <p className="auth-subtitle">Create your merchant account</p>
        <SignUp />
        <p className="auth-switch">
          Already have an account? <Link to="/sign-in">Sign in</Link>
        </p>
      </div>
    </div>
  )
}