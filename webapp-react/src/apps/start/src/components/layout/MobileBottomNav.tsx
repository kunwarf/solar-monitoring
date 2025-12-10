import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  Cpu,
  Activity,
  Settings,
  Receipt,
  ChevronUp,
  X,
  Sun,
  Moon,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/hooks/use-theme";

const primaryNavItems = [
  { title: "Dashboard", url: "/", icon: LayoutDashboard },
  { title: "Devices", url: "/devices", icon: Cpu },
  { title: "Telemetry", url: "/telemetry", icon: Activity },
  { title: "Scheduler", url: "/scheduler", icon: Brain },
];

const secondaryNavItems = [
  { title: "Settings", url: "/settings", icon: Settings },
  { title: "Billing", url: "/billing", icon: Receipt },
];

export function MobileBottomNav() {
  const [expanded, setExpanded] = useState(false);
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  return (
    <>
      {/* Overlay */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
            onClick={() => setExpanded(false)}
          />
        )}
      </AnimatePresence>

      {/* Bottom Navigation */}
      <motion.nav
        initial={false}
        animate={{ height: expanded ? "auto" : 72 }}
        className="fixed bottom-0 left-0 right-0 bg-sidebar border-t border-sidebar-border z-50 md:hidden"
      >
        {/* Expanded Menu */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="p-4 space-y-2 border-b border-sidebar-border"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-muted-foreground">More Options</span>
                <button
                  onClick={() => setExpanded(false)}
                  className="p-1.5 rounded-lg hover:bg-sidebar-accent text-muted-foreground"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Secondary Nav Items */}
              {secondaryNavItems.map((item) => {
                const isActive = location.pathname === item.url;
                return (
                  <NavLink
                    key={item.title}
                    to={item.url}
                    onClick={() => setExpanded(false)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                      isActive
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "text-sidebar-foreground hover:bg-sidebar-accent border border-transparent"
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="font-medium">{item.title}</span>
                  </NavLink>
                );
              })}

              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className="w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all text-sidebar-foreground hover:bg-sidebar-accent border border-transparent"
              >
                {theme === "dark" ? (
                  <>
                    <Sun className="w-5 h-5" />
                    <span className="font-medium">Light Mode</span>
                  </>
                ) : (
                  <>
                    <Moon className="w-5 h-5" />
                    <span className="font-medium">Dark Mode</span>
                  </>
                )}
              </button>

              {/* System Status */}
              <div className="mt-4 p-3 glass-card">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full status-online" />
                  <span className="text-xs text-muted-foreground">System Online</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Primary Nav Bar */}
        <div className="flex items-center justify-around h-[72px] px-2">
          {primaryNavItems.map((item) => {
            const isActive = location.pathname === item.url;
            return (
              <NavLink
                key={item.title}
                to={item.url}
                className={cn(
                  "flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all min-w-[64px]",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                <div className={cn(
                  "p-2 rounded-xl transition-all",
                  isActive && "bg-primary/10"
                )}>
                  <item.icon className="w-5 h-5" />
                </div>
                <span className="text-[10px] font-medium">{item.title}</span>
              </NavLink>
            );
          })}

          {/* Expand Button */}
          <button
            onClick={() => setExpanded(!expanded)}
            className={cn(
              "flex flex-col items-center gap-1 px-4 py-2 rounded-xl transition-all min-w-[64px]",
              expanded
                ? "text-primary"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            <div className={cn(
              "p-2 rounded-xl transition-all",
              expanded && "bg-primary/10"
            )}>
              <ChevronUp className={cn(
                "w-5 h-5 transition-transform duration-300",
                expanded && "rotate-180"
              )} />
            </div>
            <span className="text-[10px] font-medium">More</span>
          </button>
        </div>
      </motion.nav>
    </>
  );
}