import React, { useState, useRef, useEffect } from 'react'
import { Grid, ChevronDown, Check, Settings } from 'lucide-react'
import { useApp } from '../contexts/AppContext'
import { useMobile } from '../hooks/useMobile'
import { useTheme } from '../contexts/ThemeContext'

interface AppSelectorProps {
  isDrawer?: boolean
}

export const AppSelector: React.FC<AppSelectorProps> = ({ isDrawer = false }) => {
  const { currentApp, availableApps, switchApp, setDefaultApp } = useApp()
  const { isMobile } = useMobile()
  const { theme } = useTheme()
  const [isOpen, setIsOpen] = useState(false)
  const [isSettingDefault, setIsSettingDefault] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Debug logging - always log when component renders
  useEffect(() => {
    console.log('=== AppSelector RENDERED ===')
    console.log('availableApps count:', availableApps.length)
    console.log('availableApps:', JSON.stringify(availableApps.map(a => ({ id: a.id, name: a.name, enabled: a.enabled }))))
    console.log('currentApp:', currentApp.id, currentApp.name)
    console.log('============================')
  }, [availableApps, currentApp])

  // Debug logging when dropdown opens
  useEffect(() => {
    if (isOpen) {
      console.log('AppSelector - Dropdown OPENED')
      console.log('AppSelector - availableApps when dropdown is open:', availableApps.map(a => ({ id: a.id, name: a.name })))
      console.log('AppSelector - availableApps length:', availableApps.length)
    }
  }, [isOpen, availableApps])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleAppSelect = async (appId: string, setAsDefault: boolean = false) => {
    if (setAsDefault) {
      try {
        setIsSettingDefault(true)
        await setDefaultApp(appId)
        // Optionally show a toast notification
      } catch (error) {
        console.error('Error setting default app:', error)
        // Optionally show error toast
      } finally {
        setIsSettingDefault(false)
      }
    } else {
      switchApp(appId)
      setIsOpen(false)
    }
  }

  // Theme-aware colors
  const textColor = theme === 'dark' ? '#FFFFFF' : '#1B2234'
  const secondaryTextColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(27, 34, 52, 0.7)'
  const backgroundColor = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)'
  const hoverBg = theme === 'dark' ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.05)'
  const activeBg = theme === 'dark' ? '#3b82f6' : '#3b82f6'
  const activeText = '#FFFFFF'

  if (isDrawer || isMobile) {
    // Mobile/drawer version - simplified button
    return (
      <div className="relative" ref={dropdownRef}>
        <button
          onClick={() => {
            console.log('AppSelector button clicked, current isOpen:', isOpen)
            console.log('AppSelector - availableApps before toggle:', availableApps.length, availableApps.map(a => a.id))
            setIsOpen(!isOpen)
          }}
          className="flex flex-col items-center justify-center rounded-lg transition-colors px-2 py-1.5 flex-1"
          style={{
            backgroundColor: isOpen ? hoverBg : 'transparent',
            color: secondaryTextColor,
          }}
          aria-label="Select application"
          title={`Current: ${currentApp.name}`}
        >
          <Grid className="w-7 h-7 mb-0.5" style={{ color: secondaryTextColor }} />
          <span className="text-xs" style={{ fontSize: '9px', color: secondaryTextColor }}>App</span>
        </button>

        {/* Dropdown menu for mobile */}
        {isOpen && (
          <div
            className="absolute bottom-full left-0 mb-2 w-64 rounded-lg shadow-lg z-50 max-h-80 overflow-y-auto"
            style={{
              backgroundColor: backgroundColor,
              border: `1px solid ${borderColor}`,
            }}
          >
            <div className="px-4 py-2 border-b" style={{ borderColor: borderColor }}>
              <h3 className="text-sm font-semibold" style={{ color: textColor }}>
                Applications
              </h3>
            </div>
            <div className="py-2">
            {/* Always show debug info */}
            <div className="px-4 py-1 text-xs" style={{ backgroundColor: '#1a1a1a', color: '#00ff00', border: '1px solid #00ff00' }}>
              DEBUG: availableApps.length = {availableApps.length}
            </div>
            {availableApps.length === 0 && (
              <div className="px-4 py-2 text-xs text-red-500">
                No apps available (debug: {availableApps.length} apps)
              </div>
            )}
            {availableApps.map((app, index) => {
              console.log(`>>> [${index}] Rendering app in dropdown (mobile):`, app.id, app.name)
              return (
                <div key={app.id}>
                  <button
                    onClick={() => handleAppSelect(app.id)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:opacity-80 transition-opacity"
                    style={{
                      backgroundColor: currentApp.id === app.id ? activeBg : 'transparent',
                      color: currentApp.id === app.id ? activeText : textColor,
                    }}
                  >
                    <div className="flex flex-col flex-1">
                      <span className="text-sm font-medium">{app.name}</span>
                      <span className="text-xs opacity-70">{app.description}</span>
                    </div>
                    {currentApp.id === app.id && (
                      <Check className="w-4 h-4" style={{ color: activeText }} />
                    )}
                  </button>
                  {currentApp.id === app.id && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAppSelect(app.id, true)
                      }}
                      className="w-full flex items-center px-4 py-2 text-left text-xs opacity-70 hover:opacity-100 transition-opacity"
                      style={{ color: textColor }}
                      disabled={isSettingDefault}
                    >
                      <Settings className="w-3 h-3 mr-2" />
                      Set as default
                    </button>
                  )}
                </div>
              )
            })}
            </div>
          </div>
        )}
      </div>
    )
  }

  // Desktop version - icon button with dropdown
  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => {
          console.log('AppSelector button clicked (desktop), current isOpen:', isOpen)
          console.log('AppSelector - availableApps before toggle:', availableApps.length, availableApps.map(a => a.id))
          setIsOpen(!isOpen)
        }}
        className="w-12 h-12 flex items-center justify-center rounded-lg transition-colors flex-shrink-0"
        style={{
          backgroundColor: isOpen ? hoverBg : 'transparent',
          color: secondaryTextColor,
        }}
        onMouseEnter={(e) => {
          if (!isOpen) {
            e.currentTarget.style.backgroundColor = hoverBg
          }
        }}
        onMouseLeave={(e) => {
          if (!isOpen) {
            e.currentTarget.style.backgroundColor = 'transparent'
          }
        }}
        aria-label="Select application"
        title={`Current: ${currentApp.name}`}
      >
        <Grid className="w-6 h-6" />
      </button>

      {/* Dropdown menu for desktop */}
      {isOpen && (
        <div
          className="absolute bottom-full left-0 mb-2 w-72 rounded-lg shadow-xl"
          style={{
            backgroundColor: backgroundColor,
            border: `2px solid yellow`,
            maxHeight: '400px',
            overflowY: 'auto',
            overflowX: 'visible',
            minHeight: '200px',
            zIndex: 9999,
            position: 'absolute',
          }}
        >
          <div className="px-4 py-2 border-b" style={{ borderColor: borderColor }}>
            <h3 className="text-sm font-semibold" style={{ color: textColor }}>
              Select Application
            </h3>
            <p className="text-xs mt-1" style={{ color: secondaryTextColor }}>
              Current: {currentApp.name}
            </p>
          </div>
          <div className="py-2" style={{ minHeight: '50px' }}>
            {/* Always show debug info */}
            <div className="px-4 py-1 text-xs mb-2" style={{ backgroundColor: '#1a1a1a', color: '#00ff00', border: '1px solid #00ff00' }}>
              DEBUG: availableApps.length = {availableApps.length}
            </div>
            {availableApps.length === 0 && (
              <div className="px-4 py-2 text-xs text-red-500">
                No apps available (debug: {availableApps.length} apps)
              </div>
            )}
            {availableApps.map((app, index) => {
              console.log(`>>> [${index}] Rendering app in dropdown (desktop):`, app.id, app.name)
              return (
                <div 
                  key={app.id} 
                  style={{ 
                    display: 'block',
                    minHeight: '60px', 
                    border: '2px solid red', 
                    marginBottom: '8px',
                    padding: '4px',
                    backgroundColor: index === 0 ? 'rgba(255,0,0,0.1)' : 'rgba(0,255,0,0.1)',
                  }}
                >
                  <div style={{ color: 'yellow', fontSize: '10px', marginBottom: '4px' }}>
                    DEBUG: App {index} - {app.id} - {app.name}
                  </div>
                  <button
                    onClick={() => handleAppSelect(app.id)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left transition-colors"
                    style={{
                      backgroundColor: currentApp.id === app.id ? activeBg : 'transparent',
                      color: currentApp.id === app.id ? activeText : textColor,
                      minHeight: '60px',
                      display: 'flex',
                    }}
                    onMouseEnter={(e) => {
                      if (currentApp.id !== app.id) {
                        e.currentTarget.style.backgroundColor = hoverBg
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (currentApp.id !== app.id) {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }
                    }}
                  >
                    <div className="flex flex-col flex-1">
                      <span className="text-sm font-medium">{app.name}</span>
                      <span className="text-xs opacity-70">{app.description}</span>
                    </div>
                    {currentApp.id === app.id && (
                      <Check className="w-5 h-5 ml-2" style={{ color: activeText }} />
                    )}
                  </button>
                  {currentApp.id === app.id && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleAppSelect(app.id, true)
                      }}
                      className="w-full flex items-center px-4 py-2 text-left text-xs opacity-70 hover:opacity-100 transition-opacity"
                      style={{ color: textColor }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = hoverBg
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent'
                      }}
                      disabled={isSettingDefault}
                    >
                      <Settings className="w-3 h-3 mr-2" />
                      {isSettingDefault ? 'Setting...' : 'Set as default'}
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

