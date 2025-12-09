import React from 'react'
import { useTheme } from '../contexts/ThemeContext'

interface BadgeProps {
  children: React.ReactNode
  variant?: 'default' | 'outline' | 'secondary'
  className?: string
}

export const Badge: React.FC<BadgeProps> = ({ 
  children, 
  variant = 'default',
  className = '' 
}) => {
  const { theme } = useTheme()
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium'
  
  const getVariantStyles = () => {
    if (variant === 'outline') {
      return {
        backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
        borderColor: theme === 'dark' ? '#374151' : '#d1d5db',
        color: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#374151',
      }
    } else if (variant === 'secondary') {
      return {
        backgroundColor: theme === 'dark' ? '#374151' : '#f3f4f6',
        color: theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#1f2937',
      }
    } else {
      return {
        backgroundColor: theme === 'dark' ? '#1e3a8a' : '#dbeafe',
        color: theme === 'dark' ? '#93c5fd' : '#1e40af',
      }
    }
  }
  
  return (
    <span 
      className={`${baseClasses} ${className}`}
      style={getVariantStyles()}
    >
      {children}
    </span>
  )
}

