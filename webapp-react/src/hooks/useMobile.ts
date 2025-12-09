import { useState, useEffect } from 'react'

export const useMobile = () => {
  const [isMobile, setIsMobile] = useState(false)
  const [isCompact, setIsCompact] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768 // md breakpoint
      const compact = window.innerWidth < 640 // sm breakpoint
      setIsMobile(mobile)
      setIsCompact(compact)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  return { isMobile, isCompact }
}

