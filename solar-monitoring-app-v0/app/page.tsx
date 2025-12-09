import { Sidebar } from "@/components/sidebar"
import { DashboardContent } from "@/components/dashboard-content"

export default function Home() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <DashboardContent />
      </main>
    </div>
  )
}
