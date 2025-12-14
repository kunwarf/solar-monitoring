# Components Cleanup Analysis

## Analysis Date: 2025-01-XX

This document identifies unused components in `webapp-react/src/components` that can be safely removed.

---

## ✅ **COMPONENTS IN USE** (Keep)

### Core Components (Used in routing/layout):
- **AuthPage.tsx** - Used in main routing (`main.tsx`)
- **AuthGuard.tsx** - Used in routing
- **ProtectedRoute.tsx** - Used in start app routing
- **ErrorBoundary.tsx** - Used in main app (`main.tsx`)
- **AppSelector.tsx** - Used in SharedSidebar
- **SharedSidebar.tsx** - Used in both default and start app layouts
- **MobileBottomNav.tsx** - Used in both default and start app layouts
- **FilterBar.tsx** - Used in BillingSetupPage

### New Dashboard Components:
- **NewDashboard/EnergyDistributionDiagram.tsx** - Used in NewDashboardPage
- **NewDashboard/HomeSummaryTiles.tsx** - Used in NewDashboardPage
- **NewDashboard/Sidebar.tsx** - Used in NewDashboardPage
- **NewDashboard/TimePeriodFilter.tsx** - Used in NewDashboardPage

### Billing Components (All used in BillingDashboardPage):
- **Billing/BillTrendChart.tsx**
- **Billing/CapacityMeter.tsx**
- **Billing/CreditLedger.tsx**
- **Billing/DailyBillingWidgets.tsx**
- **Billing/ForecastCard.tsx**
- **Billing/ImportExportChart.tsx**
- **Billing/MonthlyBillCard.tsx**
- **Billing/SolarLoadComparison.tsx**

### Wizard Components (All used in SettingsPage):
- **wizard/ArraysBatteryWizard.tsx**
- **wizard/HierarchyWizard.tsx**
- **wizard/InverterConfigWizard.tsx**
- **wizard/SmartSchedulerWizard.tsx**
- **wizard/SystemSettingsWizard.tsx**
- **wizard/inverter/** (all sub-components)

### Settings Components:
- **SettingsWizard.tsx** - Used in SettingsPage
- **SettingsForm.tsx** - Used in SettingsWizard
- **SettingsTabs.tsx** - Used in SettingsWizard
- **TOUWindowGrid.tsx** - Used in wizard components

### Other Used Components:
- **SOCRing.tsx** - Used in BatteryDetailPage
- **SOHRing.tsx** - Used in wizard components
- **Toast.tsx** - Type exported in useToast hook (but component itself may be unused)
- **DeviceManager.tsx** - Used in ArraysBatteryWizard
- **DeviceHealthIndicator.tsx** - Used in DeviceManager

---

## ❌ **UNUSED COMPONENTS** (Can be deleted)

### High Priority (Definitely Unused):
1. **EnergyDashboard.tsx** - Not imported anywhere (uses StatusCard and SemiCircularGauge internally, but EnergyDashboard itself is unused)
2. **EnergyDistributionToday.tsx** - Not imported anywhere
3. **EnergyDistributionTodayNew.tsx** - Not imported anywhere
4. **EnergyStatsTiles.tsx** - Not imported anywhere
5. **BatterySOCChart.tsx** - Not imported anywhere
6. **SolarSystemDiagramNew.tsx** - Not imported anywhere
7. **BatteryDetailView.tsx** - Not imported anywhere (different from BatteryDetailPage which uses SOCRing)

### Medium Priority (Used only by unused components):
8. **StatusCard.tsx** - Only used by EnergyDashboard (which is unused)
9. **SemiCircularGauge.tsx** - Only used by EnergyDashboard (which is unused)

### Low Priority (Type-only usage, component may be unused):
10. **Toast.tsx** - Only exports type `ToastType` used in useToast hook, but the actual Toast component may not be rendered anywhere
11. **Accordion.tsx** - Not found in any imports (there's an Accordion in apps/start/src/components/ui/accordion.tsx which is the one being used)
12. **Badge.tsx** - Not found in any imports (there's a Badge in apps/start/src/components/ui/badge.tsx which is the one being used)

### ✅ **KEEP** (Actually Used):
- **Card.tsx** - Used by all Billing components (MonthlyBillCard, ForecastCard, etc.)

---

## 📊 **Summary**

### Components to Delete: **11 files**
- **High Priority (7)**: EnergyDashboard, EnergyDistributionToday, EnergyDistributionTodayNew, EnergyStatsTiles, BatterySOCChart, SolarSystemDiagramNew, BatteryDetailView
- **Medium Priority (2)**: StatusCard, SemiCircularGauge
- **Low Priority (2)**: Toast (component), Accordion, Badge

### Components to Keep: **~40+ files**
- All NewDashboard components
- All Billing components
- All wizard components
- Core routing/layout components
- Settings components

### Estimated Code Reduction: **~3000-5000 lines**

---

## ✅ **Completed Actions**

1. **Toast.tsx**: Moved `ToastType` to `useToast.ts` and deleted the unused Toast component (the app uses `apps/start/src/components/ui/toast.tsx` instead).

2. **Accordion, Badge**: These are duplicates of UI components in `apps/start/src/components/ui/`. The root components are not used.
3. **Card.tsx**: KEEP - This is used by Billing components and is different from the UI Card component.

3. **EnergyDashboard**: This component uses StatusCard and SemiCircularGauge, so deleting it will also make those components unused.

4. **BatteryDetailView**: This is different from BatteryDetailPage. BatteryDetailPage uses SOCRing, but BatteryDetailView appears to be unused.

---

## 🔍 **Verification Steps Before Deletion**

1. Search for any dynamic imports or string-based component references
2. Check if any components are used in test files
3. Verify that Accordion, Badge, Card are not used via path aliases
4. Confirm Toast component is not rendered via a toast library

