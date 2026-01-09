# Teleop Command Lag Mitigation Implementation Plan

## Overview

Reduce occasional multi-second joystick-to-motor lag by aligning teleop command send cadence with backend expectations and preventing request backlogs in the browser.

## Current State Analysis

The browser teleop loop sends `/cmd_vel` at every animation frame because `SEND_INTERVAL_MS` is 5ms, even though the backend documents a ~20 Hz send rate. The backend UART loop runs at 50 Hz and the Pico control loop runs at ~20 Hz. If the browser sends faster than the backend can process (or requests queue due to latency), older commands can arrive later and get applied in order, causing delayed motion.

## Desired End State

Teleop commands are sent at a steady ~20 Hz and the browser never queues multiple outstanding `/cmd_vel` requests. Direction changes should translate to motor motion without multi-second lag, even during brief network stalls.

### Key Discoveries:
- Teleop send interval is currently set to 5ms, which causes a send every animation frame (`pi3-rover-1/dashboard/web/teleop.js:13-371`).
- The backend describes `/cmd_vel` as ~20 Hz and updates command state on every request (`pi3-rover-1/dashboard/backend/api.py:97-107`).
- Teleop inactivity times out after 0.5s (`pi3-rover-1/dashboard/backend/command_state.py:64-87`).
- The Pico drive control loop runs at ~20 Hz (`robot/Raspberry-Pi-Pico-2/main.py:28-196`).

## What We're NOT Doing

- No changes to UART framing, backend control loop cadence, or Pico motor control logic.
- No changes to gamepad mapping, deadzones, or velocity scaling.

## Implementation Approach

Throttle `/cmd_vel` sends to 20 Hz (50ms) and add a simple in-flight guard so the browser only has one active request at a time. If a new command arrives while a request is in-flight, store it and send the latest command immediately after the previous request completes.

## Phase 1: Teleop Command Throttling + Backlog Guard

### Overview

Update the browser teleop sender to match the intended 20 Hz cadence and avoid request queueing.

### Changes Required:

#### 1. Teleop Command Sender
**File**: `pi3-rover-1/dashboard/web/teleop.js`
**Changes**: Update `SEND_INTERVAL_MS` to 50ms, add in-flight state/pending command handling, and reuse the stored command after each request completes.

```javascript
const SEND_INTERVAL_MS = 50; // 20 Hz

let pendingCmd = null;
let sendInFlight = false;

function queueTeleopCommand(vCmd, wCmd) {
  pendingCmd = { vCmd, wCmd, timestamp_ms: Date.now() };
  if (sendInFlight) return;
  flushTeleopCommand();
}

function flushTeleopCommand() {
  if (!pendingCmd || sendInFlight) return;
  const payload = pendingCmd;
  pendingCmd = null;
  sendInFlight = true;
  fetch("/cmd_vel", { ...payload... }).finally(() => {
    sendInFlight = false;
    flushTeleopCommand();
  });
}
```

### Success Criteria:

#### Automated Verification:
- [x] `pi3-rover-1/dashboard/web/teleop.js` reflects a 50ms send interval and guarded send logic.
- [ ] No linting or syntax errors introduced in `pi3-rover-1/dashboard/web/teleop.js`.

#### Manual Verification:
- [ ] Open `http://<pi-ip>:8000/static/teleop.html` and confirm command output updates smoothly while moving the sticks.
- [ ] Perform rapid direction changes and verify the motors respond without multi-second delayed motion.
- [ ] In browser devtools, verify `/cmd_vel` requests fire at ~20 Hz and do not stack in the network queue.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- Not applicable (frontend-only change, no existing unit tests for teleop.js).

### Integration Tests:
- N/A (manual teleop verification).

### Manual Testing Steps:
1. Load the teleop UI and connect the gamepad.
2. Sweep the stick forward/left/right and confirm the on-screen `v_cmd`/`w_cmd` updates in real time.
3. Execute rapid direction changes and confirm the motors react promptly without delayed action.
4. Inspect the Network tab to ensure `/cmd_vel` posts at ~20 Hz and no request backlog accumulates.

## Performance Considerations

Reducing send frequency and avoiding concurrent requests lowers HTTP overhead and prevents command backlog during transient network or CPU stalls.

## Migration Notes

None.

## References

- Original ticket: `.ai/thoughts/tickets/eng-00005.md`
- Teleop command sender: `pi3-rover-1/dashboard/web/teleop.js:13`
- Teleop endpoint expectation: `pi3-rover-1/dashboard/backend/api.py:97`
- Command timeout behavior: `pi3-rover-1/dashboard/backend/command_state.py:64`
- Pico control loop cadence: `robot/Raspberry-Pi-Pico-2/main.py:28`
