import React from 'react'
import { Card } from '../Card'

interface MonthlyBillCardProps {
  billingSummary?: any
  runningBill?: any
}

export const MonthlyBillCard: React.FC<MonthlyBillCardProps> = ({ billingSummary, runningBill }) => {
  const currentMonth = billingSummary?.billingMonth || runningBill?.billing_month_id || 'N/A'
  const billAmount = billingSummary?.bill_amount || runningBill?.bill_final_rs_to_date || 0
  const fixedCharge = billingSummary?.fixed_charge || runningBill?.fixed_prorated_rs || 0
  const creditBalance = billingSummary?.credit_balance || runningBill?.bill_credit_balance_rs_to_date || 0
  
  const importOff = billingSummary?.import_off_kwh || runningBill?.import_off_kwh || 0
  const importPeak = billingSummary?.import_peak_kwh || runningBill?.import_peak_kwh || 0
  const exportOff = billingSummary?.export_off_kwh || runningBill?.export_off_kwh || 0
  const exportPeak = billingSummary?.export_peak_kwh || runningBill?.export_peak_kwh || 0
  
  const billOffEnergy = runningBill?.bill_off_energy_rs || 0
  const billPeakEnergy = runningBill?.bill_peak_energy_rs || 0
  const expectedCycleCredit = runningBill?.expected_cycle_credit_rs || 0

  const isNegative = billAmount < 0
  const finalPayable = Math.max(0, billAmount + creditBalance)

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-white mb-4">Monthly Bill</h2>
      
      <div className="space-y-4">
        {/* Billing Period */}
        <div className="flex justify-between items-center pb-3 border-b border-gray-700">
          <span className="text-gray-400">Billing Period</span>
          <span className="text-white font-semibold">{currentMonth}</span>
        </div>

        {/* Energy Charges */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-gray-300">Energy Charges</h3>
          <div className="pl-4 space-y-1">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Off-Peak Import</span>
              <span className="text-white">{importOff.toFixed(2)} kWh</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Peak Import</span>
              <span className="text-white">{importPeak.toFixed(2)} kWh</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Off-Peak Export</span>
              <span className="text-green-400">{exportOff.toFixed(2)} kWh</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">Peak Export</span>
              <span className="text-green-400">{exportPeak.toFixed(2)} kWh</span>
            </div>
            <div className="flex justify-between text-sm pt-2 border-t border-gray-700">
              <span className="text-gray-300">Off-Peak Energy Charge</span>
              <span className="text-white">PKR {billOffEnergy.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-300">Peak Energy Charge</span>
              <span className="text-white">PKR {billPeakEnergy.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Fixed Charges */}
        <div className="flex justify-between pt-2 border-t border-gray-700">
          <span className="text-gray-400">Fixed Charge</span>
          <span className="text-white">PKR {fixedCharge.toFixed(2)}</span>
        </div>

        {/* Credits */}
        {expectedCycleCredit > 0 && (
          <div className="flex justify-between text-sm pt-2">
            <span className="text-gray-400">Expected Cycle Credit</span>
            <span className="text-green-400">-PKR {expectedCycleCredit.toFixed(2)}</span>
          </div>
        )}

        {creditBalance < 0 && (
          <div className="flex justify-between text-sm pt-2">
            <span className="text-gray-400">Credit Balance</span>
            <span className="text-green-400">PKR {Math.abs(creditBalance).toFixed(2)}</span>
          </div>
        )}

        {/* Final Payable */}
        <div className="flex justify-between items-center pt-4 border-t-2 border-gray-600">
          <span className="text-lg font-semibold text-white">Final Payable</span>
          <span className={`text-2xl font-bold ${isNegative || finalPayable === 0 ? 'text-green-400' : 'text-white'}`}>
            PKR {finalPayable.toFixed(2)}
          </span>
        </div>

        {isNegative && (
          <div className="text-sm text-green-400 text-center pt-2">
            Credit will carry forward to next month
          </div>
        )}
      </div>
    </Card>
  )
}

