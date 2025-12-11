// Main API layer exports
// This is the main entry point for all API functionality

// Client (with caching)
export { api, CACHE_TTL, clearApiCache } from './client'

// Types
export * from './types'

// Services (direct API calls)
export * from './services'

// Hooks (React Query hooks)
export * from './hooks'

// Normalizers (if needed directly)
export * from './normalizers'

// Managers
export * from './managers'

// Models (hierarchy objects)
export * from './models'

