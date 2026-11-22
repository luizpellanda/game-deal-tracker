// Landing page. It only talks to our own API (api.py):
//   GET /games, GET /games/{id}/history, POST /auth/login (recruiter button)
// URLs are relative, so the page also works when served under a path like /deals/.

// Store names for the ids CheapShark uses (from its /stores endpoint).
const STORE_NAMES = {
  1: "Steam",
  2: "GamersGate",
  3: "GreenManGaming",
  7: "GOG",
  11: "Humble Store",
  13: "Uplay",
  15: "Fanatical",
  21: "WinGameStore",
  23: "GameBillet",
  25: "Epic Games Store",
  27: "Gamesplanet",
  30: "IndieGala",
  35: "DreamGame",
};

const TOP_COUNT = 10;

const $ = (id) => document.getElementById(id);
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

const state = {
  games: [],
  selectedId: null,
  history: null,
  chart: null,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function storeName(storeId) {
  return STORE_NAMES[storeId] || `Store ${storeId}`;
}

// "2026-11-15" -> "Nov 15, 2026", read as UTC so the day never shifts.
function formatDate(isoDate, withYear = true) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  const options = { month: "short", day: "numeric", timeZone: "UTC" };
  if (withYear) {
    options.year = "numeric";
  }
  return date.toLocaleDateString("en-US", options);
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
}

// CheapShark gives small Steam capsules (231 x 87). For Steam games, ask Steam
// for the 460 px header image instead, so the big card cover stays sharp.
function coverUrl(thumbUrl) {
  if (!thumbUrl) {
    return "";
  }
  return thumbUrl.replace(/capsule_(sm_120|231x87)\.jpg/, "header.jpg");
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// ---------------------------------------------------------------------------
// Deal cards
// ---------------------------------------------------------------------------

function byDiscountThenTitle(a, b) {
  const da = a.discount_percent ?? -1;
  const db = b.discount_percent ?? -1;
  return db - da || a.title.localeCompare(b.title);
}

function dealCard(game) {
  const card = el("button", "deal-card");
  card.type = "button";
  card.dataset.id = String(game.id);
  card.setAttribute("aria-pressed", "false");

  const cover = el("div", "deal-cover");
  const image = el("img");
  image.alt = "";
  image.loading = "lazy";
  image.decoding = "async";
  image.width = 460;
  image.height = 215;
  image.addEventListener("error", () => {
    // header.jpg missing: fall back to the original small image, then to the plain tile.
    if (image.dataset.fallback !== "done" && game.thumb_url && image.src !== game.thumb_url) {
      image.dataset.fallback = "done";
      image.src = game.thumb_url;
    } else {
      image.classList.add("broken");
    }
  });
  const src = coverUrl(game.thumb_url);
  if (src) {
    image.src = src;
  } else {
    image.classList.add("broken");
  }
  cover.append(image);

  if (game.discount_percent > 0) {
    const off = el("span", "deal-off", `−${game.discount_percent}%`);
    off.setAttribute("aria-label", `${game.discount_percent} percent off`);
    cover.append(off);
  } else if (game.lowest_price !== null) {
    cover.append(el("span", "deal-off none", "Full price"));
  }

  const body = el("div", "deal-body");
  body.append(el("span", "deal-title", game.title));
  const prices = el("div", "deal-prices");
  if (game.lowest_price === null) {
    prices.append(el("span", "price-none", "No price yet"));
  } else {
    prices.append(el("span", "price-now", money.format(game.lowest_price)));
    if (game.discount_percent > 0) {
      const was = el("span", "price-was", money.format(game.normal_price));
      was.setAttribute("aria-label", `normally ${money.format(game.normal_price)}`);
      prices.append(was);
    }
  }
  body.append(prices);

  card.append(cover, body);
  card.addEventListener("click", () => selectGame(game.id));
  return card;
}

function showSkeleton() {
  const grid = $("deal-grid");
  grid.replaceChildren();
  for (let i = 0; i < 4; i += 1) {
    const item = el("li", "deal-card skeleton");
    item.setAttribute("aria-hidden", "true");
    const body = el("div", "deal-body");
    const long = el("span", "bar");
    long.style.width = "70%";
    const short = el("span", "bar");
    short.style.width = "35%";
    body.append(long, short);
    item.append(el("div", "deal-cover"), body);
    grid.append(item);
  }
}

async function loadDeals() {
  const grid = $("deal-grid");
  showSkeleton();
  try {
    const games = await getJson("games");
    state.games = games
      .filter((game) => game.lowest_price !== null)
      .sort(byDiscountThenTitle)
      .slice(0, TOP_COUNT);

    grid.replaceChildren();
    if (state.games.length === 0) {
      setStatus($("deals-status"), "No prices collected yet. They appear after the first daily collection.");
      return;
    }

    for (const game of state.games) {
      const item = el("li");
      item.append(dealCard(game));
      grid.append(item);
    }

    // The biggest discount also gets the big card in the hero.
    const best = state.games[0];
    const hero = $("hero-deal");
    hero.replaceChildren(dealCard(best), el("p", "hero-caption", "Biggest discount today"));
  } catch {
    grid.replaceChildren();
    setStatus($("deals-status"), "Could not load today's deals. Please try again in a minute.", true);
  } finally {
    grid.setAttribute("aria-busy", "false");
  }
}

function markSelectedCards() {
  for (const card of document.querySelectorAll(".deal-card[data-id]")) {
    card.setAttribute("aria-pressed", String(card.dataset.id === String(state.selectedId)));
  }
}

// ---------------------------------------------------------------------------
// Price history
// ---------------------------------------------------------------------------

// One point per day: the lowest price among all stores, and the normal price.
function groupByDay(rows) {
  const days = new Map();
  for (const row of rows) {
    const day = days.get(row.recorded_on);
    if (!day) {
      days.set(row.recorded_on, {
        date: row.recorded_on,
        lowest: row.sale_price,
        store: row.store_id,
        normal: row.normal_price,
      });
      continue;
    }
    if (row.sale_price < day.lowest) {
      day.lowest = row.sale_price;
      day.store = row.store_id;
    }
    day.normal = Math.max(day.normal, row.normal_price);
  }
  return [...days.values()].sort((a, b) => a.date.localeCompare(b.date));
}

async function selectGame(gameId) {
  state.selectedId = gameId;
  markSelectedCards();

  const game = state.games.find((item) => item.id === gameId);
  const panel = $("history");
  const area = $("history-chart-area");

  panel.hidden = false;
  $("history-title").textContent = game ? game.title : "";
  $("history-summary").textContent = "";
  $("history-pill").hidden = true;
  setStatus($("history-status"), "");
  area.style.opacity = "0.5";

  panel.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
  panel.focus({ preventScroll: true });

  try {
    const rows = await getJson(`games/${gameId}/history`);
    if (state.selectedId !== gameId) {
      return; // Another card was clicked while this one was loading.
    }
    state.history = { game, rows, days: groupByDay(rows) };
    area.hidden = false;
    renderHistory();
  } catch (error) {
    if (state.selectedId !== gameId) {
      return;
    }
    area.hidden = true;
    const message = error.status === 404
      ? "No prices collected for this game yet. They appear after the next daily collection."
      : "Could not load the price history. Please try again in a minute.";
    setStatus($("history-status"), message, error.status !== 404);
  } finally {
    area.style.opacity = "";
  }
}

function renderHistory() {
  const { game, rows, days } = state.history;
  const latest = days[days.length - 1];

  $("history-summary").replaceChildren(
    "Lowest today ",
    el("strong", "", money.format(latest.lowest)),
    ` at ${storeName(latest.store)}, normally ${money.format(latest.normal)}.`,
  );

  const pill = $("history-pill");
  if (game && game.discount_percent > 0) {
    pill.textContent = `−${game.discount_percent}% today`;
    pill.hidden = false;
  }

  const note = $("history-note");
  note.hidden = days.length > 1;
  note.textContent = "Only one day collected so far. The line grows as the daily collector runs.";

  renderTable(rows);
  renderChart();
}

function renderTable(rows) {
  const body = $("history-rows");
  body.replaceChildren();

  const cheapestByDay = new Map();
  for (const row of rows) {
    const best = cheapestByDay.get(row.recorded_on);
    if (best === undefined || row.sale_price < best) {
      cheapestByDay.set(row.recorded_on, row.sale_price);
    }
  }

  const sorted = [...rows].sort((a, b) =>
    b.recorded_on.localeCompare(a.recorded_on) || a.sale_price - b.sale_price);

  for (const row of sorted) {
    const isCheapest = row.sale_price === cheapestByDay.get(row.recorded_on);
    const tr = el("tr", isCheapest ? "cheapest" : "");
    const store = el("td", "", storeName(row.store_id));
    if (isCheapest) {
      store.append(el("span", "tag", "Cheapest"));
    }
    tr.append(
      el("td", "", formatDate(row.recorded_on)),
      store,
      el("td", "num", money.format(row.sale_price)),
      el("td", "num", money.format(row.normal_price)),
    );
    body.append(tr);
  }
}

// Vertical hairline that follows the hovered day.
const crosshair = {
  id: "crosshair",
  afterDatasetsDraw(chartInstance) {
    const active = chartInstance.tooltip?.getActiveElements?.() || [];
    if (active.length === 0) {
      return;
    }
    const { ctx, chartArea: area } = chartInstance;
    const x = active[0].element.x;
    ctx.save();
    ctx.strokeStyle = cssVar("--axis");
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(x, area.top);
    ctx.lineTo(x, area.bottom);
    ctx.stroke();
    ctx.restore();
  },
};

function renderChart() {
  if (!state.history || typeof Chart === "undefined") {
    return;
  }
  const { days } = state.history;
  const colors = {
    lowest: cssVar("--series-lowest"),
    normal: cssVar("--series-normal"),
    surface: cssVar("--surface"),
    grid: cssVar("--grid"),
    axis: cssVar("--axis"),
    muted: cssVar("--text-muted"),
    primary: cssVar("--text-primary"),
    secondary: cssVar("--text-secondary"),
  };
  const mono = cssVar("--font-mono");

  const line = (label, values, color, dashed) => ({
    label,
    data: values,
    borderColor: color,
    backgroundColor: color,
    borderWidth: 2,
    borderDash: dashed ? [6, 4] : [],
    borderCapStyle: "round",
    borderJoinStyle: "round",
    pointRadius: dashed ? 0 : 4,
    pointHoverRadius: 6,
    pointBorderWidth: 2,
    pointBorderColor: colors.surface,
    pointHitRadius: 12,
    tension: 0,
  });

  const data = {
    labels: days.map((day) => formatDate(day.date, false)),
    datasets: [
      line("Lowest price", days.map((day) => day.lowest), colors.lowest, false),
      line("Normal price", days.map((day) => day.normal), colors.normal, true),
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: reducedMotion.matches ? false : { duration: 250 },
    interaction: { mode: "index", intersect: false },
    layout: { padding: { top: 8, right: 8 } },
    scales: {
      x: {
        offset: true,
        grid: { display: false },
        border: { color: colors.axis },
        ticks: { color: colors.muted, maxRotation: 0, autoSkip: true, font: { family: mono } },
      },
      y: {
        beginAtZero: true,
        grid: { color: colors.grid },
        border: { display: false },
        ticks: {
          color: colors.muted,
          font: { family: mono },
          callback: (value) => money.format(value),
        },
      },
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: colors.surface,
        titleColor: colors.secondary,
        bodyColor: colors.primary,
        borderColor: colors.axis,
        borderWidth: 1,
        padding: 10,
        boxWidth: 12,
        boxHeight: 2,
        bodyFont: { family: mono },
        callbacks: {
          title(items) {
            return formatDate(days[items[0].dataIndex].date);
          },
          label(context) {
            const day = days[context.dataIndex];
            const value = money.format(context.parsed.y);
            if (context.datasetIndex === 0) {
              return ` ${value}  Lowest (${storeName(day.store)})`;
            }
            return ` ${value}  Normal`;
          },
          labelColor(context) {
            const color = context.dataset.borderColor;
            return { borderColor: color, backgroundColor: color };
          },
        },
      },
    },
  };

  if (state.chart) {
    state.chart.data = data;
    state.chart.options = options;
    state.chart.update();
  } else {
    state.chart = new Chart($("history-chart"), {
      type: "line",
      data,
      options,
      plugins: [crosshair],
    });
  }
}

// Redraw the chart in the new colors when the theme changes (event from site.js).
document.addEventListener("themechange", () => {
  // Wait one frame so the new CSS colors are applied before reading them.
  requestAnimationFrame(renderChart);
});

// ---------------------------------------------------------------------------
// "Recruiter?" balloon
// ---------------------------------------------------------------------------

function setUpRecruiter() {
  const toggle = $("recruiter-toggle");
  const balloon = $("recruiter-balloon");
  const loginButton = $("recruiter-login");

  function setOpen(open) {
    balloon.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
  }

  toggle.addEventListener("click", () => setOpen(balloon.hidden));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !balloon.hidden) {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener("click", (event) => {
    if (!balloon.hidden && !balloon.contains(event.target) && event.target !== toggle) {
      setOpen(false);
    }
  });

  loginButton.addEventListener("click", async () => {
    loginButton.disabled = true;
    loginButton.textContent = "Logging in…";
    setStatus($("recruiter-error"), "");
    try {
      const response = await fetch("auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: "recruiter", password: "recruiter" }),
      });
      if (response.ok) {
        window.location.href = "account.html";
        return;
      }
      const message = response.status === 429
        ? "Too many login attempts. Try again later."
        : "The recruiter account isn't available right now. Please try again later.";
      setStatus($("recruiter-error"), message, true);
    } catch {
      setStatus($("recruiter-error"), "Can't reach the server. Check your connection and try again.", true);
    }
    loginButton.disabled = false;
    loginButton.textContent = "Log in as recruiter";
  });
}

setUpRecruiter();
loadDeals();
