import React from 'react'
import { useMobile } from '../../hooks/useMobile'
import { useTheme } from '../../contexts/ThemeContext'

interface PowerGaugeProps {
  title: string
  value: number // watts or percentage
  maxValue?: number // max watts or percentage for gauge
  color: string
  subtitle?: string
  unit?: string // Unit to display (default: 'W', use '%' for percentage)
}

export const PowerGauge: React.FC<PowerGaugeProps> = ({
  title,
  value,
  maxValue = 5000,
  color,
  subtitle,
  unit,
}) => {
  const { isMobile } = useMobile()
  const { theme } = useTheme()
  const percentage = Math.min((value / maxValue) * 100, 100)
  
  // Determine unit - if maxValue is 100, assume percentage, otherwise use provided unit or default to 'W'
  const displayUnit = unit || (maxValue === 100 ? '%' : 'W')
  
  // Theme-aware colors with proper contrast
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  const backgroundColor = theme === 'dark' 
    ? 'rgba(255, 255, 255, 0.08)' 
    : 'rgba(255, 255, 255, 1)' // Solid white for light theme
  const boxShadowColor = theme === 'dark' 
    ? 'rgba(0, 0, 0, 0.08)' 
    : 'rgba(0, 0, 0, 0.1)' // Slightly darker shadow for light theme
  const innerArcFill = 'transparent' // Transparent to reflect background color
  const backgroundArcStroke = theme === 'dark' ? '#EFEFEF' : '#E0E0E0' // Slightly darker for light theme
  // Calculate angle in radians for semi-circle (0 to π)
  const angleRad = (percentage / 100) * Math.PI
  // Calculate end point of arc
  // For semi-circle: x = 100 + 100 * cos(π - angle), y = 100 - 100 * sin(π - angle)
  const endX = 100 + 100 * Math.cos(Math.PI - angleRad)
  const endY = 100 - 100 * Math.sin(Math.PI - angleRad)

  return (
    <div 
      className="rounded-[24px] w-full"
      style={{
        width: isMobile ? '100%' : '240px',
        height: isMobile ? '160px' : '170px',
        backgroundColor: backgroundColor,
        boxShadow: `0px 4px 40px ${boxShadowColor}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '16px'
      }}
    >
      <h4 
        style={{
          fontFamily: 'Roboto, sans-serif',
          fontStyle: 'normal',
          fontWeight: 700,
          fontSize: '16px',
          lineHeight: '18px',
          color: textColor,
          textAlign: 'center',
          marginTop: '0px',
          marginBottom: '0px',
          paddingBottom: '1px'
        }}
      >
        {title}
      </h4>
      <div className="relative w-full flex items-center justify-center" style={{ height: '110px', flex: 1, minHeight: '110px' }}>
        <div className="relative" style={{ width: isMobile ? '100%' : '160px', maxWidth: '160px' }}>
          <svg 
            viewBox="-20 -20 240 120" 
            className="w-full h-full" 
            style={{ 
              width: isMobile ? '100%' : '160px', 
              height: isMobile ? '80px' : '100px',
              maxWidth: '160px',
              overflow: 'visible'
            }}
          >
            
            {/* Inner arc - matches the gauge arc shape with smaller radius, filled semi-circle */}
            <path
              d="M 20 100 A 80 80 0 0 1 180 100 L 180 120 L 20 120 Z"
              fill={innerArcFill}
            />
            
            {/* Background arc - theme-aware */}
            <path
              d="M 0 100 A 100 100 0 0 1 200 100"
              fill="none"
              stroke={backgroundArcStroke}
              strokeWidth="35"
              strokeLinecap="round"
            />
            
            {/* Value arc - Subtract: dynamic color based on percentage */}
            {percentage > 0 && (
              <path
                d={`M 0 100 A 100 100 0 ${percentage > 50 ? '1' : '0'} 1 ${endX} ${endY}`}
                fill="none"
                stroke={color}
                strokeWidth="35"
                strokeLinecap="round"
              />
            )}
            
            {/* Value text centered in the gauge */}
            <text
              x="100"
              y="70"
              textAnchor="middle"
              fill={textColor}
              fontSize="15px"
              fontWeight="700"
              fontFamily="Roboto, sans-serif"
              style={{ lineHeight: '19px' }}
            >
              {value.toLocaleString()} {displayUnit}
            </text>
            {subtitle && (
              <text
                x="100"
                y="88"
                textAnchor="middle"
                fill={textColor}
                fontSize="15px"
                fontWeight="700"
                fontFamily="Roboto, sans-serif"
                style={{ lineHeight: '19px' }}
              >
                {subtitle}
              </text>
            )}
          </svg>
        </div>
      </div>
    </div>
  )
}

