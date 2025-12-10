import { API_BASE_URL } from '../config'

// Cache configuration
interface CacheConfig {
  ttl: number // Time to live in milliseconds
  key: string // Cache key
}

// Cache entry structure
interface CacheEntry<T> {
  data: T
  timestamp: number
  ttl: number
}

// Cache TTL constants (in milliseconds)
export const CACHE_TTL = {
  TELEMETRY: 5 * 1000, // 5 seconds
  ENERGY: 300 * 1000, // 5 minutes (300 seconds)
  DEVICES: 60 * 1000, // 1 minute
  HIERARCHY: 60 * 1000, // 1 minute
  BILLING: 300 * 1000, // 5 minutes
  CONFIG: Infinity, // No cache, always fetch fresh
} as const

// Cache key prefix
const CACHE_PREFIX = 'solar_api_cache_'

/**
 * Get cache key from path
 */
function getCacheKey(path: string): string {
  return `${CACHE_PREFIX}${path}`
}

/**
 * Get cached data if valid
 */
function getCached<T>(key: string): T | null {
  try {
    const cached = localStorage.getItem(key)
    if (!cached) return null

    const entry: CacheEntry<T> = JSON.parse(cached)
    const now = Date.now()
    const age = now - entry.timestamp

    // Check if cache is still valid
    if (age < entry.ttl) {
      return entry.data
    }

    // Cache expired, remove it
    localStorage.removeItem(key)
    return null
  } catch (error) {
    console.warn('Error reading cache:', error)
    return null
  }
}

/**
 * Set cache data
 */
function setCached<T>(key: string, data: T, ttl: number): void {
  try {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
      ttl,
    }
    localStorage.setItem(key, JSON.stringify(entry))
  } catch (error) {
    console.warn('Error writing cache:', error)
    // If localStorage is full, try to clear old entries
    try {
      clearExpiredCache()
      localStorage.setItem(key, JSON.stringify({ data, timestamp: Date.now(), ttl }))
    } catch (e) {
      console.error('Failed to write cache after cleanup:', e)
    }
  }
}

/**
 * Clear expired cache entries
 */
function clearExpiredCache(): void {
  try {
    const keys = Object.keys(localStorage)
    const now = Date.now()
    let cleared = 0

    for (const key of keys) {
      if (key.startsWith(CACHE_PREFIX)) {
        try {
          const cached = localStorage.getItem(key)
          if (cached) {
            const entry: CacheEntry<unknown> = JSON.parse(cached)
            const age = now - entry.timestamp
            if (age >= entry.ttl) {
              localStorage.removeItem(key)
              cleared++
            }
          }
        } catch (e) {
          // Invalid cache entry, remove it
          localStorage.removeItem(key)
          cleared++
        }
      }
    }

    if (cleared > 0) {
      console.log(`Cleared ${cleared} expired cache entries`)
    }
  } catch (error) {
    console.warn('Error clearing expired cache:', error)
  }
}

/**
 * Clear all API cache
 */
export function clearApiCache(): void {
  try {
    const keys = Object.keys(localStorage)
    for (const key of keys) {
      if (key.startsWith(CACHE_PREFIX)) {
        localStorage.removeItem(key)
      }
    }
  } catch (error) {
    console.warn('Error clearing API cache:', error)
  }
}

/**
 * Enhanced request function with caching
 */
async function request<T>(
  path: string,
  init?: RequestInit,
  cacheConfig?: CacheConfig
): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  // Use custom cache key if provided, otherwise generate from path
  const cacheKey = cacheConfig ? getCacheKey(cacheConfig.key || path) : null

  // Try to get from cache first (only for GET requests)
  if (cacheConfig && !init?.method && cacheKey) {
    const cached = getCached<T>(cacheKey)
    if (cached !== null) {
      return cached
    }
  }

  // Make API request
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API ${res.status}: ${text}`)
  }

  const ct = res.headers.get('content-type') || ''
  let data: T

  if (ct.includes('application/json')) {
    data = await res.json()
  } else {
    // @ts-expect-error: allow non-json text payloads
    data = await res.text()
  }

  // Cache the response (only for GET requests with cache config)
  if (cacheConfig && !init?.method && cacheKey && cacheConfig.ttl !== Infinity) {
    setCached(cacheKey, data, cacheConfig.ttl)
  }

  return data
}

/**
 * Enhanced API client with caching support
 */
export const api = {
  /**
   * GET request with optional caching
   */
  get: <T>(path: string, cacheConfig?: CacheConfig) =>
    request<T>(path, undefined, cacheConfig),

  /**
   * POST request (no caching)
   */
  post: <T>(path: string, body?: any) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),

  /**
   * PUT request (no caching)
   */
  put: <T>(path: string, body?: any) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),

  /**
   * DELETE request (no caching)
   */
  delete: <T>(path: string) =>
    request<T>(path, { method: 'DELETE' }),
}

// Clean up expired cache on module load
if (typeof window !== 'undefined') {
  clearExpiredCache()
  // Clean up expired cache every 5 minutes
  setInterval(clearExpiredCache, 5 * 60 * 1000)
}

