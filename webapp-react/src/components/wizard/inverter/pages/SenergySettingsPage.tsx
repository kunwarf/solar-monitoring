import React, { useState, useEffect } from 'react'
import { useTheme } from '../../../../contexts/ThemeContext'
import { api } from '../../../../lib/api'
import { SpecificationCard } from '../sections/SpecificationCard'
import { GridSettingsCard } from '../sections/GridSettingsCard'
import { BatteryTypeCard } from '../sections/BatteryTypeCard'
import { BatteryChargingCard } from '../sections/BatteryChargingCard'
import { WorkModeCard } from '../sections/WorkModeCard'
import { WorkModeDetailCard } from '../sections/WorkModeDetailCard'
import { AuxiliarySettingsCard } from '../sections/AuxiliarySettingsCard'
import { SenergyTOUCard } from '../sections/SenergyTOUCard'

interface SenergySettingsPageProps {
  inverterId: string
}

export const SenergySettingsPage: React.FC<SenergySettingsPageProps> = ({
  inverterId
}) => {
  const { theme } = useTheme()
  const [loading, setLoading] = useState(true)
  const [specification, setSpecification] = useState<any>(null)
  const [gridSettings, setGridSettings] = useState<any>(null)
  const [batteryType, setBatteryType] = useState<any>(null)
  const [batteryCharging, setBatteryCharging] = useState<any>(null)
  const [workMode, setWorkMode] = useState<any>(null)
  const [workModeDetail, setWorkModeDetail] = useState<any>(null)
  const [auxiliary, setAuxiliary] = useState<any>(null)

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'

  useEffect(() => {
    loadAllData()
  }, [inverterId])

  const loadAllData = async () => {
    if (!inverterId || inverterId === 'all') return
    
    setLoading(true)
    try {
      const [
        specRes,
        gridRes,
        batteryTypeRes,
        batteryChargingRes,
        workModeRes,
        workModeDetailRes,
        auxiliaryRes
      ] = await Promise.all([
        api.get(`/api/inverter/specification?inverter_id=${inverterId}`),
        api.get(`/api/inverter/grid-settings?inverter_id=${inverterId}`),
        api.get(`/api/inverter/battery-type?inverter_id=${inverterId}`),
        api.get(`/api/inverter/battery-charging?inverter_id=${inverterId}`),
        api.get(`/api/inverter/work-mode?inverter_id=${inverterId}`),
        api.get(`/api/inverter/work-mode-detail?inverter_id=${inverterId}`),
        api.get(`/api/inverter/auxiliary-settings?inverter_id=${inverterId}`)
      ]) as any[]

      setSpecification((specRes as any).specification || null)
      setGridSettings((gridRes as any).grid_settings || null)
      setBatteryType((batteryTypeRes as any).battery_type || null)
      setBatteryCharging((batteryChargingRes as any).battery_charging || null)
      setWorkMode((workModeRes as any).work_mode || null)
      setWorkModeDetail((workModeDetailRes as any).work_mode_detail || null)
      setAuxiliary((auxiliaryRes as any).auxiliary || null)
    } catch (error) {
      console.error('Error loading settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDataChange = () => {
    loadAllData()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-2" style={{ color: textColor }}>
          Senergy Inverter Settings
        </h2>
        <p className="text-sm" style={{ color: textSecondary }}>
          Configure Senergy inverter settings and controls
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SpecificationCard 
          inverterId={inverterId}
          data={specification}
          loading={loading}
        />
        <GridSettingsCard
          inverterId={inverterId}
          data={gridSettings}
          loading={loading}
          onDataChange={handleDataChange}
        />
        <BatteryTypeCard
          inverterId={inverterId}
          data={batteryType}
          loading={loading}
          onDataChange={handleDataChange}
        />
        <BatteryChargingCard
          inverterId={inverterId}
          data={batteryCharging}
          batteryOperation={batteryType?.battery_operation}
          loading={loading}
          onDataChange={handleDataChange}
        />
        <WorkModeCard
          inverterId={inverterId}
          data={workMode}
          loading={loading}
          onDataChange={handleDataChange}
        />
        <WorkModeDetailCard
          inverterId={inverterId}
          data={workModeDetail}
          loading={loading}
          onDataChange={handleDataChange}
        />
        <AuxiliarySettingsCard
          inverterId={inverterId}
          data={auxiliary}
          loading={loading}
          onDataChange={handleDataChange}
        />
      </div>

      <SenergyTOUCard inverterId={inverterId} batteryOperation={batteryType?.battery_operation} />
    </div>
  )
}

