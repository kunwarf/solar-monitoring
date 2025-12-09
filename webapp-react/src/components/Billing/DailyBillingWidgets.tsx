import React, { useMemo } from 'react'
import { Card } from '../Card'

interface DailyBillingWidgetsProps {
  runningBill?: any
  dailyData?: any[]
}

export const DailyBillingWidgets: React.FC<DailyBillingWidgetsProps> = ({ runningBill, dailyData }) => {
  const surplusDeficit = useMemo(() => {
    if (!runningBill) return null
    const netKwh = runningBill.net_import_off_kwh + runningBill.net_import_peak_kwh
    return {
      flag: runningBill.surplus_deficit_flag || (netKwh < 0 ? 'SURPLUS' : netKwh > 0 ? 'DEFICIT' : 'NEUTRAL'),
      kwh: Math.abs(netKwh),
      netKwh
    }
  }, [runningBill])

  const monthProgress = useMemo(() => {
    if (!runningBill?.billing_month_id) return null
    // Extract anchor day from billing month (simplified - would need actual month boundaries)
    const today = new Date()
    const anchorDay = 15 // Default, should come from config
    const currentDay = today.getDate()
    const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate()
    const elapsedDays = Math.max(0, currentDay - anchorDay)
    const totalDays = daysInMonth - anchorDay + 1
    return {
      elapsed: elapsedDays,
      total: totalDays,
      percentage: totalDays > 0 ? (elapsedDays / totalDays) * 100 : 0
    }
  }, [runningBill])

  const cycleInfo = useMemo(() => {
    // Simplified cycle calculation - would need actual cycle tracking
    const today = new Date()
    const month = today.getMonth() + 1
    const cycleNumber = Math.floor((month - 1) / 3) + 1
    const cycleMonth = ((cycleNumber - 1) * 3) + 1
    const nextCycleEnd = new Date(today.getFullYear(), cycleMonth + 2, 15) // Approximate
    const daysToSettlement = Math.ceil((nextCycleEnd.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
    return {
      cycleNumber,
      cycleInYear: cycleNumber,
      daysToSettlement: Math.max(0, daysToSettlement)
    }
  }, [])

  const sparklineData = useMemo(() => {
    if (!dailyData || dailyData.length === 0) return null
    const last30Days = dailyData.slice(-30)
    return {
      imports: last30Days.map(d => (d.import_off_kwh || 0) + (d.import_peak_kwh || 0)),
      exports: last30Days.map(d => (d.export_off_kwh || 0) + (d.export_peak_kwh || 0)),
      dates: last30Days.map(d => d.date)
    }
  }, [dailyData])

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Surplus/Deficit Chip */}
      <Card className="p-4">
        <div className="text-sm text-gray-400 mb-2">Daily Status</div>
        {surplusDeficit && (
          <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold ${
            surplusDeficit.flag === 'SURPLUS' 
              ? 'bg-green-500/20 text-green-400' 
              : surplusDeficit.flag === 'DEFICIT'
              ? 'bg-red-500/20 text-red-400'
              : 'bg-gray-500/20 text-gray-400'
          }`}>
            {surplusDeficit.flag} {surplusDeficit.flag === 'SURPLUS' ? '+' : '-'}{surplusDeficit.kwh.toFixed(1)} kWh
            {runningBill?.billing_month_id && ` since ${runningBill.billing_month_id.split('-')[2] || '15th'}`}
          </div>
        )}
      </Card>

      {/* Month Progress */}
      <Card className="p-4">
        <div className="text-sm text-gray-400 mb-2">Month Progress</div>
        {monthProgress && (
          <div>
            <div className="w-full bg-gray-700 rounded-full h-2 mb-2">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all"
                style={{ width: `${Math.min(100, monthProgress.percentage)}%` }}
              />
            </div>
            <div className="text-xs text-gray-400">
              {monthProgress.elapsed} / {monthProgress.total} days
            </div>
          </div>
        )}
      </Card>

      {/* Cycle Countdown */}
      <Card className="p-4">
        <div className="text-sm text-gray-400 mb-2">Cycle Status</div>
        <div className="text-white font-semibold">
          Cycle {cycleInfo.cycleNumber}/4
        </div>
        <div className="text-xs text-gray-400 mt-1">
          {cycleInfo.daysToSettlement} days to settlement
        </div>
      </Card>

      {/* Running Bill Progress */}
      <Card className="p-4">
        <div className="text-sm text-gray-400 mb-2">Running Bill</div>
        {runningBill && (
          <div>
            <div className="text-lg font-bold text-white">
              PKR {runningBill.bill_final_rs_to_date?.toFixed(2) || '0.00'}
            </div>
            <div className="text-xs text-gray-400 mt-1">To date this month</div>
          </div>
        )}
      </Card>

      {/* Sparkline Chart (simplified) */}
      {sparklineData && (
        <Card className="p-4 md:col-span-2 lg:col-span-4">
          <div className="text-sm text-gray-400 mb-2">Cumulative Import vs Export (Last 30 Days)</div>
          <div className="h-32 flex items-end justify-between gap-1">
            {sparklineData.imports.slice(-30).map((imp, idx) => {
              const exp = sparklineData.exports[idx] || 0
              const maxVal = Math.max(...sparklineData.imports, ...sparklineData.exports)
              return (
                <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full flex flex-col-reverse gap-0.5">
                    <div
                      className="bg-red-500/60 rounded-t"
                      style={{ height: `${(imp / maxVal) * 100}%`, minHeight: '2px' }}
                    />
                    <div
                      className="bg-green-500/60 rounded-t"
                      style={{ height: `${(exp / maxVal) * 100}%`, minHeight: '2px' }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
          <div className="flex justify-center gap-4 mt-2 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-red-500/60 rounded" />
              <span className="text-gray-400">Import</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 bg-green-500/60 rounded" />
              <span className="text-gray-400">Export</span>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

