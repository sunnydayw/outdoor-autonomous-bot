// teleop.js

// === CONFIG SECTION ===
// Axes observed in debug.html
const FWD_AXIS_INDEX = 1; // stick up/down
const STR_AXIS_INDEX = 0; // stick left/right

// Max speeds and deadzone
const DEFAULT_LINEAR_MAX = 2.0;  // m/s (linear speed)
const DEFAULT_ANGULAR_MAX = 2.0; // rad/s (angular speed)
const DEADZONE = 0.05;  // used on STR, and as a tiny post-threshold cleanup on FWD

// Teleop send rate (browser -> backend)
const SEND_INTERVAL_MS = 50; // 20 Hz

// Telemetry display behavior
const TELEMETRY_STALE_MS = 1500;
const TELEMETRY_STATUS_INTERVAL_MS = 250;

// Battery percent mapping
const BATTERY_MIN_V = 9.0;
const BATTERY_MAX_V = 12.5;

// === RUNTIME STATE ===
let activeGamepad = null;
let lastSendTime = 0;
let lastTelemetryUpdateMs = null;
let telemetryHasData = false;
let telemetryWsConnected = false;
let vMax = DEFAULT_LINEAR_MAX;
let wMax = DEFAULT_ANGULAR_MAX;
let pendingCmd = null;
let sendInFlight = false;

// UI elements
const statusEl     = document.getElementById("status");
const rawFwdEl     = document.getElementById("raw-fwd");
const rawStrEl     = document.getElementById("raw-str");
const normFwdEl    = document.getElementById("norm-fwd");
const normStrEl    = document.getElementById("norm-str");
const vCmdEl       = document.getElementById("v-cmd");
const wCmdEl       = document.getElementById("w-cmd");
const vMaxSlider   = document.getElementById("v-max-slider");
const wMaxSlider   = document.getElementById("w-max-slider");
const vMaxValueEl  = document.getElementById("v-max-value");
const wMaxValueEl  = document.getElementById("w-max-value");

// Telemetry UI elements
const leftTargetRpmEl = document.getElementById("left-target-rpm");
const rightTargetRpmEl = document.getElementById("right-target-rpm");
const leftActualRpmEl = document.getElementById("left-actual-rpm");
const rightActualRpmEl = document.getElementById("right-actual-rpm");
const batteryVoltageEl = document.getElementById("battery-voltage");
const telemetryStatusEl = document.getElementById("telemetry-status");
const telemetryLastSeenEl = document.getElementById("telemetry-last-seen");
const batteryPercentEl = document.getElementById("battery-percent");
const batteryFillEl = document.getElementById("battery-fill");
const accelXEl = document.getElementById("accel-x");
const accelYEl = document.getElementById("accel-y");
const accelZEl = document.getElementById("accel-z");
const gyroXEl = document.getElementById("gyro-x");
const gyroYEl = document.getElementById("gyro-y");
const gyroZEl = document.getElementById("gyro-z");

function setLimitDefaults() {
  if (vMaxSlider) vMaxSlider.value = DEFAULT_LINEAR_MAX.toFixed(1);
  if (wMaxSlider) wMaxSlider.value = DEFAULT_ANGULAR_MAX.toFixed(1);
  vMax = DEFAULT_LINEAR_MAX;
  wMax = DEFAULT_ANGULAR_MAX;
  if (vMaxValueEl) vMaxValueEl.textContent = vMax.toFixed(1);
  if (wMaxValueEl) wMaxValueEl.textContent = wMax.toFixed(1);
}

function bindLimitSlider(sliderEl, valueEl, setter) {
  if (!sliderEl || !valueEl) return;
  sliderEl.addEventListener("input", () => {
    const value = parseFloat(sliderEl.value);
    if (!Number.isFinite(value)) return;
    setter(value);
    valueEl.textContent = value.toFixed(1);
  });
}

setLimitDefaults();
bindLimitSlider(vMaxSlider, vMaxValueEl, (value) => { vMax = value; });
bindLimitSlider(wMaxSlider, wMaxValueEl, (value) => { wMax = value; });

function setStatus(text, cls) {
  statusEl.textContent = text;
  statusEl.className = cls;
}

// === GAMEPAD HANDLING ===

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

// === MAPPING FUNCTIONS ===

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

// === BACKEND COMMUNICATION ===

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

  fetch("/cmd_vel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      v_cmd: payload.vCmd,
      w_cmd: payload.wCmd,
      timestamp_ms: payload.timestamp_ms,
      source: "web_teleop"
    })
  }).catch((err) => {
    // Network errors only – backend 4xx/5xx still resolve the fetch promise
    console.error("Failed to send /cmd_vel:", err);
  }).finally(() => {
    sendInFlight = false;
    if (pendingCmd) {
      flushTeleopCommand();
    }
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function formatAge(ms) {
  if (!Number.isFinite(ms) || ms < 0) return "–";
  const seconds = ms / 1000;
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remaining = Math.floor(seconds % 60);
  return `${minutes}m ${remaining}s`;
}

function setTelemetryStatus(state, label) {
  if (!telemetryStatusEl) return;
  telemetryStatusEl.textContent = label;
  telemetryStatusEl.dataset.state = state;
}

function updateBatteryUI(voltage) {
  if (!batteryPercentEl || !batteryFillEl) return;
  if (!Number.isFinite(voltage)) {
    batteryPercentEl.textContent = "–%";
    batteryFillEl.style.width = "0%";
    batteryFillEl.dataset.level = "mid";
    return;
  }

  const clamped = clamp(voltage, BATTERY_MIN_V, BATTERY_MAX_V);
  const percent = (clamped - BATTERY_MIN_V) / (BATTERY_MAX_V - BATTERY_MIN_V);
  const percentValue = Math.round(percent * 100);

  batteryPercentEl.textContent = `${percentValue}%`;
  batteryFillEl.style.width = `${percentValue}%`;

  if (percentValue <= 20) {
    batteryFillEl.dataset.level = "low";
  } else if (percentValue <= 50) {
    batteryFillEl.dataset.level = "mid";
  } else {
    batteryFillEl.dataset.level = "high";
  }
}

function updateTelemetryStatus() {
  if (!telemetryLastSeenEl || !telemetryStatusEl) return;
  if (!telemetryHasData || !lastTelemetryUpdateMs) {
    telemetryLastSeenEl.textContent = "–";
    if (telemetryWsConnected) {
      setTelemetryStatus("no-data", "No data");
    } else {
      setTelemetryStatus("disconnected", "Disconnected");
    }
    return;
  }

  const ageMs = Date.now() - lastTelemetryUpdateMs;
  telemetryLastSeenEl.textContent = `${formatAge(ageMs)} ago`;

  if (!telemetryWsConnected || ageMs > TELEMETRY_STALE_MS) {
    setTelemetryStatus("disconnected", "Disconnected");
  } else {
    setTelemetryStatus("connected", "Connected");
  }
}

// === WEBSOCKET FOR TELEMETRY ===

let telemetryWs = null;

function connectTelemetryWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/telemetry`;

  telemetryWs = new WebSocket(wsUrl);

  telemetryWs.onopen = () => {
    console.log("Telemetry WebSocket connected");
    telemetryWsConnected = true;
    updateTelemetryStatus();
  };

  telemetryWs.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateTelemetryUI(data);
    } catch (err) {
      console.error("Failed to parse telemetry:", err);
    }
  };

  telemetryWs.onclose = () => {
    console.log("Telemetry WebSocket disconnected");
    telemetryWsConnected = false;
    updateTelemetryStatus();
    // Reconnect after a delay
    setTimeout(connectTelemetryWebSocket, 1000);
  };

  telemetryWs.onerror = (err) => {
    console.error("Telemetry WebSocket error:", err);
  };
}

function updateTelemetryUI(data) {
  const isValid = Boolean(data.valid);
  telemetryHasData = isValid;

  if (isValid) {
    lastTelemetryUpdateMs = Date.now() - (data.age_s * 1000);
    leftTargetRpmEl.textContent = data.left_target_rpm.toFixed(1);
    rightTargetRpmEl.textContent = data.right_target_rpm.toFixed(1);
    leftActualRpmEl.textContent = data.left_actual_rpm.toFixed(1);
    rightActualRpmEl.textContent = data.right_actual_rpm.toFixed(1);
    batteryVoltageEl.textContent = data.battery_voltage.toFixed(2);
    accelXEl.textContent = data.accel_x.toFixed(2);
    accelYEl.textContent = data.accel_y.toFixed(2);
    accelZEl.textContent = data.accel_z.toFixed(2);
    gyroXEl.textContent = data.gyro_x.toFixed(2);
    gyroYEl.textContent = data.gyro_y.toFixed(2);
    gyroZEl.textContent = data.gyro_z.toFixed(2);
    updateBatteryUI(data.battery_voltage);
  } else {
    lastTelemetryUpdateMs = null;
    // Clear values if invalid
    leftTargetRpmEl.textContent = "–";
    rightTargetRpmEl.textContent = "–";
    leftActualRpmEl.textContent = "–";
    rightActualRpmEl.textContent = "–";
    batteryVoltageEl.textContent = "–";
    accelXEl.textContent = "–";
    accelYEl.textContent = "–";
    accelZEl.textContent = "–";
    gyroXEl.textContent = "–";
    gyroYEl.textContent = "–";
    gyroZEl.textContent = "–";
    updateBatteryUI(Number.NaN);
  }

  updateTelemetryStatus();
}

// === MAIN LOOP ===

function update() {
  const gp = getGamepad();

  if (!gp) {
    setStatus(
      "No gamepad detected. Plug in the FrSky XSR-SIM and move a stick or press a button.",
      "warn"
    );

    // Clear UI values
    rawFwdEl.textContent  = "0.00";
    rawStrEl.textContent  = "0.00";
    normFwdEl.textContent = "0.00";
    normStrEl.textContent = "0.00";
    vCmdEl.textContent    = "0.000";
    wCmdEl.textContent    = "0.000";

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

  const vCmd = normFwd * vMax;
  // Map stick left (negative STR axis) to positive ω (CCW).
  const wCmd = -normStr * wMax;

  // Update UI
  rawFwdEl.textContent  = rawFwdAxis.toFixed(2);
  rawStrEl.textContent  = rawStrAxis.toFixed(2);
  normFwdEl.textContent = normFwd.toFixed(2);
  normStrEl.textContent = normStr.toFixed(2);
  vCmdEl.textContent    = vCmd.toFixed(3);
  wCmdEl.textContent    = wCmd.toFixed(3);

  // Fixed-rate send to backend (20 Hz)
  const now = performance.now();
  if (now - lastSendTime >= SEND_INTERVAL_MS) {
    queueTeleopCommand(vCmd, wCmd);
    lastSendTime = now;
  }

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

// Kick off main loop
update();

// Connect to telemetry WebSocket
connectTelemetryWebSocket();

// Periodically refresh telemetry status display
setInterval(updateTelemetryStatus, TELEMETRY_STATUS_INTERVAL_MS);
