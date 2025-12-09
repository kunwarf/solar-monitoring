import React, { useState, ReactNode } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { useMobile } from '../hooks/useMobile'
import { ChevronRight, Check } from 'lucide-react'

interface WizardStep {
  id: string
  label: string
  icon?: ReactNode
  description?: string
}

interface SettingsWizardProps {
  steps: WizardStep[]
  currentStep: number
  onStepChange: (step: number) => void
  children: ReactNode
  onSave?: () => Promise<void>
  onCancel?: () => void
  saving?: boolean
}

export const SettingsWizard: React.FC<SettingsWizardProps> = ({
  steps,
  currentStep,
  onStepChange,
  children,
  onSave,
  onCancel,
  saving = false
}) => {
  const { theme } = useTheme()
  const { isMobile } = useMobile()
  
  // Theme-aware colors
  const bgColor = theme === 'dark' ? '#111827' : '#f9fafb' // gray-900 or gray-50
  const cardBg = theme === 'dark' ? '#1f2937' : '#ffffff' // gray-800 or white
  const textColor = theme === 'dark' ? '#ffffff' : '#1f2937' // white or gray-800
  const textSecondary = theme === 'dark' ? 'rgba(255, 255, 255, 0.7)' : '#6b7280' // gray-400
  const borderColor = theme === 'dark' ? '#374151' : '#e5e7eb' // gray-700 or gray-200
  const activeBg = theme === 'dark' ? '#3b82f6' : '#3b82f6' // blue-600
  const completedBg = theme === 'dark' ? '#10b981' : '#10b981' // green-600
  const inactiveBg = theme === 'dark' ? '#374151' : '#e5e7eb' // gray-700 or gray-200

  const canGoNext = currentStep < steps.length - 1
  const canGoPrev = currentStep > 0

  const handleNext = () => {
    if (canGoNext) {
      onStepChange(currentStep + 1)
    }
  }

  const handlePrev = () => {
    if (canGoPrev) {
      onStepChange(currentStep - 1)
    }
  }

  return (
    <div 
      className="min-h-screen"
      style={{ backgroundColor: bgColor }}
    >
      <div className={`max-w-6xl mx-auto ${isMobile ? 'p-4' : 'p-6'}`}>
        {/* Wizard Header */}
        <div className={`${isMobile ? 'mb-4' : 'mb-8'}`}>
          <h1 
            className={`${isMobile ? 'text-xl' : 'text-3xl'} font-bold ${isMobile ? 'mb-1' : 'mb-2'}`}
            style={{ color: textColor }}
          >
            Settings Configuration
          </h1>
          <p 
            className={`${isMobile ? 'text-xs' : 'text-sm'}`}
            style={{ color: textSecondary }}
          >
            Configure your solar monitoring system step by step
          </p>
        </div>

        {/* Step Indicator */}
        <div 
          className={`${isMobile ? 'mb-4 p-3' : 'mb-8 p-6'} rounded-lg overflow-x-auto`}
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
          }}
        >
          <div className={`flex ${isMobile ? 'items-start gap-2 min-w-max' : 'items-center justify-between'}`}>
            {steps.map((step, index) => {
              const isActive = index === currentStep
              const isCompleted = index < currentStep
              const isLast = index === steps.length - 1

              return (
                <React.Fragment key={step.id}>
                  <div className={`flex items-center ${isMobile ? 'flex-shrink-0' : 'flex-1'}`}>
                    <div className={`flex flex-col items-center ${isMobile ? 'w-16' : 'flex-1'}`}>
                      {/* Step Circle */}
                      <div
                        className={`${isMobile ? 'w-10 h-10' : 'w-12 h-12'} rounded-full flex items-center justify-center font-semibold ${isMobile ? 'text-xs' : 'text-sm'} transition-all`}
                        style={{
                          backgroundColor: isCompleted 
                            ? completedBg 
                            : isActive 
                              ? activeBg 
                              : inactiveBg,
                          color: isActive || isCompleted ? '#ffffff' : textSecondary,
                          border: isActive ? `2px solid ${activeBg}` : 'none',
                        }}
                      >
                        {isCompleted ? (
                          <Check className={isMobile ? 'w-5 h-5' : 'w-6 h-6'} />
                        ) : (
                          index + 1
                        )}
                      </div>
                      {/* Step Label */}
                      <div className={`${isMobile ? 'mt-1' : 'mt-2'} text-center`}>
                        <div 
                          className={`${isMobile ? 'text-xs' : 'text-sm'} font-medium`}
                          style={{ 
                            color: isActive ? textColor : textSecondary 
                          }}
                        >
                          {step.label}
                        </div>
                        {step.description && !isMobile && (
                          <div 
                            className="text-xs mt-1"
                            style={{ color: textSecondary }}
                          >
                            {step.description}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                  {!isLast && (
                    <div 
                      className={`${isMobile ? 'w-2 h-0.5 mx-1 flex-shrink-0' : 'flex-1 h-0.5 mx-4'}`}
                      style={{ 
                        backgroundColor: isCompleted ? completedBg : borderColor 
                      }}
                    />
                  )}
                </React.Fragment>
              )
            })}
          </div>
        </div>

        {/* Step Content */}
        <div 
          className={`rounded-lg ${isMobile ? 'p-4 mb-4' : 'p-6 mb-6'}`}
          style={{
            backgroundColor: cardBg,
            border: `1px solid ${borderColor}`,
            minHeight: isMobile ? '300px' : '400px',
          }}
        >
          {children}
        </div>

        {/* Navigation Buttons */}
        <div className={`flex ${isMobile ? 'flex-col-reverse gap-3' : 'justify-between items-center'}`}>
          <button
            onClick={handlePrev}
            disabled={!canGoPrev}
            className={`${isMobile ? 'w-full' : ''} ${isMobile ? 'py-3' : 'px-6 py-2'} rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed`}
            style={{
              backgroundColor: canGoPrev ? (theme === 'dark' ? '#374151' : '#e5e7eb') : 'transparent',
              color: canGoPrev ? textColor : textSecondary,
              border: `1px solid ${borderColor}`,
              minHeight: '44px', // Minimum touch target
            }}
          >
            Previous
          </button>

          <div className={`flex ${isMobile ? 'flex-col gap-3 w-full' : 'gap-3'}`}>
            {onCancel && (
              <button
                onClick={onCancel}
                disabled={saving}
                className={`${isMobile ? 'w-full' : ''} ${isMobile ? 'py-3' : 'px-6 py-2'} rounded-lg font-medium transition-colors`}
                style={{
                  backgroundColor: 'transparent',
                  color: textColor,
                  border: `1px solid ${borderColor}`,
                  minHeight: '44px', // Minimum touch target
                }}
              >
                Cancel
              </button>
            )}
            {onSave && currentStep === steps.length - 1 && (
              <button
                onClick={onSave}
                disabled={saving}
                className={`${isMobile ? 'w-full' : ''} ${isMobile ? 'py-3' : 'px-6 py-2'} rounded-lg font-medium text-white transition-colors disabled:opacity-50`}
                style={{
                  backgroundColor: saving ? '#6b7280' : '#3b82f6',
                  minHeight: '44px', // Minimum touch target
                }}
              >
                {saving ? 'Saving...' : 'Save All'}
              </button>
            )}
            {canGoNext && (
              <button
                onClick={handleNext}
                className={`${isMobile ? 'w-full' : ''} ${isMobile ? 'py-3' : 'px-6 py-2'} rounded-lg font-medium text-white transition-colors flex items-center ${isMobile ? 'justify-center' : 'gap-2'}`}
                style={{ 
                  backgroundColor: '#3b82f6',
                  minHeight: '44px', // Minimum touch target
                }}
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

