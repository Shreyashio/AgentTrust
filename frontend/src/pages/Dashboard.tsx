import { NavLink, Route, Routes } from 'react-router-dom'
import { useClerk, useUser } from '@clerk/clerk-react'
import { API_BASE_URL } from '../lib/api'
import OverviewPage from './sections/OverviewPage'
import InventoryPage from './sections/InventoryPage'
import AgentPage from './sections/AgentPage'
import GovernancePage from './sections/GovernancePage'
import OrdersPage from './sections/OrdersPage'
import RoasPage from './sections/RoasPage'
import AuditPage from './sections/AuditPage'

const navLinks = [
  { to: '/dashboard', label: 'Overview', end: true },
  { to: '/dashboard/inventory', label: 'Inventory' },
  { to: '/dashboard/agent', label: 'Agent' },
  { to: '/dashboard/governance', label: 'Governance' },
  { to: '/dashboard/orders', label: 'Orders' },
  { to: '/dashboard/roas', label: 'ROAS' },
  { to: '/dashboard/audit', label: 'Audit Trail' },
]

export default function Dashboard() {
  const { signOut } = useClerk()
  const { user } = useUser()

  return (
    <div className="dashboard">
      <aside className="sidebar">
        <div className="brand">AgentTrust</div>
        <nav>
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      <main className="content">
        <header className="topbar">
          <span className="user-email">
            {user?.emailAddresses[0]?.emailAddress}{' '}
            <a href={`${API_BASE_URL}/storefront`} target="_blank" rel="noreferrer" style={{ marginLeft: '1rem' }}>
              Demo Storefront
            </a>
          </span>
          {/* Sign Out button — visible on every dashboard page. */}
          <button className="signout-btn" onClick={() => signOut({ redirectUrl: '/sign-in' })}>
            Sign Out
          </button>
        </header>

        <Routes>
          <Route index element={<OverviewPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="agent" element={<AgentPage />} />
          <Route path="governance" element={<GovernancePage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="roas" element={<RoasPage />} />
          <Route path="audit" element={<AuditPage />} />
        </Routes>
      </main>
    </div>
  )
}