"use client"

import { useState } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import { Home, Cpu, Battery, Gauge, Receipt, Settings, Sun, ChevronLeft, ChevronRight, Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"

const navItems = [
  { icon: Home, label: "Dashboard", href: "/" },
  { icon: Cpu, label: "Inverters", href: "/inverters", badge: "3" },
  { icon: Battery, label: "Batteries", href: "/batteries", badge: "2" },
  { icon: Gauge, label: "Energy Meters", href: "/meters" },
  { icon: Receipt, label: "Billing", href: "/billing" },
  { icon: Settings, label: "Settings", href: "/settings" },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        "flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300 relative",
        collapsed ? "w-16" : "w-64",
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
          const isActive = pathname === item.href
          return (
            <Link key={item.label} href={item.href}>
              <Button
                variant={isActive ? "secondary" : "ghost"}
                className={cn(
                  "w-full justify-start gap-3 h-11",
                  isActive && "bg-sidebar-accent text-sidebar-accent-foreground",
                  collapsed && "justify-center px-2",
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
        <Button variant="ghost" className={cn("w-full justify-start gap-3", collapsed && "justify-center px-2")}>
          <Bell className="h-5 w-5" />
          {!collapsed && <span>Notifications</span>}
          {!collapsed && <Badge className="ml-auto bg-destructive text-destructive-foreground text-xs">2</Badge>}
        </Button>

        <div
          className={cn(
            "flex items-center gap-3 p-2 rounded-lg hover:bg-sidebar-accent transition-colors cursor-pointer",
            collapsed && "justify-center",
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
