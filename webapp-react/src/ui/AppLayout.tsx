import React, { useState, useEffect } from 'react'
import { Link, Outlet, useLocation } from 'react-router-dom'
import { api } from '../lib/api'
import { ArraysResponse, ArrayInfo } from '../types/telemetry'

// Create a context for array selection
export const ArrayContext = React.createContext<{
  arrays: ArrayInfo[];
  selectedArray: string | null;
  setSelectedArray: (arrayId: string | null) => void;
}>({
  arrays: [],
  selectedArray: null,
  setSelectedArray: () => {},
})

export const AppLayout: React.FC = () => {
  const { pathname } = useLocation()
  const [arrays, setArrays] = useState<ArrayInfo[]>([])
  const [selectedArray, setSelectedArray] = useState<string | null>(null)

  useEffect(() => {
    const fetchArrays = async () => {
      try {
        const response: ArraysResponse = await api.get('/api/arrays')
        if (response.arrays && response.arrays.length > 0) {
          setArrays(response.arrays)
          // Auto-select first array if none selected
          if (!selectedArray) {
            setSelectedArray(response.arrays[0].id)
          }
        }
      } catch (error) {
        console.error('Error loading arrays:', error)
      }
    }
    fetchArrays()
  }, [])

  return (
    <ArrayContext.Provider value={{ arrays, selectedArray, setSelectedArray }}>
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
    </ArrayContext.Provider>
  )
}

