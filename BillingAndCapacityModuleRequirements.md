### Billing & Capacity Analysis Module – Requirements Document

> Scope: Requirements only – no implementation or code.

---

## 1. Overview

### 1.1 Purpose

Design a **separate backend module** responsible for:

- **Bill generation**  
  Simulate monthly and annual electricity bills using:
  - Historical load, solar generation, grid import/export
  - Time‑of‑use tariffs
  - Net‑metering rules (with 3‑month cycles)
  - Fixed charges

- **Capacity & forecasting analysis**  
  Analyze whether the system is **under‑capacity or over‑capacity** and by how much, and identify:
  - In which months the customer will have a positive bill
  - How system sizing (kW of PV) affects bills

### 1.2 Out of Scope

- No battery behaviour:
  - Ignore battery SOC, charge/discharge energy, and battery sizing.
- No UI implementation:
  - This module exposes data via functions / APIs only.
- No code in this document:
  - This is a **requirements specification only**.

---

## 2. Data Inputs

### 2.1 PV Capacity Configuration

- Source: configuration (`config.yaml` and/or configuration table via `/api/config`).
- Schema (from `config.yaml`):

```yaml
inverters:
  - id: senergy1
    solar:
      - pv_dc_kw: 4
        ...
  - id: powdrive1
    solar:
      - pv_dc_kw: 4
        ...
```

- For each inverter:
  - One or more `solar` entries, each with `pv_dc_kw` (kW).
- **Total installed PV capacity**:
  - \( C_\text{pv} = \sum_{\text{inverters}} \sum_{\text{solar arrays}} pv\_dc\_kw \)
  - Units: kW
- The module must:
  - Fetch config via `/api/config`.
  - Sum `pv_dc_kw` for all inverters and their solar arrays.
  - Treat this sum as the **site‑wide installed PV capacity**.

### 2.2 Historical Energy Data

- Source:
  - `hourly_energy` table; accessed via:
    - `/api/energy/hourly` (hourly aggregation)
    - `/api/energy/daily` (daily aggregation)
- Required energy fields:
  - `solar_energy_kwh` (or `total_solar_kwh`)
  - `load_energy_kwh` (or `total_load_kwh`)
  - `grid_import_energy_kwh` (or `total_grid_import_kwh`)
  - `grid_export_energy_kwh` (or `total_grid_export_kwh`)
- Requirements:
  - Support aggregation across **all inverters** (`inverter_id=all`).
  - Support aggregation over arbitrary time ranges (based on billing periods defined below).

### 2.3 Tariff & Billing Parameters

All tariff parameters must be **configurable**, ideally via config DB and exposed via `/api/config` or a dedicated billing config.

#### 2.3.1 Time‑of‑Use (TOU) Windows

- **Peak hours**:
  - One or more daily time windows (e.g. 17:00–22:00).
- **Off‑peak hours**:
  - All hours not in peak windows.
- Module must determine for each hour whether it is **peak** or **off‑peak**.

#### 2.3.2 Energy Prices

- `price_offpeak_import` – price per kWh of **net off‑peak import**.
- `price_peak_import` – price per kWh of **net peak import**.

- Settlement prices for expired credits:
  - `price_offpeak_settlement` – price per kWh when **off‑peak export credits** are settled to cash after a 3‑month netting cycle.
  - `price_peak_settlement` – price per kWh when **peak export credits** are settled to cash after a 3‑month netting cycle.
    - May initially equal `price_offpeak_settlement`, but must be configurable separately.

#### 2.3.3 Fixed Charges

- `fixed_charge_per_billing_month` – a fixed amount added to every billing month, representing:
  - Meter rent
  - Service charges
  - Other non‑energy costs

Module must allow this to be configured and included in the bill.

---

## 3. Billing Calendar & Netting Cycles

### 3.1 Billing Month Definition (Anchor Date)

- **Billing months do not align with calendar months.**
- A **billing month** is defined as the period between two occurrences of a configurable **anchor date** (day of month).
  - Default anchor: **15th**.
- Example (anchor = 15, year 2025):
  - Month 1: Jan 15 – Feb 14
  - Month 2: Feb 15 – Mar 14
  - Month 3: Mar 15 – Apr 14
  - …
- Requirements:
  - Anchor **day of month** must be configurable.
  - Time zone must be respected (using configured system timezone).

### 3.2 Three‑Month Netting Cycles (Both Peak and Off‑peak)

- Both **off‑peak** and **peak** imports/exports use a **3‑billing‑month netting cycle**.
- For example (anchor = 15):

| Cycle | Start       | End        | Billing Months |
|-------|------------|------------|----------------|
| 1     | Jan 15     | Apr 14     | 1–3            |
| 2     | Apr 15     | Jul 14     | 4–6            |
| 3     | Jul 15     | Oct 14     | 7–9            |
| 4     | Oct 15     | next Jan 14| 10–12          |

- At the **end of each cycle**:
  - Remaining **energy credits (kWh)** for off‑peak and peak are **settled to cash credit** using their respective settlement prices.
  - The kWh credit balances for that cycle are reset to zero.
  - Cash credits appear as **negative billing amounts** and are carried forward (see §6.1).

---

## 4. Hourly → Billing Month Aggregation

For each hour \( h \) in the historical data:

- Known:
  - `load_kwh(h)`
  - `solar_kwh(h)`
  - `grid_import_kwh(h)`
  - `grid_export_kwh(h)`
  - `is_peak(h)` – derived from time‑of‑day and TOU configuration.

For each billing month \( m \):

### 4.1 Off‑peak Aggregation

- Off‑peak import:
  - \( Import_\text{off}(m) = \sum_{h \in m,\ is\_peak(h)=false} grid\_import\_kwh(h) \)
- Off‑peak export:
  - \( Export_\text{off}(m) = \sum_{h \in m,\ is\_peak(h)=false} grid\_export\_kwh(h) \)

### 4.2 Peak Aggregation

- Peak import:
  - \( Import_\text{peak}(m) = \sum_{h \in m,\ is\_peak(h)=true} grid\_import\_kwh(h) \)
- Peak export:
  - \( Export_\text{peak}(m) = \sum_{h \in m,\ is\_peak(h)=true} grid\_export\_kwh(h) \)

### 4.3 Totals for Capacity Analysis (Informational)

- Total solar generation in month:
  - \( G_\text{solar}(m) = \sum_{h \in m} solar\_kwh(h) \)
- Total load in month:
  - \( L(m) = \sum_{h \in m} load\_kwh(h) \)

These totals are for capacity analysis and reporting, not for billing logic directly.

---

## 5. Net Metering Rules

> **Important**: **Battery is ignored**. All logic is based on netting grid imports/exports only.

We maintain **separate kWh credit pools** for **off‑peak** and **peak** within each 3‑month cycle:

- `Credits_off_cycle` – off‑peak kWh credits
- `Credits_peak_cycle` – peak kWh credits

These credits are used to reduce future imports within the same cycle.

### 5.1 Off‑Peak Net Metering (3‑Month Cycle)

Within a given cycle:

1. For each billing month \( m \) in the cycle, compute raw off‑peak net import:

   \[
   raw\_net\_off(m) = Import_\text{off}(m) - Export_\text{off}(m)
   \]

2. Apply cycle‑credits:

   - If `raw_net_off(m) > 0` (import > export):

     - Use `Credits_off_cycle` to offset imports:

       \[
       net\_import\_off(m) = \max(0, raw\_net\_off(m) - Credits\_off\_cycle)
       \]
       \[
       Credits\_off\_cycle \leftarrow \max(0, Credits\_off\_cycle - raw\_net\_off(m))
       \]

     - `net_import_off(m)` is the billable off‑peak import in kWh for month `m`.

   - If `raw_net_off(m) \le 0` (export ≥ import):

     - No off‑peak import billed:

       \[
       net\_import\_off(m) = 0
       \]

     - Additional export becomes new credits:

       \[
       Credits\_off\_cycle \leftarrow Credits\_off\_cycle + (-raw\_net\_off(m))
       \]

3. At cycle end:

   - Remaining off‑peak credits are settled to cash:

     \[
     Cash\_credit\_off\_cycle = Credits\_off\_cycle \times price\_offpeak\_settlement
     \]

   - This appears as a **negative amount** on the bill.
   - Reset `Credits_off_cycle = 0` for the next cycle.

### 5.2 Peak Net Metering (3‑Month Cycle)

Peak exports are netted **only against peak imports** using the same 3‑month concept.

1. For each billing month \( m \):

   \[
   raw\_net\_peak(m) = Import_\text{peak}(m) - Export_\text{peak}(m)
   \]

2. Apply peak credits:

   - If `raw_net_peak(m) > 0`:

     \[
     net\_import\_peak(m) = \max(0, raw\_net\_peak(m) - Credits\_peak\_cycle)
     \]
     \[
     Credits\_peak\_cycle \leftarrow \max(0, Credits\_peak\_cycle - raw\_net\_peak(m))
     \]

   - If `raw_net_peak(m) \le 0`:

     \[
     net\_import\_peak(m) = 0
     \]
     \[
     Credits\_peak\_cycle \leftarrow Credits\_peak\_cycle + (-raw\_net\_peak(m))
     \]

3. At cycle end:

   - Remaining `Credits_peak_cycle` are settled:

     \[
     Cash\_credit\_peak\_cycle = Credits\_peak\_cycle \times price\_peak\_settlement
     \]

   - Appears as a **negative bill item**.
   - Reset `Credits_peak_cycle = 0` for next cycle.

---

## 6. Monthly Bill Computation

### 6.1 Energy Charges

For each billing month \( m \):

- **Off‑peak energy charge**:

  \[
  B_\text{off\_energy}(m) = net\_import\_off(m) \times price\_offpeak\_import
  \]

- **Peak energy charge**:

  \[
  B_\text{peak\_energy}(m) = net\_import\_peak(m) \times price\_peak\_import
  \]

### 6.2 Fixed Charges

- **Fixed monthly charge**:

  \[
  B_\text{fixed}(m) = fixed\_charge\_per\_billing\_month
  \]

### 6.3 Cycle Settlement Credits

- In the **final month of each 3‑month cycle**, include:

  - Off‑peak settlement:

    \[
    B_\text{cycle\_credit\_off}(m) = -Cash\_credit\_off\_cycle
    \]

  - Peak settlement:

    \[
    B_\text{cycle\_credit\_peak}(m) = -Cash\_credit\_peak\_cycle
    \]

  (For non‑cycle‑end months, these terms are zero.)

### 6.4 Raw Monthly Bill

- Before monetary carry‑forward:

  \[
  B_\text{raw}(m) = B_\text{off\_energy}(m) + B_\text{peak\_energy}(m) + B_\text{fixed}(m) + B_\text{cycle\_credit\_off}(m) + B_\text{cycle\_credit\_peak}(m)
  \]

### 6.5 Monetary Carry‑Forward

- Maintain a **monetary credit balance**:

  - `Bill_credit_balance` (currency), initial value 0.

- For each billing month:

  1. If `B_raw(m) > 0` and `Bill_credit_balance < 0`:
     - Offset the bill with existing credit:

       \[
       B_\text{final}(m) = \max(0, B_\text{raw}(m) + Bill\_credit\_balance)
       \]
       \[
       Bill\_credit\_balance \leftarrow \min(0, Bill\_credit\_balance + B_\text{raw}(m))
       \]

  2. If `B_raw(m) ≤ 0`:
     - No payment this month; add to credit:

       \[
       B_\text{final}(m) = 0
       \]
       \[
       Bill\_credit\_balance \leftarrow Bill\_credit\_balance + B_\text{raw}(m)
       \]

- Edge case (explicitly required):  
  - Months can have **negative raw bill** (e.g. large settlement credits). These negative amounts **carry forward** until they are completely used to offset future positive bills.

---

## 7. Capacity & “No Bill” Analysis (Battery Ignored)

### 7.1 Annual Simulation with Current Capacity

Given:

- Installed capacity \( C_\text{pv} \) (from config)
- Hourly/daily energy history for a full year
- Tariffs and netting rules as above

The module must:

1. Partition the year into billing months (anchor date).
2. Split energy into **peak/off‑peak imports and exports**.
3. Run the **3‑month netting cycles** (peak + off‑peak) with settlement at cycle end.
4. Include **fixed monthly charges** and **monetary carry‑forward**.
5. Produce, for each billing month:
   - Energy summary: `Import_off`, `Export_off`, `Import_peak`, `Export_peak`, `G_solar`, `L`.
   - Billing summary: `B_off_energy`, `B_peak_energy`, `B_fixed`, settlements, `B_raw`, `B_final`.
6. Produce annual summary:
   - Sum of `B_final(m)` and final `Bill_credit_balance`.
   - If the **final annual net bill > 0** ⇒ system is **under‑capacity** from a “no bill” perspective.
   - Identify which months have `B_final(m) > 0` (customer pays).

### 7.2 Per‑kW Production Metrics

For each billing month \( m \):

- Compute **production per kW** using current capacity:

  \[
  P_\text{per\_kW}(m) = 
  \begin{cases}
  \dfrac{G_\text{solar}(m)}{C_\text{pv}} & \text{if } C_\text{pv} > 0 \\
  0 & \text{otherwise}
  \end{cases}
  \]

Units: kWh per kW over that billing month.

These metrics are used later for capacity sizing and forecasting (not implemented now).

### 7.3 Future: Capacity Scenarios (for later implementation)

> Not to implement now, but the module should be designed to support it.

- Given a hypothetical capacity \( C'_\text{pv} \):
  - Scale solar generation accordingly (approximate linear scaling).
  - Re‑run billing simulation for the year with all the same rules.
  - Determine:
    - Whether annual **net bill becomes ≤ 0**.
    - How many months still show positive monthly bills.
- Use this to estimate:
  - How many **extra kW of PV** are needed to:
    - Eliminate the annual bill.
    - Or ensure no positive monthly bills at all.

---

## 8. Module Responsibilities & Interfaces

### 8.1 Bill Generation Submodule

**Responsibilities:**

- Fetch or receive:
  - Energy time series (hourly/daily).
  - Installed PV capacity.
  - Tariff and billing configuration (TOU windows, prices, fixed charges).
- Implement:
  - Mapping timestamps → billing months (anchor date, timezone aware).
  - Aggregation into `Import_off`, `Export_off`, `Import_peak`, `Export_peak`.
  - 3‑month netting cycles for peak and off‑peak.
  - Cycle settlement and kWh → monetary credit.
  - Fixed monthly charges.
  - Monetary carry‑forward across months.
- Outputs:
  - Detailed per‑month bill breakdown.
  - Annual summary and final credit balance.

### 8.2 Forecast & Capacity Analysis Submodule

**Responsibilities:**

- Use bill generation output plus:
  - Installed PV capacity.
  - Historical production per kW (per month or period).
- Provide:
  - Per‑month production per kW.
  - Identification of billing months where a positive bill persists.
  - (Later) Simulation of capacity changes and their impact on bills.

### 8.3 Interfaces (Conceptual)

Example APIs / functions (names indicative only):

- `simulateBilling({ year, capacityKw, tariffs, anchorDay }) -> BillingResult`
- `getBillingSummary({ year }) -> AnnualSummary`
- `computePerKwProduction({ year }) -> PerMonthProductionMetrics`
- `simulateCapacityScenario({ year, capacityKwScenario }) -> ScenarioResult`

---

## 9. Forecasting & Reporting Extensions

> This section defines additional (future) capabilities. They should be designed into the module, but do not need to be fully implemented in the first version.

### 9.1 Bill Forecasting

**Goal**: Estimate the **next billing month** (or configurable horizon) bill based on historical data and simple statistical methods.

- **Scope**:
  - Forecasted values are informational; they do not affect actual billing logic or credits.

- **Methods (configurable)**:
  - **Trend‑based**:
    - Use the last 12 billing months of `import_off`, `import_peak`, `export_off`, `export_peak`, and resulting bill amounts.
    - Compute an **exponential moving average (EMA)** or similar smoothing to project:
      - `predicted_import_kwh`
      - `predicted_export_kwh`
      - `predicted_bill_amount`
  - **Seasonal pattern**:
    - For a given upcoming month, look at the **same month in previous years** (or same season) and adjust using recent trend.
  - **Scenario input**:
    - Accept a request structure like:
      - `{ monthsAhead: number, method: "trend" | "seasonal" }`
    - Defaults:
      - `monthsAhead = 1`
      - `method = "trend"`

- **Forecast output (per request)**:
  - `predicted_import_kwh`
  - `predicted_export_kwh`
  - `predicted_bill_amount`
  - Optional:
    - `predicted_import_peak_kwh`
    - `predicted_import_off_kwh`
  - `confidence` – numeric (0–1) confidence indicator derived from variance of historical residuals.

### 9.2 Capacity Forecasting

**Goal**: Use historical solar and load data to estimate whether current PV capacity is sufficient to achieve a **zero‑bill scenario**, and by how much the system is over/under‑sized.

- **Inputs**:
  - Historical per‑month:
    - `G_solar(m)`, `L(m)`, `Import_off(m)`, `Import_peak(m)`, `Export_off(m)`, `Export_peak(m)`
  - Installed capacity \( C_\text{pv} \).
  - Optional: forecast results from §9.1.

- **Outputs**:
  - `installed_kw` – current installed capacity.
  - `required_kw_for_zero_bill` – estimated capacity such that annual net bill ≤ 0 under historical patterns.
  - `deficit_kw = required_kw_for_zero_bill - installed_kw` (can be negative, meaning over‑capacity).
  - `status`:
    - `"under-capacity"` if `deficit_kw > threshold_kw` (e.g. > 0.25 kW).
    - `"over-capacity"` if `deficit_kw < -threshold_kw`.
    - `"balanced"` otherwise.

- **Future enhancement**:
  - Run **scenario simulations**:
    - Try `installed_kw + Δ` for Δ in `{+0.5, +1, +2, ...}` and recompute annual bill.
    - Return a curve: `capacity_kw` vs `annual_bill`.

### 9.3 Reporting & Visualization APIs

The module should expose REST‑style endpoints (or equivalent service functions) to support frontend dashboards:

- **Billing summary**:
  - Endpoint: `/api/billing/summary`
  - Returns:
    - Current billing month’s:
      - `billingMonth`
      - `import_off_kwh`, `import_peak_kwh`
      - `export_off_kwh`, `export_peak_kwh`
      - `fixed_charge`
      - `bill_amount` (B_final for that month)
      - `credit_balance` (monetary carry‑forward)

- **Billing trend**:
  - Endpoint: `/api/billing/trend`
  - Returns:
    - Last N billing months (e.g. 12):
      - Per‑month energy/bill breakdown for charting.

- **Next bill forecast**:
  - Endpoint: `/api/forecast/next`
  - Query/body:
    - Optional `{ monthsAhead, method }` as in §9.1.
  - Returns:
    - Forecast metrics noted above (`predicted_import_kwh`, etc.).

- **Capacity status**:
  - Endpoint: `/api/capacity/status`
  - Returns:
    - Fields from §9.2:
      - `installed_kw`, `required_kw_for_zero_bill`, `deficit_kw`, `status`.

### 9.4 Frontend Dashboard Outputs (Informational Requirements)

These are **UI expectations** that the backend must support via data, but the actual rendering is done in the frontend.

- **Monthly Bill Card**:
  - Shows billing period, energy charges (peak/off‑peak), fixed charges, credits, and final payable amount.

- **Import vs Export Chart**:
  - Stacked bar per billing month:
    - `import_peak`, `import_off`, `export_off`, `export_peak`.

- **3‑Month Netting Cycle Chart**:
  - Shows for each cycle:
    - Imports, exports, credits used, and settled cash amounts.

- **Bill Amount Trend Chart**:
  - Monthly `B_final(m)` with optional forecast overlay from §9.1.

- **Solar vs Load Comparison**:
  - Dual‑axis line chart:
    - Monthly solar generation vs load.

- **Capacity Meter**:
  - Gauge showing:
    - Current `installed_kw`.
    - `required_kw_for_zero_bill`.
    - Status (under/over/balanced).

- **Next‑Month Forecast Card**:
  - Quick view of:
    - Predicted off‑peak and peak import/export.
    - Predicted bill in currency.

- **Seasonal Pattern Chart**:
  - Highlights per‑month net export/deficit to see seasonal under/over‑capacity.

- **Credit Ledger Table**:
  - Shows:
    - Cycle‑level credit generation.
    - Credits applied.
    - Credits settled in cash.
    - Running monetary credit balance.

### 9.5 API Output Example

An example JSON response for a combined billing + forecast + capacity endpoint (illustrative only):

```json
{
  "billingMonth": "2025-09",
  "import_off_kwh": 1016,
  "import_peak_kwh": 290,
  "export_off_kwh": 699,
  "export_peak_kwh": 0,
  "fixed_charge": 2800,
  "bill_amount": 36314.87,
  "credit_balance": -1238.88,
  "forecast_next_month": {
    "predicted_import_kwh": 500,
    "predicted_export_kwh": 200,
    "predicted_bill": 24000,
    "confidence": 0.85
  },
  "capacity": {
    "installed_kw": 13.5,
    "required_kw_for_zero_bill": 14.0,
    "status": "under-capacity",
    "deficit_kw": 0.5
  }
}
```

---

This file is the **requirements specification** for the **Bill Generation and Forecasting Module**. It includes:

- Separate 3‑month netting cycles for **peak and off‑peak imports/exports**.
- **Fixed charges**.
- **Configurable billing anchor date** (e.g. Jan 15).
- **KWh credit netting** with cycle settlement to **cash credit**.
- **Monetary carry‑forward** for negative bill amounts.
- Clear separation between **billing logic** and **capacity/forecast analysis**, while explicitly **ignoring battery behaviour**.
- Extensible **forecasting and reporting layer** with well‑defined APIs and data structures to support dashboards and planning tools.

---

## 10. Scheduler, Daily Accruals & End‑of‑Cycle Archival

### 10.1 Objectives

- Provide a **daily running view** of the current billing month showing whether the site is in **surplus (net export)** or **deficit (net import)** since the anchor date.
- **Persist daily snapshots** for reporting, anomaly detection, and forecast tuning.
- At the **end of each billing month** and **end of each 3‑month cycle**, finalize computations, settle credits, and **archive a normalized record** to the DB.

### 10.2 Scheduler

A system scheduler shall run **daily at 00:30 local time** (configurable) to:

1. Determine the current billing month window using the anchor day & timezone.
2. Aggregate hourly → daily imports/exports split by TOU (peak/off‑peak).
3. Update cycle credit balances (off‑peak & peak) using the partial month to‑date values.
4. Compute a **provisional running bill to date**.
5. Write a **daily snapshot row** (idempotent for the day).
6. The scheduler shall automatically detect cycle boundaries to execute settlement logic (see §10.5).

### 10.3 Running Bill (To‑Date) Computation

Use the same formulas as §§4–6 with the following clarifications for **partial months**:

- **Energy charges to‑date** are computed from cumulative `net_import_off(m, toDate)` and `net_import_peak(m, toDate)` after applying available cycle credits so far.
- **Fixed charge proration** is configurable:
  - `fixed_proration: none | linear_by_day` (default: `none`).
  - If `linear_by_day`, apply `fixed_charge_per_billing_month × (elapsed_days / total_days_in_billing_month)`.
- **Cycle settlements** are not applied until the actual cycle end; however, the system shall compute an **expected settlement preview field** for UI (`expected_cycle_credit_rs`).

### 10.4 Data Model (Minimum Schema)

#### `billing_daily` — one row per site per date (composite key: `site_id`, `date`).

- `date`
- `billing_month_id` (FK)
- `import_off_kwh`, `export_off_kwh`, `import_peak_kwh`, `export_peak_kwh`
- `net_import_off_kwh`, `net_import_peak_kwh`
- `credits_off_cycle_kwh_balance`, `credits_peak_cycle_kwh_balance`
- `bill_off_energy_rs`, `bill_peak_energy_rs`
- `fixed_prorated_rs`
- `expected_cycle_credit_rs`
- `bill_raw_rs_to_date`, `bill_credit_balance_rs_to_date`, `bill_final_rs_to_date`
- `surplus_deficit_flag` (enum: `SURPLUS`, `DEFICIT`, `NEUTRAL`)
- `generated_at_ts`

#### `billing_months` — finalized monthly records.

- Anchor dates, peak/off‑peak imports/exports, settlements, fixed charge, `B_raw`, `B_final`, closing `bill_credit_balance`.

#### `billing_cycles` — finalized 3‑month cycle summaries.

- Start/end dates, cycle kWh credits consumed/created, settlement Rs, reset markers.

### 10.5 End‑of‑Month & End‑of‑Cycle Finalization

#### End of billing month:

1. Freeze month aggregates; compute `B_raw(m)` and apply monetary carry‑forward to produce `B_final(m)`.
2. Upsert `billing_months` with immutable results and a **hash of the input parameters** (tariffs, TOU windows, capacity) for auditability.

#### End of 3‑month cycle:

1. Convert remaining `Credits_off_cycle` & `Credits_peak_cycle` to cash (`price_*_settlement`) and record as settlement Rs.
2. Reset kWh cycle credits to zero; insert a `billing_cycles` record.

### 10.6 APIs for Daily View & Archival

- **`GET /api/billing/running?date=YYYY-MM-DD`** → current‑month to‑date status and provisional bill.
- **`GET /api/billing/daily?from=YYYY-MM-DD&to=YYYY-MM-DD`** → time‑series for sparklines.
- **`POST /api/billing/cycle/close`** → admin endpoint to force close a cycle (with safety checks).
- **`GET /api/billing/month/{id}`** → finalized monthly record.

### 10.7 Frontend Widgets (Daily Focus)

- **Daily Surplus/Deficit Chip**: `SURPLUS +23 kWh since 15th` or `DEFICIT −145 kWh`.
- **Cumulative kWh Sparkline (to‑date)**: two lines — cumulative import vs cumulative export; shaded region indicates net position.
- **Running Bill Progress**: bar showing `bill_final_rs_to_date` vs. last 3‑month average, with a marker at expected settlement.
- **Month Elapsed Progress**: progress bar (`elapsed_days / total_days_in_billing_month`) with tooltip showing days remaining until anchor.
- **Cycle Countdown**: chip `Cycle 2/4 · 11 days to settlement`.
- **Anomaly Banner (optional)**: if day‑over‑day delta deviates > N σ from 30‑day mean.

### 10.8 Operational Requirements

- **Idempotent daily job** (re‑runs for the same day must produce identical totals).
- **Backfill mode** to recompute a date range when tariffs or TOU windows change.
- All time handling shall be **timezone aware** and anchored to the configured site timezone.
- **Observability**: emit metrics for scheduler latency, rows written, and cycle closures.

---

## 11. Settings & Setup Wizard Requirements (Frontend + Backend Support)

> This section defines the configuration UX and corresponding backend requirements needed to support the billing and capacity module. It is still requirements‑only (no implementation).

### 11.1 Configuration Domains

The system must provide a structured way (UI + APIs) to view and edit at least the following configuration groups:

1. **Global billing settings**
   - Currency (e.g. PKR).
   - Billing anchor date (day‑of‑month, default 15).
   - Timezone (must stay consistent with backend).

2. **Tariff & TOU settings**
   - Off‑peak unit price (`price_offpeak_import`).
   - Peak unit price (`price_peak_import`).
   - Off‑peak settlement price (`price_offpeak_settlement`).
   - Peak settlement price (`price_peak_settlement`).
   - Peak time windows (one or more time ranges per day).

3. **Fixed & miscellaneous charges**
   - Fixed charge per billing month (`fixed_charge_per_billing_month`).
   - Optional additional fixed items (e.g. meter rent, service fee) that can be added later without changing the core billing logic.

4. **PV capacity & system metadata**
   - Display read‑only `pv_dc_kw` per inverter (from config).
   - Display computed total installed capacity `C_pv`.
   - Allow marking inverters as “included in billing simulation” or “ignored” (for future multi‑array support).

5. **Forecasting parameters**
   - Default forecasting method: `"trend"` or `"seasonal"`.
   - Number of months to look back for trend (e.g. 6, 12, 24).
   - Number of months ahead for default forecast (e.g. 1).
   - Confidence threshold for warnings (e.g. flag low‑confidence forecasts).

### 11.2 Setup Wizard (First‑Time & Reconfiguration)

The frontend should offer a **wizard‑style setup flow** for billing/capacity configuration. The backend must expose APIs to read/write config atomically to support this.

**Wizard steps (suggested):**

1. **Account & basic info**
   - Show instructions to copy key values from the utility bill (e.g. customer ID, tariff type, currency).
   - Let user select or confirm:
     - Currency
     - Timezone
     - Billing anchor date (e.g. “My bill cycle starts around 15th of the month”).

2. **PV system overview**
   - Read config via `/api/config`.
   - Display list of inverters with:
     - `id`, `name`, `pv_dc_kw` per solar array.
   - Show computed total `C_pv`.
   - Allow user to:
     - Confirm these values.
     - Optionally exclude certain inverters from billing simulation.

3. **Tariff definition**
   - Wizard screen to:
     - Enter off‑peak and peak unit prices (use examples from a real bill).
     - Define/to edit peak time windows via a simple UI (time pickers).
   - Validation:
     - Peak windows must not overlap.
     - Peak + off‑peak must cover 24 hours.

4. **Net‑metering & settlement**
   - Explain 3‑month cycle in UI (with simple diagram).
   - Fields:
     - Off‑peak settlement price (per kWh).
     - Peak settlement price (per kWh).
   - Option to run a quick “dry‑run” using past data:
     - Call billing simulation with new settings and show how many months would have a bill or credit.

5. **Fixed charges**
   - Enter fixed monthly charge amount.
   - Optionally add labeled fixed components (e.g. “Meter rent”, “Service fee”), combined into `fixed_charge_per_billing_month` for backend.

6. **Forecast tuning (optional)**
   - Choose default forecast method (trend vs seasonal).
   - Choose look‑back window (e.g. last 12 months).
   - Specify default monthsAhead for `/api/forecast/next`.

7. **Review & confirm**
   - Summary page:
     - Show all entered settings.
     - Show preview: last 3 months’ computed bills under these settings vs the ones on actual utility bills (where available).
   - On confirmation:
     - Backend API is called to save all changes in a single update (e.g. `POST /api/config` or dedicated billing config endpoint).

### 11.3 Backend Requirements for Settings

To support the wizard and settings UI, the backend must:

- Provide **read API**:
  - `GET /api/config` already exists; it should include or be extended to include:
    - Tariff settings (prices, TOU windows).
    - Billing anchor day.
    - Fixed charges.
    - Forecasting defaults.

- Provide **update API**:
  - Either reuse `POST /api/config` or add a dedicated endpoint (e.g. `POST /api/billing-config`) that accepts:
    - The complete billing/tariff configuration object.
  - Updates should be **atomic**:
    - Either all billing config fields are saved or none are, to avoid partial updates.

- Validation & error reporting:
  - Reject invalid configs, e.g.:
    - Negative prices or charges.
    - Peak windows that overlap or are out of range.
  - Return clear error messages that the wizard can display.

### 11.4 Non‑Functional Requirements for Settings

- **Security & access control**:
  - Only authorized roles (e.g. admin/installer) can modify billing and tariff settings.
  - Read‑only access can be available to standard users.

- **Auditability**:
  - The system should log configuration changes (timestamp, user, old vs new values) for tariff‑related settings.

- **Idempotency**:
  - Re‑running the wizard with the same values should not cause duplicate or inconsistent state.

- **Preview without committing**:
  - The wizard should be able to call a “simulate with unsaved settings” endpoint or pass overrides to `simulateBilling` without persisting them, allowing the user to see the impact before saving.



