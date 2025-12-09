import React from 'react'

interface DeviceHealthIndicatorProps {
  connected: boolean
  warning?: boolean
  lastUpdate?: string
  onTest?: () => void
}

export const DeviceHealthIndicator: React.FC<DeviceHealthIndicatorProps> = ({
  connected,
  warning = false,
  lastUpdate,
  onTest
}) => {
  const getStatusColor = () => {
    if (!connected) return 'text-red-500 bg-red-100'
    if (warning) return 'text-yellow-500 bg-yellow-100'
    return 'text-green-500 bg-green-100'
  }

  const getStatusIcon = () => {
    if (!connected) return '🔴'
    if (warning) return '🟡'
    return '🟢'
  }

  const getStatusText = () => {
    if (!connected) return 'Disconnected'
    if (warning) return 'Warning'
    return 'Connected'
  }

  return (
    <div className="flex items-center space-x-3">
      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${getStatusColor()}`}>
        <span className="mr-1.5">{getStatusIcon()}</span>
        {getStatusText()}
      </span>
      {lastUpdate && (
        <span className="text-xs text-gray-500">
          Last update: {lastUpdate}
        </span>
      )}
      {onTest && (
        <button
          onClick={onTest}
          className="text-xs text-blue-600 hover:text-blue-800 font-medium"
        >
          Test Connection
        </button>
      )}
    </div>
  )
}

