import React, { useState } from 'react'
import { useLocation, Link } from 'react-router-dom'
import { cn } from '../lib/utils'
import { Home, Cpu, Battery, Gauge, Receipt, Settings, Sun, ChevronLeft, ChevronRight, Bell } from 'lucide-react'
import { Button } from './ui/button'
import { Avatar, AvatarFallback } from './ui/avatar'
import { Badge } from './ui/badge'

const navItems = [
  { icon: Home, label: 'Dashboard', href: '/v0' },
  { icon: Cpu, label: 'Inverters', href: '/v0/inverters', badge: '3' },
  { icon: Battery, label: 'Batteries', href: '/v0/batteries', badge: '2' },
  { icon: Gauge, label: 'Energy Meters', href: '/v0/meters' },
  { icon: Receipt, label: 'Billing', href: '/v0/billing' },
  { icon: Settings, label: 'Settings', href: '/v0/settings' },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  return (
    <aside
      className={cn(
        'flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300 relative',
        collapsed ? 'w-16' : 'w-64',
      )}
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
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.href || (item.href === '/v0' && location.pathname === '/v0')
          return (
            <Link key={item.label} to={item.href}>
              <Button
                variant={isActive ? 'secondary' : 'ghost'}
                className={cn(
                  'w-full justify-start gap-3 h-11',
                  isActive && 'bg-sidebar-accent text-sidebar-accent-foreground',
                  collapsed && 'justify-center px-2',
                )}
              >
                <item.icon className="h-5 w-5 shrink-0" />
                {!collapsed && (
                  <>
                    <span className="flex-1 text-left">{item.label}</span>
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
        <Button variant="ghost" className={cn('w-full justify-start gap-3', collapsed && 'justify-center px-2')}>
          <Bell className="h-5 w-5" />
          {!collapsed && <span>Notifications</span>}
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

