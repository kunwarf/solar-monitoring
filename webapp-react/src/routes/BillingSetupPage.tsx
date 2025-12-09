import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { FilterBar } from '../components/FilterBar'

interface BillingPeakWindow {
  start: string
  end: string
}

interface BillingForecastConfig {
  default_method: string
  lookback_months: number
  default_months_ahead: number
  low_confidence_threshold: number
}

interface BillingConfig {
  currency: string
  anchor_day: number
  price_offpeak_import: number
  price_peak_import: number
  price_offpeak_settlement: number
  price_peak_settlement: number
  fixed_charge_per_billing_month: number
  peak_windows: BillingPeakWindow[]
  forecast: BillingForecastConfig
}

interface ConfigResponse {
  config: {
    billing?: BillingConfig
  }
}

const defaultBillingConfig: BillingConfig = {
  currency: 'PKR',
  anchor_day: 15,
  price_offpeak_import: 40,
  price_peak_import: 47,
  price_offpeak_settlement: 40,
  price_peak_settlement: 40,
  fixed_charge_per_billing_month: 0,
  peak_windows: [{ start: '17:00', end: '22:00' }],
  forecast: {
    default_method: 'trend',
    lookback_months: 12,
    default_months_ahead: 1,
    low_confidence_threshold: 0.5,
  },
}

export const BillingSetupPage: React.FC = () => {
  const [billingConfig, setBillingConfig] = useState<BillingConfig>(defaultBillingConfig)
  const [step, setStep] = useState<number>(1)
  const [loading, setLoading] = useState<boolean>(true)
  const [saving, setSaving] = useState<boolean>(false)
  const [preview, setPreview] = useState<any | null>(null)
  
  // Check if mobile
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768

  useEffect(() => {
    const loadConfig = async () => {
      try {
        setLoading(true)
        const res: any = await api.get('/api/config')
        const cfg = (res as ConfigResponse)?.config || res?.config || res
        if (cfg?.billing) {
          setBillingConfig({
            ...defaultBillingConfig,
            ...cfg.billing,
            forecast: { ...defaultBillingConfig.forecast, ...(cfg.billing.forecast || {}) },
          })
        }
      } catch (e) {
        console.error('Error loading billing config', e)
      } finally {
        setLoading(false)
      }
    }
    loadConfig()
  }, [])

  const handleSave = async () => {
    try {
      setSaving(true)
      await api.post('/api/config', { billing: billingConfig })
      alert('Billing configuration saved successfully.')
    } catch (e: any) {
      alert(`Failed to save billing configuration: ${e?.message || e}`)
    } finally {
      setSaving(false)
    }
  }

  const handlePreview = async () => {
    try {
      setSaving(true)
      // Use simulate endpoint to preview current year with current saved settings
      const res: any = await api.get('/api/billing/summary')
      setPreview(res)
    } catch (e: any) {
      console.error('Failed to preview billing simulation', e)
      alert(`Failed to preview billing simulation: ${e?.message || e}`)
    } finally {
      setSaving(false)
    }
  }

  const updatePeakWindow = (index: number, field: keyof BillingPeakWindow, value: string) => {
    setBillingConfig((prev) => {
      const windows = [...prev.peak_windows]
      windows[index] = { ...windows[index], [field]: value }
      return { ...prev, peak_windows: windows }
    })
  }

  const addPeakWindow = () => {
    setBillingConfig((prev) => ({
      ...prev,
      peak_windows: [...prev.peak_windows, { start: '17:00', end: '22:00' }],
    }))
  }

  const removePeakWindow = (index: number) => {
    setBillingConfig((prev) => ({
      ...prev,
      peak_windows: prev.peak_windows.filter((_, i) => i !== index),
    }))
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-lg text-gray-700">Loading billing setup…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#1B2234' }}>
      <div className="max-w-4xl mx-auto p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Billing Setup Wizard</h1>
            <p className="text-gray-400">Configure billing cycle, tariffs, net-metering and forecasting</p>
          </div>
          <a
            href="/billing"
            className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm"
          >
            View Dashboard
          </a>
        </div>

        {/* Step indicator */}
        <div className="flex items-center mb-6 text-sm">
          {[1, 2, 3, 4].map((s) => (
            <div key={s} className="flex items-center">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center ${
                  step === s ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-400'
                }`}
              >
                {s}
              </div>
              {s < 4 && <div className="w-8 h-px bg-gray-700 mx-1" />}
            </div>
          ))}
        </div>

        {/* Step content */}
        {step === 1 && (
          <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">1. Global Billing Settings</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-300">Currency</label>
                <input
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.currency}
                  onChange={(e) => setBillingConfig({ ...billingConfig, currency: e.target.value })}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">Billing Anchor Day (1–28)</label>
                <input
                  type="number"
                  min={1}
                  max={28}
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.anchor_day}
                  onChange={(e) =>
                    setBillingConfig({ ...billingConfig, anchor_day: Number(e.target.value) || 15 })
                  }
                />
                <p className="mt-1 text-xs text-gray-400">Your billing cycle starts on this day of each month</p>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">2. Tariff & Net‑Metering</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300">Off‑peak price (per kWh)</label>
                <input
                  type="number"
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.price_offpeak_import}
                  onChange={(e) =>
                    setBillingConfig({ ...billingConfig, price_offpeak_import: Number(e.target.value) || 0 })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">Peak price (per kWh)</label>
                <input
                  type="number"
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.price_peak_import}
                  onChange={(e) =>
                    setBillingConfig({ ...billingConfig, price_peak_import: Number(e.target.value) || 0 })
                  }
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">Off‑peak settlement price</label>
                <input
                  type="number"
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.price_offpeak_settlement}
                  onChange={(e) =>
                    setBillingConfig({
                      ...billingConfig,
                      price_offpeak_settlement: Number(e.target.value) || 0,
                    })
                  }
                />
                <p className="mt-1 text-xs text-gray-400">Price paid for excess export credits at cycle end</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300">Peak settlement price</label>
                <input
                  type="number"
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.price_peak_settlement}
                  onChange={(e) =>
                    setBillingConfig({
                      ...billingConfig,
                      price_peak_settlement: Number(e.target.value) || 0,
                    })
                  }
                />
                <p className="mt-1 text-xs text-gray-400">Price paid for excess peak export credits at cycle end</p>
              </div>
            </div>

            <div className="mt-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-white">Peak Time Windows</h3>
                <button
                  type="button"
                  onClick={addPeakWindow}
                  className="text-xs px-2 py-1 rounded-md bg-blue-600 text-white hover:bg-blue-700"
                >
                  + Add Window
                </button>
              </div>
              <div className="space-y-2">
                {billingConfig.peak_windows.map((w, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <input
                      type="time"
                      className="bg-gray-700 border border-gray-600 rounded-md px-2 py-1 text-sm text-white"
                      value={w.start}
                      onChange={(e) => updatePeakWindow(idx, 'start', e.target.value)}
                    />
                    <span className="text-xs text-gray-400">to</span>
                    <input
                      type="time"
                      className="bg-gray-700 border border-gray-600 rounded-md px-2 py-1 text-sm text-white"
                      value={w.end}
                      onChange={(e) => updatePeakWindow(idx, 'end', e.target.value)}
                    />
                    {billingConfig.peak_windows.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removePeakWindow(idx)}
                        className="text-xs text-red-400 hover:text-red-300"
                      >
                        Remove
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">3. Fixed Charges & Forecast</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300">Fixed charge per billing month</label>
                <input
                  type="number"
                  className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                  value={billingConfig.fixed_charge_per_billing_month}
                  onChange={(e) =>
                    setBillingConfig({
                      ...billingConfig,
                      fixed_charge_per_billing_month: Number(e.target.value) || 0,
                    })
                  }
                />
                <p className="mt-1 text-xs text-gray-400">Meter rent, service fee, etc.</p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300">Forecast method</label>
                  <select
                    className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                    value={billingConfig.forecast.default_method}
                    onChange={(e) =>
                      setBillingConfig({
                        ...billingConfig,
                        forecast: { ...billingConfig.forecast, default_method: e.target.value },
                      })
                    }
                  >
                    <option value="trend">Trend‑based</option>
                    <option value="seasonal">Seasonal</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300">Look‑back months</label>
                  <input
                    type="number"
                    className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                    value={billingConfig.forecast.lookback_months}
                    onChange={(e) =>
                      setBillingConfig({
                        ...billingConfig,
                        forecast: {
                          ...billingConfig.forecast,
                          lookback_months: Number(e.target.value) || 12,
                        },
                      })
                    }
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300">Default months ahead</label>
                  <input
                    type="number"
                    className="mt-1 w-full bg-gray-700 border border-gray-600 rounded-md px-3 py-2 text-sm text-white"
                    value={billingConfig.forecast.default_months_ahead}
                    onChange={(e) =>
                      setBillingConfig({
                        ...billingConfig,
                        forecast: {
                          ...billingConfig.forecast,
                          default_months_ahead: Number(e.target.value) || 1,
                        },
                      })
                    }
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="bg-gray-800 rounded-xl shadow-lg border border-gray-700 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-white">4. Review & Preview</h2>
            <pre className="bg-gray-900 text-gray-100 text-xs rounded-md p-3 overflow-x-auto border border-gray-700">
              {JSON.stringify(billingConfig, null, 2)}
            </pre>

            <div className="space-y-2">
              <button
                type="button"
                onClick={handlePreview}
                className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm hover:bg-indigo-700"
                disabled={saving}
              >
                Preview Billing Simulation
              </button>
              {preview && (
                <div className="mt-3 text-sm bg-indigo-900/30 border border-indigo-700 rounded-md p-3 text-gray-200">
                  <div className="font-semibold mb-2 text-white">Preview (current year)</div>
                  <div className="space-y-1 text-xs">
                    <div>Annual final bill: {preview?.billing?.summary?.annual_final_bill?.toFixed?.(2) ?? '—'} {billingConfig.currency}</div>
                    <div>
                      Capacity status: {preview?.capacity?.status ?? '—'} (installed{' '}
                      {preview?.capacity?.installed_kw ?? '—'} kW, required{' '}
                      {preview?.capacity?.required_kw_for_zero_bill ?? '—'} kW)
                    </div>
                    <div>
                      Forecast next bill: {preview?.forecast_next?.predicted_bill ?? '—'}{' '}
                      {billingConfig.currency}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="mt-6 flex items-center justify-between">
          <button
            type="button"
            disabled={step === 1}
            onClick={() => setStep((s) => Math.max(1, s - 1))}
            className={`px-4 py-2 rounded-md text-sm ${
              step === 1 ? 'bg-gray-700 text-gray-500 cursor-not-allowed' : 'bg-gray-700 text-white hover:bg-gray-600'
            }`}
          >
            Back
          </button>
          <div className="flex items-center gap-2">
            {step === 4 ? (
              <button
                type="button"
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-md text-sm bg-blue-600 text-white hover:bg-blue-700"
              >
                {saving ? 'Saving…' : 'Save Configuration'}
              </button>
            ) : (
              <button
                type="button"
                onClick={() => setStep((s) => Math.min(4, s + 1))}
                className="px-4 py-2 rounded-md text-sm bg-blue-600 text-white hover:bg-blue-700"
              >
                Next
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


