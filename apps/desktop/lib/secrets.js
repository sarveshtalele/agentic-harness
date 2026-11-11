// Admin login and the signing key live in userData as OS-encrypted blobs (safeStorage). Plain text is never written.
const { safeStorage } = require("electron");
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const MIN_PASSWORD = 12;

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

function validate({ username, password }) {
  if (!username || !username.trim()) return "Enter a username.";
  if (!password || password.length < MIN_PASSWORD) return `The password needs at least ${MIN_PASSWORD} characters.`;
  return null;
}

const files = (userData) => ({ admin: path.join(userData, "admin.bin"), key: path.join(userData, "secret.bin") });

function loadAdmin(userData) {
  return read(files(userData).admin);
}

function saveAdmin(userData, creds) {
  write(files(userData).admin, { username: creds.username.trim(), password: creds.password });
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

module.exports = { loadAdmin, saveAdmin, loadOrCreateKey, validate };
