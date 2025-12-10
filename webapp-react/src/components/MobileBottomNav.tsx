import { useState } from "react";
import { useLocation, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  Home,
  Cpu,
  Battery,
  Gauge,
  Receipt,
  Settings,
  ChevronUp,
  X,
  Sun,
  Moon,
  Brain,
} from "lucide-react";
import { cn } from "../apps/v0/lib/utils";
import { useApp } from "../contexts/AppContext";
import { AppSelector } from "./AppSelector";

// Import theme contexts
import { useTheme as useDefaultTheme } from "../contexts/ThemeContext";
import { useV0Theme } from "../apps/v0/contexts/V0ThemeContext";
import { useTheme as useStartTheme } from "../apps/start/src/hooks/use-theme";

// Navigation items configuration per app
const getPrimaryNavItems = (appId: string) => {
  if (appId === "v0") {
    return [
      { icon: Home, label: "Dashboard", href: "/v0" },
      { icon: Cpu, label: "Inverters", href: "/v0/inverters" },
      { icon: Battery, label: "Batteries", href: "/v0/batteries" },
      { icon: Gauge, label: "Meters", href: "/v0/meters" },
    ];
  }
  
  if (appId === "start") {
    return [
      { icon: Home, label: "Dashboard", href: "/start" },
      { icon: Cpu, label: "Devices", href: "/start/devices" },
      { icon: Gauge, label: "Telemetry", href: "/start/telemetry" },
      { icon: Brain, label: "Scheduler", href: "/start/scheduler" },
    ];
  }
  
  // Default app
  return [
    { icon: Home, label: "Dashboard", href: "/" },
    { icon: Battery, label: "Battery", href: "/battery-detail" },
    { icon: Gauge, label: "Meter", href: "/meter" },
    { icon: Receipt, label: "Billing", href: "/billing" },
  ];
};

const getSecondaryNavItems = (appId: string) => {
  if (appId === "v0") {
    return [
      { icon: Receipt, label: "Billing", href: "/v0/billing" },
      { icon: Settings, label: "Settings", href: "/v0/settings" },
    ];
  }
  
  if (appId === "start") {
    return [
      { icon: Receipt, label: "Billing", href: "/start/billing" },
      { icon: Settings, label: "Settings", href: "/start/settings" },
    ];
  }
  
  // Default app
  return [
    { icon: Settings, label: "Settings", href: "/settings" },
  ];
};

export function MobileBottomNav() {
  const [expanded, setExpanded] = useState(false);
  const location = useLocation();
  const { currentApp } = useApp();
  
  // Always call all theme hooks (required by React rules)
  const v0Theme = useV0Theme();
  const startTheme = useStartTheme();
  const defaultTheme = useDefaultTheme();
  
  // Use appropriate theme based on current app
  let theme: "light" | "dark";
  let toggleTheme: () => void;
  
  if (currentApp.id === "v0") {
    theme = v0Theme.theme;
    toggleTheme = v0Theme.toggleTheme;
  } else if (currentApp.id === "start") {
    theme = startTheme.theme;
    toggleTheme = startTheme.toggleTheme;
  } else {
    theme = defaultTheme.theme;
    toggleTheme = defaultTheme.toggleTheme;
  }

  const primaryNavItems = getPrimaryNavItems(currentApp.id);
  const secondaryNavItems = getSecondaryNavItems(currentApp.id);

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
        className="fixed bottom-0 left-0 right-0 bg-sidebar border-t border-sidebar-border z-50 md:hidden overflow-hidden"
      >
        {/* Expanded Menu */}
        <AnimatePresence>
          {expanded && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              className="p-4 space-y-2 border-b border-sidebar-border max-h-[60vh] overflow-y-auto"
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

              {/* App Selector - Mobile version with all apps visible */}
              <div className="mb-3">
                <AppSelector isMobileExpanded={true} />
              </div>

              {/* Secondary Nav Items */}
              {secondaryNavItems.map((item) => {
                const isActive = location.pathname === item.href || 
                  (item.href === "/v0" && location.pathname === "/v0") ||
                  (item.href === "/" && location.pathname === "/") ||
                  (item.href === "/start" && location.pathname === "/start");
                return (
                  <Link
                    key={item.label}
                    to={item.href}
                    onClick={() => setExpanded(false)}
                    className={cn(
                      "flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
                      isActive
                        ? "bg-primary/10 text-primary border border-primary/20"
                        : "text-sidebar-foreground hover:bg-sidebar-accent border border-transparent"
                    )}
                  >
                    <item.icon className="w-5 h-5" />
                    <span className="font-medium">{item.label}</span>
                  </Link>
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
            const isActive = location.pathname === item.href || 
              (item.href === "/v0" && location.pathname === "/v0") ||
              (item.href === "/" && location.pathname === "/") ||
              (item.href === "/start" && location.pathname === "/start");
            return (
              <Link
                key={item.label}
                to={item.href}
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
                <span className="text-[10px] font-medium">{item.label}</span>
              </Link>
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

