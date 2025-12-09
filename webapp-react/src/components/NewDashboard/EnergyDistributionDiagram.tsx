import React from 'react'
import { useNavigate } from 'react-router-dom'
import { useMobile } from '../../hooks/useMobile'
import { useTheme } from '../../contexts/ThemeContext'
import { Sun, Battery, Home, Zap } from 'lucide-react'
import gridIcon from '../../assets/images/grid-icon.png'
import inverterIcon from '../../assets/images/inverter-icon.png'
import homeIcon from '../../assets/images/home-icon.svg'

interface EnergyDistributionDiagramProps {
  solarEnergy: number // kWh
  solarPower?: number // watts - current solar power
  gridPower?: number // watts - current grid power (positive = export, negative = import)
  batteryPower?: number // watts - current battery power (positive = charging, negative = discharging)
  loadPower?: number // watts - current load power
  gridExport: number // kWh
  gridImport: number // kWh
  batteryCharge: number // kWh
  batteryDischarge: number // kWh
  loadEnergy: number // kWh
  batterySOC?: number // Battery State of Charge percentage (0-100)
  batteryTemp?: number // Battery temperature in Celsius
}

export const EnergyDistributionDiagram: React.FC<EnergyDistributionDiagramProps> = ({
  solarEnergy,
  solarPower = 0,
  gridPower = 0,
  batteryPower = 0,
  loadPower = 0,
  gridExport,
  gridImport,
  batteryCharge,
  batteryDischarge,
  loadEnergy,
  batterySOC = 0,
  batteryTemp,
}) => {
  const navigate = useNavigate()
  const { isMobile } = useMobile()
  const { theme } = useTheme()
  
  // Theme-aware text colors - ensure visibility in both themes
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  const secondaryTextColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  // Text color for colored backgrounds (green/yellow circles) - always dark for contrast
  const textOnColoredBg = '#1B2234'
  
  // Desktop scale factor: Reduce overall size
  const elementScale = isMobile ? 1 : 0.75
  
  // Mobile scaling factor - use consistent scaling for mobile to prevent distortion
  const visualScale = isMobile ? 0.9 : elementScale
  
  // Container scale - keep at 1.0 to maintain original container size
  const desktopScale = isMobile ? 1 : 1.0
  
  // Circle size multiplier for all circles - increased slightly for better visibility
  const circleSizeMultiplier = 0.75  // Increased from 0.65 to 0.75
  
  const gridRadius = 60 * elementScale * circleSizeMultiplier
  const solarRadius = 60 * elementScale * circleSizeMultiplier
  const inverterRadius = 60 * elementScale * circleSizeMultiplier
  const batteryRadius = 60 * elementScale * circleSizeMultiplier
  const loadRadius = 60 * elementScale * circleSizeMultiplier
  
  // Find the maximum radius needed to accommodate all circles
  // The background circle edge should pass through the center of each peripheral circle
  const maxCircleRadius = Math.max(gridRadius, solarRadius, batteryRadius, loadRadius)
  
  // Base values (desktop) - scale inner elements by elementScale, but keep container size
  // Mobile uses fixed radius, desktop uses scaled radius
  // Background radius should be large enough so its edge passes through the center of peripheral circles
  // Increased background circle size for mobile only to make inner area bigger and more readable
  const bgRadius = isMobile 
    ? (150 + maxCircleRadius) * 1.1  // Increased from 0.7 to 1.1 for larger inner circle on mobile
    : ((200 * elementScale * 1.0) + maxCircleRadius) * 0.7  // Keep original 0.7 for desktop
  
  // Center positions - properly centered in the viewBox
  // Desktop viewBox is 520 * elementScale x 480 * elementScale, so center should be at half of those
  // Mobile uses fixed center for consistent positioning
  const centerX = isMobile ? 200 : (520 * elementScale) / 2
  const centerY = isMobile ? 200 : (480 * elementScale) / 2
  
  // Grid circle position - center of circle on LEFT edge of background circle (vertically centered)
  const gridCx = centerX - bgRadius
  const gridCy = centerY
  
  // Solar circle position - center of circle on TOP edge of background circle (horizontally centered)
  const solarCx = centerX
  const solarCy = centerY - bgRadius
  
  // Inverter circle position (center)
  const inverterCx = centerX
  const inverterCy = centerY
  
  // Load circle position - center of circle on RIGHT edge of background circle (vertically centered)
  const loadCx = centerX + bgRadius
  const loadCy = centerY
  
  // Battery circle position - center of circle on BOTTOM edge of background circle (horizontally centered)
  const batteryCx = centerX
  const batteryCy = centerY + bgRadius
  
  // Calculate content bounds for tighter viewBox - reduced padding for mobile only to minimize outer area
  const padding = isMobile ? 15 : 20 * elementScale  // Reduced from 30 to 15 for mobile, keep 20 for desktop
  const contentLeft = gridCx - gridRadius - padding
  const contentRight = loadCx + loadRadius + padding
  const contentTop = solarCy - solarRadius - padding
  const contentBottom = batteryCy + batteryRadius + padding
  
  // Mobile viewBox - use fixed bounds for consistent rendering
  // For desktop, scale viewBox to match reduced container size
  const mobileViewBox = isMobile 
    ? `${contentLeft} ${contentTop} ${contentRight - contentLeft} ${contentBottom - contentTop}`
    : `0 0 ${520 * elementScale} ${480 * elementScale}` // Reduced to match smaller container
  
  // Icon sizes - scale for better visibility on mobile and desktop
  // Apply circleSizeMultiplier to all icons inside circles
  // Increased by 30% (multiply by 1.3)
  const gridIconSize = 40 * visualScale * circleSizeMultiplier * 1.3
  const solarIconSize = 40 * visualScale * circleSizeMultiplier * 1.3
  const inverterIconSize = 48 * visualScale * circleSizeMultiplier * 1.3 // Increased to 48 for better visibility
  const batteryIconSize = 32 * visualScale * circleSizeMultiplier * 1.3
  const homeIconSize = 32 * visualScale * circleSizeMultiplier * 1.3
  
  // Text sizes - scale for better visibility on mobile and desktop
  // Match font sizes with home card stats (text-sm for values, text-xs for labels)
  // Home card uses: text-sm font-medium for power values, text-xs for labels
  const textSize = isMobile ? 18 * visualScale : 16 * visualScale // Base text size
  const smallTextSize = isMobile ? 18 * visualScale : 14 * visualScale // 18 for mobile, 14 for desktop (reduced from 16)
  const extraSmallTextSize = isMobile ? 12 * visualScale : 12 * visualScale // Match home card text-xs (12px)
  
  // Stroke widths scale with visual scale
  const strokeWidthScale = visualScale
  
  return (
    <div 
      className="rounded-[24px] w-full max-w-full mx-auto"
      style={{
        width: isMobile ? '100%' : '520px',
        height: isMobile ? 'auto' : '480px',
        minHeight: isMobile ? 'auto' : '480px',
        backgroundColor: 'transparent',
        boxShadow: 'none',
        border: 'none',
        position: 'relative',
        padding: isMobile ? '0px 4px' : '0',  // Reduced from '2px 8px' to '0px 4px' for mobile only
        marginTop: isMobile ? '-32px' : '-8px',  // Increased negative margin for mobile, keep original for desktop
        marginBottom: isMobile ? '-32px' : '-8px',  // Increased negative margin for mobile, keep original for desktop
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center'
      }}
    >
      <div className="relative w-full flex justify-center items-center" style={{ 
        height: isMobile ? 'auto' : '480px',
        minHeight: isMobile ? '360px' : '460px',  // Reduced from 380 to 360 for mobile, keep 460 for desktop
        paddingTop: isMobile ? '0' : '0',
        paddingBottom: isMobile ? '0' : '0'
      }}>
        {/* SVG Container - matches section dimensions */}
        <svg
          viewBox={mobileViewBox}
          className="w-full h-full"
          xmlns="http://www.w3.org/2000/svg"
          preserveAspectRatio="xMidYMid meet"
          style={{
            width: '100%',
            height: isMobile ? '100%' : '100%',
            minHeight: isMobile ? '400px' : 'auto'
          }}
        >
          {/* Background circle - lighter, with gaps where circles overlap */}
          {(() => {
            // Calculate angles for circle positions
            // Grid: left (180 degrees), Solar: top (270 degrees), Load: right (0 degrees), Battery: bottom (90 degrees)
            const gridAngle = Math.atan2(gridCy - centerY, gridCx - centerX) * (180 / Math.PI)
            const solarAngle = Math.atan2(solarCy - centerY, solarCx - centerX) * (180 / Math.PI)
            const loadAngle = Math.atan2(loadCy - centerY, loadCx - centerX) * (180 / Math.PI)
            const batteryAngle = Math.atan2(batteryCy - centerY, batteryCx - centerX) * (180 / Math.PI)
            
            // Calculate gap size based on circle radius (in degrees)
            // We want to hide the stroke where circles overlap, so we need a gap
            const maxCircleRadius = Math.max(gridRadius, solarRadius, batteryRadius, loadRadius)
            const gapAngle = (Math.asin(maxCircleRadius / bgRadius) * (180 / Math.PI)) * 2 + 5 // Add 5 degrees padding
            
            // Draw circle in 4 arcs, skipping areas where circles are
            const strokeColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.10)' : 'rgba(0, 0, 0, 0.08)'
            const strokeWidth = 2
            
            // Helper function to create arc path
            const createArc = (startAngle: number, endAngle: number) => {
              const startRad = (startAngle * Math.PI) / 180
              const endRad = (endAngle * Math.PI) / 180
              const startX = centerX + bgRadius * Math.cos(startRad)
              const startY = centerY + bgRadius * Math.sin(startRad)
              const endX = centerX + bgRadius * Math.cos(endRad)
              const endY = centerY + bgRadius * Math.sin(endRad)
              const largeArc = endAngle - startAngle > 180 ? 1 : 0
              return `M ${startX} ${startY} A ${bgRadius} ${bgRadius} 0 ${largeArc} 1 ${endX} ${endY}`
            }
            
            // Create 4 arcs, each skipping the area around a circle
            const arcs = [
              // Arc from grid to solar (skipping grid area)
              { start: gridAngle + gapAngle / 2, end: solarAngle - gapAngle / 2 },
              // Arc from solar to load (skipping solar area)
              { start: solarAngle + gapAngle / 2, end: loadAngle - gapAngle / 2 },
              // Arc from load to battery (skipping load area)
              { start: loadAngle + gapAngle / 2, end: batteryAngle - gapAngle / 2 },
              // Arc from battery to grid (skipping battery area)
              { start: batteryAngle + gapAngle / 2, end: gridAngle - gapAngle / 2 + 360 }
            ]
            
            return (
              <>
                {arcs.map((arc, idx) => {
                  // Normalize angles to 0-360 range
                  let startAngle = arc.start
                  let endAngle = arc.end
                  
                  // Handle wrap-around
                  if (endAngle > 360) {
                    endAngle = endAngle - 360
                  }
                  if (startAngle < 0) {
                    startAngle = startAngle + 360
                  }
                  
                  // Only draw if there's a valid arc
                  if (endAngle > startAngle || (endAngle < startAngle && endAngle + 360 > startAngle)) {
                    const actualEndAngle = endAngle < startAngle ? endAngle + 360 : endAngle
                    return (
                      <path
                        key={idx}
                        d={createArc(startAngle, actualEndAngle)}
                        fill="none"
                        stroke={strokeColor}
                        strokeWidth={strokeWidth}
                        style={{ filter: 'none' }}
                      />
                    )
                  }
                  return null
                })}
              </>
            )
          })()}
          {/* Define arrow markers */}
          <defs>
            <marker
              id="arrowhead"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill={theme === 'dark' ? '#888888' : '#666666'}
              />
            </marker>
            <marker
              id="arrowhead-start"
              markerWidth="10"
              markerHeight="10"
              refX="1"
              refY="3"
              orient="auto"
            >
              <polygon
                points="10 0, 0 3, 10 6"
                fill={theme === 'dark' ? '#888888' : '#666666'}
              />
            </marker>
            {/* Yellow arrowhead for solar flow */}
            <marker
              id="arrowhead-yellow"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill="#FFD600"
              />
            </marker>
            {/* Blue arrowhead for grid export (grid to inverter) */}
            <marker
              id="arrowhead-blue"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill="#3b82f6"
              />
            </marker>
            {/* Purple arrowhead for grid import (inverter to grid) */}
            <marker
              id="arrowhead-purple"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill="#a855f7"
              />
            </marker>
            {/* Green arrowhead for battery discharge (battery to inverter) */}
            <marker
              id="arrowhead-green"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill="#10b981"
              />
            </marker>
            {/* Red arrowhead for battery charge (inverter to battery) */}
            <marker
              id="arrowhead-red"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon
                points="0 0, 10 3, 0 6"
                fill="#ef4444"
              />
            </marker>
          </defs>

          <g 
            onClick={() => navigate('/grid-detail')}
            style={{ cursor: 'pointer' }}
            className="hover:opacity-80 transition-opacity"
          >
            {/* Grid circle - moved towards left edge of background circle */}
            <circle
              cx={gridCx}
              cy={gridCy}
              r={gridRadius}
              fill="transparent"
              stroke="#00F17D"
              strokeWidth={4 * visualScale * circleSizeMultiplier}
            />
            
            {/* Grid icon - green when present, grey when not (consistent for mobile and web) */}
            {(() => {
              // Determine if grid is present (has power flow or energy import/export)
              const isGridPresent = Math.abs(gridPower) > 0 || gridImport > 0 || gridExport > 0
              
              // CSS filter to change icon color
              // For green (#00F17D): use brightness, contrast, and hue-rotate
              // For grey: use grayscale and brightness
              const iconFilter = isGridPresent 
                ? 'brightness(0) saturate(100%) invert(58%) sepia(95%) saturate(1352%) hue-rotate(95deg) brightness(102%) contrast(101%)' // Green filter
                : (theme === 'dark' 
                    ? 'brightness(0) invert(1) opacity(0.5)' // Grey/white for dark theme
                    : 'brightness(0) opacity(0.4)' // Grey/black for light theme
                  )
              
              // Apply filter via both style and as SVG attribute for better mobile support
              // Ensure filter is applied to both g and image elements for mobile compatibility
              return (
                <g style={{ filter: iconFilter, WebkitFilter: iconFilter }}>
                  <image
                    href={gridIcon}
                    x={gridCx - gridIconSize / 2}
                    y={gridCy - gridIconSize / 2}
                    width={gridIconSize}
                    height={gridIconSize}
                    style={{
                      filter: iconFilter,
                      WebkitFilter: iconFilter
                    }}
                  />
                </g>
              )
            })()}
            
            {/* Grid to Inverter Arrow - Blue/Purple/Grey with animation - Straight */}
            <g>
              {/* Determine color and direction based on gridPower */}
              {/* Convention: positive = importing (grid supplying), negative = exporting */}
              {/* Calculate connection points for straight line */}
              {(() => {
                // Grid connection point - right side of grid circle
                const gridConnectionX = gridCx + gridRadius
                const gridConnectionY = gridCy
                
                // Inverter connection point - left side of inverter circle
                const inverterConnectionX = inverterCx - inverterRadius
                const inverterConnectionY = inverterCy
                
                // Midpoint for text positioning
                const midX = (gridConnectionX + inverterConnectionX) / 2
                const midY = (gridConnectionY + inverterConnectionY) / 2
                
                return (
                  <>
                    {gridPower > 0 ? (
                      // Grid importing (grid supplying to inverter) - Blue
                      <>
                        <line
                          x1={gridConnectionX}
                          y1={gridConnectionY}
                          x2={inverterConnectionX}
                          y2={inverterConnectionY}
                          stroke="#3b82f6"
                          strokeWidth={2 * visualScale}
                        />
                        {/* Animated blue circle moving from grid to inverter */}
                        <circle r={4 * visualScale} fill="#3b82f6">
                          <animateMotion
                            dur="2.5s"
                            repeatCount="indefinite"
                            path={`M ${gridConnectionX} ${gridConnectionY} L ${inverterConnectionX} ${inverterConnectionY}`}
                          />
                        </circle>
                        {/* Power value text - theme-aware color */}
                        <text
                          x={midX}
                          y={midY - 8 * visualScale}
                          textAnchor="middle"
                          fill={textColor}
                          fontSize={smallTextSize}
                          fontWeight={isMobile ? "700" : "500"}
                          fontFamily="Roboto, sans-serif"
                          style={{
                            filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                          }}
                        >
                          {gridPower.toFixed(0)} W
                        </text>
                      </>
                    ) : gridPower < 0 ? (
                      // Grid exporting (inverter exporting to grid) - Purple
                      <>
                        <line
                          x1={inverterConnectionX}
                          y1={inverterConnectionY}
                          x2={gridConnectionX}
                          y2={gridConnectionY}
                          stroke="#a855f7"
                          strokeWidth={2 * visualScale}
                        />
                        {/* Animated purple circle moving from inverter to grid */}
                        <circle r={4 * visualScale} fill="#a855f7">
                          <animateMotion
                            dur="2.5s"
                            repeatCount="indefinite"
                            path={`M ${inverterConnectionX} ${inverterConnectionY} L ${gridConnectionX} ${gridConnectionY}`}
                          />
                        </circle>
                        {/* Power value text - theme-aware color */}
                        <text
                          x={midX}
                          y={midY - 8 * visualScale}
                          textAnchor="middle"
                          fill={textColor}
                          fontSize={smallTextSize}
                          fontWeight={isMobile ? "700" : "500"}
                          fontFamily="Roboto, sans-serif"
                          style={{
                            filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                          }}
                        >
                          {Math.abs(gridPower).toFixed(0)} W
                        </text>
                      </>
                    ) : (
                      // No power flow - Grey (theme-aware visible color)
                      <line
                        x1={inverterConnectionX}
                        y1={inverterConnectionY}
                        x2={gridConnectionX}
                        y2={gridConnectionY}
                        stroke={theme === 'dark' ? '#888888' : '#666666'}
                        strokeWidth={1 * visualScale}
                      />
                    )}
                  </>
                )
              })()}
            </g>
          </g>

         
          <g 
            onClick={() => navigate('/solar-detail')}
            style={{ cursor: 'pointer' }}
            className="hover:opacity-80 transition-opacity"
          >
            {/* Solar circle - moved towards right edge of background circle */}
            <circle
              cx={solarCx}
              cy={solarCy}
              r={solarRadius}
              fill="transparent"
              stroke="#FFD600"
              strokeWidth={4 * visualScale * circleSizeMultiplier}
            />
            
            {/* Solar icon - yellow when producing, grey when not (consistent for mobile and web) */}
            {(() => {
              // Determine if solar is currently producing (only check current power, not cumulative energy)
              const isSolarProducing = solarPower > 0
              // Color: yellow if producing, grey if not (with theme-aware contrast)
              const iconColor = isSolarProducing 
                ? '#FFD600' // Yellow when solar is producing
                : (theme === 'dark' ? '#888888' : '#666666') // Grey for both themes when not producing
              
              return (
                <g transform={`translate(${solarCx - solarIconSize / 2}, ${solarCy - solarIconSize / 2})`}>
                  <svg width={solarIconSize} height={solarIconSize} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M6.05 4.14005L5.66 3.75005C5.27 3.36005 4.64 3.37005 4.26 3.75005L4.25 3.76005C3.86 4.15005 3.86 4.78005 4.25 5.16005L4.64 5.55005C5.03 5.94005 5.65 5.94005 6.04 5.55005L6.05 5.54005C6.44 5.16005 6.44 4.52005 6.05 4.14005ZM3.01 10.5H1.99C1.44 10.5 1 10.94 1 11.49V11.5C1 12.05 1.44 12.49 1.99 12.49H3C3.56 12.5 4 12.06 4 11.51V11.5C4 10.94 3.56 10.5 3.01 10.5ZM12.01 0.550049H12C11.44 0.550049 11 0.990049 11 1.54005V2.50005C11 3.05005 11.44 3.49005 11.99 3.49005H12C12.56 3.50005 13 3.06005 13 2.51005V1.54005C13 0.990049 12.56 0.550049 12.01 0.550049ZM19.75 3.76005C19.36 3.37005 18.73 3.37005 18.34 3.75005L17.95 4.14005C17.56 4.53005 17.56 5.16005 17.95 5.54005L17.96 5.55005C18.35 5.94005 18.98 5.94005 19.36 5.55005L19.75 5.16005C20.14 4.77005 20.14 4.15005 19.75 3.76005ZM17.94 18.8601L18.33 19.25C18.72 19.64 19.35 19.64 19.74 19.25C20.13 18.8601 20.13 18.23 19.74 17.84L19.35 17.4501C18.96 17.0601 18.33 17.0701 17.95 17.4501C17.55 17.85 17.55 18.4701 17.94 18.8601ZM20 11.49V11.5C20 12.05 20.44 12.49 20.99 12.49H22C22.55 12.49 22.99 12.05 22.99 11.5V11.49C22.99 10.94 22.55 10.5 22 10.5H20.99C20.44 10.5 20 10.94 20 11.49ZM12 5.50005C8.69 5.50005 6 8.19005 6 11.5C6 14.81 8.69 17.5 12 17.5C15.31 17.5 18 14.81 18 11.5C18 8.19005 15.31 5.50005 12 5.50005ZM11.99 22.4501H12C12.55 22.4501 12.99 22.01 12.99 21.46V20.5C12.99 19.9501 12.55 19.51 12 19.51H11.99C11.44 19.51 11 19.9501 11 20.5V21.46C11 22.01 11.44 22.4501 11.99 22.4501ZM4.25 19.24C4.64 19.63 5.27 19.63 5.66 19.24L6.05 18.85C6.44 18.4601 6.43 17.83 6.05 17.4501L6.04 17.4401C5.65 17.0501 5.02 17.0501 4.63 17.4401L4.24 17.83C3.86 18.23 3.86 18.85 4.25 19.24Z" fill={iconColor}/>
                  </svg>
                </g>
              )
            })()}
            {/* Solar to Inverter Arrow - Yellow with animation - Straight */}
            {(() => {
              // Calculate connection points for straight line
              // Solar connection point - bottom of solar circle
              const solarConnectionX = solarCx
              const solarConnectionY = solarCy + solarRadius
              
              // Inverter connection point - top of inverter circle
              const inverterConnectionX = inverterCx
              const inverterConnectionY = inverterCy - inverterRadius
              
              // Midpoint for text positioning
              const midX = (solarConnectionX + inverterConnectionX) / 2
              const midY = (solarConnectionY + inverterConnectionY) / 2
              
              // Calculate perpendicular offset to place text on the right side of the line
              // Line goes from solar (top) to inverter (bottom), so right side is to the east
              // Vector from solar to inverter: (0, positive) - vertical line
              // Perpendicular to the right: (positive, 0) - horizontal offset
              const offsetX = 15 * visualScale  // Offset to the right side
              const offsetY = 0  // No vertical offset for vertical line
              
              return (
                <>
                  {/* Base line - yellow if solar power > 0, otherwise gray */}
                  <line
                    x1={solarConnectionX}
                    y1={solarConnectionY}
                    x2={inverterConnectionX}
                    y2={inverterConnectionY}
                    stroke={solarPower > 0 ? "#FFD600" : (theme === 'dark' ? '#888888' : '#666666')}
                    strokeWidth={solarPower > 0 ? 2 * visualScale : 1 * visualScale}
                  />
                  
                  {/* Animated yellow circle moving along the path - only show if solarPower > 0 */}
                  {solarPower > 0 && (
                    <circle r={4 * visualScale} fill="#FFD600">
                      <animateMotion
                        dur="2.5s"
                        repeatCount="indefinite"
                        path={`M ${solarConnectionX} ${solarConnectionY} L ${inverterConnectionX} ${inverterConnectionY}`}
                      />
                    </circle>
                  )}
                  
                  {/* Power value text positioned on the right side of the line - theme-aware color */}
                  {solarPower > 0 && (
                    <text
                      x={midX + offsetX}
                      y={midY + offsetY}
                      textAnchor="start"
                      fill={textColor}
                      fontSize={smallTextSize}
                      fontWeight={isMobile ? "700" : "500"}
                      fontFamily="Roboto, sans-serif"
                      style={{
                        filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                      }}
                    >
                      {solarPower.toFixed(0)} W
                    </text>
                  )}
                </>
              )
            })()}
          </g>

          
          <g 
            onClick={() => navigate('/inverter-detail')}
            style={{ cursor: 'pointer' }}
            className="hover:opacity-80 transition-opacity"
          >
            <circle
              cx={inverterCx}
              cy={inverterCy}
              r={inverterRadius}
              fill="transparent"
              stroke="#0F91FF"
              strokeWidth={8 * visualScale * circleSizeMultiplier}
            />
            
            {/* Inverter icon - theme-aware */}
            {(() => {
              // CSS filter to make icon theme-aware
              // For blue (#0F91FF): use brightness, contrast, and hue-rotate
              // For theme-aware: white for dark theme, dark for light theme
              const iconFilter = theme === 'dark' 
                ? 'brightness(0) invert(1)' // White for dark theme
                : 'brightness(0) saturate(100%)' // Dark for light theme
              
              return (
                <g style={{ filter: iconFilter }}>
                  <image
                    href={inverterIcon}
                    x={inverterCx - inverterIconSize / 2}
                    y={inverterCy - inverterIconSize / 2}
                    width={inverterIconSize}
                    height={inverterIconSize}
                    style={{
                      filter: iconFilter
                    }}
                  />
                </g>
              )
            })()}
          </g>

          {/* Battery (Bottom Right) - Pink */}
          
          <g 
            onClick={() => navigate('/battery-detail')}
            style={{ cursor: 'pointer' }}
            className="hover:opacity-80 transition-opacity"
          >
            <circle
              cx={batteryCx}
              cy={batteryCy}
              r={batteryRadius}
              fill="transparent"
              stroke="#FF5F85"
              strokeWidth={4 * visualScale * circleSizeMultiplier}
            />
            {/* Battery icon - centered in circle with SOC bars */}
            {(() => {
              // Determine color based on SOC
              const socColor = batterySOC > 70 ? '#10b981' : batterySOC >= 50 ? '#f59e0b' : '#ef4444' // Green, Orange, Red
              
              // Calculate how many bars should be filled (5 bars, each representing 20%)
              const filledBars = Math.ceil(batterySOC / 20)
              
              return (
                <g transform={`translate(${batteryCx}, ${batteryCy})`}>
                  <g transform={`translate(${-batteryIconSize / 2}, ${-batteryIconSize / 2})`}>
                    <svg width={batteryIconSize} height={batteryIconSize} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                      {/* Battery outline - theme-aware */}
                      <path d="M15.67 4H14V2C14 1.45 13.55 1 13 1H11C10.45 1 10 1.45 10 2V4H8.33C7.6 4 7 4.6 7 5.33V20.67C7 21.4 7.6 22 8.33 22H15.66C16.4 22 17 21.4 17 20.67V5.33C17 4.6 16.4 4 15.67 4Z" fill="none" stroke={textColor} strokeWidth="1.5"/>
                      {/* Battery terminal - theme-aware */}
                      <rect x="13" y="1" width="2" height="3" fill={textColor}/>
                      {/* SOC bars - 5 horizontal bars, each representing 20%, filling from bottom to top */}
                      {[1, 2, 3, 4, 5].map((barNum) => {
                        // Bars fill from bottom (bar 1) to top (bar 5)
                        // So bar 1 is bottom, bar 5 is top
                        const isFilled = barNum <= filledBars
                        
                        // Battery interior: x from ~8 to ~16, y from ~5.33 to ~20.67
                        const barX = 8.5 // Left edge
                        const barWidth = 7 // Width of bars
                        const totalBarHeight = 14 // Total height for all bars
                        const barHeight = totalBarHeight / 5 // Height of each bar (~2.8)
                        const barSpacing = 0.2 // Small gap between bars
                        const bottomY = 20.67 - 1 // Bottom of battery interior
                        
                        // Calculate Y position from bottom to top
                        // Bar 1 (bottom) should be at bottomY, Bar 5 (top) should be higher
                        const barY = bottomY - (barNum - 1) * (barHeight + barSpacing) - barHeight
                        
                        return (
                          <rect
                            key={barNum}
                            x={barX}
                            y={barY}
                            width={barWidth}
                            height={barHeight}
                            fill={isFilled ? socColor : 'rgba(255, 255, 255, 0.2)'}
                            rx="0.2"
                          />
                        )
                      })}
                    </svg>
                  </g>
                </g>
              )
            })()}
            {/* Battery SOC and Temperature removed as per user request */}
            {/* Battery to Inverter Arrow - Green/Red/Grey with animation - Straight */}
            {(() => {
              // Calculate connection points for straight line
              // Battery connection point - top of battery circle
              const batteryConnectionX = batteryCx
              const batteryConnectionY = batteryCy - batteryRadius
              
              // Inverter connection point - bottom of inverter circle
              const inverterConnectionX = inverterCx
              const inverterConnectionY = inverterCy + inverterRadius
              
              // Midpoint for text positioning
              const midX = (batteryConnectionX + inverterConnectionX) / 2
              const midY = (batteryConnectionY + inverterConnectionY) / 2
              
              // Calculate perpendicular offset to place text on the right side of the line
              // Line goes from battery (bottom) to inverter (top), so right side is to the east
              // Vector from battery to inverter: (0, negative) - vertical line upward
              // Perpendicular to the right: (positive, 0) - horizontal offset to the right
              const offsetX = 15 * visualScale  // Offset to the right side
              const offsetY = 0  // No vertical offset for vertical line
              
              return (
                <g>
                  {/* Determine color and direction based on batteryPower */}
                  {Math.abs(batteryPower) < 10 ? (
                    // No significant power flow - Grey (theme-aware visible color)
                    <line
                      x1={inverterConnectionX}
                      y1={inverterConnectionY}
                      x2={batteryConnectionX}
                      y2={batteryConnectionY}
                      stroke={theme === 'dark' ? '#888888' : '#666666'}
                      strokeWidth={1 * visualScale}
                    />
                  ) : batteryPower < 0 ? (
                    // Battery discharging (battery to inverter) - Green
                    <>
                      <line
                        x1={batteryConnectionX}
                        y1={batteryConnectionY}
                        x2={inverterConnectionX}
                        y2={inverterConnectionY}
                        stroke="#10b981"
                        strokeWidth={2 * visualScale}
                      />
                      {/* Animated green circle moving from battery to inverter */}
                      <circle r={4 * visualScale} fill="#10b981">
                        <animateMotion
                          dur="2.5s"
                          repeatCount="indefinite"
                          path={`M ${batteryConnectionX} ${batteryConnectionY} L ${inverterConnectionX} ${inverterConnectionY}`}
                        />
                      </circle>
                      {/* Power value text - positioned on the right side of the line - theme-aware color */}
                      <text
                        x={midX + offsetX}
                        y={midY + offsetY}
                        textAnchor="start"
                        fill={textColor}
                        fontSize={smallTextSize}
                        fontWeight={isMobile ? "700" : "500"}
                        fontFamily="Roboto, sans-serif"
                        style={{
                          filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                        }}
                      >
                        {Math.abs(batteryPower).toFixed(0)} W
                      </text>
                    </>
                  ) : (
                    // Battery charging (inverter to battery) - Red
                    <>
                      <line
                        x1={inverterConnectionX}
                        y1={inverterConnectionY}
                        x2={batteryConnectionX}
                        y2={batteryConnectionY}
                        stroke="#ef4444"
                        strokeWidth={2 * visualScale}
                      />
                      {/* Animated red circle moving from inverter to battery */}
                      <circle r={4 * visualScale} fill="#ef4444">
                        <animateMotion
                          dur="2.5s"
                          repeatCount="indefinite"
                          path={`M ${inverterConnectionX} ${inverterConnectionY} L ${batteryConnectionX} ${batteryConnectionY}`}
                        />
                      </circle>
                      {/* Power value text - positioned on the right side of the line - theme-aware color */}
                      <text
                        x={midX + offsetX}
                        y={midY + offsetY}
                        textAnchor="start"
                        fill={textColor}
                        fontSize={smallTextSize}
                        fontWeight={isMobile ? "700" : "500"}
                        fontFamily="Roboto, sans-serif"
                        style={{
                          filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                        }}
                      >
                        {batteryPower.toFixed(0)} W
                      </text>
                    </>
                  )}
                </g>
              )
            })()}
          </g>

          
          <g 
            onClick={() => navigate('/load-detail')}
            style={{ cursor: 'pointer' }}
            className="hover:opacity-80 transition-opacity"
          >
            {/* Load circle with segmented colors based on energy sources */}
            {(() => {
              // Calculate energy contributions to load
              // These represent the energy from each source that went to the load
              const solarContribution = Math.max(0, solarEnergy)
              const batteryContribution = Math.max(0, batteryDischarge)
              const gridContribution = Math.max(0, gridImport)
              
              // Calculate total energy supplied to load
              // This is the sum of all contributions (what actually supplied the load)
              const totalEnergySupplied = solarContribution + batteryContribution + gridContribution
              
              // Calculate percentages based on proportions of total energy supplied
              // Each source's percentage = its contribution / total contributions
              const denominator = totalEnergySupplied > 0 ? totalEnergySupplied : 1
              const normalizedSolar = totalEnergySupplied > 0 ? solarContribution / denominator : 0
              const normalizedBattery = totalEnergySupplied > 0 ? batteryContribution / denominator : 0
              const normalizedGrid = totalEnergySupplied > 0 ? gridContribution / denominator : 0
              
              // Debug logging
              console.log('Load circle energy mix:', {
                solarEnergy,
                batteryDischarge,
                gridImport,
                loadEnergy,
                solarContribution,
                batteryContribution,
                gridContribution,
                totalEnergySupplied,
                normalizedSolar,
                normalizedBattery,
                normalizedGrid
              })
              
              // Ensure they sum to 1 (they should already, but just in case)
              const totalPercent = normalizedSolar + normalizedBattery + normalizedGrid
              
              // Colors for each source
              const solarColor = '#FFD600' // Yellow
              const batteryColor = '#FF5F85' // Pink/Red
              const gridColor = '#a855f7' // Purple
              
              // Calculate arc angles
              const startAngle = -90 // Start from top
              
              // Calculate cumulative angles
              const solarStartAngle = startAngle
              const solarEndAngle = startAngle + normalizedSolar * 360
              const batteryStartAngle = solarEndAngle
              const batteryEndAngle = batteryStartAngle + normalizedBattery * 360
              const gridStartAngle = batteryEndAngle
              const gridEndAngle = gridStartAngle + normalizedGrid * 360
              
              // Helper function to create ring arc path (outer edge only)
              const createRingArc = (startAngle: number, endAngle: number, outerRadius: number, innerRadius: number) => {
                const innerStart = {
                  x: loadCx + innerRadius * Math.cos((startAngle * Math.PI) / 180),
                  y: loadCy + innerRadius * Math.sin((startAngle * Math.PI) / 180)
                }
                const outerStart = {
                  x: loadCx + outerRadius * Math.cos((startAngle * Math.PI) / 180),
                  y: loadCy + outerRadius * Math.sin((startAngle * Math.PI) / 180)
                }
                const innerEnd = {
                  x: loadCx + innerRadius * Math.cos((endAngle * Math.PI) / 180),
                  y: loadCy + innerRadius * Math.sin((endAngle * Math.PI) / 180)
                }
                const outerEnd = {
                  x: loadCx + outerRadius * Math.cos((endAngle * Math.PI) / 180),
                  y: loadCy + outerRadius * Math.sin((endAngle * Math.PI) / 180)
                }
                const largeArcFlag = endAngle - startAngle > 180 ? 1 : 0
                return `M ${outerStart.x} ${outerStart.y} A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} 1 ${outerEnd.x} ${outerEnd.y} L ${innerEnd.x} ${innerEnd.y} A ${innerRadius} ${innerRadius} 0 ${largeArcFlag} 0 ${innerStart.x} ${innerStart.y} Z`
              }
              
              // Calculate inner radius (keep 85% of radius for blue center, outer 15% for colored ring)
              const innerRadius = loadRadius * 0.85
              const ringThickness = loadRadius - innerRadius
              
              return (
                <>
                  {/* Base circle - visible circle with theme-aware subtle outline (no blue) */}
                  <circle
                    cx={loadCx}
                    cy={loadCy}
                    r={loadRadius}
                    fill="transparent"
                    stroke={theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                    strokeWidth={4 * visualScale * circleSizeMultiplier}
                    style={{
                      filter: 'drop-shadow(0px 4px 40px rgba(0, 0, 0, 0.08))'
                    }}
                  />
                  
                  {/* Solar segment ring - Yellow */}
                  {normalizedSolar > 0.001 && solarEndAngle !== solarStartAngle && (
                    <path
                      d={createRingArc(solarStartAngle, solarEndAngle, loadRadius, innerRadius)}
                      fill={solarColor}
                      stroke={solarColor}
                      strokeWidth={0.5 * visualScale}
                    />
                  )}
                  
                  {/* Battery segment ring - Pink/Red */}
                  {normalizedBattery > 0.001 && batteryEndAngle !== batteryStartAngle && (
                    <path
                      d={createRingArc(batteryStartAngle, batteryEndAngle, loadRadius, innerRadius)}
                      fill={batteryColor}
                      stroke={batteryColor}
                      strokeWidth={0.5 * visualScale}
                    />
                  )}
                  
                  {/* Grid segment ring - Purple */}
                  {normalizedGrid > 0.001 && gridEndAngle !== gridStartAngle && (
                    <path
                      d={createRingArc(gridStartAngle, gridEndAngle, loadRadius, innerRadius)}
                      fill={gridColor}
                      stroke={gridColor}
                      strokeWidth={0.5 * visualScale}
                    />
                  )}
                  
                  {/* Fallback: If no energy data, show a default ring */}
                  {totalEnergySupplied === 0 && (
                    <path
                      d={createRingArc(startAngle, startAngle + 360, loadRadius, innerRadius)}
                      fill={theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'}
                    />
                  )}
                </>
              )
            })()}
            {/* Home icon - theme-aware */}
            <g transform={`translate(${loadCx - homeIconSize / 2}, ${loadCy - homeIconSize / 2})`}>
              <svg width={homeIconSize} height={homeIconSize} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M10.0001 19V14H14.0001V19C14.0001 19.55 14.4501 20 15.0001 20H18.0001C18.5501 20 19.0001 19.55 19.0001 19V12H20.7001C21.1601 12 21.3801 11.43 21.0301 11.13L12.6701 3.59997C12.2901 3.25997 11.7101 3.25997 11.3301 3.59997L2.9701 11.13C2.6301 11.43 2.8401 12 3.3001 12H5.0001V19C5.0001 19.55 5.4501 20 6.0001 20H9.0001C9.5501 20 10.0001 19.55 10.0001 19Z" fill={textColor}/>
              </svg>
            </g>
            {/* Arrow from Inverter to Load - Color based on dominant power source */}
            {(() => {
              // Calculate power sources (only positive contributions to load)
              // Convention: gridPower > 0 = importing (grid supplying), gridPower < 0 = exporting
              const gridImportPower = gridPower > 0 ? gridPower : 0
              const solarPowerValue = solarPower > 0 ? solarPower : 0
              // Convention: batteryPower < 0 = discharging (battery supplying), batteryPower > 0 = charging
              const batteryDischargePower = batteryPower < 0 ? Math.abs(batteryPower) : 0
              
              // Determine dominant power source
              const isGridDominant = gridImportPower > solarPowerValue && gridImportPower > batteryDischargePower
              const isSolarDominant = solarPowerValue > batteryDischargePower && solarPowerValue > gridImportPower
              const isBatteryDominant = batteryDischargePower > gridImportPower && batteryDischargePower > solarPowerValue
              
              // Calculate total load power for animation threshold
              const totalLoadPower = gridImportPower + solarPowerValue + batteryDischargePower
              
              // Determine color and marker based on dominant source
              let lineColor, circleColor, markerId, showAnimation
              if (isGridDominant) {
                lineColor = '#3b82f6' // Blue
                circleColor = '#3b82f6'
                markerId = 'url(#arrowhead-blue)'
                showAnimation = loadPower > 10
              } else if (isSolarDominant) {
                lineColor = '#FFD600' // Yellow
                circleColor = '#FFD600'
                markerId = 'url(#arrowhead-yellow)'
                showAnimation = loadPower > 10
              } else if (isBatteryDominant) {
                lineColor = '#10b981' // Green
                circleColor = '#10b981'
                markerId = 'url(#arrowhead-green)'
                showAnimation = loadPower > 10
              } else {
                lineColor = theme === 'dark' ? '#888888' : '#666666' // Grey (theme-aware visible color)
                circleColor = theme === 'dark' ? '#888888' : '#666666'
                markerId = 'url(#arrowhead)'
                showAnimation = false
              }
              
              // Calculate connection points for straight line
              // Inverter connection point - right side of inverter circle
              const inverterConnectionX = inverterCx + inverterRadius
              const inverterConnectionY = inverterCy
              
              // Load connection point - left side of load circle
              const loadConnectionX = loadCx - loadRadius
              const loadConnectionY = loadCy
              
              // Midpoint for text positioning
              const midX = (inverterConnectionX + loadConnectionX) / 2
              const midY = (inverterConnectionY + loadConnectionY) / 2
              
              return (
                <g>
                  <line
                    x1={inverterConnectionX}
                    y1={inverterConnectionY}
                    x2={loadConnectionX}
                    y2={loadConnectionY}
                    stroke={lineColor}
                    strokeWidth={showAnimation ? 2 * visualScale : 1 * visualScale}
                  />
                  {showAnimation && (
                    <>
                      {/* Animated circle moving from inverter to load */}
                      <circle r={4 * visualScale} fill={circleColor}>
                        <animateMotion
                          dur="2.5s"
                          repeatCount="indefinite"
                          path={`M ${inverterConnectionX} ${inverterConnectionY} L ${loadConnectionX} ${loadConnectionY}`}
                        />
                      </circle>
                      {/* Power value text - positioned above the line - theme-aware color */}
                      <text
                        x={midX}
                        y={midY - 8 * visualScale}
                        textAnchor="middle"
                        fill={textColor}
                        fontSize={smallTextSize}
                        fontWeight={isMobile ? "700" : "500"}
                        fontFamily="Roboto, sans-serif"
                        style={{
                          filter: 'drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.5))'
                        }}
                      >
                        {loadPower.toFixed(0)} W
                      </text>
                    </>
                  )}
                </g>
              )
            })()}
          </g>
        </svg>
      </div>
    </div>
  )
}


