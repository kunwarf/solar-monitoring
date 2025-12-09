import React, { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Card, CardHeader, CardTitle, CardContent } from './Card'
import { Badge } from './Badge'

interface SchedulerPlan {
  array_id: string
  tick_ts: string
  array_target_w: {
    charge: number
    discharge: number
  }
  mode: string
  per_inverter: Array<{
    inverter_id: string
    target_w: {
      charge: number
      discharge: number
    }
    headroom_w: {
      charge: number
      discharge: number
    }
    rated_w: {
      charge: number
      discharge: number
    }
  }>
  unmet_w: {
    charge: number
    discharge: number
  }
}

interface SchedulerTimelineProps {
  arrayId: string | null
}

export const SchedulerTimeline: React.FC<SchedulerTimelineProps> = ({ arrayId }) => {
  const [plan, setPlan] = useState<SchedulerPlan | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!arrayId) {
      setPlan(null)
      setLoading(false)
      return
    }

    const fetchPlan = async () => {
      try {
        const response: any = await api.get(`/api/arrays/${arrayId}/scheduler/plan`)
        if (response.plan) {
          setPlan(response.plan)
        }
      } catch (error) {
        console.error('Error fetching scheduler plan:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPlan()
    const interval = setInterval(fetchPlan, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [arrayId])

  if (!arrayId) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <p className="text-gray-500 text-center">Select an array to view scheduler plan</p>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  if (!plan) {
    return (
      <div className="bg-white rounded-2xl shadow-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Scheduler Plan</h3>
        <p className="text-gray-500 text-center">No scheduler plan available yet</p>
      </div>
    )
  }

  const formatPower = (watts: number) => {
    if (Math.abs(watts) >= 1000) return `${(watts / 1000).toFixed(1)} kW`
    return `${Math.round(watts)} W`
  }

  // Generate timeline segments (mock for now - should come from scheduler API)
  const segments = [
    { label: 'Charge', color: 'bg-emerald-500', start: 0, end: 6 },
    { label: 'Idle', color: 'bg-gray-400', start: 6, end: 10 },
    { label: 'Discharge', color: 'bg-amber-500', start: 10, end: 18 },
    { label: 'Hold', color: 'bg-sky-500', start: 18, end: 22 },
    { label: 'Idle', color: 'bg-gray-400', start: 22, end: 24 },
  ]

  return (
    <Card className="border-none">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <span className="text-lg">⏱️</span>
            Smart Scheduler
          </CardTitle>
          <Badge variant="outline">Mode: {plan.mode}</Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-3 space-y-4">
        <div>
          <div className="mb-2 text-xs text-gray-500 dark:text-gray-400">Today</div>
          <div className="h-3 w-full rounded-full bg-gray-200 dark:bg-gray-700 overflow-hidden">
            <div className="flex h-full w-full">
              {segments.map((s, i) => (
                <div
                  key={i}
                  className={`${s.color} h-full`}
                  style={{ width: `${((s.end - s.start) / 24) * 100}%` }}
                  title={`${s.label} ${s.start}:00–${s.end}:00`}
                />
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {plan.per_inverter.map((inv) => {
            const maxHeadroom = Math.max(inv.headroom_w.charge, inv.headroom_w.discharge)
            const currentTarget = Math.max(inv.target_w.charge, inv.target_w.discharge)
            const progressPercent = maxHeadroom > 0 ? (currentTarget / maxHeadroom) * 100 : 0
            
            return (
              <div key={inv.inverter_id} className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-gray-900 dark:text-gray-100">{inv.inverter_id}</div>
                  <Badge variant="secondary">Headroom {formatPower(maxHeadroom)}</Badge>
                </div>
                <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">Target: {formatPower(currentTarget)}</div>
                <div className="mt-2 h-2 w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-300"
                    style={{ width: `${Math.min(progressPercent, 100)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>

      </CardContent>
    </Card>
  )
}

