// Game Deal Tracker page: talks only to our own API (api.py).

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

const gameSelect = document.getElementById("game-select");
const chartArea = document.getElementById("chart-area");
const chartTitle = document.getElementById("chart-title");
const chartSummary = document.getElementById("chart-summary");
const chartNote = document.getElementById("chart-note");
const historyRows = document.getElementById("history-rows");
const historyStatus = document.getElementById("history-status");
const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("search-input");
const searchButton = document.getElementById("search-button");
const searchStatus = document.getElementById("search-status");
const searchResults = document.getElementById("search-results");

const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

let trackedIds = new Set();
let chart = null;
let lastHistory = null;

function storeName(storeId) {
  return STORE_NAMES[storeId] || `Store ${storeId}`;
}

function formatDate(isoDate) {
  // "2026-11-15" -> "Nov 15, 2026", read as UTC so the day never shifts.
  const date = new Date(`${isoDate}T00:00:00Z`);
  return date.toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric", timeZone: "UTC",
  });
}

function setStatus(element, text, isError = false) {
  element.textContent = text;
  element.classList.toggle("error", isError);
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
// Tracked games and price history
// ---------------------------------------------------------------------------

async function loadTrackedGames() {
  try {
    const games = await getJson("/games");
    trackedIds = new Set(games.map((game) => game.id));

    gameSelect.replaceChildren();
    for (const game of games) {
      const option = document.createElement("option");
      option.value = String(game.id);
      option.textContent = game.title;
      gameSelect.append(option);
    }
    gameSelect.disabled = games.length === 0;

    if (games.length > 0) {
      showHistory(games[0].id);
    } else {
      chartArea.hidden = true;
      setStatus(historyStatus, "No tracked games yet.");
    }
  } catch (error) {
    gameSelect.replaceChildren(new Option("Unavailable"));
    chartArea.hidden = true;
    setStatus(historyStatus, `Could not load tracked games: ${error.message}`, true);
  }
}

// One point per day: the lowest price among all stores, and the normal price.
function groupByDay(rows) {
  const days = new Map();
  for (const row of rows) {
    const day = days.get(row.recorded_on);
    if (!day || row.sale_price < day.lowest) {
      days.set(row.recorded_on, {
        date: row.recorded_on,
        lowest: row.sale_price,
        store: row.store_id,
        normal: Math.max(row.normal_price, day ? day.normal : 0),
      });
    } else {
      day.normal = Math.max(day.normal, row.normal_price);
    }
  }
  return [...days.values()].sort((a, b) => a.date.localeCompare(b.date));
}

async function showHistory(gameId) {
  gameSelect.value = String(gameId);
  const title = gameSelect.selectedOptions[0]?.textContent || "";
  chartArea.style.opacity = "0.5";
  setStatus(historyStatus, "");

  try {
    const rows = await getJson(`/games/${gameId}/history`);
    lastHistory = { title, rows, days: groupByDay(rows) };
    chartArea.hidden = false;
    renderHistory();
  } catch (error) {
    chartArea.hidden = true;
    const message = error.status === 404
      ? `No prices collected for ${title} yet.`
      : `Could not load the price history: ${error.message}`;
    setStatus(historyStatus, message, error.status !== 404);
  } finally {
    chartArea.style.opacity = "";
  }
}

function renderHistory() {
  if (!lastHistory) {
    return;
  }
  const { title, rows, days } = lastHistory;
  const latest = days[days.length - 1];

  chartTitle.textContent = title;
  chartSummary.textContent =
    `Lowest today: ${money.format(latest.lowest)} at ${storeName(latest.store)} ` +
    `(normal ${money.format(latest.normal)})`;

  if (days.length === 1) {
    chartNote.hidden = false;
    chartNote.textContent =
      "Only one day collected so far. The line grows as the daily collector runs.";
  } else {
    chartNote.hidden = true;
  }

  renderTable(rows);
  renderChart(days);
}

function renderTable(rows) {
  historyRows.replaceChildren();
  const sorted = [...rows].sort((a, b) =>
    b.recorded_on.localeCompare(a.recorded_on) || a.sale_price - b.sale_price);

  for (const row of sorted) {
    const tr = document.createElement("tr");
    const cells = [
      [formatDate(row.recorded_on), ""],
      [storeName(row.store_id), ""],
      [money.format(row.sale_price), "num"],
      [money.format(row.normal_price), "num"],
    ];
    for (const [text, className] of cells) {
      const td = document.createElement("td");
      td.textContent = text;
      if (className) {
        td.className = className;
      }
      tr.append(td);
    }
    historyRows.append(tr);
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

function renderChart(days) {
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
    labels: days.map((day) => formatDate(day.date)),
    datasets: [
      line("Lowest price", days.map((day) => day.lowest), colors.lowest),
      line("Normal price", days.map((day) => day.normal), colors.normal),
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? false : { duration: 250 },
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
        ticks: {
          color: colors.muted,
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
        usePointStyle: false,
        callbacks: {
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

  if (chart) {
    chart.data = data;
    chart.options = options;
    chart.update();
  } else {
    chart = new Chart(document.getElementById("history-chart"), {
      type: "line",
      data,
      options,
      plugins: [crosshair],
    });
  }
}

// Redraw with the right colors when the OS theme changes.
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", renderHistory);

gameSelect.addEventListener("change", () => showHistory(Number(gameSelect.value)));

// ---------------------------------------------------------------------------
// Search (only on submit, so typing never spends CheapShark calls)
// ---------------------------------------------------------------------------

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = searchInput.value.trim();
  if (title.length < 2) {
    setStatus(searchStatus, "Type at least 2 characters.", true);
    searchInput.focus();
    return;
  }

  searchButton.disabled = true;
  searchResults.style.opacity = "0.5";
  setStatus(searchStatus, "Searching…");

  try {
    const games = await getJson(`/games/search?title=${encodeURIComponent(title)}`);
    renderResults(games);
    setStatus(
      searchStatus,
      games.length === 0 ? `No games found for "${title}".` : `${games.length} result(s).`,
    );
  } catch (error) {
    const message = error.status === 502
      ? "CheapShark is not answering right now. Try again later."
      : `Search failed: ${error.message}`;
    setStatus(searchStatus, message, true);
  } finally {
    searchButton.disabled = false;
    searchResults.style.opacity = "";
  }
});

function renderResults(games) {
  searchResults.replaceChildren();
  for (const game of games) {
    const item = document.createElement("li");
    item.className = "result";

    const image = document.createElement("img");
    image.src = game.thumb_url;
    image.alt = "";
    image.loading = "lazy";
    image.width = 92;
    image.height = 43;
    // Some store CDNs refuse to serve images to other sites; keep a blank tile then.
    image.addEventListener("error", () => { image.style.visibility = "hidden"; }, { once: true });

    const text = document.createElement("div");
    text.className = "result-text";
    const name = document.createElement("div");
    name.className = "result-title";
    name.textContent = game.title;
    const price = document.createElement("div");
    price.className = "result-price";
    price.textContent = `From ${money.format(game.cheapest_price)}`;
    text.append(name, price);

    item.append(image, text);

    if (trackedIds.has(game.id)) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = "View history";
      button.setAttribute("aria-label", `View price history of ${game.title}`);
      button.addEventListener("click", () => {
        showHistory(game.id);
        document.getElementById("history-title").scrollIntoView({ behavior: "smooth" });
      });
      item.append(button);
    }

    searchResults.append(item);
  }
}

loadTrackedGames();
