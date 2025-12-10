import { createContext, useContext, useEffect, useState, ReactNode } from "react";

type Theme = "dark" | "light";

interface ThemeContextType {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("theme") as Theme;
      if (stored) {
        // Apply theme immediately on initialization
        const root = window.document.documentElement;
        root.classList.remove("light", "dark");
        root.classList.add(stored);
        return stored;
      }
      const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      // Apply system theme immediately
      const root = window.document.documentElement;
      root.classList.remove("light", "dark");
      root.classList.add(systemTheme);
      return systemTheme;
    }
    return "dark";
  });

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(theme);
    localStorage.setItem("theme", theme);
    console.log("Theme changed to:", theme, "Classes:", root.classList.toString());
  }, [theme]);

  const toggleTheme = () => {
    const newTheme = theme === "dark" ? "light" : "dark";
    console.log("Toggling theme from", theme, "to", newTheme);
    // Update DOM immediately and synchronously BEFORE state update for instant feedback
    const root = window.document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(newTheme);
    localStorage.setItem("theme", newTheme);
    // Force CSS recalculation by accessing computed style
    getComputedStyle(root).getPropertyValue('--background');
    // Then update state to trigger re-render (useEffect will also run as backup)
    setTheme(newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    // Return safe defaults instead of throwing, for compatibility with SharedSidebar
    console.warn("useTheme called outside ThemeProvider, using defaults");
    return {
      theme: (typeof window !== "undefined" && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light" as "dark" | "light",
      setTheme: () => {},
      toggleTheme: () => {},
    };
  }
  return context;
}