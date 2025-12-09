import React from 'react'
import { useTheme } from '../../../../contexts/ThemeContext'
import { TOUWindowGrid } from '../../../TOUWindowGrid'
import { Settings as SettingsIcon } from 'lucide-react'

interface PowdriveTOUCardProps {
  inverterId: string
  batteryOperation?: 'Voltage' | 'State of charge' | null
}

export const PowdriveTOUCard: React.FC<PowdriveTOUCardProps> = ({
  inverterId,
  batteryOperation
}) => {
  const { theme } = useTheme()

  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280'
  const cardBg = theme === 'dark' ? '#374151' : '#f3f4f6'
  const borderColor = theme === 'dark' ? '#4b5563' : '#d1d5db'

  return (
    <div 
      className="p-6 rounded-lg"
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
      }}
    >
      <div className="flex items-center gap-3 mb-4">
        <SettingsIcon className="w-5 h-5" style={{ color: textColor }} />
        <div>
          <h3 className="font-semibold" style={{ color: textColor }}>Time of Use (TOU) Windows</h3>
          <p className="text-sm" style={{ color: textSecondary }}>
            Configure 6 bidirectional windows (charge/discharge/auto)
          </p>
        </div>
      </div>
      {inverterId && <TOUWindowGrid inverterId={inverterId} batteryOperation={batteryOperation} />}
    </div>
  )
}

