// Central sign-in (docs/PHASE2_PLAN.md R6, 12.7): the member signs in to the team's server, which returns a signed grant.
// Only the grant and the server's public key are kept (encrypted by secrets.js); the password is used once and dropped.

const LOOPBACK = new Set(["localhost", "127.0.0.1", "[::1]"]);

function serverUrl(text) {
  let url;
  try {
    url = new URL(String(text || "").trim());
  } catch {
    return { error: "Enter the server address, for example https://aqe.example.com" };
  }
  if (url.protocol !== "https:" && !(url.protocol === "http:" && LOOPBACK.has(url.hostname))) {
    return { error: "The server address must start with https:// (http:// only for this computer)." };
  }
  return { url: url.origin };
}

async function call(url, options) {
  try {
    return await fetch(url, { ...options, redirect: "error", signal: AbortSignal.timeout(20000) });
  } catch (error) {
    throw new Error(`The server did not answer (${error.cause?.code || error.name}). Check the address and your network.`);
  }
}

async function detail(response) {
  try {
    const body = await response.json();
    return body.message || body.detail || `HTTP ${response.status}`;
  } catch {
    return `HTTP ${response.status}`;
  }
}

// Resolves { server, grant, public_key, expires } or { error }.
async function signIn({ server, username, password }) {
  const where = serverUrl(server);
  if (where.error) return where;
  if (!username || !password) return { error: "Enter your username and password." };
  const login = await call(`${where.url}/api/auth/login`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ username, password }) });
  if (!login.ok) return { error: await detail(login) };
  const cookie = login.headers.getSetCookie().map((c) => c.split(";")[0]).join("; ");
  const made = await call(`${where.url}/api/auth/desktop-session`, { method: "POST", headers: { cookie } });
  const result = made.ok ? { server: where.url, ...(await made.json()) } : { error: await detail(made) };
  await call(`${where.url}/api/auth/logout`, { method: "POST", headers: { cookie } }).catch(() => {}); // the grant replaces the web session
  return result;
}

// Signs the app's window in to the local backend with the grant it was started with; returns the session cookie value.
async function localSession(apiOrigin, grant, cookieName) {
  const response = await call(`${apiOrigin}/api/auth/desktop`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ grant }) });
  if (!response.ok) throw new Error(`The local backend refused the sign-in: ${await detail(response)}`);
  const found = response.headers.getSetCookie().map((c) => c.split(";")[0]).find((c) => c.startsWith(`${cookieName}=`));
  if (!found) throw new Error("The local backend gave no session.");
  return found.slice(cookieName.length + 1);
}

module.exports = { serverUrl, signIn, localSession };
