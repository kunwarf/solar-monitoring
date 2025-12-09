"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import {
  Settings,
  Home,
  Sun,
  Battery,
  Plus,
  Trash2,
  Bell,
  User,
  Shield,
  ChevronRight,
  Building2,
  Layers,
} from "lucide-react"

// Types for system hierarchy
interface InverterConfig {
  id: string
  name: string
  model: string
  maxPower: number
}

interface BatteryConfig {
  id: string
  name: string
  model: string
  capacity: number
}

interface InverterArray {
  id: string
  name: string
  inverters: InverterConfig[]
}

interface BatteryArray {
  id: string
  name: string
  batteries: BatteryConfig[]
}

interface HomeConfig {
  id: string
  name: string
  address: string
  inverterArrays: InverterArray[]
  batteryArrays: BatteryArray[]
}

// Mock initial data
const initialHomes: HomeConfig[] = [
  {
    id: "home-1",
    name: "Main Residence",
    address: "123 Solar Street, Sunnyville",
    inverterArrays: [
      {
        id: "inv-array-1",
        name: "Roof Array",
        inverters: [
          { id: "inv-1", name: "Inverter 1", model: "SolarEdge SE10K", maxPower: 10 },
          { id: "inv-2", name: "Inverter 2", model: "SolarEdge SE10K", maxPower: 10 },
        ],
      },
      {
        id: "inv-array-2",
        name: "Ground Array",
        inverters: [{ id: "inv-3", name: "Inverter 3", model: "SolarEdge SE7K", maxPower: 7 }],
      },
    ],
    batteryArrays: [
      {
        id: "bat-array-1",
        name: "Main Storage",
        batteries: [
          { id: "bat-1", name: "Battery A1", model: "Tesla Powerwall 2", capacity: 13.5 },
          { id: "bat-2", name: "Battery A2", model: "Tesla Powerwall 2", capacity: 13.5 },
        ],
      },
    ],
  },
  {
    id: "home-2",
    name: "Beach House",
    address: "456 Ocean Drive, Coastville",
    inverterArrays: [
      {
        id: "inv-array-3",
        name: "Roof Array",
        inverters: [{ id: "inv-4", name: "Roof Inverter", model: "Fronius Primo 6.0", maxPower: 6 }],
      },
    ],
    batteryArrays: [
      {
        id: "bat-array-2",
        name: "Garage Storage",
        batteries: [{ id: "bat-4", name: "Garage Battery", model: "BYD Battery-Box", capacity: 10.2 }],
      },
    ],
  },
]

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<"homes" | "devices" | "notifications" | "account">("homes")
  const [homes, setHomes] = useState<HomeConfig[]>(initialHomes)
  const [expandedHome, setExpandedHome] = useState<string | null>("home-1")

  const addHome = () => {
    const newHome: HomeConfig = {
      id: `home-${Date.now()}`,
      name: `New Home ${homes.length + 1}`,
      address: "Enter address",
      inverterArrays: [],
      batteryArrays: [],
    }
    setHomes([...homes, newHome])
  }

  const removeHome = (homeId: string) => {
    setHomes(homes.filter((h) => h.id !== homeId))
  }

  const addInverterArray = (homeId: string) => {
    setHomes(
      homes.map((home) => {
        if (home.id === homeId) {
          return {
            ...home,
            inverterArrays: [
              ...home.inverterArrays,
              {
                id: `inv-array-${Date.now()}`,
                name: `Array ${home.inverterArrays.length + 1}`,
                inverters: [],
              },
            ],
          }
        }
        return home
      }),
    )
  }

  const addBatteryArray = (homeId: string) => {
    setHomes(
      homes.map((home) => {
        if (home.id === homeId) {
          return {
            ...home,
            batteryArrays: [
              ...home.batteryArrays,
              {
                id: `bat-array-${Date.now()}`,
                name: `Storage ${home.batteryArrays.length + 1}`,
                batteries: [],
              },
            ],
          }
        }
        return home
      }),
    )
  }

  const addInverter = (homeId: string, arrayId: string) => {
    setHomes(
      homes.map((home) => {
        if (home.id === homeId) {
          return {
            ...home,
            inverterArrays: home.inverterArrays.map((arr) => {
              if (arr.id === arrayId) {
                const newId = `inv-${Date.now()}`
                return {
                  ...arr,
                  inverters: [
                    ...arr.inverters,
                    {
                      id: newId,
                      name: `Inverter ${arr.inverters.length + 1}`,
                      model: "New Inverter",
                      maxPower: 5,
                    },
                  ],
                }
              }
              return arr
            }),
          }
        }
        return home
      }),
    )
  }

  const addBattery = (homeId: string, arrayId: string) => {
    setHomes(
      homes.map((home) => {
        if (home.id === homeId) {
          return {
            ...home,
            batteryArrays: home.batteryArrays.map((arr) => {
              if (arr.id === arrayId) {
                const newId = `bat-${Date.now()}`
                return {
                  ...arr,
                  batteries: [
                    ...arr.batteries,
                    {
                      id: newId,
                      name: `Battery ${arr.batteries.length + 1}`,
                      model: "New Battery",
                      capacity: 10,
                    },
                  ],
                }
              }
              return arr
            }),
          }
        }
        return home
      }),
    )
  }

  const tabs = [
    { id: "homes", label: "Homes & System", icon: Building2 },
    { id: "devices", label: "Device Settings", icon: Settings },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "account", label: "Account", icon: User },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground">Manage your solar system configuration</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-border pb-2">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Homes & System Tab */}
      {activeTab === "homes" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-foreground">System Hierarchy</h2>
            <Button onClick={addHome} size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Add Home
            </Button>
          </div>

          {homes.map((home) => (
            <Card key={home.id} className="bg-card/50 border-border/50">
              <CardHeader
                className="cursor-pointer"
                onClick={() => setExpandedHome(expandedHome === home.id ? null : home.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <Home className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{home.name}</CardTitle>
                      <CardDescription>{home.address}</CardDescription>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                      {home.inverterArrays.reduce((acc, arr) => acc + arr.inverters.length, 0)} inverters
                    </span>
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-1 rounded">
                      {home.batteryArrays.reduce((acc, arr) => acc + arr.batteries.length, 0)} batteries
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={(e) => {
                        e.stopPropagation()
                        removeHome(home.id)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <ChevronRight
                      className={`h-5 w-5 text-muted-foreground transition-transform ${expandedHome === home.id ? "rotate-90" : ""}`}
                    />
                  </div>
                </div>
              </CardHeader>

              {expandedHome === home.id && (
                <CardContent className="pt-0 space-y-4">
                  {/* Inverter Arrays */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                        <Layers className="h-4 w-4 text-amber-500" />
                        Inverter Arrays
                      </h3>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => addInverterArray(home.id)}
                        className="h-7 text-xs"
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Add Array
                      </Button>
                    </div>

                    {home.inverterArrays.map((array) => (
                      <div key={array.id} className="ml-4 p-3 rounded-lg bg-amber-500/5 border border-amber-500/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-foreground">{array.name}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => addInverter(home.id, array.id)}
                            className="h-6 text-xs"
                          >
                            <Plus className="h-3 w-3 mr-1" />
                            Add Inverter
                          </Button>
                        </div>
                        <div className="space-y-2">
                          {array.inverters.map((inv) => (
                            <div
                              key={inv.id}
                              className="flex items-center justify-between p-2 rounded bg-background/50"
                            >
                              <div className="flex items-center gap-2">
                                <Sun className="h-4 w-4 text-amber-500" />
                                <span className="text-sm text-foreground">{inv.name}</span>
                                <span className="text-xs text-muted-foreground">({inv.model})</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">{inv.maxPower} kW</span>
                                <Link href={`/settings/inverter/${inv.id}`}>
                                  <Button variant="ghost" size="icon" className="h-6 w-6">
                                    <Settings className="h-3 w-3" />
                                  </Button>
                                </Link>
                              </div>
                            </div>
                          ))}
                          {array.inverters.length === 0 && (
                            <p className="text-xs text-muted-foreground text-center py-2">No inverters in this array</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Battery Arrays */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
                        <Layers className="h-4 w-4 text-blue-500" />
                        Battery Arrays
                      </h3>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => addBatteryArray(home.id)}
                        className="h-7 text-xs"
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Add Array
                      </Button>
                    </div>

                    {home.batteryArrays.map((array) => (
                      <div key={array.id} className="ml-4 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-foreground">{array.name}</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => addBattery(home.id, array.id)}
                            className="h-6 text-xs"
                          >
                            <Plus className="h-3 w-3 mr-1" />
                            Add Battery
                          </Button>
                        </div>
                        <div className="space-y-2">
                          {array.batteries.map((bat) => (
                            <div
                              key={bat.id}
                              className="flex items-center justify-between p-2 rounded bg-background/50"
                            >
                              <div className="flex items-center gap-2">
                                <Battery className="h-4 w-4 text-blue-500" />
                                <span className="text-sm text-foreground">{bat.name}</span>
                                <span className="text-xs text-muted-foreground">({bat.model})</span>
                              </div>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">{bat.capacity} kWh</span>
                                <Link href={`/settings/battery/${bat.id}`}>
                                  <Button variant="ghost" size="icon" className="h-6 w-6">
                                    <Settings className="h-3 w-3" />
                                  </Button>
                                </Link>
                              </div>
                            </div>
                          ))}
                          {array.batteries.length === 0 && (
                            <p className="text-xs text-muted-foreground text-center py-2">No batteries in this array</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}

      {/* Device Settings Tab */}
      {activeTab === "devices" && (
        <div className="grid grid-cols-2 gap-6">
          {/* Inverter Settings */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sun className="h-5 w-5 text-amber-500" />
                Inverter Settings
              </CardTitle>
              <CardDescription>Global settings for all inverters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-foreground">Power Limiting</span>
                  <Switch defaultChecked />
                </div>
                <p className="text-sm text-muted-foreground">Limit maximum power output during grid instability</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-foreground">MPPT Optimization</span>
                  <Switch defaultChecked />
                </div>
                <p className="text-sm text-muted-foreground">Enable advanced maximum power point tracking</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="font-medium text-foreground mb-2">Export Limit</p>
                <div className="flex items-center gap-4">
                  <div className="flex-1 h-2 bg-muted rounded-full">
                    <div className="w-4/5 h-full bg-amber-500 rounded-full" />
                  </div>
                  <span className="text-foreground font-medium">80%</span>
                </div>
                <p className="text-sm text-muted-foreground mt-2">Maximum grid export as % of capacity</p>
              </div>
            </CardContent>
          </Card>

          {/* Battery Settings */}
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Battery className="h-5 w-5 text-blue-500" />
                Battery Settings
              </CardTitle>
              <CardDescription>Global settings for all batteries</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="font-medium text-foreground mb-2">Minimum Reserve</p>
                <div className="flex items-center gap-4">
                  <div className="flex-1 h-2 bg-muted rounded-full">
                    <div className="w-1/5 h-full bg-blue-500 rounded-full" />
                  </div>
                  <span className="text-foreground font-medium">20%</span>
                </div>
                <p className="text-sm text-muted-foreground mt-2">Minimum charge level for backup</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-foreground">Cell Balancing</span>
                  <Switch defaultChecked />
                </div>
                <p className="text-sm text-muted-foreground">Automatic cell voltage balancing</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="font-medium text-foreground mb-2">Charge Rate Limit</p>
                <div className="flex items-center gap-4">
                  <div className="flex-1 h-2 bg-muted rounded-full">
                    <div className="w-full h-full bg-blue-500 rounded-full" />
                  </div>
                  <span className="text-foreground font-medium">1C</span>
                </div>
                <p className="text-sm text-muted-foreground mt-2">Maximum charging rate</p>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-foreground">Temperature Protection</span>
                  <Switch defaultChecked />
                </div>
                <p className="text-sm text-muted-foreground">Reduce charging when temperature exceeds 45°C</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Notifications Tab */}
      {activeTab === "notifications" && (
        <Card className="bg-card/50 border-border/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notification Preferences
            </CardTitle>
            <CardDescription>Choose what notifications you want to receive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {[
                { title: "System Alerts", desc: "Critical system warnings and errors", defaultChecked: true },
                { title: "Production Reports", desc: "Daily and weekly energy reports", defaultChecked: true },
                { title: "Battery Alerts", desc: "Low battery and charging notifications", defaultChecked: true },
                { title: "Grid Events", desc: "Outages and grid connection issues", defaultChecked: true },
                { title: "Maintenance Reminders", desc: "Scheduled maintenance notifications", defaultChecked: false },
                { title: "Billing Updates", desc: "Invoice and payment notifications", defaultChecked: true },
              ].map((item) => (
                <div key={item.title} className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
                  <div>
                    <p className="font-medium text-foreground">{item.title}</p>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
                  </div>
                  <Switch defaultChecked={item.defaultChecked} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Account Tab */}
      {activeTab === "account" && (
        <div className="grid grid-cols-2 gap-6">
          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="h-5 w-5" />
                Profile Information
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm text-muted-foreground">First Name</label>
                  <input
                    type="text"
                    defaultValue="John"
                    className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-lg"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground">Last Name</label>
                  <input
                    type="text"
                    defaultValue="Smith"
                    className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-lg"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Email</label>
                <input
                  type="email"
                  defaultValue="john.smith@email.com"
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-lg"
                />
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Phone</label>
                <input
                  type="tel"
                  defaultValue="+1 (555) 123-4567"
                  className="w-full mt-1 px-3 py-2 bg-background border border-border rounded-lg"
                />
              </div>
              <Button className="w-full">Save Changes</Button>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Security
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-foreground">Two-Factor Authentication</p>
                    <p className="text-sm text-muted-foreground">Add an extra layer of security</p>
                  </div>
                  <Switch />
                </div>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="font-medium text-foreground mb-2">Change Password</p>
                <Button variant="outline" className="w-full bg-transparent">
                  Update Password
                </Button>
              </div>
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="font-medium text-foreground mb-2">Active Sessions</p>
                <p className="text-sm text-muted-foreground mb-2">2 devices currently logged in</p>
                <Button variant="outline" className="w-full text-destructive bg-transparent">
                  Sign Out All Devices
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
