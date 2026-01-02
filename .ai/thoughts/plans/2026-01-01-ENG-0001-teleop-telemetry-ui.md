# Teleop Telemetry UI Improvements Implementation Plan

## Overview

Redesign the teleop telemetry section for clarity during robot operation, add a dedicated battery section with percentage mapping, and update telemetry status logic to immediately reflect Pico disconnects with a last-seen time.

## Current State Analysis

Telemetry UI is a single table inside the Telemetry from Pico card, with status displayed as a table cell and no distinct grouping for IMU, RPM, or battery (`pi3-rover-1/dashboard/web/teleop.html:115`). The telemetry WebSocket only updates the UI when a message arrives, so status stays "Valid (0.1s ago)" when telemetry stops until the page is refreshed (`pi3-rover-1/dashboard/web/teleop.js:171`). The backend WebSocket only pushes telemetry when it changes, not on a fixed cadence (`pi3-rover-1/dashboard/backend/api.py:176`).

## Desired End State

The teleop telemetry UI is visually grouped into separate sections (status, RPM, IMU, battery), with clearer hierarchy and readability while operating. The telemetry status updates to "Disconnected" within a short timeout after no updates, and shows a "last update" time when stale. The battery panel displays voltage and a percentage derived from 9.0V–12.5V (0%–100%), clamped to that range.

### Key Discoveries:
- Telemetry data already includes `valid` and `age_s` values used on the frontend (`pi3-rover-1/dashboard/web/teleop.js:171`).
- Telemetry snapshots already contain `age_s` and `last_update_ts` from the backend (`pi3-rover-1/dashboard/backend/command_state.py:178`).
- The existing telemetry UI uses a single table layout that mixes status, battery, RPM, and IMU (`pi3-rover-1/dashboard/web/teleop.html:115`).

## What We're NOT Doing

- No changes to the Pico telemetry protocol or UART bridge.
- No backend changes to telemetry cadence or websocket frequency.
- No changes to teleop command mapping or gamepad logic.

## Implementation Approach

Update the HTML/CSS to create a more legible, grouped telemetry layout using a bold, high-contrast visual style that prioritizes quick scanning. Update the frontend JavaScript to track last telemetry update timestamps, compute stale/disconnected states locally, and compute battery percentage from the voltage range provided. Keep backend unchanged and rely on the existing telemetry payload fields.

## Phase 1: Telemetry UI Restructure & Styling

### Overview
Restructure the telemetry section into distinct grouped panels (Status, RPM, IMU, Battery) with clearer typography and visual hierarchy.

### Changes Required:

#### 1. Telemetry Layout & Styles
**File**: `pi3-rover-1/dashboard/web/teleop.html`
**Changes**: Replace the telemetry table with grouped layout blocks (Status, RPM, IMU, Battery). Add placeholders for battery percentage, last-seen time, and a dedicated status badge. Introduce a more intentional design using CSS variables, stronger type hierarchy, and a distinct background treatment per section.

```html
<!-- Example structure -->
<div class="telemetry-grid">
  <section class="telemetry-card status-card">
    <div class="status-badge" id="telemetry-status">Disconnected</div>
    <div class="last-seen" id="telemetry-last-seen">Last update: –</div>
  </section>
  <section class="telemetry-card rpm-card">
    <!-- left/right target + actual rpm -->
  </section>
  <section class="telemetry-card imu-card">
    <!-- accel + gyro -->
  </section>
  <section class="telemetry-card battery-card">
    <div class="battery-voltage" id="battery-voltage">–</div>
    <div class="battery-percent" id="battery-percent">–%</div>
  </section>
</div>
```

### Success Criteria:

#### Automated Verification:
- [x] `pi3-rover-1/dashboard/web/teleop.html` includes distinct telemetry sections and new DOM IDs for status, last-seen, and battery percent.

#### Manual Verification:
- [ ] Telemetry section is visually grouped and easy to scan at a glance.
- [ ] RPM, IMU, and Battery data appear in separate, labeled sections.
- [ ] Status is prominent and readable while operating.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Telemetry Status & Battery Logic

### Overview
Update telemetry UI logic to detect stale telemetry, show last update time, and compute battery percentage from the configured voltage range.

### Changes Required:

#### 1. Telemetry Status Timer & Battery Mapping
**File**: `pi3-rover-1/dashboard/web/teleop.js`
**Changes**: Track a `lastTelemetryUpdateMs` value on each telemetry update. Add a periodic timer (e.g., `setInterval`) to update the status badge and last-seen text based on elapsed time. Compute battery percentage using `(voltage - 9.0) / (12.5 - 9.0)` clamped to [0, 1], then format as 0–100%.

```js
// Example logic outline
const BATTERY_MIN_V = 9.0;
const BATTERY_MAX_V = 12.5;
let lastTelemetryUpdateMs = null;

function updateTelemetryUI(data) {
  lastTelemetryUpdateMs = Date.now();
  // Update values + battery percent
}

function updateTelemetryStatus() {
  if (!lastTelemetryUpdateMs) { /* show no data */ }
  const ageMs = Date.now() - lastTelemetryUpdateMs;
  if (ageMs > STALE_THRESHOLD_MS) { /* show disconnected */ }
  else { /* show connected/valid */ }
  // update last seen string
}
```

### Success Criteria:

#### Automated Verification:
- [x] `pi3-rover-1/dashboard/web/teleop.js` computes battery percent based on 9.0V–12.5V and updates the DOM.
- [x] Telemetry status updates on a timer without requiring a WebSocket message.

#### Manual Verification:
- [ ] When Pico telemetry stops, the status changes to Disconnected within the stale timeout.
- [ ] The UI shows a "last update" time and continues updating it while disconnected.
- [ ] Battery voltage displays with a percentage in the Battery section.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- Not required for this UI-only update (no existing frontend test harness found).

### Integration Tests:
- Optional: `python -m pytest pi3-rover-1/dashboard/test` if the environment is configured.

### Manual Testing Steps:
1. Open `http://<pi-ip>:8000/static/teleop.html` and verify the telemetry layout.
2. Confirm telemetry values update when Pico is sending data.
3. Stop Pico telemetry and verify status flips to Disconnected within the timeout and shows last update time.
4. Verify battery percentage matches the voltage range (9.0V → 0%, 12.5V → 100%).

## Performance Considerations

- Status timer should run at a modest cadence (e.g., 200–500 ms) to avoid unnecessary UI churn.

## Migration Notes

- No data migrations or backend changes required.

## References

- Original ticket: `.ai/thoughts/tickets/eng-0001.md`
- Telemetry UI: `pi3-rover-1/dashboard/web/teleop.html:115`
- Telemetry UI logic: `pi3-rover-1/dashboard/web/teleop.js:171`
- Telemetry backend snapshot: `pi3-rover-1/dashboard/backend/command_state.py:178`
- Telemetry websocket: `pi3-rover-1/dashboard/backend/api.py:176`
