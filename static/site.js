// Shared by every page: the theme switch and the header links.
// The saved theme is applied in each page's <head>, before it paints.

(() => {
  const root = document.documentElement;
  const darkScheme = window.matchMedia("(prefers-color-scheme: dark)");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const themeSwitch = document.getElementById("theme-switch");
  let fadeTimer;

  function currentTheme() {
    const forced = root.dataset.theme;
    if (forced === "light" || forced === "dark") {
      return forced;
    }
    return darkScheme.matches ? "dark" : "light";
  }

  function updateSwitch() {
    const dark = currentTheme() === "dark";
    themeSwitch.setAttribute("aria-checked", String(dark));
  }

  themeSwitch.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    if (!reducedMotion.matches) {
      // Fade the colors only during the switch, never on page load.
      root.classList.add("theme-fade");
      clearTimeout(fadeTimer);
      fadeTimer = setTimeout(() => root.classList.remove("theme-fade"), 400);
    }
    root.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch {
      // Storage blocked: the choice lasts until the page is closed.
    }
    updateSwitch();
    document.dispatchEvent(new CustomEvent("themechange"));
  });

  darkScheme.addEventListener("change", () => {
    updateSwitch();
    document.dispatchEvent(new CustomEvent("themechange"));
  });

  updateSwitch();

  // Header: show "Account" instead of "Log in" / "Create account" when logged in.
  const loggedOut = document.querySelectorAll("[data-show='logged-out']");
  const loggedIn = document.querySelectorAll("[data-show='logged-in']");
  if (loggedOut.length || loggedIn.length) {
    fetch("auth/me")
      .then((response) => (response.ok ? response.json() : null))
      .then((me) => {
        loggedOut.forEach((node) => { node.hidden = Boolean(me); });
        loggedIn.forEach((node) => { node.hidden = !me; });
      })
      .catch(() => {
        // Server unreachable: keep the logged-out links.
      });
  }
})();
