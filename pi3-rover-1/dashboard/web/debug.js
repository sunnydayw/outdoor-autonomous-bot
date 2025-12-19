let activeGamepad = null;

const statusEl        = document.getElementById("status");
const axesTableBody   = document.querySelector("#axes-table tbody");
const buttonsTableBody = document.querySelector("#buttons-table tbody");

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
  buildTables();
});

window.addEventListener("gamepaddisconnected", (e) => {
  if (activeGamepad && e.gamepad.index === activeGamepad.index) {
    activeGamepad = null;
    setStatus(
      "Gamepad disconnected. Plug it back in and move a stick or press a button.",
      "err"
    );
    clearTables();
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

function clearTables() {
  axesTableBody.innerHTML = "";
  buttonsTableBody.innerHTML = "";
}

function buildTables() {
  const gp = getGamepad();
  clearTables();
  if (!gp) return;

  gp.axes.forEach((_, idx) => {
    const tr = document.createElement("tr");
    const label = `CH${idx + 1}`;
    tr.innerHTML = `
      <td>${idx}</td>
      <td>${label}</td>
      <td class="mono" id="axis-val-${idx}">0.00</td>
    `;
    axesTableBody.appendChild(tr);
  });

  gp.buttons.forEach((_, idx) => {
    const tr = document.createElement("tr");
    const label = `SW${idx + 1}`;
    tr.innerHTML = `
      <td>${idx}</td>
      <td>${label}</td>
      <td class="mono" id="btn-pressed-${idx}">false</td>
      <td class="mono" id="btn-val-${idx}">0.00</td>
    `;
    buttonsTableBody.appendChild(tr);
  });
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

  if (axesTableBody.children.length === 0 && gp.axes.length > 0) {
    activeGamepad = gp;
    setStatus(
      `Gamepad connected: "${gp.id}" (index ${gp.index}).`,
      "ok"
    );
    buildTables();
  }

  gp.axes.forEach((val, idx) => {
    const cell = document.getElementById(`axis-val-${idx}`);
    if (cell) cell.textContent = val.toFixed(2);
  });

  gp.buttons.forEach((btn, idx) => {
    const pressedCell = document.getElementById(`btn-pressed-${idx}`);
    const valCell     = document.getElementById(`btn-val-${idx}`);
    if (pressedCell) pressedCell.textContent = btn.pressed ? "true" : "false";
    if (valCell)     valCell.textContent     = btn.value.toFixed(2);
  });

  requestAnimationFrame(update);
}

// Some browsers need user interaction before gamepad data flows
window.addEventListener("click", () => {
  const gp = getGamepad();
  if (gp) {
    activeGamepad = gp;
    setStatus(
      `Gamepad active: "${gp.id}" (index ${gp.index}).`,
      "ok"
    );
    buildTables();
  }
});

update();
