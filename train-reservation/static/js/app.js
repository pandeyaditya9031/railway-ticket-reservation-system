/* app.js
   Drives the Railway Ticket Reservation single-page app:
   menu navigation, live clock, and calls to the Flask JSON API
   for each of the five menu options carried over from the
   original console program. */

const API = {
  classes: () => fetch("/api/classes").then(handle),
  trains: () => fetch("/api/trains").then(handle),
  train: (no) => fetch(`/api/trains/${no}`).then(handle),
  addTrain: (body) => fetch("/api/trains", postOpts(body)).then(handle),
  reserve: (body) => fetch("/api/reserve", postOpts(body)).then(handle),
  cancel: (body) => fetch("/api/cancel", postOpts(body)).then(handle),
  ticket: (resno) => fetch(`/api/ticket/${resno}`).then(handle),
};

function postOpts(body) {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

async function handle(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = data.error || "Something went wrong. Please try again.";
    throw new Error(message);
  }
  return data;
}

function alertBox(message, kind = "error") {
  const box = document.createElement("div");
  box.className = `alert alert--${kind}`;
  box.textContent = message;
  return box;
}

/* -------------------------------------------------------------------------
   Navigation between the five panels
   ------------------------------------------------------------------------- */
const tiles = document.querySelectorAll(".menu__tile");
const panels = document.querySelectorAll(".panel");

function showSection(name) {
  panels.forEach((p) => (p.hidden = p.id !== `panel-${name}`));
  tiles.forEach((t) => t.classList.toggle("is-active", t.dataset.section === name));
  window.scrollTo({ top: document.querySelector(".menu").offsetTop - 12, behavior: "smooth" });

  if (name === "trains") loadTrains();
}

tiles.forEach((tile) => {
  tile.addEventListener("click", () => showSection(tile.dataset.section));
});

/* -------------------------------------------------------------------------
   Live clock in the header, station-board style
   ------------------------------------------------------------------------- */
function tickClock() {
  const el = document.getElementById("liveClock");
  const now = new Date();
  el.textContent = now.toLocaleTimeString("en-GB", { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

/* -------------------------------------------------------------------------
   01. Train details
   ------------------------------------------------------------------------- */
async function loadTrains() {
  const list = document.getElementById("trainsList");
  list.innerHTML = "<p class='empty-note'>Loading trains&hellip;</p>";
  try {
    const trains = await API.trains();
    if (trains.length === 0) {
      list.innerHTML = "<p class='empty-note'>No trains in the system yet. Add one under \u201cUpdate Train Details\u201d.</p>";
      return;
    }
    const classes = await API.classes();
    list.innerHTML = "";
    for (const t of trains) {
      const full = await API.train(t.trainno);
      list.appendChild(renderTrainCard(full, classes));
    }
  } catch (err) {
    list.innerHTML = "";
    list.appendChild(alertBox(err.message));
  }
}

function renderTrainCard(train, classes) {
  const card = document.createElement("article");
  card.className = "train-card";

  const seatRows = Object.entries(classes).map(([code, label]) => {
    const a = train.availability[code];
    const cls = a.available === 0 ? "low" : "ok";
    return `<span>${label}</span><span class="seat-avail ${cls}">${a.available}/${a.total} free</span>`;
  }).join("");

  card.innerHTML = `
    <div class="train-card__no">TRAIN NO. ${train.trainno}</div>
    <div class="train-card__name">${escapeHtml(train.trainname)}</div>
    <div class="train-card__route">${escapeHtml(train.startingpoint)} &rarr; ${escapeHtml(train.destination)}</div>
    <div class="train-card__seats">${seatRows}</div>
  `;
  return card;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

/* -------------------------------------------------------------------------
   02. Update train details
   ------------------------------------------------------------------------- */
document.getElementById("updateForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const resultSlot = document.getElementById("updateResult");
  resultSlot.innerHTML = "";

  const body = Object.fromEntries(new FormData(form).entries());

  try {
    const data = await API.addTrain(body);
    resultSlot.appendChild(alertBox(`Saved. Train ${data.train.trainno} \u2014 ${data.train.trainname}.`, "success"));
    form.reset();
  } catch (err) {
    resultSlot.appendChild(alertBox(err.message));
  }
});

/* -------------------------------------------------------------------------
   03. Reserve a ticket
   ------------------------------------------------------------------------- */
async function populateClassSelect() {
  const select = document.getElementById("classSelect");
  try {
    const classes = await API.classes();
    for (const [code, label] of Object.entries(classes)) {
      const opt = document.createElement("option");
      opt.value = code;
      opt.textContent = label;
      select.appendChild(opt);
    }
  } catch (err) {
    /* select just stays with its placeholder if this fails */
  }
}
populateClassSelect();

document.getElementById("reserveForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const resultSlot = document.getElementById("reserveResult");
  resultSlot.innerHTML = "";

  const body = Object.fromEntries(new FormData(form).entries());

  try {
    const ticket = await API.reserve(body);
    resultSlot.appendChild(buildTicketStub(ticket));
    form.reset();
  } catch (err) {
    resultSlot.appendChild(alertBox(err.message));
  }
});

function buildTicketStub(ticket) {
  const tpl = document.getElementById("ticketStubTemplate");
  const node = tpl.content.cloneNode(true);

  node.querySelector(".ticket-name").textContent = ticket.name;
  node.querySelector(".ticket-age").textContent = ticket.age;
  node.querySelector(".ticket-train").textContent =
    ticket.trainname ? `${ticket.trainname} (#${ticket.trainno})` : `#${ticket.trainno}`;
  node.querySelector(".ticket-class").textContent = ticket.class_name;
  node.querySelector(".ticket-stub__resno").textContent = `#${ticket.resno}`;

  const statusEl = node.querySelector(".ticket-stub__status");
  statusEl.textContent = ticket.status;
  statusEl.classList.add(ticket.status);

  return node;
}

/* -------------------------------------------------------------------------
   04. Cancel a ticket
   ------------------------------------------------------------------------- */
document.getElementById("cancelForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const resultSlot = document.getElementById("cancelResult");
  resultSlot.innerHTML = "";

  const body = Object.fromEntries(new FormData(form).entries());

  try {
    const data = await API.cancel(body);
    resultSlot.appendChild(alertBox(data.message, "success"));
    form.reset();
  } catch (err) {
    resultSlot.appendChild(alertBox(err.message));
  }
});

/* -------------------------------------------------------------------------
   05. Check ticket status
   ------------------------------------------------------------------------- */
document.getElementById("statusForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const resultSlot = document.getElementById("statusResult");
  resultSlot.innerHTML = "";

  const resno = new FormData(form).get("resno");

  try {
    const ticket = await API.ticket(resno);
    resultSlot.appendChild(buildTicketStub(ticket));
  } catch (err) {
    resultSlot.appendChild(alertBox(err.message));
  }
});

/* -------------------------------------------------------------------------
   Initial state: show the train details panel first
   ------------------------------------------------------------------------- */
showSection("trains");
