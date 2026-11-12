// The server sign-in (grant and server key) and the local data key live in userData as OS-encrypted blobs (safeStorage).
// Plain text is never written. No password is kept: the grant from central sign-in (central.js) is all the app holds.
const { safeStorage } = require("electron");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

function requireEncryption() {
  if (!safeStorage.isEncryptionAvailable()) throw new Error("The operating system keychain is not available, so credentials cannot be stored safely.");
}

function read(file) {
  if (!fs.existsSync(file)) return null;
  requireEncryption();
  return JSON.parse(safeStorage.decryptString(fs.readFileSync(file)));
}

function write(file, value) {
  requireEncryption();
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, safeStorage.encryptString(JSON.stringify(value)), { mode: 0o600 });
}

const files = (userData) => ({ signIn: path.join(userData, "signin.bin"), key: path.join(userData, "secret.bin") });

// The saved sign-in while it is still valid, else null (an ended one means signing in again).
function loadSignIn(userData) {
  const saved = read(files(userData).signIn);
  return saved && saved.expires * 1000 > Date.now() + 60000 ? saved : null;
}

function saveSignIn(userData, signIn) {
  write(files(userData).signIn, { server: signIn.server, grant: signIn.grant, public_key: signIn.public_key, expires: signIn.expires });
}

function clearSignIn(userData) {
  fs.rmSync(files(userData).signIn, { force: true }); // sign-out: the grant is gone, the next start asks again
}

// The signing key is made once and reused, so saved data stays readable after a restart.
function loadOrCreateKey(userData) {
  const file = files(userData).key;
  const existing = read(file);
  if (existing) return existing.key;
  const key = crypto.randomBytes(32).toString("base64url");
  write(file, { key });
  return key;
}

module.exports = { loadSignIn, saveSignIn, clearSignIn, loadOrCreateKey };
