// Game Deal Tracker page. It only talks to our own API (api.py):
//   GET /games, GET /stats, GET /games/{id}/history, GET /games/search?title=
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

const $ = (id) => document.getElementById(id);

const SEARCH_COOLDOWN_MS = 2000;

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");

const state = {
  games: [],
  gamesById: new Map(),
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

function plural(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
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

function thumbnail(url, width) {
  const wrap = el("div", "thumb-wrap");
  const image = el("img", "thumb");
  image.alt = "";
  image.loading = "lazy";
  image.decoding = "async";
  image.width = width;
  image.height = Math.round((width * 87) / 231);
  // Some store CDNs refuse to serve images to other sites; keep the gray tile then.
  image.addEventListener("error", () => image.classList.add("broken"), { once: true });
  if (url) {
    image.src = url;
  } else {
    image.classList.add("broken");
  }
  wrap.append(image);
  return wrap;
}

function discountBadge(percent) {
  const badge = el("span", "badge", `−${percent}%`);
  badge.setAttribute("aria-label", `${percent} percent off`);
  return badge;
}

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Body was not JSON; keep the generic message.
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

function currentTheme() {
  const forced = document.documentElement.dataset.theme;
  if (forced === "light" || forced === "dark") {
    return forced;
  }
  return darkScheme.matches ? "dark" : "light";
}

function updateThemeButton() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  $("theme-toggle").setAttribute("aria-label", `Switch to ${next} theme`);
}

$("theme-toggle").addEventListener("click", () => {
  const next = currentTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  try {
    localStorage.setItem("theme", next);
  } catch {
    // Storage blocked: the choice lasts until the page is closed.
  }
  updateThemeButton();
  renderChart();
});

darkScheme.addEventListener("change", () => {
  updateThemeButton();
  renderChart();
});

updateThemeButton();

// ---------------------------------------------------------------------------
// Stats
// ---------------------------------------------------------------------------

async function loadStats() {
  try {
    const stats = await getJson("stats");
    $("stat-games").textContent = String(stats.games_tracked);
    $("stat-days").textContent = plural(stats.days_collected, "day");
    $("stat-days-since").textContent = stats.first_day
      ? `since ${formatDate(stats.first_day)}`
      : "starts after the first collection";
  } catch {
    $("stat-days-since").textContent = "unavailable";
  }
}

function renderBiggestDiscount() {
  const best = state.games
    .filter((game) => game.discount_percent !== null)
    .sort((a, b) => b.discount_percent - a.discount_percent)[0];

  if (best && best.discount_percent > 0) {
    $("stat-discount").textContent = `−${best.discount_percent}%`;
    $("stat-discount-game").textContent = best.title;
  } else {
    $("stat-discount").textContent = "–";
    $("stat-discount-game").textContent = "no discounts today";
  }
}

// ---------------------------------------------------------------------------
// Tracked games grid
// ---------------------------------------------------------------------------

function byDiscountThenTitle(a, b) {
  const da = a.discount_percent ?? -1;
  const db = b.discount_percent ?? -1;
  return db - da || a.title.localeCompare(b.title);
}

async function loadGames() {
  const grid = $("game-grid");
  try {
    const games = await getJson("games");
    state.games = [...games].sort(byDiscountThenTitle);
    state.gamesById = new Map(games.map((game) => [game.id, game]));
    renderGrid();
    renderBiggestDiscount();

    if (state.games.length > 0) {
      selectGame(state.games[0].id, { scroll: false });
    } else {
      setStatus($("games-status"), "No tracked games yet.");
      $("chart-area").hidden = true;
      setStatus($("history-status"), "Add games with the seed script to see prices here.");
    }
  } catch (error) {
    setStatus($("games-status"), `Could not load tracked games: ${error.message}`, true);
    $("chart-area").hidden = true;
    setStatus($("history-status"), "Price history is unavailable right now.", true);
  } finally {
    grid.setAttribute("aria-busy", "false");
  }
}

function renderGrid() {
  const grid = $("game-grid");
  grid.replaceChildren();

  for (const game of state.games) {
    const item = el("li");
    const card = el("button", "game-card");
    card.type = "button";
    card.dataset.id = String(game.id);
    card.setAttribute("aria-pressed", "false");

    const body = el("div", "card-body");
    body.append(el("span", "card-title", game.title));

    const prices = el("div", "card-prices");
    if (game.lowest_price === null) {
      prices.append(el("span", "price-none", "No price yet"));
    } else {
      prices.append(el("span", "price-now", money.format(game.lowest_price)));
      if (game.discount_percent > 0) {
        const was = el("span", "price-was", money.format(game.normal_price));
        was.setAttribute("aria-label", `normally ${money.format(game.normal_price)}`);
        prices.append(was, discountBadge(game.discount_percent));
      }
    }
    body.append(prices);

    card.append(thumbnail(game.thumb_url, 231), body);
    card.addEventListener("click", () => selectGame(game.id, { scroll: true }));
    item.append(card);
    grid.append(item);
  }
}

function markSelectedCard() {
  for (const card of document.querySelectorAll(".game-card")) {
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

async function selectGame(gameId, { scroll }) {
  state.selectedId = gameId;
  markSelectedCard();

  const game = state.gamesById.get(gameId);
  const title = game ? game.title : "";
  const panel = $("history-panel");
  const area = $("chart-area");

  if (scroll) {
    panel.scrollIntoView({ behavior: reducedMotion.matches ? "auto" : "smooth", block: "start" });
    panel.focus({ preventScroll: true });
  }

  area.style.opacity = "0.5";
  setStatus($("history-status"), "");

  try {
    const rows = await getJson(`games/${gameId}/history`);
    if (state.selectedId !== gameId) {
      return; // Another card was clicked while this one was loading.
    }
    state.history = { game, title, rows, days: groupByDay(rows) };
    area.hidden = false;
    renderHistory();
  } catch (error) {
    if (state.selectedId !== gameId) {
      return;
    }
    area.hidden = true;
    const message = error.status === 404
      ? `No prices collected for ${title} yet. They appear after the next daily collection.`
      : `Could not load the price history: ${error.message}`;
    setStatus($("history-status"), message, error.status !== 404);
  } finally {
    area.style.opacity = "";
  }
}

function renderHistory() {
  const { game, title, rows, days } = state.history;
  const latest = days[days.length - 1];

  $("chart-title").textContent = title;

  $("chart-summary").replaceChildren(
    "Lowest today ",
    el("strong", "", money.format(latest.lowest)),
    ` at ${storeName(latest.store)}, normally ${money.format(latest.normal)}.`,
  );

  const badge = $("chart-badge");
  const percent = game ? game.discount_percent : null;
  if (percent > 0) {
    badge.textContent = `−${percent}% today`;
    badge.setAttribute("aria-label", `${percent} percent off today`);
    badge.hidden = false;
  } else {
    badge.hidden = true;
  }

  const note = $("chart-note");
  if (days.length === 1) {
    note.textContent = "Only one day collected so far. The line grows as the daily collector runs.";
    note.hidden = false;
  } else {
    note.hidden = true;
  }

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
      store.append(el("span", "badge tag-cheapest", "Cheapest"));
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

// ---------------------------------------------------------------------------
// Chart
// ---------------------------------------------------------------------------

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
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
  if (!state.history) {
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

  const line = (label, values, color) => ({
    label,
    data: values,
    borderColor: color,
    backgroundColor: color,
    borderWidth: 2,
    borderCapStyle: "round",
    borderJoinStyle: "round",
    pointRadius: 4,
    pointHoverRadius: 6,
    pointBorderWidth: 2,
    pointBorderColor: colors.surface,
    pointHitRadius: 12,
    tension: 0,
  });

  const data = {
    labels: days.map((day) => formatDate(day.date, false)),
    datasets: [
      line("Lowest price", days.map((day) => day.lowest), colors.lowest),
      line("Normal price", days.map((day) => day.normal), colors.normal),
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
        ticks: { color: colors.muted, maxRotation: 0, autoSkip: true },
      },
      y: {
        beginAtZero: true,
        grid: { color: colors.grid },
        border: { display: false },
        ticks: { color: colors.muted, callback: (value) => money.format(value) },
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

// ---------------------------------------------------------------------------
// Search (only on submit, so typing never spends CheapShark calls)
// ---------------------------------------------------------------------------

function showSearchSkeleton() {
  const results = $("search-results");
  results.replaceChildren();
  for (let i = 0; i < 3; i += 1) {
    const item = el("li", "result skeleton");
    item.setAttribute("aria-hidden", "true");
    const text = el("div", "result-text");
    const long = el("span", "bar");
    long.style.width = "60%";
    const short = el("span", "bar");
    short.style.width = "30%";
    text.append(long, short);
    item.append(el("div", "skeleton-thumb"), text);
    results.append(item);
  }
}

$("search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const input = $("search-input");
  const button = $("search-button");
  const status = $("search-status");
  const title = input.value.trim();

  if (title.length < 2) {
    setStatus(status, "Type at least 2 characters.", true);
    input.focus();
    return;
  }

  button.disabled = true;
  setStatus(status, "Searching…");
  showSearchSkeleton();

  try {
    const games = await getJson(`games/search?title=${encodeURIComponent(title)}`);
    renderResults(games);
    setStatus(
      status,
      games.length === 0 ? `No games found for "${title}".` : `${plural(games.length, "result")}.`,
    );
  } catch (error) {
    $("search-results").replaceChildren();
    const message = error.status === 502
      ? "CheapShark is not answering right now. Try again in a few minutes."
      : `Search failed: ${error.message}`;
    setStatus(status, message, true);
  } finally {
    // Short cooldown so repeated clicks can't flood the API.
    setTimeout(() => {
      button.disabled = false;
    }, SEARCH_COOLDOWN_MS);
  }
});

function renderResults(games) {
  const results = $("search-results");
  results.replaceChildren();

  for (const game of games) {
    const item = el("li", "result");
    const text = el("div", "result-text");
    text.append(el("span", "result-title", game.title));

    const meta = el("div", "result-meta");
    meta.append(el("span", "", `From ${money.format(game.cheapest_price)}`));
    const tracked = state.gamesById.has(game.id);
    if (tracked) {
      meta.append(el("span", "badge", "Tracked"));
    }
    text.append(meta);

    item.append(thumbnail(game.thumb_url, 104), text);

    if (tracked) {
      const button = el("button", "button button-small", "View history");
      button.type = "button";
      button.setAttribute("aria-label", `View price history of ${game.title}`);
      button.addEventListener("click", () => selectGame(game.id, { scroll: true }));
      item.append(button);
    }

    results.append(item);
  }
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

loadStats();
loadGames();
