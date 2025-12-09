import { ReactNode } from "react";
import { AppSidebar } from "./AppSidebar";
import { MobileBottomNav } from "./MobileBottomNav";

interface AppLayoutProps {
  children: ReactNode;
}

export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-background flex">
      <AppSidebar />
      <MobileBottomNav />
      <main className="flex-1 md:ml-[72px] lg:ml-64 transition-all duration-300 pb-20 md:pb-0">
        {children}
      </main>
    </div>
  );
}
