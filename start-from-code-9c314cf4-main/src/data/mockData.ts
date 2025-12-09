// Mock data for the solar monitoring application

export const energyStats = {
  solarPower: 8.4,
  batteryPower: 2.1,
  batteryLevel: 78,
  consumption: 5.2,
  gridPower: 1.1,
  isGridExporting: true,
  dailyProduction: 42.6,
  dailyConsumption: 38.2,
  selfConsumption: 89,
  gridExported: 4.4,
  // New environmental & financial metrics
  co2Saved: 18.7, // kg CO2 saved today
  moneySaved: 12.45, // $ saved today from solar
  monthlyBillAmount: 48.20, // Current month bill estimate
  dailyPrediction: 45.0, // Predicted kWh for today
  avgKwPerKwp: 4.26, // Average kWh produced per kWp of installed capacity
  installedCapacity: 10, // kWp of installed solar panels
};

export const devices = [
  {
    id: "inv-001",
    name: "Inverter Array 1",
    type: "inverter" as const,
    status: "online" as const,
    model: "SolarMax 10K",
    serialNumber: "SM-2024-INV-001",
    value: "8.4",
    unit: "kW",
    metrics: [
      { label: "Power Output", value: "8.4", unit: "kW" },
      { label: "Efficiency", value: "97.2", unit: "%" },
      { label: "DC Voltage", value: "580", unit: "V" },
      { label: "Temperature", value: "42", unit: "°C" },
    ],
  },
  {
    id: "inv-002",
    name: "Inverter Array 2",
    type: "inverter" as const,
    status: "online" as const,
    model: "SolarMax 10K",
    serialNumber: "SM-2024-INV-002",
    value: "7.8",
    unit: "kW",
    metrics: [
      { label: "Power Output", value: "7.8", unit: "kW" },
      { label: "Efficiency", value: "96.8", unit: "%" },
      { label: "DC Voltage", value: "575", unit: "V" },
      { label: "Temperature", value: "44", unit: "°C" },
    ],
  },
  {
    id: "bat-001",
    name: "Battery Pack 1",
    type: "battery" as const,
    status: "online" as const,
    model: "PowerStore 15kWh",
    serialNumber: "PS-2024-BAT-001",
    value: "78",
    unit: "%",
    metrics: [
      { label: "State of Charge", value: "78", unit: "%" },
      { label: "Charge Rate", value: "2.1", unit: "kW" },
      { label: "Cell Voltage", value: "3.42", unit: "V" },
      { label: "Temperature", value: "28", unit: "°C" },
    ],
  },
  {
    id: "bat-002",
    name: "Battery Pack 2",
    type: "battery" as const,
    status: "warning" as const,
    model: "PowerStore 15kWh",
    serialNumber: "PS-2024-BAT-002",
    value: "65",
    unit: "%",
    metrics: [
      { label: "State of Charge", value: "65", unit: "%" },
      { label: "Charge Rate", value: "1.8", unit: "kW" },
      { label: "Cell Voltage", value: "3.38", unit: "V" },
      { label: "Temperature", value: "32", unit: "°C" },
    ],
  },
  {
    id: "mtr-001",
    name: "Main Energy Meter",
    type: "meter" as const,
    status: "online" as const,
    model: "GridSense Pro",
    serialNumber: "GS-2024-MTR-001",
    value: "5.2",
    unit: "kW",
    metrics: [
      { label: "Power", value: "5.2", unit: "kW" },
      { label: "Grid Export", value: "1.1", unit: "kW" },
      { label: "Frequency", value: "50.02", unit: "Hz" },
      { label: "Power Factor", value: "0.98", unit: "" },
    ],
  },
  {
    id: "mtr-002",
    name: "Solar Production Meter",
    type: "meter" as const,
    status: "online" as const,
    model: "GridSense Pro",
    serialNumber: "GS-2024-MTR-002",
    value: "16.2",
    unit: "kW",
    metrics: [
      { label: "Total Power", value: "16.2", unit: "kW" },
      { label: "Today's Yield", value: "42.6", unit: "kWh" },
      { label: "Voltage L1", value: "238", unit: "V" },
      { label: "Current", value: "22.4", unit: "A" },
    ],
  },
];

export const chartData = Array.from({ length: 24 }, (_, i) => {
  const hour = i;
  const sunIntensity = Math.max(0, Math.sin((hour - 6) * Math.PI / 12));
  return {
    time: `${hour.toString().padStart(2, "0")}:00`,
    solar: parseFloat((sunIntensity * 10 + Math.random() * 2).toFixed(1)),
    consumption: parseFloat((3 + Math.random() * 4 + (hour >= 18 && hour <= 22 ? 3 : 0)).toFixed(1)),
    battery: parseFloat((sunIntensity > 0.5 ? 2 + Math.random() : -1 - Math.random()).toFixed(1)),
    grid: parseFloat((Math.random() * 2 - 1).toFixed(1)),
  };
});

export const telemetryData = [
  { id: "1", timestamp: "14:32:15", parameter: "DC Voltage", value: "580.2", unit: "V", status: "normal" as const },
  { id: "2", timestamp: "14:32:15", parameter: "AC Current", value: "22.4", unit: "A", status: "normal" as const },
  { id: "3", timestamp: "14:32:15", parameter: "Power Output", value: "8.42", unit: "kW", status: "normal" as const },
  { id: "4", timestamp: "14:32:15", parameter: "Inverter Temp", value: "42.1", unit: "°C", status: "normal" as const },
  { id: "5", timestamp: "14:32:15", parameter: "Efficiency", value: "97.2", unit: "%", status: "normal" as const },
  { id: "6", timestamp: "14:32:15", parameter: "Battery SOC", value: "78", unit: "%", status: "normal" as const },
  { id: "7", timestamp: "14:32:15", parameter: "Battery Temp", value: "32.5", unit: "°C", status: "warning" as const },
  { id: "8", timestamp: "14:32:15", parameter: "Cell Voltage", value: "3.42", unit: "V", status: "normal" as const },
  { id: "9", timestamp: "14:32:15", parameter: "Grid Frequency", value: "50.02", unit: "Hz", status: "normal" as const },
  { id: "10", timestamp: "14:32:15", parameter: "Power Factor", value: "0.98", unit: "", status: "normal" as const },
];

export const billingData = {
  currentPeriod: {
    startDate: "2024-11-01",
    endDate: "2024-11-30",
    daysRemaining: 12,
  },
  energyProduced: 1284.6,
  energyConsumed: 892.4,
  energyExported: 392.2,
  energyImported: 124.8,
  feedInRate: 0.08,
  importRate: 0.24,
  earnings: 31.38,
  costs: 29.95,
  netBalance: 1.43,
  monthlyHistory: [
    { month: "Jun", produced: 1456, consumed: 780, exported: 676, imported: 98, earnings: 54.08, costs: 23.52, netBalance: 30.56, lastYearBill: 68.50, thisYearBill: 23.52 },
    { month: "Jul", produced: 1589, consumed: 820, exported: 769, imported: 112, earnings: 61.52, costs: 26.88, netBalance: 34.64, lastYearBill: 72.40, thisYearBill: 26.88 },
    { month: "Aug", produced: 1423, consumed: 856, exported: 567, imported: 134, earnings: 45.36, costs: 32.16, netBalance: 13.20, lastYearBill: 78.20, thisYearBill: 32.16 },
    { month: "Sep", produced: 1234, consumed: 890, exported: 344, imported: 156, earnings: 27.52, costs: 37.44, netBalance: -9.92, lastYearBill: 85.60, thisYearBill: 37.44 },
    { month: "Oct", produced: 1089, consumed: 912, exported: 177, imported: 189, earnings: 14.16, costs: 45.36, netBalance: -31.20, lastYearBill: 92.30, thisYearBill: 45.36 },
    { month: "Nov", produced: 1284, consumed: 892, exported: 392, imported: 125, earnings: 31.38, costs: 29.95, netBalance: 1.43, lastYearBill: 88.75, thisYearBill: 29.95 },
  ],
};

export const settingsData = {
  system: {
    name: "Home Solar System",
    location: "123 Solar Street, Sunnyvale",
    timezone: "UTC+5:00",
    currency: "USD",
  },
  notifications: {
    email: true,
    push: true,
    sms: false,
    alerts: {
      lowBattery: 20,
      highTemperature: 50,
      gridOutage: true,
      maintenanceReminder: true,
    },
  },
  gridExport: {
    enabled: true,
    maxExportPower: 10,
    feedInTariff: 0.08,
    peakHoursStart: "18:00",
    peakHoursEnd: "22:00",
  },
  battery: {
    minimumSoc: 10,
    maximumSoc: 95,
    chargePriority: "solar-first",
    dischargePriority: "peak-shaving",
  },
};
