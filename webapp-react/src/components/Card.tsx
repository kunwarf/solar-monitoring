import React from 'react'
import { useTheme } from '../contexts/ThemeContext'

interface CardProps {
  children: React.ReactNode
  className?: string
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

interface CardTitleProps {
  children: React.ReactNode
  className?: string
}

interface CardContentProps {
  children: React.ReactNode
  className?: string
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  const { theme } = useTheme()
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff'
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'
  const shadowColor = theme === 'dark' ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.1)'

  return (
    <div 
      className={`rounded-lg shadow-lg ${className}`}
      style={{
        backgroundColor: cardBg,
        border: `1px solid ${borderColor}`,
        boxShadow: `0px 4px 6px ${shadowColor}`,
      }}
    >
      {children}
    </div>
  )
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className = '' }) => {
  const { theme } = useTheme()
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb'

  return (
    <div 
      className={`px-6 py-4 border-b ${className}`}
      style={{ borderColor }}
    >
      {children}
    </div>
  )
}

export const CardTitle: React.FC<CardTitleProps> = ({ children, className = '' }) => {
  const { theme } = useTheme()
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937'

  return (
    <h3 
      className={`text-lg font-semibold ${className}`}
      style={{ color: textColor }}
    >
      {children}
    </h3>
  )
}

export const CardContent: React.FC<CardContentProps> = ({ children, className = '' }) => {
  return (
    <div className={`px-6 py-4 ${className}`}>
      {children}
    </div>
  )
}

