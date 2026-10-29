const loginScreen = document.getElementById("screen-login");
const consoleScreen = document.getElementById("screen-console");
const loginError = document.getElementById("login-error");
const banner = document.getElementById("banner");
const confirmBox = document.getElementById("confirm");

let stickyError = "";
let signedOn = false;

const PHASES = {
  idle: "Idle",
  ignitor: "Ignitor on",
  wait: "Waiting",
  valves: "Opening ox and fuel",
  complete: "Mains open",
  aborted: "Aborted",
};

function showLogin() {
  signedOn = false;
  loginScreen.hidden = false;
  consoleScreen.hidden = true;
}

function setBanner(text) {
  if (!text) {
    banner.hidden = true;
    banner.textContent = "";
    return;
  }
  banner.hidden = false;
  banner.textContent = text;
}

async function post(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await response.json();
  if (data.authenticated === false) {
    showLogin();
    return data;
  }
  if (Object.prototype.hasOwnProperty.call(data, "ok")) {
    stickyError = data.ok ? "" : (data.error || "Request failed");
  }
  if (data.valves) render(data);
  return data;
}

function render(state) {
  if (!state || state.authenticated === false) {
    showLogin();
    return;
  }
  signedOn = true;
  loginScreen.hidden = true;
  consoleScreen.hidden = false;

  markLink("link-arduino", "Arduino", state.links.arduino);
  markLink("link-esp32", "ESP32", state.links.esp32);

  const arm = document.getElementById("arm-state");
  arm.textContent = state.armed ? "Armed " + state.arm_remaining_s + "s" : "Safe";
  arm.className = state.armed ? "pill armed" : "pill";

  const ignitor = document.getElementById("ignitor-state");
  ignitor.textContent = state.relay ? "Ignitor hot" : "Ignitor off";
  ignitor.className = state.relay ? "pill hot" : "pill";

  document.getElementById("mock-note").hidden = !state.mock;
  document.querySelector(".top").classList.toggle("sequence-hot", ["ignitor", "wait", "valves"].includes(state.phase));

  ["fill", "purge", "ox", "fuel"].forEach(function (name) {
    const node = document.getElementById("valve-" + name);
    const open = state.valves[name] === "open";
    node.textContent = open ? "Open" : "Closed";
    node.className = open ? "position open" : "position closed";
  });

  const hot = ["ignitor", "wait", "valves"].includes(state.phase);
  const canMove = state.armed && !hot;
  document.querySelectorAll("[data-valve]").forEach(function (button) {
    const valve = button.dataset.valve;
    const linkUp = valve === "ox" || valve === "fuel" ? state.links.esp32 : state.links.arduino;
    button.disabled = !canMove || !linkUp;
  });
  const valvesShut = Object.keys(state.valves).every(function (name) {
    return state.valves[name] !== "open";
  });
  document.getElementById("btn-relay").disabled = !canMove || !state.links.arduino || !valvesShut || state.relay;

  const delay = Number(state.fire_delay_s);
  const delayText = Number.isInteger(delay) ? String(delay) : String(delay);
  document.getElementById("step-wait-label").textContent = "Wait " + delayText + " seconds";
  markSteps(state.phase);
  document.getElementById("phase-label").textContent = PHASES[state.phase] || state.phase;

  const ready = state.armed && state.links.arduino && state.links.esp32 && state.phase === "idle" && valvesShut && !state.relay;
  document.getElementById("btn-fire").disabled = !ready;

  const log = document.getElementById("event-log");
  log.replaceChildren();
  (state.events || []).forEach(function (text) {
    const item = document.createElement("li");
    item.textContent = text;
    log.appendChild(item);
  });

  setBanner(stickyError || state.message);
}

function markLink(id, name, up) {
  const node = document.getElementById(id);
  node.textContent = name + (up ? " up" : " down");
  node.className = up ? "pill up" : "pill";
}

function markSteps(phase) {
  const order = ["ignitor", "wait", "valves", "complete"];
  const at = order.indexOf(phase);
  ["ignitor", "wait", "valves"].forEach(function (name, index) {
    const node = document.getElementById("step-" + name);
    node.classList.toggle("active", index === at);
    node.classList.toggle("done", at > index);
  });
}

document.getElementById("login-form").addEventListener("submit", async function (event) {
  event.preventDefault();
  const data = await post("/api/login", {
    user: document.getElementById("login-user").value,
    password: document.getElementById("login-password").value,
  });
  document.getElementById("login-password").value = "";
  if (!data.ok) {
    loginError.hidden = false;
    loginError.textContent = data.error || "Sign on rejected";
    return;
  }
  loginError.hidden = true;
  stickyError = "";
  const state = await fetch("/api/state").then(function (response) { return response.json(); });
  render(state);
});

document.getElementById("arm-form").addEventListener("submit", async function (event) {
  event.preventDefault();
  const field = document.getElementById("arm-code");
  const code = field.value;
  field.value = "";
  await post("/api/arm", { code: code });
});

document.getElementById("btn-abort").addEventListener("click", function () {
  confirmBox.hidden = true;
  post("/api/abort");
});

document.getElementById("btn-logout").addEventListener("click", async function () {
  await post("/api/abort");
  await fetch("/api/logout", { method: "POST" });
  showLogin();
});

document.getElementById("tab-test").addEventListener("click", function () {
  document.getElementById("panel-test").hidden = false;
  document.getElementById("panel-fire").hidden = true;
  document.getElementById("tab-test").classList.add("active");
  document.getElementById("tab-fire").classList.remove("active");
});

document.getElementById("tab-fire").addEventListener("click", function () {
  document.getElementById("panel-test").hidden = true;
  document.getElementById("panel-fire").hidden = false;
  document.getElementById("tab-test").classList.remove("active");
  document.getElementById("tab-fire").classList.add("active");
});

document.querySelectorAll("[data-valve]").forEach(function (button) {
  button.addEventListener("click", function () {
    post("/api/valve", { valve: button.dataset.valve, position: button.dataset.position });
  });
});

document.getElementById("btn-relay").addEventListener("click", function () {
  post("/api/relay");
});

document.getElementById("btn-fire").addEventListener("click", function () {
  confirmBox.hidden = false;
});

document.getElementById("confirm-cancel").addEventListener("click", function () {
  confirmBox.hidden = true;
});

document.getElementById("confirm-start").addEventListener("click", function () {
  confirmBox.hidden = true;
  post("/api/fire");
});

document.getElementById("connect-arduino").addEventListener("click", function () {
  post("/api/connect", { target: "arduino", port: document.getElementById("arduino-port").value });
});

document.getElementById("connect-esp32").addEventListener("click", function () {
  post("/api/connect", {
    target: "esp32",
    mac: document.getElementById("esp32-mac").value,
    port: document.getElementById("esp32-port").value,
  });
});

setInterval(async function () {
  if (!signedOn) return;
  const state = await fetch("/api/state").then(function (response) { return response.json(); });
  render(state);
}, 250);

fetch("/api/state")
  .then(function (response) { return response.json(); })
  .then(render)
  .catch(function () { showLogin(); });
