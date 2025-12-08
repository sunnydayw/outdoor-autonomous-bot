// teleop.js
// === CONFIG SECTION ===
// Set these to the axes you observed in debug.html.
// Example: axis 1 = FWD (stick up/down), axis 0 = STR (stick left/right).
const FWD_AXIS_INDEX = 1;
const STR_AXIS_INDEX = 0;

// Max speeds and deadzone
const V_MAX    = 0.30;  // m/s (linear speed)
const W_MAX    = 1.50;  // rad/s (angular speed)
const DEADZONE = 0.05;  // used on STR, and as a tiny post-threshold cleanup on FWD

// === RUNTIME STATE ===
let activeGamepad = null;

const statusEl     = document.getElementById("status");
const cfgFwdAxisEl = document.getElementById("cfg-fwd-axis");
const cfgStrAxisEl = document.getElementById("cfg-str-axis");
const rawFwdEl     = document.getElementById("raw-fwd");
const rawStrEl     = document.getElementById("raw-str");
const normFwdEl    = document.getElementById("norm-fwd");
const normStrEl    = document.getElementById("norm-str");
const vCmdEl       = document.getElementById("v-cmd");
const wCmdEl       = document.getElementById("w-cmd");

cfgFwdAxisEl.textContent = FWD_AXIS_INDEX;
cfgStrAxisEl.textContent = STR_AXIS_INDEX;

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = cls;
}

window.addEventListener("gamepadconnected", (e) => {
  activeGamepad = e.gamepad;
  setStatus(
    `Gamepad connected: "${activeGamepad.id}" (index ${activeGamepad.index}). Move sticks to see values.`,
    "ok"
  );
});

window.addEventListener("gamepaddisconnected", (e) => {
  if (activeGamepad && e.gamepad.index === activeGamepad.index) {
    activeGamepad = null;
    setStatus(
      "Gamepad disconnected. Plug it back in and move a stick or press a button.",
      "err"
    );
  }
});

function getGamepad() {
  if (activeGamepad) {
    const gps = navigator.getGamepads ? navigator.getGamepads() : [];
    const gp = gps[activeGamepad.index];
    if (gp) return gp;
  }
  const gps = navigator.getGamepads ? navigator.getGamepads() : [];
  for (const gp of gps) {
    if (gp) return gp;
  }
  return null;
}

// Deadzone for symmetric axes (STR)
function applyDeadzone(x) {
  const ax = Math.abs(x);
  if (ax < DEADZONE) return 0.0;
  const scale = (ax - DEADZONE) / (1.0 - DEADZONE);
  return Math.sign(x) * Math.min(scale, 1.0);
}

// FWD mapping:
//   raw in [-1, 1]
//   - For raw <= 0: no motion → normFwd = 0
//   - For raw > 0: map [0 .. 1] → [0 .. 1] (with small deadzone on norm)
function mapFwd(raw) {
  if (raw <= 0) {
    return 0.0;
  }
  // Clamp to [0, 1]
  const clamped = Math.min(raw, 1.0);
  let norm = clamped;  // since we treat 0 as "start" of travel

  // Small deadzone near 0 on the normalized value to avoid jitter
  if (norm < DEADZONE) {
    norm = 0.0;
  }
  return Math.min(Math.max(norm, 0.0), 1.0);
}

function update() {
  const gp = getGamepad();
  if (!gp) {
    setStatus(
      "No gamepad detected. Plug in the FrSky XSR-SIM and move a stick or press a button.",
      "warn"
    );
    requestAnimationFrame(update);
    return;
  }

  // Read raw axes
  let rawFwdAxis = 0.0;
  let rawStrAxis = 0.0;

  if (FWD_AXIS_INDEX < gp.axes.length) {
    rawFwdAxis = gp.axes[FWD_AXIS_INDEX];
  }
  if (STR_AXIS_INDEX < gp.axes.length) {
    rawStrAxis = gp.axes[STR_AXIS_INDEX];
  }

  // FWD: start at raw=-1, ramp up, but we only care about raw > 0
  const normFwd = mapFwd(rawFwdAxis);

  // STR: symmetric left/right, deadzone around 0
  const normStr = applyDeadzone(rawStrAxis);

  const vCmd = normFwd * V_MAX;
  const wCmd = normStr * W_MAX;

  // Update UI
  rawFwdEl.textContent  = rawFwdAxis.toFixed(2);
  rawStrEl.textContent  = rawStrAxis.toFixed(2);
  normFwdEl.textContent = normFwd.toFixed(2);
  normStrEl.textContent = normStr.toFixed(2);
  vCmdEl.textContent    = vCmd.toFixed(3);
  wCmdEl.textContent    = wCmd.toFixed(3);

  requestAnimationFrame(update);
}

// Some browsers need a user interaction before gamepad data flows smoothly
window.addEventListener("click", () => {
  const gp = getGamepad();
  if (gp) {
    activeGamepad = gp;
    setStatus(
      `Gamepad active: "${gp.id}" (index ${gp.index}).`,
      "ok"
    );
  }
});

update();
