// Account pages: log in, sign up and account (log out, delete).
// The login token lives in an HttpOnly cookie: this script never sees it.
// The browser sends it on every request, and the API answers who is logged in.

const page = document.body.dataset.page;
const AFTER_LOGIN = "account.html";

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

// POST a JSON body. Returns { ok, status, detail } and never throws.
async function postJson(url, body) {
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    let detail = "";
    try {
      const data = await response.json();
      // FastAPI sends a list of problems on 422 and a plain text otherwise.
      detail = typeof data.detail === "string" ? data.detail : "";
    } catch {
      // Empty or non-JSON body.
    }
    return { ok: response.ok, status: response.status, detail };
  } catch {
    return { ok: false, status: 0, detail: "" };
  }
}

// Who is logged in? Returns { id, username } or null.
async function getMe() {
  try {
    const response = await fetch("/auth/me");
    return response.ok ? await response.json() : null;
  } catch {
    return null;
  }
}

function friendlyError(result) {
  if (result.status === 0) {
    return "Can't reach the server. Check your connection and try again.";
  }
  if (result.status >= 500) {
    return "Something went wrong on our side. Please try again in a minute.";
  }
  return result.detail || "Something went wrong. Please try again.";
}

// ---------------------------------------------------------------------------
// Form helpers
// ---------------------------------------------------------------------------

function showError(form, message, field) {
  form.querySelector(".form-error").textContent = message;
  form.querySelectorAll("input").forEach((input) => input.removeAttribute("aria-invalid"));
  if (field) {
    field.setAttribute("aria-invalid", "true");
    field.focus();
  }
}

function clearError(form) {
  showError(form, "");
}

function setBusy(form, busy, busyText) {
  const button = form.querySelector('button[type="submit"]');
  if (!button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  button.disabled = busy;
  button.textContent = busy ? busyText : button.dataset.label;
}

// ---------------------------------------------------------------------------
// Log in
// ---------------------------------------------------------------------------

async function logIn(form, username, password) {
  clearError(form);
  setBusy(form, true, "Logging in…");
  const result = await postJson("/auth/login", { username, password });
  if (result.ok) {
    window.location.href = AFTER_LOGIN;
    return;
  }
  setBusy(form, false);
  const field = result.status === 401 ? form.elements.password : null;
  showError(form, friendlyError(result), field);
}

function setUpLogin() {
  const form = document.getElementById("login-form");
  const username = form.elements.username;
  const password = form.elements.password;

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!username.value.trim()) {
      showError(form, "Type your username.", username);
      return;
    }
    if (!password.value) {
      showError(form, "Type your password.", password);
      return;
    }
    logIn(form, username.value.trim(), password.value);
  });

  document.getElementById("recruiter-button").addEventListener("click", () => {
    username.value = "recruiter";
    password.value = "recruiter";
    logIn(form, "recruiter", "recruiter");
  });
}

// ---------------------------------------------------------------------------
// Sign up
// ---------------------------------------------------------------------------

function setUpRegister() {
  const form = document.getElementById("register-form");
  const username = form.elements.username;
  const password = form.elements.password;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const name = username.value.trim();

    // Same rules as the API, checked here first for a clearer message.
    if (name.length < 3 || name.length > 20) {
      showError(form, "Username needs 3 to 20 characters.", username);
      return;
    }
    if (!/^[a-zA-Z0-9_]+$/.test(name)) {
      showError(form, "Username can only have letters, numbers and _.", username);
      return;
    }
    if (password.value.length < 8) {
      showError(form, "Password needs at least 8 characters.", password);
      return;
    }

    clearError(form);
    setBusy(form, true, "Creating account…");
    const created = await postJson("/auth/register", { username: name, password: password.value });

    if (!created.ok) {
      setBusy(form, false);
      const field = created.status === 409 ? username : null;
      const message = created.status === 422
        ? "Check the username and password rules above."
        : friendlyError(created);
      showError(form, message, field);
      return;
    }

    // Account created: log in right away, so the person lands on their account.
    const login = await postJson("/auth/login", { username: name, password: password.value });
    window.location.href = login.ok ? AFTER_LOGIN : "login.html";
  });
}

// ---------------------------------------------------------------------------
// Account: who am I, log out, delete
// ---------------------------------------------------------------------------

async function setUpAccount() {
  const me = await getMe();
  if (!me) {
    window.location.replace("login.html");
    return;
  }

  document.getElementById("who-name").textContent = me.username;
  document.getElementById("account-loading").hidden = true;
  document.getElementById("account-content").hidden = false;

  const logoutButton = document.getElementById("logout-button");
  logoutButton.addEventListener("click", async () => {
    logoutButton.disabled = true;
    logoutButton.textContent = "Logging out…";
    await postJson("/auth/logout");
    window.location.href = "login.html";
  });

  const form = document.getElementById("delete-form");
  const password = form.elements.password;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!password.value) {
      showError(form, "Type your password to confirm.", password);
      return;
    }

    clearError(form);
    setBusy(form, true, "Deleting…");
    const result = await postJson("/auth/delete-account", { password: password.value });

    if (result.ok) {
      window.location.href = "./";
      return;
    }

    setBusy(form, false);
    if (result.status === 401 && result.detail === "Not logged in.") {
      window.location.replace("login.html");
      return;
    }
    password.value = "";
    showError(form, friendlyError(result), result.status === 401 ? password : null);
  });
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

async function start() {
  if (page === "account") {
    setUpAccount();
    return;
  }

  // Attach the form handlers first: a form submitted before this runs would
  // send the password in the address bar.
  if (page === "login") {
    setUpLogin();
  } else if (page === "register") {
    setUpRegister();
  }

  // Already logged in? Skip the log in / sign up forms.
  if (await getMe()) {
    window.location.replace(AFTER_LOGIN);
  }
}

start();
