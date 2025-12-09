import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

type Theme = 'light' | 'dark'

interface V0ThemeContextType {
  theme: Theme
  toggleTheme: () => void
  setTheme: (theme: Theme) => void
}

const V0ThemeContext = createContext<V0ThemeContextType | undefined>(undefined)

export const V0ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    // Check localStorage first, then system preference
    const stored = localStorage.getItem('v0-theme') as Theme | null
    if (stored) return stored
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    // Remove any existing theme classes
    root.classList.remove('dark', 'light')
    // Add the current theme class
    root.classList.add(theme)
    localStorage.setItem('v0-theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme)
  }

  return (
    <V0ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </V0ThemeContext.Provider>
  )
}

export const useV0Theme = () => {
  const context = useContext(V0ThemeContext)
  if (context === undefined) {
    // Return a safe default instead of throwing
    // This allows the hook to be called even when not in V0ThemeProvider
    return {
      theme: (localStorage.getItem('v0-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')) as Theme,
      toggleTheme: () => {},
      setTheme: () => {},
    }
  }
  return context
}

