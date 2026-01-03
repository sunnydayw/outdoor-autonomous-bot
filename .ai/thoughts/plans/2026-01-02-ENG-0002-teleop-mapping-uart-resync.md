# ENG-0002 Teleop Mapping + UART Resync Implementation Plan

## Overview

Redesign the teleop Command Mapping (v, ω) UI while keeping the dashboard visual language consistent, and update the Pi-side UART telemetry parser to resync quietly on reconnect without warning spam. Battery behavior remains unchanged (drops to 0% when telemetry is invalid).

## Current State Analysis

- The teleop mapping UI is a simple table with minimal structure in `pi3-rover-1/dashboard/web/teleop.html:313`.
- Telemetry UI updates battery percentage directly from `battery_voltage`, clearing values when telemetry is invalid (`pi3-rover-1/dashboard/web/teleop.js:168`, `pi3-rover-1/dashboard/web/teleop.js:253`).
- The UART telemetry parser warns on any payload length mismatch before checking message ID, which surfaces warnings when reconnect noise or non-telemetry bytes appear (`pi3-rover-1/dashboard/backend/uart_bridge.py:169`).
- The current Pi <-> Pico spec and code define telemetry as 11 floats (length 44) and velocity as 2 floats (length 8) (`robot/Raspberry-Pi-Pico-2/communication_spec.md:15`).

## Desired End State

- The Command Mapping (v, ω) section is redesigned with clearer hierarchy and a more intentional layout, preserving existing DOM IDs so `teleop.js` remains compatible.
- UART telemetry parsing silently resyncs on reconnect without emitting repeated "Unexpected telemetry payload length" warnings, while still accepting valid telemetry frames.
- Battery display behavior remains unchanged (drops to 0% when telemetry is invalid).

### Key Discoveries
- Telemetry length mismatch warnings occur before msg_id filtering (`pi3-rover-1/dashboard/backend/uart_bridge.py:169`).
- Teleop mapping content is confined to a single card in `pi3-rover-1/dashboard/web/teleop.html:313`.
- Battery percentage mapping is already implemented and should not be altered (`pi3-rover-1/dashboard/web/teleop.js:168`).

## What We're NOT Doing

- No changes to battery handling or telemetry retention logic.
- No changes to telemetry cadence, WebSocket behavior, or backend APIs.
- No changes to Pico firmware or the UART framing spec.

## Implementation Approach

Update the UART telemetry parser to treat unexpected payload lengths as resync signals without warning logs. Then redesign the Command Mapping card using the frontend-design skill, keeping the existing CSS variables, dark theme, and DOM IDs to avoid JS changes.

## Phase 1: UART Telemetry Resync Without Warnings

### Overview
Quietly resync the RX buffer on reconnect noise without logging warnings for non-telemetry lengths.

### Changes Required

#### 1. UART RX parsing behavior
**File**: `pi3-rover-1/dashboard/backend/uart_bridge.py`
**Changes**: When the payload length does not match `TELEMETRY_LEN`, drop bytes to resync without warning. Optionally gate warnings behind debug, but default behavior should be silent.

### Success Criteria

#### Automated Verification
- [ ] No lints or formatting errors introduced in `pi3-rover-1/dashboard/backend/uart_bridge.py`.

#### Manual Verification
- [ ] On Pico reconnect, the dashboard backend no longer logs repeated "Unexpected telemetry payload length" warnings.
- [ ] Telemetry still updates when valid frames arrive.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Command Mapping (v, ω) UI Redesign

### Overview
Redesign the mapping card to improve readability and visual hierarchy while keeping the dashboard look consistent.

### Changes Required

#### 1. Command Mapping layout and styling
**File**: `pi3-rover-1/dashboard/web/teleop.html`
**Changes**: Rebuild the Command Mapping card into a clearer layout with sections (axes configuration, raw vs normalized, computed outputs). Preserve existing DOM IDs (`cfg-fwd-axis`, `cfg-str-axis`, `raw-fwd`, `raw-str`, `norm-fwd`, `norm-str`, `v-cmd`, `w-cmd`).

### Success Criteria

#### Automated Verification
- [x] `pi3-rover-1/dashboard/web/teleop.html` retains all required DOM IDs used by `teleop.js`.

#### Manual Verification
- [ ] The Command Mapping card is visually consistent with the existing dashboard theme.
- [ ] Raw, normalized, and output values remain visible and easy to scan.
- [ ] Layout is responsive on mobile widths.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests
- None present for this UI or UART module.

### Integration Tests
- None present.

### Manual Testing Steps
1. Open `http://<pi-ip>:8000/static/teleop.html` and verify the Command Mapping layout and values update while moving the controller.
2. Reconnect the Pico and confirm the backend no longer logs payload length warnings.
3. Verify battery display still drops to 0% when telemetry is invalid (disconnect Pico).

## Performance Considerations

- UART parsing remains O(n) on buffer length; only logging behavior changes.
- UI changes are static HTML/CSS; no runtime performance impact expected.

## Migration Notes

- None.

## References

- Original ticket: `.ai/thoughts/tickets/eng-0002.md`
- UART parser: `pi3-rover-1/dashboard/backend/uart_bridge.py:158`
- Teleop UI: `pi3-rover-1/dashboard/web/teleop.html:313`
- Telemetry battery mapping: `pi3-rover-1/dashboard/web/teleop.js:168`
- Communication spec: `robot/Raspberry-Pi-Pico-2/communication_spec.md:15`
