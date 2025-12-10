// Backend response types (if billing endpoints exist)
export interface BackendBillingResponse {
  status: string
  billing?: {
    current_period?: {
      start_date?: string
      end_date?: string
      days_remaining?: number
    }
    energy_produced?: number
    energy_consumed?: number
    energy_exported?: number
    energy_imported?: number
    feed_in_rate?: number
    import_rate?: number
    earnings?: number
    costs?: number
    net_balance?: number
  }
}

// Normalized frontend types
export interface BillingData {
  currentPeriod: {
    startDate: string
    endDate: string
    daysRemaining: number
  }
  energyProduced: number // kWh
  energyConsumed: number // kWh
  energyExported: number // kWh
  energyImported: number // kWh
  feedInRate: number // currency per kWh
  importRate: number // currency per kWh
  earnings: number // currency
  costs: number // currency
  netBalance: number // currency
}

