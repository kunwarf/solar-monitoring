import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type Theme = 'light' | 'dark'

interface StartThemeContextType {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const StartThemeContext = createContext<StartThemeContextType | undefined>(undefined)

export const StartThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first, then system preference
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('start-theme') as Theme | null
      if (stored) return stored
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    // Remove any existing theme classes
    root.classList.remove('dark', 'light')
    // Add the current theme class
    root.classList.add(theme)
    if (typeof window !== 'undefined') {
      localStorage.setItem('start-theme', theme)
    }
  }, [theme])

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <StartThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </StartThemeContext.Provider>
  )
}

export const useStartTheme = () => {
  const context = useContext(StartThemeContext)
  // Return a default safe value if context is undefined
  if (context === undefined) {
    console.warn('useStartTheme must be used within a StartThemeProvider, but was not. Returning default theme values.')
    return {
      theme: 'dark' as Theme,
      toggleTheme: () => { console.warn('toggleTheme called outside StartThemeProvider'); },
      setTheme: () => { console.warn('setTheme called outside StartThemeProvider'); },
    }
  }
  return context
}

