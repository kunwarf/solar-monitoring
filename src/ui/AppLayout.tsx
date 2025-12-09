import React from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'

export const AppLayout: React.FC = () => {
  const { pathname } = useLocation()
  return (
    <div className="app">
      <nav className="nav">
        <div className="brand">Solar Monitoring</div>
        <div className="links">
          <Link className={pathname === '/' ? 'active' : ''} to="/">Home</Link>
          <Link className={pathname.startsWith('/dashboard') ? 'active' : ''} to="/dashboard">Dashboard</Link>
          <Link className={pathname.startsWith('/battery') ? 'active' : ''} to="/battery">Battery</Link>
          <Link className={pathname.startsWith('/settings') ? 'active' : ''} to="/settings">Settings</Link>
          <Link className={pathname.startsWith('/analytics') ? 'active' : ''} to="/analytics">Analytics</Link>
        </div>
      </nav>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}

