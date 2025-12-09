/**
 * API service for managing application preferences
 * Handles getting and setting the default application preference
 */

import { api } from '../lib/api'

const PREFERENCE_KEY = 'default_app'

/**
 * Get user's default app preference from backend
 * @returns Promise<string> - The app ID that should be used as default
 */
export const getAppPreference = async (): Promise<string | null> => {
  try {
    const response = await api.get<{ default_app?: string }>('/api/user/preferences')
    return response.default_app || null
  } catch (error) {
    console.error('Error fetching app preference:', error)
    // Return null if API fails (will use system default)
    return null
  }
}

/**
 * Set user's default app preference on backend
 * @param appId - The app ID to set as default
 */
export const setAppPreference = async (appId: string): Promise<void> => {
  try {
    await api.post('/api/user/preferences', {
      [PREFERENCE_KEY]: appId,
    })
  } catch (error) {
    console.error('Error setting app preference:', error)
    throw error
  }
}

