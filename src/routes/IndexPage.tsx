import React, { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export const IndexPage: React.FC = () => {
  const navigate = useNavigate()
  
  useEffect(() => {
    // Redirect to Energy Dashboard as the home screen
    navigate('/dashboard', { replace: true })
  }, [navigate])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="text-lg text-gray-600">Redirecting to Energy Dashboard...</div>
      </div>
    </div>
  )
}

