import React from 'react'
import { useMobile } from '../../hooks/useMobile'
import { useTheme } from '../../contexts/ThemeContext'

type Period = 'today' | 'week' | 'month' | 'year' | 'custom'

interface TimePeriodFilterProps {
  selectedPeriod: Period
  onPeriodChange: (period: Period) => void
}

// Calendar icon SVG from Figma design (16x16)
const CalendarIcon: React.FC<{ color?: string }> = ({ color = '#FFFFFF' }) => (
  <svg width="16" height="16" viewBox="0 0 15 16" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ width: '16px', height: '16px' }}>
    <path d="M13.0909 1.45455H12.3636V0.727273C12.3636 0.327273 12.0364 0 11.6364 0C11.2364 0 10.9091 0.327273 10.9091 0.727273V1.45455H3.63636V0.727273C3.63636 0.327273 3.30909 0 2.90909 0C2.50909 0 2.18182 0.327273 2.18182 0.727273V1.45455H1.45455C0.654545 1.45455 0 2.10909 0 2.90909V14.5455C0 15.3455 0.654545 16 1.45455 16H13.0909C13.8909 16 14.5455 15.3455 14.5455 14.5455V2.90909C14.5455 2.10909 13.8909 1.45455 13.0909 1.45455ZM12.3636 14.5455H2.18182C1.78182 14.5455 1.45455 14.2182 1.45455 13.8182V5.09091H13.0909V13.8182C13.0909 14.2182 12.7636 14.5455 12.3636 14.5455Z" fill={color}/>
  </svg>
)

export const TimePeriodFilter: React.FC<TimePeriodFilterProps> = ({
  selectedPeriod,
  onPeriodChange,
}) => {
  const { isMobile } = useMobile()
  const { theme } = useTheme()
  
  // Theme-aware colors
  // Buttons have transparent background for both themes
  const buttonBg = 'transparent' // Transparent for both themes
  const activeTextColor = theme === 'dark' 
    ? 'rgba(255, 255, 255, 0.8)' 
    : '#1B2234' // Dark text for light theme
  const inactiveTextColor = theme === 'dark' 
    ? 'rgba(255, 255, 255, 0.6)' 
    : 'rgba(27, 34, 52, 0.6)' // Dark text with opacity for light theme
  
  const periods: { value: Period; label: string }[] = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' },
    { value: 'year', label: 'year' },
    { value: 'custom', label: 'Custom' },
  ]

  return (
    <div className={`flex ${isMobile ? 'gap-[4px]' : 'gap-[8px]'} items-center ${isMobile ? 'overflow-x-auto pb-2 -mx-2 px-2 scrollbar-hide' : 'justify-center'}`} style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
      {periods.map((period) => {
        const isActive = selectedPeriod === period.value
        const isCustom = period.value === 'custom'
        const textColor = isActive ? activeTextColor : inactiveTextColor
        
        return (
          <button
            key={period.value}
            onClick={() => onPeriodChange(period.value)}
            className="flex items-center justify-center gap-[8px] rounded-[50px] flex-shrink-0"
            style={{
              width: isMobile ? '80px' : '120px',
              height: isMobile ? '28px' : '32px',
              fontFamily: 'Lato, sans-serif',
              fontStyle: 'normal',
              fontSize: isMobile ? '11px' : '14px',
              lineHeight: isMobile ? '13px' : '17px',
              backgroundColor: buttonBg,
              color: textColor,
              fontWeight: isActive ? 700 : 600,
              padding: isMobile ? '0 8px' : '0',
              border: 'none',
              cursor: 'pointer',
              flex: 'none',
              flexGrow: 0,
              whiteSpace: 'nowrap'
            }}
          >
            {isCustom && <CalendarIcon color={textColor} />}
            <span style={{ color: textColor }}>{period.label}</span>
          </button>
        )
      })}
    </div>
  )
}

