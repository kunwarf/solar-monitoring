import React from 'react'
import { Card } from '../Card'

interface CreditLedgerProps {
  billingSummary?: any
  trendData?: any[]
}

export const CreditLedger: React.FC<CreditLedgerProps> = ({ billingSummary, trendData }) => {
  // Simplified credit ledger - would need cycle-level data from backend
  const currentCreditBalance = billingSummary?.credit_balance || 0

  // Extract cycle information from trend data (simplified)
  const cycleData = React.useMemo(() => {
    if (!trendData || trendData.length === 0) return []
    
    const cycles: any[] = []
    trendData.forEach((month, idx) => {
      const cycleNum = Math.floor(idx / 3) + 1
      const cycleMonth = (idx % 3) + 1
      
      if (cycleMonth === 1) {
        cycles.push({
          cycleNumber: cycleNum,
          startMonth: month.billingMonth,
          creditsCreated: 0,
          creditsConsumed: 0,
          creditsSettled: 0
        })
      }
      
      const currentCycle = cycles[cycles.length - 1]
      if (currentCycle) {
        const netExport = (month.export_off_kwh || 0) + (month.export_peak_kwh || 0) - 
                          (month.import_off_kwh || 0) - (month.import_peak_kwh || 0)
        if (netExport > 0) {
          currentCycle.creditsCreated += netExport
        } else {
          currentCycle.creditsConsumed += Math.abs(netExport)
        }
        
        if (cycleMonth === 3) {
          // End of cycle - settlement
          currentCycle.creditsSettled = Math.max(0, currentCycle.creditsCreated - currentCycle.creditsConsumed)
          currentCycle.endMonth = month.billingMonth
        }
      }
    })
    
    return cycles
  }, [trendData])

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Credit Ledger</h2>
      
      <div className="space-y-4">
        {/* Current Balance */}
        <div className="pb-3 border-b border-gray-700">
          <div className="flex justify-between items-center">
            <span className="text-gray-400">Current Credit Balance</span>
            <span className={`text-lg font-bold ${currentCreditBalance < 0 ? 'text-green-400' : 'text-white'}`}>
              PKR {Math.abs(currentCreditBalance).toFixed(2)}
            </span>
          </div>
        </div>

        {/* Cycle History */}
        <div className="space-y-3 max-h-64 overflow-y-auto">
          {cycleData.length > 0 ? (
            cycleData.map((cycle, idx) => (
              <div key={idx} className="p-3 bg-gray-800/50 rounded-lg space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-semibold text-white">Cycle {cycle.cycleNumber}</span>
                  <span className="text-xs text-gray-400">
                    {cycle.startMonth} - {cycle.endMonth || 'Ongoing'}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-gray-400">Created:</span>
                    <span className="text-green-400 ml-2">{cycle.creditsCreated.toFixed(1)} kWh</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Consumed:</span>
                    <span className="text-red-400 ml-2">{cycle.creditsConsumed.toFixed(1)} kWh</span>
                  </div>
                  {cycle.creditsSettled > 0 && (
                    <div className="col-span-2 pt-1 border-t border-gray-700">
                      <span className="text-gray-400">Settled:</span>
                      <span className="text-green-400 ml-2">PKR {cycle.creditsSettled.toFixed(2)}</span>
                    </div>
                  )}
                </div>
              </div>
            ))
          ) : (
            <div className="text-gray-400 text-center py-4 text-sm">No cycle data available</div>
          )}
        </div>
      </div>
    </Card>
  )
}

