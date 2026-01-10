import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "@/hooks/use-theme";
import { BillingConfigProvider } from "@/hooks/use-billing-config";
import { AuthProvider } from "@/hooks/use-auth";
import ProtectedRoute from "@/components/ProtectedRoute";
import { ServiceWorkerUpdatePrompt } from "@/components/ServiceWorkerUpdatePrompt";
import Auth from "./pages/Auth";
import Index from "./pages/Index";
import Devices from "./pages/Devices";
import DeviceSettings from "./pages/DeviceSettings";
import DeviceManagement from "./pages/DeviceManagement";
import Telemetry from "./pages/Telemetry";
import SmartScheduler from "./pages/SmartScheduler";
import Settings from "./pages/Settings";
import Billing from "./pages/Billing";
import BillingSettings from "./pages/BillingSettings";
import Notifications from "./pages/Notifications";
import Profile from "./pages/Profile";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <ThemeProvider>
      <BillingConfigProvider>
        <AuthProvider>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <ServiceWorkerUpdatePrompt />
            <BrowserRouter basename="/start">
              <Routes>
                <Route path="/auth" element={<Auth />} />
                <Route path="/" element={<ProtectedRoute><Index /></ProtectedRoute>} />
                <Route path="/devices" element={<ProtectedRoute><Devices /></ProtectedRoute>} />
                <Route path="/devices/manage" element={<ProtectedRoute><DeviceManagement /></ProtectedRoute>} />
                <Route path="/devices/:deviceId/settings" element={<ProtectedRoute><DeviceSettings /></ProtectedRoute>} />
                <Route path="/telemetry" element={<ProtectedRoute><Telemetry /></ProtectedRoute>} />
                <Route path="/scheduler" element={<ProtectedRoute><SmartScheduler /></ProtectedRoute>} />
                <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
                <Route path="/billing" element={<ProtectedRoute><Billing /></ProtectedRoute>} />
                <Route path="/billing/settings" element={<ProtectedRoute><BillingSettings /></ProtectedRoute>} />
                <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
                <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </BrowserRouter>
          </TooltipProvider>
        </AuthProvider>
      </BillingConfigProvider>
    </ThemeProvider>
  </QueryClientProvider>
);

export default App;
