import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Home, Settings, Battery, Moon, Sun, Receipt, Gauge } from 'lucide-react'
import { useTheme } from '../../contexts/ThemeContext'
import { useMobile } from '../../hooks/useMobile'
import { AppSelector } from '../AppSelector'

interface SidebarProps {
  onClose?: () => void
  isDrawer?: boolean // If true, render horizontally for bottom drawer
}

export const Sidebar: React.FC<SidebarProps> = ({ onClose, isDrawer = false }) => {
  const location = useLocation()
  const { theme, toggleTheme } = useTheme()
  const { isMobile } = useMobile()

  const isActive = (path: string) => {
    if (path === '/' || path === '/dashboard-new') {
      return location.pathname === '/' || location.pathname === '/dashboard-new'
    }
    return location.pathname.startsWith(path)
  }

  const navItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/battery-detail', icon: Battery, label: 'Battery Detail' },
    { path: '/meter', icon: Gauge, label: 'Meter' },
    { path: '/billing', icon: Receipt, label: 'Billing' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  // Theme-aware colors
  const sidebarBg = theme === 'dark' ? '#312e81' : '#1f2937' // indigo-900 or gray-800
  const activeBg = theme === 'dark' ? '#1f2937' : '#ffffff' // gray-800 or white
  const activeText = theme === 'dark' ? '#ffffff' : '#312e81' // white or indigo-900
  const inactiveText = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(255, 255, 255, 0.7)'
  const hoverBg = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(255, 255, 255, 0.1)'
  const userBadgeBg = theme === 'dark' ? '#4b5563' : '#374151' // gray-600 or gray-700

  // Drawer-specific colors (drawer has different background)
  const drawerActiveBg = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(27, 34, 52, 0.1)'
  const drawerActiveText = theme === 'dark' ? '#ffffff' : '#1B2234'
  const drawerInactiveText = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(27, 34, 52, 0.7)'

  // Horizontal layout for bottom drawer
  if (isDrawer || (isMobile && onClose)) {
    // Split nav items into two rows for mobile (3 items per row)
    const firstRow = navItems.slice(0, 3)
    const secondRow = navItems.slice(3)
    
    return (
      <div 
        className="flex flex-col items-center justify-center px-2 py-3 gap-2"
        style={{ backgroundColor: 'transparent' }}
      >
        {/* Logo */}
        <div className="w-8 h-8 flex items-center justify-center flex-shrink-0 mb-1">
          <div className="w-7 h-7 bg-pink-500 rounded-lg flex items-center justify-center">
            <span className="text-white text-xs font-bold">S</span>
          </div>
        </div>

        {/* Navigation - Two rows */}
        <div className="flex flex-col gap-2 w-full">
          {/* First Row */}
          <div className="flex flex-row gap-2 justify-center">
            {firstRow.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onClose}
                  className="flex flex-col items-center justify-center rounded-lg transition-colors px-2 py-1.5 flex-1"
                  style={{
                    backgroundColor: active ? drawerActiveBg : 'transparent',
                    color: active ? drawerActiveText : drawerInactiveText,
                  }}
                  title={item.label}
                >
                  <Icon className="w-7 h-7 mb-0.5" style={{ color: active ? drawerActiveText : drawerInactiveText }} />
                  <span className="text-xs" style={{ fontSize: '9px', color: active ? drawerActiveText : drawerInactiveText }}>{item.label}</span>
                </Link>
              )
            })}
          </div>
          
          {/* Second Row */}
          <div className="flex flex-row gap-2 justify-center">
            {secondRow.map((item) => {
              const Icon = item.icon
              const active = isActive(item.path)
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={onClose}
                  className="flex flex-col items-center justify-center rounded-lg transition-colors px-2 py-1.5 flex-1"
                  style={{
                    backgroundColor: active ? drawerActiveBg : 'transparent',
                    color: active ? drawerActiveText : drawerInactiveText,
                  }}
                  title={item.label}
                >
                  <Icon className="w-7 h-7 mb-0.5" style={{ color: active ? drawerActiveText : drawerInactiveText }} />
                  <span className="text-xs" style={{ fontSize: '9px', color: active ? drawerActiveText : drawerInactiveText }}>{item.label}</span>
                </Link>
              )
            })}
            {/* App Selector in second row */}
            <AppSelector isDrawer={true} />
            {/* Theme Toggle in second row */}
            <button
              onClick={toggleTheme}
              className="flex flex-col items-center justify-center rounded-lg transition-colors px-2 py-1.5 flex-1"
              style={{
                backgroundColor: 'transparent',
                color: drawerInactiveText,
              }}
              aria-label="Toggle theme"
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? (
                <Sun className="w-7 h-7 mb-0.5" style={{ color: drawerInactiveText }} />
              ) : (
                <Moon className="w-7 h-7 mb-0.5" style={{ color: drawerInactiveText }} />
              )}
              <span className="text-xs" style={{ fontSize: '9px', color: drawerInactiveText }}>Theme</span>
            </button>
          </div>
        </div>

        {/* User Badge */}
        <div 
          className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
          style={{ backgroundColor: userBadgeBg }}
        >
          <span className="text-white text-xs font-bold">UN</span>
        </div>
      </div>
    )
  }

  // Vertical layout for desktop sidebar
  return (
    <div 
      className="fixed left-0 top-0 h-screen w-16 flex flex-col items-center py-6 gap-6 z-30"
      style={{ backgroundColor: sidebarBg }}
    >
      {/* Logo */}
      <div className="w-10 h-10 flex items-center justify-center flex-shrink-0">
        <div className="w-8 h-8 bg-pink-500 rounded-lg flex items-center justify-center">
          <span className="text-white text-xs font-bold">S</span>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex flex-col gap-4 flex-shrink-0">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = isActive(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              onClick={onClose}
              className="w-12 h-12 flex items-center justify-center rounded-lg transition-colors flex-shrink-0"
              style={{
                backgroundColor: active ? activeBg : 'transparent',
                color: active ? activeText : inactiveText,
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.backgroundColor = hoverBg
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.backgroundColor = 'transparent'
                }
              }}
              title={item.label}
            >
              <Icon className="w-6 h-6" />
            </Link>
          )
        })}
      </div>

      {/* App Selector */}
      <div className="mt-auto mb-2" style={{ position: 'relative', zIndex: 100 }}>
        <AppSelector />
      </div>
      {/* Theme Toggle */}
      <button
        onClick={toggleTheme}
        className="w-12 h-12 flex items-center justify-center rounded-lg transition-colors flex-shrink-0"
        style={{
          color: inactiveText,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = hoverBg
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'transparent'
        }}
        aria-label="Toggle theme"
        title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      >
        {theme === 'dark' ? (
          <Sun className="w-6 h-6" />
        ) : (
          <Moon className="w-6 h-6" />
        )}
      </button>

      {/* User Badge */}
      <div 
        className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
        style={{ backgroundColor: userBadgeBg }}
      >
        <span className="text-white text-xs font-bold">UN</span>
      </div>
    </div>
  )
}
