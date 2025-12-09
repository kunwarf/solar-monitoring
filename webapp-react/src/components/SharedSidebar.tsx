import React, { useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { Home, Cpu, Battery, Gauge, Receipt, Settings, Sun, ChevronLeft, ChevronRight, Bell, Moon } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import { AppSelector } from './AppSelector'
import { cn } from '../apps/v0/lib/utils'

// Import UI components - use v0 components for consistent styling
import { Button } from '../apps/v0/components/ui/button'
import { Avatar, AvatarFallback } from '../apps/v0/components/ui/avatar'
import { Badge } from '../apps/v0/components/ui/badge'

// Import theme contexts
import { useTheme as useDefaultTheme } from '../contexts/ThemeContext'
import { useV0Theme } from '../apps/v0/contexts/V0ThemeContext'

// Import v0 styles for CSS variables
import '../apps/v0/styles/globals.css'

// Navigation items configuration per app
const getNavItems = (appId: string) => {
  if (appId === 'v0') {
    return [
      { icon: Home, label: 'Dashboard', href: '/v0' },
      { icon: Cpu, label: 'Inverters', href: '/v0/inverters', badge: '3' },
      { icon: Battery, label: 'Batteries', href: '/v0/batteries', badge: '2' },
      { icon: Gauge, label: 'Energy Meters', href: '/v0/meters' },
      { icon: Receipt, label: 'Billing', href: '/v0/billing' },
      { icon: Settings, label: 'Settings', href: '/v0/settings' },
    ]
  }
  
  // Default app navigation
  return [
    { icon: Home, label: 'Dashboard', href: '/' },
    { icon: Battery, label: 'Battery Detail', href: '/battery-detail' },
    { icon: Gauge, label: 'Meter', href: '/meter' },
    { icon: Receipt, label: 'Billing', href: '/billing' },
    { icon: Settings, label: 'Settings', href: '/settings' },
  ]
}

export function SharedSidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const { currentApp } = useApp()
  const navItems = getNavItems(currentApp.id)
  
  // Always call both theme hooks (required by React rules)
  // useV0Theme now returns a safe default if not in provider
  const v0Theme = useV0Theme()
  const defaultTheme = useDefaultTheme()
  
  // Use v0 theme if in v0 app, otherwise use default theme
  const theme = currentApp.id === 'v0' ? v0Theme.theme : defaultTheme.theme
  const toggleTheme = currentApp.id === 'v0' ? v0Theme.toggleTheme : defaultTheme.toggleTheme

  return (
    <aside
      className={cn(
        'flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300 relative h-screen overflow-hidden',
        collapsed ? 'w-16' : 'w-64',
      )}
      style={{
        backgroundColor: 'var(--sidebar)',
        borderColor: 'var(--sidebar-border)',
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 p-4 border-b border-sidebar-border">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
          <Sun className="h-6 w-6 text-primary-foreground" />
        </div>
        {!collapsed && (
          <div>
            <h1 className="font-semibold text-sidebar-foreground">SolarFlow</h1>
            <p className="text-xs text-muted-foreground">Energy Monitor</p>
          </div>
        )}
      </div>

      {/* Navigation - Using Link for proper navigation */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href || 
            (item.href === '/v0' && location.pathname === '/v0') ||
            (item.href === '/' && location.pathname === '/')
          return (
            <Link key={item.label} to={item.href}>
              <Button
                variant={isActive ? 'secondary' : 'ghost'}
                className={cn(
                  'w-full justify-start gap-3 h-11',
                  isActive 
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground' 
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  collapsed && 'justify-center px-2',
                )}
              >
                <item.icon className={cn(
                  'h-5 w-5 shrink-0',
                  isActive ? 'text-sidebar-accent-foreground' : 'text-sidebar-foreground'
                )} />
                {!collapsed && (
                  <>
                    <span className={cn(
                      'flex-1 text-left',
                      isActive ? 'text-sidebar-accent-foreground' : 'text-sidebar-foreground'
                    )}>{item.label}</span>
                    {item.badge && (
                      <Badge variant="secondary" className="bg-primary/20 text-primary text-xs">
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </Button>
            </Link>
          )
        })}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 border-t border-sidebar-border space-y-2">
        {/* App Selector */}
        <div className={cn('w-full', collapsed && 'flex justify-center')}>
          {collapsed ? (
            <AppSelector />
          ) : (
            <div className="w-full">
              <AppSelector />
            </div>
          )}
        </div>

        {/* Theme Toggle */}
        <Button 
          variant="ghost" 
          className={cn(
            'w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
            collapsed && 'justify-center px-2'
          )}
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {theme === 'dark' ? (
            <Sun className="h-5 w-5 text-sidebar-foreground" />
          ) : (
            <Moon className="h-5 w-5 text-sidebar-foreground" />
          )}
          {!collapsed && <span className="text-sidebar-foreground">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
        </Button>

        <Button 
          variant="ghost" 
          className={cn(
            'w-full justify-start gap-3 text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
            collapsed && 'justify-center px-2'
          )}
        >
          <Bell className="h-5 w-5 text-sidebar-foreground" />
          {!collapsed && <span className="text-sidebar-foreground">Notifications</span>}
          {!collapsed && <Badge className="ml-auto bg-destructive text-destructive-foreground text-xs">2</Badge>}
        </Button>

        <div
          className={cn(
            'flex items-center gap-3 p-2 rounded-lg hover:bg-sidebar-accent transition-colors cursor-pointer',
            collapsed && 'justify-center',
          )}
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback className="bg-primary/20 text-primary text-sm">JD</AvatarFallback>
          </Avatar>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-sidebar-foreground truncate">John Doe</p>
              <p className="text-xs text-muted-foreground truncate">Home Owner</p>
            </div>
          )}
        </div>
      </div>

      {/* Collapse Toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-1/2 -right-3 h-6 w-6 rounded-full border border-sidebar-border bg-sidebar hover:bg-sidebar-accent"
        onClick={() => setCollapsed(!collapsed)}
      >
        {collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronLeft className="h-3 w-3" />}
      </Button>
    </aside>
  )
}

