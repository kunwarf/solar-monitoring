import React, { useState, useEffect, useContext } from 'react'
import { api } from '../lib/api'
import { ArrayContext } from '../ui/AppLayout'
import { useMobile } from '../hooks/useMobile'
import { MonthlyBillCard } from '../components/Billing/MonthlyBillCard'
import { ImportExportChart } from '../components/Billing/ImportExportChart'
import { DailyBillingWidgets } from '../components/Billing/DailyBillingWidgets'
import { CapacityMeter } from '../components/Billing/CapacityMeter'
import { ForecastCard } from '../components/Billing/ForecastCard'
import { CreditLedger } from '../components/Billing/CreditLedger'
import { BillTrendChart } from '../components/Billing/BillTrendChart'
import { SolarLoadComparison } from '../components/Billing/SolarLoadComparison'

export const BillingDashboardPage: React.FC = () => {
  const { selectedArray } = useContext(ArrayContext)
  const { isMobile } = useMobile()
  const [loading, setLoading] = useState(true)
  const [billingSummary, setBillingSummary] = useState<any>(null)
  const [runningBill, setRunningBill] = useState<any>(null)
  const [dailyData, setDailyData] = useState<any[]>([])
  const [trendData, setTrendData] = useState<any[]>([])
  const [capacityStatus, setCapacityStatus] = useState<any>(null)
  const [forecast, setForecast] = useState<any>(null)
  const [selectedYear, setSelectedYear] = useState<number>(new Date().getFullYear())
  const [triggering, setTriggering] = useState(false)
  const [triggerMessage, setTriggerMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  useEffect(() => {
    fetchBillingData()
  }, [selectedYear])

  const fetchBillingData = async () => {
    setLoading(true)
    try {
      // Fetch current billing summary
      const summaryRes = await api.get('/api/billing/summary')
      if (summaryRes?.status === 'ok') {
        setBillingSummary(summaryRes.billing)
      }

      // Fetch running bill (current month to-date)
      const runningRes = await api.get('/api/billing/running')
      if (runningRes && !runningRes.error) {
        setRunningBill(runningRes)
      }

      // Fetch daily data for last 30 days
      const today = new Date()
      const thirtyDaysAgo = new Date(today)
      thirtyDaysAgo.setDate(today.getDate() - 30)
      const dailyRes = await api.get(
        `/api/billing/daily?from=${thirtyDaysAgo.toISOString().split('T')[0]}&to=${today.toISOString().split('T')[0]}`
      )
      if (dailyRes && !dailyRes.error) {
        setDailyData(dailyRes.data || [])
      }

      // Fetch trend data for the year
      const trendRes = await api.get(`/api/billing/trend?year=${selectedYear}`)
      if (trendRes?.status === 'ok') {
        setTrendData(trendRes.trend || [])
      }

      // Fetch capacity status
      const capacityRes = await api.get(`/api/capacity/status?year=${selectedYear}`)
      if (capacityRes?.status === 'ok') {
        setCapacityStatus(capacityRes.capacity)
      }

      // Forecast is included in summary
      if (summaryRes?.billing?.forecast_next_month) {
        setForecast(summaryRes.billing.forecast_next_month)
      }
    } catch (error) {
      console.error('Error fetching billing data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleTriggerScheduler = async () => {
    setTriggering(true)
    setTriggerMessage(null)
    try {
      const response = await api.post('/api/billing/trigger')
      if (response?.status === 'success') {
        setTriggerMessage({ type: 'success', text: response.message || 'Billing scheduler completed successfully' })
        // Refresh billing data after successful trigger
        setTimeout(() => {
          fetchBillingData()
        }, 1000)
      } else {
        setTriggerMessage({ type: 'error', text: response?.error || 'Failed to trigger billing scheduler' })
      }
    } catch (error: any) {
      setTriggerMessage({ type: 'error', text: error?.response?.data?.error || error?.message || 'Error triggering billing scheduler' })
    } finally {
      setTriggering(false)
      // Clear message after 5 seconds
      setTimeout(() => {
        setTriggerMessage(null)
      }, 5000)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen" style={{ backgroundColor: '#1B2234' }}>
        <div className="text-white text-lg">Loading billing data...</div>
      </div>
    )
  }

  return (
    <div
      className={`overflow-x-hidden relative w-full min-h-screen ${isMobile ? 'p-4' : 'p-6'}`}
      style={{ backgroundColor: '#1B2234' }}
    >
      {/* Gradient Overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(99.07deg, rgba(0, 212, 151, 0.1) -3.97%, rgba(15, 145, 255, 0.1) 48.41%, rgba(205, 115, 255, 0.1) 97.94%)',
        }}
      />

      {/* Main Content */}
      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Billing & Capacity Dashboard</h1>
            <p className="text-gray-400">Monitor your electricity bills, capacity, and forecasts</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleTriggerScheduler}
              disabled={triggering}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {triggering ? (
                <>
                  <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Running...
                </>
              ) : (
                <>
                  <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Run Scheduler
                </>
              )}
            </button>
            <a
              href="/billing-setup"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              Configure Billing
            </a>
          </div>
        </div>

        {/* Trigger Message */}
        {triggerMessage && (
          <div className={`mb-4 p-4 rounded-lg ${
            triggerMessage.type === 'success' 
              ? 'bg-green-900/50 border border-green-700 text-green-200' 
              : 'bg-red-900/50 border border-red-700 text-red-200'
          }`}>
            <div className="flex items-center gap-2">
              {triggerMessage.type === 'success' ? (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              <span>{triggerMessage.text}</span>
            </div>
          </div>
        )}

        {/* Year Selector */}
        <div className="mb-6">
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className="px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700"
          >
            {[selectedYear - 1, selectedYear, selectedYear + 1].map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>

        {/* Daily Billing Widgets Row */}
        <div className="mb-6">
          <DailyBillingWidgets runningBill={runningBill} dailyData={dailyData} />
        </div>

        {/* Main Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Left Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Monthly Bill Card */}
            <MonthlyBillCard billingSummary={billingSummary} runningBill={runningBill} />

            {/* Import vs Export Chart */}
            <ImportExportChart trendData={trendData} />

            {/* Bill Amount Trend Chart */}
            <BillTrendChart trendData={trendData} />

            {/* Solar vs Load Comparison */}
            <SolarLoadComparison trendData={trendData} />
          </div>

          {/* Right Column */}
          <div className="space-y-6">
            {/* Capacity Meter */}
            <CapacityMeter capacityStatus={capacityStatus} />

            {/* Next-Month Forecast Card */}
            <ForecastCard forecast={forecast} />

            {/* Credit Ledger */}
            <CreditLedger billingSummary={billingSummary} trendData={trendData} />
          </div>
        </div>
      </div>
    </div>
  )
}

