// Configuration types
export interface SystemConfig {
  home: {
    id: string
    name: string
    description?: string
  }
  arrays: Array<{
    id: string
    name: string
    inverterIds: string[]
  }>
  batteryBankArrays: Array<{
    id: string
    name: string
    batteryBankIds: string[]
  }>
  batteryBankArrayAttachments: Array<{
    batteryBankArrayId: string
    inverterArrayId: string
    attachedSince?: string
    detachedAt?: string | null
  }>
}

