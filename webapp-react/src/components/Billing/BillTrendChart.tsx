import React from 'react'
import { Card } from '../Card'

interface BillTrendChartProps {
  trendData?: any[]
}

export const BillTrendChart: React.FC<BillTrendChartProps> = ({ trendData }) => {
  if (!trendData || trendData.length === 0) {
    return (
      <Card className="p-6">
        <h2 className="text-xl font-bold text-white mb-4">Bill Amount Trend</h2>
        <div className="text-gray-400 text-center py-8">No data available</div>
      </Card>
    )
  }

  const bills = trendData.map(m => m.final_bill || 0)
  const maxBill = Math.max(...bills, 1)
  const minBill = Math.min(...bills, 0)
  const range = maxBill - minBill || 1

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Bill Amount Trend</h2>
      
      <div className="space-y-3">
        {trendData.map((month, idx) => {
          const bill = month.final_bill || 0
          const height = range > 0 ? ((bill - minBill) / range) * 100 : 0
          const isPositive = bill > 0
          const isNegative = bill < 0

          return (
            <div key={idx} className="flex items-end gap-2">
              <div className="text-xs text-gray-400 w-20 text-right">
                {month.billingMonth || `M${idx + 1}`}
              </div>
              <div className="flex-1 relative">
                <div className="h-8 bg-gray-800 rounded flex items-end">
                  <div
                    className={`w-full rounded transition-all ${
                      isNegative
                        ? 'bg-green-500'
                        : isPositive
                        ? 'bg-red-500'
                        : 'bg-gray-600'
                    }`}
                    style={{ height: `${Math.max(5, Math.abs(height))}%` }}
                  />
                </div>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={`text-xs font-semibold ${
                    isNegative ? 'text-green-400' : isPositive ? 'text-red-400' : 'text-gray-400'
                  }`}>
                    PKR {bill.toFixed(0)}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="flex justify-center gap-4 mt-4 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded" />
          <span className="text-gray-400">Payable</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-green-500 rounded" />
          <span className="text-gray-400">Credit</span>
        </div>
      </div>
    </Card>
  )
}

