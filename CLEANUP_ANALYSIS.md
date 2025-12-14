# Default App Cleanup Analysis

## Summary
Analysis of the default (legacy) app to identify unused pages and components that can be removed.

## Pages Currently in Routes

### ✅ **ACTIVELY USED** (Keep)
1. **NewDashboardPage** (`/`, `/dashboard-new`)
   - Main dashboard, linked in sidebar
   - Status: **KEEP**

2. **BatteryDetailPage** (`/battery-detail`)
   - Linked in sidebar navigation
   - Status: **KEEP**

3. **MeterPage** (`/meter`)
   - Linked in sidebar navigation
   - Status: **KEEP**

4. **BillingDashboardPage** (`/billing`)
   - Linked in sidebar navigation
   - Status: **KEEP**

5. **BillingSetupPage** (`/billing-setup`)
   - Linked from billing dashboard
   - Status: **KEEP**

6. **SettingsPage** (`/settings`)
   - Linked in sidebar navigation
   - Status: **KEEP**

### ⚠️ **LINKED FROM DASHBOARD DIAGRAM** (Keep)
7. **GridDetailPage** (`/grid-detail`)
   - **Linked from**: EnergyDistributionDiagram component (clickable grid node)
   - **Not in sidebar**: Yes
   - Status: **KEEP** (used from dashboard diagram)

8. **SolarDetailPage** (`/solar-detail`)
   - **Linked from**: EnergyDistributionDiagram component (clickable solar node)
   - **Not in sidebar**: Yes
   - Status: **KEEP** (used from dashboard diagram)

9. **LoadDetailPage** (`/load-detail`)
   - **Linked from**: EnergyDistributionDiagram component (clickable load/home node)
   - **Not in sidebar**: Yes
   - Status: **KEEP** (used from dashboard diagram)

10. **InverterDetailPage** (`/inverter-detail`)
    - **Linked from**: EnergyDistributionDiagram component (clickable inverter node)
    - **Not in sidebar**: Yes
    - Status: **KEEP** (used from dashboard diagram)

11. **BatteryPage** (`/battery`)
    - **Linked from**: Not found in codebase
    - **Not in sidebar**: Only `/battery-detail` is linked
    - Status: **REMOVE** (redundant, use BatteryDetailPage instead)

12. **TelemetryPage** (`/telemetry`)
    - **Linked from**: Not found in codebase
    - **Not in sidebar**: Yes
    - Status: **REMOVE** (not linked anywhere)

13. **DashboardPage** (`/analytics`)
    - **Linked from**: Route exists but not in sidebar
    - **Comment in routes**: "Analytics links to old dashboard"
    - Status: **REMOVE** (old dashboard, replaced by NewDashboardPage)

### ❌ **COMPLETELY UNUSED** (Remove)
14. **AnalyticsPage** (`AnalyticsPage.tsx`)
    - **Not imported** in routes.tsx
    - **Not linked** anywhere
    - Status: **REMOVE**

15. **IndexPage** (`IndexPage.tsx`)
    - **Not imported** in routes.tsx
    - **Not linked** anywhere
    - Status: **REMOVE**

## Recommendations

### High Priority Removals
1. **AnalyticsPage.tsx** - Not imported, not used
2. **IndexPage.tsx** - Not imported, not used
3. **BatteryPage.tsx** - Redundant (BatteryDetailPage exists and is used)
4. **TelemetryPage.tsx** - Not linked anywhere
5. **DashboardPage.tsx** - Old dashboard, replaced by NewDashboardPage

## Files to Delete

```
webapp-react/src/routes/AnalyticsPage.tsx
webapp-react/src/routes/IndexPage.tsx
webapp-react/src/routes/BatteryPage.tsx
webapp-react/src/routes/TelemetryPage.tsx
webapp-react/src/routes/DashboardPage.tsx
```

## Routes to Remove from defaultAppRoutes

```typescript
// Remove these routes:
{ path: 'telemetry', element: <TelemetryPage /> },
{ path: 'battery', element: <BatteryPage /> },
{ path: 'analytics', element: <DashboardPage /> },
```

## Imports to Remove from routes.tsx

```typescript
// Remove these imports:
import { TelemetryPage } from '../../routes/TelemetryPage'
import { BatteryPage } from '../../routes/BatteryPage'
import { DashboardPage } from '../../routes/DashboardPage'
```

## Final Route Structure (After Cleanup)

```typescript
export const defaultAppRoutes = (): RouteObject[] => {
  return [
    {
      path: '/',
      element: <DefaultAppLayout />,
      children: [
        { index: true, element: <NewDashboardPage /> },
        { path: 'dashboard-new', element: <NewDashboardPage /> },
        { path: 'grid-detail', element: <GridDetailPage /> }, // Linked from EnergyDistributionDiagram
        { path: 'solar-detail', element: <SolarDetailPage /> }, // Linked from EnergyDistributionDiagram
        { path: 'load-detail', element: <LoadDetailPage /> }, // Linked from EnergyDistributionDiagram
        { path: 'inverter-detail', element: <InverterDetailPage /> }, // Linked from EnergyDistributionDiagram
        { path: 'battery-detail', element: <BatteryDetailPage /> }, // Linked from sidebar and diagram
        { path: 'meter', element: <MeterPage /> },
        { path: 'settings', element: <SettingsPage /> },
        { path: 'billing-setup', element: <BillingSetupPage /> },
        { path: 'billing', element: <BillingDashboardPage /> },
      ],
    },
  ]
}
```

## Unused Components Analysis

### ❌ **COMPONENTS ONLY USED IN REMOVED PAGES** (Remove)

#### Used only in DashboardPage (removed):
1. **PowerFlowChart.tsx** - Only used in DashboardPage
2. **PowerFlowDiagram.tsx** - Only used in DashboardPage
3. **EnergyFlowPro.tsx** - Only used in DashboardPage
4. **SolarSystemDiagram.tsx** - Only used in DashboardPage
5. **PVForecastChart.tsx** - Only used in DashboardPage
6. **Overview24hChart.tsx** - Only used in DashboardPage
7. **SelfSufficiencyBar.tsx** - Only used in DashboardPage
8. **DetailedTelemetry.tsx** - Only used in DashboardPage
9. **SummaryBar.tsx** - Only used in DashboardPage
10. **MobileSummaryBar.tsx** - Only used in DashboardPage
11. **ArrayCard.tsx** - Only used in DashboardPage
12. **SchedulerTimeline.tsx** - Only used in DashboardPage
13. **CompactMetricTile.tsx** - Only used in DashboardPage
14. **SwipeableCarousel.tsx** - Only used in DashboardPage
15. **KPICard.tsx** - Only used in DashboardPage
16. **BatteryPackCard.tsx** - Only used in DashboardPage
17. **HealthStatusCard.tsx** - Only used in DashboardPage
18. **NewDashboard/PowerGauge.tsx** - Only used in DashboardPage

#### Used only in TelemetryPage (removed):
19. **TelemetryDashboard.tsx** - Only used in TelemetryPage

#### Used only in BatteryPage (removed):
20. **BatteryBankView.tsx** - Only used in BatteryPage

### ⚠️ **POTENTIALLY UNUSED COMPONENTS** (Review)

21. **EnergyDistributionDiagram.tsx** (root level) - Not used, only NewDashboard version is used
22. **EnergyDistributionToday.tsx** - Not found in any imports
23. **EnergyDistributionTodayNew.tsx** - Not found in any imports
24. **SolarSystemDiagramNew.tsx** - Not found in any imports
25. **EnergyDashboard.tsx** - Not found in any imports (uses StatusCard and SemiCircularGauge)
26. **EnergyStatsTiles.tsx** - Not found in any imports
27. **BatterySOCChart.tsx** - Not found in any imports
28. **BatteryDetailView.tsx** - Not found in any imports
29. **SettingsTabs.tsx** - Not found in any imports
30. **Accordion.tsx** - Not found in any imports
31. **Toast.tsx** - Not found in any imports (but might be used via Toaster)
32. **Card.tsx** - Used in v0/start apps, not in default app
33. **Badge.tsx** - Used in v0/start apps, not in default app

### ✅ **COMPONENTS USED IN WIZARDS** (Keep - Used in SettingsPage)

- **DeviceManager.tsx** - Used in ArraysBatteryWizard
- **DeviceHealthIndicator.tsx** - Used in DeviceManager
- **SettingsForm.tsx** - Used in multiple wizard components (InverterConfigWizard, SmartSchedulerWizard, SystemSettingsWizard, SettingsCard, InverterControlsCard)
- **TOUWindowGrid.tsx** - Used in PowdriveTOUCard and SenergyTOUCard
- **StatusCard.tsx** - Used in EnergyDashboard (but EnergyDashboard itself is unused)
- **SemiCircularGauge.tsx** - Used in EnergyDashboard (but EnergyDashboard itself is unused)

### ✅ **COMPONENTS IN USE** (Keep)

- **NewDashboard/** folder components (TimePeriodFilter, EnergyDistributionDiagram, HomeSummaryTiles, Sidebar)
- **Billing/** folder components (all used in BillingDashboardPage)
- **wizard/** folder components (all used in SettingsPage)
- **SOCRing.tsx** (used in BatteryDetailPage)
- **FilterBar.tsx** (used in BillingSetupPage)
- **SharedSidebar.tsx** (used in AppLayout)
- **MobileBottomNav.tsx** (used in AppLayout)
- **ProtectedRoute.tsx** (used in routing)
- **ErrorBoundary.tsx** (used in main app)
- **AuthPage.tsx** (used in routing)
- **AuthGuard.tsx** (used in routing)
- **AppSelector.tsx** (used in SharedSidebar)

## Component Files to Delete

### High Priority (Used only in removed pages):
```
webapp-react/src/components/PowerFlowChart.tsx
webapp-react/src/components/PowerFlowDiagram.tsx
webapp-react/src/components/EnergyFlowPro.tsx
webapp-react/src/components/SolarSystemDiagram.tsx
webapp-react/src/components/PVForecastChart.tsx
webapp-react/src/components/Overview24hChart.tsx
webapp-react/src/components/SelfSufficiencyBar.tsx
webapp-react/src/components/DetailedTelemetry.tsx
webapp-react/src/components/SummaryBar.tsx
webapp-react/src/components/MobileSummaryBar.tsx
webapp-react/src/components/ArrayCard.tsx
webapp-react/src/components/SchedulerTimeline.tsx
webapp-react/src/components/CompactMetricTile.tsx
webapp-react/src/components/SwipeableCarousel.tsx
webapp-react/src/components/KPICard.tsx
webapp-react/src/components/BatteryPackCard.tsx
webapp-react/src/components/HealthStatusCard.tsx
webapp-react/src/components/NewDashboard/PowerGauge.tsx
webapp-react/src/components/TelemetryDashboard.tsx
webapp-react/src/components/BatteryBankView.tsx
```

### Medium Priority (Potentially unused - verify before deleting):
```
webapp-react/src/components/EnergyDistributionDiagram.tsx (root level - duplicate of NewDashboard version)
webapp-react/src/components/EnergyDistributionToday.tsx
webapp-react/src/components/EnergyDistributionTodayNew.tsx
webapp-react/src/components/SolarSystemDiagramNew.tsx
webapp-react/src/components/EnergyDashboard.tsx (unused, but uses StatusCard and SemiCircularGauge)
webapp-react/src/components/EnergyStatsTiles.tsx
webapp-react/src/components/BatterySOCChart.tsx
webapp-react/src/components/BatteryDetailView.tsx
webapp-react/src/components/SettingsTabs.tsx
webapp-react/src/components/Accordion.tsx
```

### Components to KEEP (Used in wizards/settings):
```
webapp-react/src/components/DeviceManager.tsx (used in ArraysBatteryWizard)
webapp-react/src/components/DeviceHealthIndicator.tsx (used in DeviceManager)
webapp-react/src/components/SettingsForm.tsx (used in multiple wizard components)
webapp-react/src/components/TOUWindowGrid.tsx (used in TOU cards)
webapp-react/src/components/StatusCard.tsx (used in EnergyDashboard, but EnergyDashboard is unused - review)
webapp-react/src/components/SemiCircularGauge.tsx (used in EnergyDashboard, but EnergyDashboard is unused - review)
```

### Low Priority (Used in other apps, not default):
```
webapp-react/src/components/Card.tsx (used in v0/start apps)
webapp-react/src/components/Badge.tsx (used in v0/start apps)
```

## Summary of Unused Components

### Confirmed Unused (Safe to Delete):
- 20 components used only in removed pages (DashboardPage, TelemetryPage, BatteryPage)
- 1 duplicate component (root level EnergyDistributionDiagram)

### Needs Review Before Deletion:
- 9 components that appear unused but should be verified
- 2 components (StatusCard, SemiCircularGauge) used only in unused EnergyDashboard

### Must Keep:
- All NewDashboard/ components (used in NewDashboardPage)
- All Billing/ components (used in BillingDashboardPage)
- All wizard/ components (used in SettingsPage)
- DeviceManager, DeviceHealthIndicator, SettingsForm, TOUWindowGrid (used in wizards)
- SOCRing, FilterBar (used in kept pages)
- SharedSidebar, MobileBottomNav (used in layouts)

## Estimated Cleanup Impact

- **Page files to delete**: 5 files
- **Component files to delete**: ~20-30 files (20 confirmed + 9-10 after review)
- **Routes to remove**: 3 routes
- **Code reduction**: ~5000-7000 lines of unused code
- **Maintenance burden**: Significantly reduced

