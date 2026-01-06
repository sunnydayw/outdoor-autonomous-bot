# ENG-0004 Command Mapping Layout + Limit Sliders Implementation Plan

## Overview

Update the teleop Command Mapping card to remove axis index display, combine raw and normalized stick data into a FWD/STR side-by-side layout, and add adjustable linear/angular limit sliders that reset to defaults on reload.

## Current State Analysis

- The Command Mapping card renders four panels (Axes, Raw Input, Normalized, Command Output) in `pi3-rover-1/dashboard/web/teleop.html:420`.
- Axis indices are displayed via `cfg-fwd-axis` and `cfg-str-axis` which are populated in `pi3-rover-1/dashboard/web/teleop.js:31-60`.
- Linear and angular maximums are hardcoded as `V_MAX` and `W_MAX` in `pi3-rover-1/dashboard/web/teleop.js:8-10`.

## Desired End State

- The Axes panel is removed and axis index display is gone.
- Raw + Normalized values are combined into a single “Stick Input” panel with side-by-side FWD and STR subcards.
- A “Limits” panel lets operators adjust linear and angular max values via sliders (default 2.0, max 10.0, step 0.5), with live value readouts.
- Limits reset to defaults on every page load (no persistence).

### Key Discoveries
- Command Mapping DOM IDs used by JS are `raw-fwd`, `raw-str`, `norm-fwd`, `norm-str`, `v-cmd`, `w-cmd` (`pi3-rover-1/dashboard/web/teleop.html:433`).
- The mapping logic consumes `V_MAX` and `W_MAX` constants for `v_cmd` and `w_cmd` (`pi3-rover-1/dashboard/web/teleop.js:331-333`).

## What We're NOT Doing

- No changes to telemetry UI, backend APIs, or Pico firmware.
- No persistence of limits across reloads.
- No changes to the mapping logic beyond using slider-driven max values.

## Implementation Approach

Redesign the Command Mapping card using the existing dark neon visual language, add a new “Stick Input” grid to combine raw/normalized values, and introduce a “Limits” panel with sliders. Update `teleop.js` to remove axis index references and replace hardcoded `V_MAX`/`W_MAX` with live slider values.

## Phase 1: Command Mapping UI Restructure

### Overview
Restructure the Command Mapping HTML/CSS to remove the Axes panel, combine raw/normalized values into FWD/STR cards, and add a limits panel with sliders and value readouts.

### Changes Required:

#### 1. Command Mapping layout and styles
**File**: `pi3-rover-1/dashboard/web/teleop.html`
**Changes**: Replace the Axes/Raw/Normalized panels with a “Stick Input” section containing FWD/STR subcards. Add a “Limits” panel with range inputs and value readouts for linear and angular maximums. Keep existing IDs for `raw-fwd`, `raw-str`, `norm-fwd`, `norm-str`, `v-cmd`, `w-cmd`.

```html
<section class="mapping-panel input">
  <div class="panel-title">Stick Input</div>
  <div class="input-grid">
    <div class="input-card">
      <div class="input-title">FWD</div>
      <div class="mapping-row">
        <span class="mapping-label">Raw</span>
        <span class="mapping-value mono" id="raw-fwd">0.00</span>
      </div>
      <div class="mapping-row">
        <span class="mapping-label">Norm</span>
        <span class="mapping-value mono" id="norm-fwd">0.00</span>
      </div>
    </div>
    <div class="input-card">
      <div class="input-title">STR</div>
      <div class="mapping-row">
        <span class="mapping-label">Raw</span>
        <span class="mapping-value mono" id="raw-str">0.00</span>
      </div>
      <div class="mapping-row">
        <span class="mapping-label">Norm</span>
        <span class="mapping-value mono" id="norm-str">0.00</span>
      </div>
    </div>
  </div>
</section>

<section class="mapping-panel limits">
  <div class="panel-title">Limits</div>
  <div class="limit-row">
    <div class="limit-label">Linear max</div>
    <input id="v-max-slider" type="range" min="0" max="10" step="0.5" value="2.0" />
    <div class="limit-value"><span class="mono" id="v-max-value">2.0</span> m/s</div>
  </div>
  <div class="limit-row">
    <div class="limit-label">Angular max</div>
    <input id="w-max-slider" type="range" min="0" max="10" step="0.5" value="2.0" />
    <div class="limit-value"><span class="mono" id="w-max-value">2.0</span> rad/s</div>
  </div>
  <div class="mapping-foot small">Limits reset on reload.</div>
</section>
```

### Success Criteria:

#### Automated Verification:
- [x] `pi3-rover-1/dashboard/web/teleop.html` removes axis index display and introduces new slider UI while preserving existing mapping value IDs.

#### Manual Verification:
- [ ] The Command Mapping card reads cleanly at a glance with FWD/STR inputs side by side.
- [ ] Limits panel is clear and aligned with the existing dark neon theme.
- [ ] Layout remains usable on narrow/mobile widths.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Phase 2: Slider-Driven Limits in JS

### Overview
Replace hardcoded max speed constants with slider-driven values that default to 2.0 and update live as the sliders move.

### Changes Required:

#### 1. Limit slider wiring
**File**: `pi3-rover-1/dashboard/web/teleop.js`
**Changes**: Remove axis index DOM usage and replace `V_MAX`/`W_MAX` with runtime values sourced from sliders. Update UI readouts on input events.

```js
const DEFAULT_LINEAR_MAX = 2.0;
const DEFAULT_ANGULAR_MAX = 2.0;

const vMaxSlider = document.getElementById("v-max-slider");
const wMaxSlider = document.getElementById("w-max-slider");
const vMaxValueEl = document.getElementById("v-max-value");
const wMaxValueEl = document.getElementById("w-max-value");

let vMax = DEFAULT_LINEAR_MAX;
let wMax = DEFAULT_ANGULAR_MAX;

function syncLimit(sliderEl, valueEl, setter) {
  if (!sliderEl || !valueEl) return;
  const value = parseFloat(sliderEl.value);
  setter(value);
  valueEl.textContent = value.toFixed(1);
}

vMaxSlider?.addEventListener("input", () => {
  syncLimit(vMaxSlider, vMaxValueEl, (value) => { vMax = value; });
});

wMaxSlider?.addEventListener("input", () => {
  syncLimit(wMaxSlider, wMaxValueEl, (value) => { wMax = value; });
});
```

### Success Criteria:

#### Automated Verification:
- [x] `pi3-rover-1/dashboard/web/teleop.js` computes `v_cmd` and `w_cmd` using slider-driven limits instead of hardcoded constants.
- [x] Axis index DOM references are removed from the JS.

#### Manual Verification:
- [ ] Moving the sliders updates the limit readouts and affects `v_cmd` / `w_cmd` scaling.
- [ ] Reloading the page resets limits to 2.0.

**Implementation Note**: After completing this phase and all automated verification passes, pause here for manual confirmation from the human that the manual testing was successful before proceeding to the next phase.

---

## Testing Strategy

### Unit Tests:
- None present for this UI.

### Integration Tests:
- None present.

### Manual Testing Steps:
1. Open `http://<pi-ip>:8000/static/teleop.html` and confirm the Command Mapping card layout.
2. Move the controller sticks and verify raw/normalized values update in the FWD/STR cards.
3. Move the linear and angular sliders and confirm `v_cmd` / `w_cmd` scale changes.
4. Reload the page and confirm both sliders return to 2.0.

## Performance Considerations

- Slider handling is event-driven and should not impact the animation loop.

## Migration Notes

- None.

## References

- Original ticket: `.ai/thoughts/tickets/eng-0004.md`
- Command Mapping UI: `pi3-rover-1/dashboard/web/teleop.html:420`
- Teleop mapping logic: `pi3-rover-1/dashboard/web/teleop.js:331`
