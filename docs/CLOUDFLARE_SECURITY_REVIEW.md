# Cloudflare Repository Security Review
**Project:** Agentic QE Platform (`agentic-harness`)  
**Audit Standard:** Cloudflare Repository Security Standards & Zero Trust Architecture  
**Scope:** API Endpoints, Subprocess Execution & Environment Isolation, Cryptographic Storage & Key Derivation, Secret Detection Scanners, Assertion Preservation Guardrails & Autonomous Healing Workflows.

---

## 1. Executive Summary & Threat Dashboard

| Severity | Count | Summary of Key Areas |
| :--- | :---: | :--- |
| 🔴 **CRITICAL (P0)** | 4 | Subprocess Environment Leakage in Sandbox & Git; Missing Host Sandbox Virtualization / Arbitrary Code Execution; Broken Object-Level Authorization (BOLA/IDOR) in Harness API; Quality Gate HITL Approval Timeout Fail-Open |
| 🟠 **HIGH (P1)** | 5 | Incomplete Assertion Preservation Counting Heuristics; Unsalted Single-Round SHA-256 Fernet Key Derivation; SSRF in Git Remote Validation; Path Traversal / Git Hook Hijacking in Sandbox File Creation; In-Memory Account Lockout Denial of Service |
| 🟡 **MEDIUM (P2)** | 4 | Inadequate CORS and Origin Guard on Cross-Site GET Requests; Secret Scanner Blindspots (Tokens < 40 chars, lines > 2000 chars, missing cloud token regexes); Denylist-based Scrubbing in `clean_env()`; Multi-Line Assertion Detection Flaws |
| 🔵 **LOW (P3)** | 3 | Absence of Cryptographic Key Rotation Mechanism; Leaking Partial Secrets via Redaction Slices; Lack of Native API Rate-Limiting Middleware on Unauthenticated Routes |

---

## 2. API Endpoints Review (`src/backend/api/` & `src/backend/app.py`)

### 2.1 Broken Object-Level Authorization (BOLA/IDOR) in Harness Chat & Documents
* **Severity:** 🔴 **CRITICAL (P0)**
* **Affected Files:** `src/backend/api/harness.py` (Lines 158–169, 208–261), `src/backend/core/auth.py` (Lines 391–395)
* **Mechanics:**
  In `auth.py`, routes matching `/api/harness(/.*)?` are classified under `SESSION_ONLY`. This enforces that a valid session cookie is present, but it **never verifies project-level membership or write authorization** for harness actions.
  In `src/backend/api/harness.py`:
  - `POST /api/harness/chat` accepts an arbitrary `projectId` within the JSON body.
  - `POST /api/harness/documents` accepts an arbitrary `projectId` in JSON body and creates documents.
  Neither endpoint invokes `auth.can_see_project(project_id)` or `auth.can_write(project_id)`.
* **Impact:** Any authenticated user—even with a read-only `viewer` role in an unrelated project—can read context, execute prompts, invoke tools, and write/overwrite documents in **any other tenant's project**.
* **Remediation:** Enforce project membership checks in `stream_chat` and `create_harness_document`:
  ```python
  if req.projectId:
      if not auth.can_see_project(req.projectId):
          raise HTTPException(404, "Project not found")
      if not auth.can_write(req.projectId):
          raise HTTPException(403, "Viewer role cannot execute agent tasks")
  ```

---

### 2.2 CORS and Cross-Site Origin Guard Vulnerabilities
* **Severity:** 🟡 **MEDIUM (P2)**
* **Affected Files:** `src/backend/app.py` (Lines 92–103), `src/backend/config.py` (Lines 32–36)
* **Mechanics:**
  1. `origin_guard` only validates the `Origin` header for state-changing HTTP verbs:
     ```python
     if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin not in config.ALLOWED_ORIGINS:
         return fail(request, 403, "Origin not allowed")
     ```
     `GET` requests are exempt from origin verification.
  2. The application lacks standard FastAPI `CORSMiddleware`. While `origin_guard` inspects the incoming `Origin` header on writes, it does not manage proper CORS negotiation headers (`Access-Control-Allow-Origin`, `Access-Control-Allow-Credentials`, preflight `OPTIONS`).
* **Impact:** Cross-origin malicious websites visited by an authenticated user could issue credentialed `GET` requests (`fetch('http://localhost:8000/api/projects', {credentials: 'include'})`), bypassing origin filtering if reverse proxies or browsers allow cross-origin reads on loopback.
* **Remediation:** Add FastAPI `CORSMiddleware` with explicit origin allowlisting and `allow_credentials=True`. Enforce strict CSRF protections / SameSite cookie isolation across all endpoints.

---

### 2.3 Session Management & Credential Security
* **Severity:** 🟢 **DEFENSIBLE (with P2/P3 Caveats)**
* **Affected Files:** `src/backend/core/auth.py` (Lines 82–159, 557–579), `src/backend/api/auth.py` (Lines 59–77)
* **Findings:**
  - **Positive Security Controls:**
    - High-entropy cryptographic session tokens (`secrets.token_urlsafe(32)`).
    - Database stores only the SHA-256 hash of tokens (`hashlib.sha256(token.encode()).hexdigest()`), mitigating session exposure from database snapshots.
    - Strict cookie flags: `httponly=True, samesite="strict", secure=secure, max_age=SESSION_HOURS * 3600, path="/"`.
    - Idle timeout enforcement (480 minutes) and rolling last-seen updates throttled to 60-second intervals.
    - Password updates terminate all concurrent sessions except the active token (`DELETE FROM sessions WHERE user_id=? AND token_hash<>?`).
  - **Identified Weakness:** Single-token per session model lacks explicit cryptographically signed refresh tokens or token rotation on privilege transitions.

---

### 2.4 Rate Limiting & Denial of Service Vulnerabilities
* **Severity:** 🟠 **HIGH (P1)**
* **Affected Files:** `src/backend/core/auth.py` (Lines 30–38, 97–123), `src/backend/app.py`
* **Mechanics:**
  1. In-memory failure tracking map: `_failures: dict[str, tuple[int, float]]`.
  2. Memory exhaustion DoS: If an attacker floods the login endpoint with randomized usernames, `_failures` grows unbounded because failed attempt keys are never evicted unless a subsequent login on that exact username succeeds.
  3. Account lockout DoS: An unauthenticated attacker knowing a victim's username (or targeting `admin`) can deliberately send 5 bad passwords to lock the account for 300 seconds (`LOCK_SECONDS`).
  4. Missing endpoint rate limiting: Public routes like `/api/health`, `/api/auth/status`, and `/api/auth/login` have no L7 rate-limiting middleware (e.g. token bucket / leaky bucket per IP).
* **Remediation:**
  - Implement Redis-backed or SQLite-backed rate limiting per IP and per username.
  - Implement progressive delays (exponential backoff) rather than complete account lockout to prevent denial-of-service against administrators.
  - Integrate SlowAPI or Cloudflare Rate Limiting rules on all authentication endpoints.

---

## 3. Subprocess Execution & Environment Isolation

### 3.1 Unrestricted Subprocess Execution & Total Environment Leakage in Sandbox
* **Severity:** 🔴 **CRITICAL (P0)**
* **Affected Files:** `src/backend/repos/sandbox.py` (Lines 74–101, 103–128), `src/backend/harness/qe_tools.py` (Lines 202–207)
* **Mechanics:**
  In `sandbox.py`:
  ```python
  def execute_code(project_id: str, code: str, runtime: str = "python", timeout: int = 60) -> dict:
      repo = ensure_sandbox(project_id)
      script_file = repo / ("_sandbox_exec.py" if runtime == "python" else "_sandbox_exec.js")
      script_file.write_text(code, encoding="utf-8")
      ...
      proc = subprocess.run([binary, str(script_file)], cwd=repo, capture_output=True, text=True, timeout=timeout)
  ```
  Neither call sets the `env` argument! When `env` is omitted in Python's `subprocess.run`, the child process **inherits 100% of the parent process's environment variables (`os.environ`)**.
* **Impact:** The code being executed is user-generated or LLM-generated code. Any script running in `execute_code` can execute:
  ```python
  import os
  print(os.environ["ATLAS_ADMIN_PASSWORD"], os.environ["ATLAS_SECRET_KEY"], os.environ["OPENAI_API_KEY"])
  ```
  All platform master keys, database paths, AI API tokens, and administration credentials are completely compromised.
* **Remediation:**
  Every subprocess call must strictly pass an allowlisted clean environment. Never inherit `os.environ`:
  ```python
  def clean_sandbox_env() -> dict:
      return {
          "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
          "LANG": "en_US.UTF-8",
          "HOME": "/tmp",
          "TMPDIR": "/tmp",
          "PYTHONDONTWRITEBYTECODE": "1"
      }
  ```

---

### 3.2 Platform Secret Leakage to Git Subprocesses & Static Analyzers
* **Severity:** 🔴 **CRITICAL (P0)**
* **Affected Files:** `src/backend/repos/git.py` (Lines 19–25, 36), `src/backend/repos/static_analysis.py` (Lines 37–43)
* **Mechanics:**
  `_env(token)` and `subprocess.run(command, ..., env={**os.environ, "NO_COLOR": "1"})` explicitly unpack `{**os.environ}`. Git repos may contain custom smudge/clean filters, credential helpers, hooks, or external commands.
* **Impact:** Git processes and static analysis tooling run with full knowledge of platform secrets. Any invoked git filter, external hook, or compromised dependency can read credentials directly from memory/environment.
* **Remediation:** Strip `os.environ` to a strictly allowlisted set (`PATH`, `GIT_EXEC_PATH`, `HOME`).

---

### 3.3 Arbitrary File Overwrite & Git Hook Hijacking in `sandbox.create_file`
* **Severity:** 🟠 **HIGH (P1)**
* **Affected Files:** `src/backend/repos/sandbox.py` (Lines 65–72), `src/backend/core/security.py` (Lines 143–153)
* **Mechanics:**
  In `src/backend/repos/sandbox.py`:
  ```python
  def create_file(project_id: str, rel_path: str, content: str) -> dict:
      repo = ensure_sandbox(project_id)
      target = safe_path(repo, rel_path)
      target.parent.mkdir(parents=True, exist_ok=True)
      target.write_text(content, encoding="utf-8")
  ```
  Notice: `safe_path(repo, rel_path)` is called without passing `for_write=True`!
  Because `for_write=False` is the default, the `PROTECTED` directory check (`.git`, `.venv`, `node_modules`, `.qe`) is **bypassed**.
* **Impact:** An attacker or agent can call `create_file(project_id, ".git/hooks/post-commit", malicious_bash)` or overwrite `.git/config` with custom commands. When subsequent git operations run, the hook executes on the host with full privileges of the application process.
* **Remediation:** Always pass `for_write=True` in `sandbox.create_file()`:
  ```python
  target = safe_path(repo, rel_path, for_write=True)
  ```

---

### 3.4 Server-Side Request Forgery (SSRF) in Git Remote URL Validation
* **Severity:** 🟠 **HIGH (P1)**
* **Affected Files:** `src/backend/repos/git.py` (Lines 44–52)
* **Mechanics:**
  `validate_url` performs only a superficial check:
  ```python
  def validate_url(url: str) -> str:
      parsed = urlparse(url.strip())
      if parsed.scheme != "https" or not parsed.hostname:
          raise GitError("Only https:// git URLs are accepted")
      if parsed.username or parsed.password:
          raise GitError("Remove credentials from the URL. Use a saved connection instead")
      return url.strip()
  ```
  It does not resolve `parsed.hostname` or verify whether the target IP falls into private or reserved ranges (e.g. `127.0.0.1`, RFC 1918 `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, or Cloud Metadata IP `169.254.169.254`).
* **Impact:** An attacker can provide `https://169.254.169.254/latest/meta-data/` or internal corporate endpoints as repository URLs.
* **Remediation:** Resolve DNS before initiating clone operations and forbid loopback, RFC1918, link-local, and cloud metadata addresses.

---

### 3.5 Denylist-based Scrubbing in `clean_env()`
* **Severity:** 🟡 **MEDIUM (P2)**
* **Affected Files:** `src/backend/qe/execution.py` (Lines 15, 20–24)
* **Mechanics:**
  `clean_env()` uses regex denylisting. This violates Cloudflare Zero Trust guidelines (Deny by Default / Allowlist).
* **Remediation:** Replace denylisting with a strict allowlist.

---

## 4. Token Security & Secret Scanners

### 4.1 Unsalted Single-Round SHA-256 Fernet Key Derivation
* **Severity:** 🟠 **HIGH (P1)**
* **Affected Files:** `src/backend/core/security.py` (Lines 33–44)
* **Mechanics:**
  Deriving a symmetric AES-128-CBC / Fernet key from `ATLAS_SECRET_KEY` using unsalted single-round SHA-256 is cryptographically insecure if the environment variable contains a passphrase rather than 32 cryptographically random bytes.
* **Remediation:** Use PBKDF2HMAC (min 600,000 iterations), HKDF, or Argon2id with a static application salt to derive the 32-byte Fernet key.

---

### 4.2 Lack of Key Rotation Mechanism & Catastrophic Lockout
* **Severity:** 🟡 **MEDIUM (P2)**
* **Affected Files:** `src/backend/core/security.py`, `src/backend/core/auth.py` (Line 61)
* **Impact:** There is no key rotation mechanism (such as `cryptography.fernet.MultiFernet`). If `ATLAS_SECRET_KEY` is rotated or `.secret.key` is replaced, every user account in the database is locked permanently.
* **Remediation:** Introduce `MultiFernet` with key version identifiers.

---

### 4.3 Secret Scanner Detection Blindspots & Line Truncation
* **Severity:** 🟡 **MEDIUM (P2)**
* **Affected Files:** `src/backend/core/security.py` (Lines 19–31, 70–90)
* **Remediation:** Tokenize long lines before scanning; lower entropy threshold checking to 30 characters; expand `SECRET_PATTERNS` to cover Cloudflare, GCP, Stripe, and Slack token patterns.

---

## 5. QE Guardrails, Assertion Preservation & Healing Workflows

### 5.1 Flawed Counting Heuristics in `QEGuardrails.validate_assertion_preservation`
* **Severity:** 🔴 **CRITICAL (P0)**
* **Affected Files:** `src/backend/harness/qe_guardrails.py` (Lines 60–80)
* **Mechanics:**
  `QEGuardrails.validate_assertion_preservation` only verifies `len(prop_matches) < len(orig_matches)`. It never checks whether the original assertions still exist in the proposed content, allowing assertion gutting attacks.
* **Remediation:** Enforce AST-level assertion contract matching or verbatim assertion line preservation.

---

### 5.2 Quality Gate Approval Fail-Open Timeout Flaw
* **Severity:** 🔴 **CRITICAL (P0)**
* **Affected Files:** `src/backend/harness/harness_agent.py` (Lines 721–728)
* **Mechanics:**
  When a tool requiring HITL gate approval times out after 25 seconds, execution proceeds anyway. Quality gates must **Fail-Closed**.
* **Remediation:** On `asyncio.TimeoutError`, abort execution immediately (Fail-Closed).

---

### 5.3 Limitations in `execution.assertions_preserved`
* **Severity:** 🟡 **MEDIUM (P2)**
* **Affected Files:** `src/backend/qe/execution.py` (Lines 208–219)
* **Remediation:** Use Python `ast.parse` to extract `ast.Assert` statements and compare normalized AST nodes rather than single-line strings.

---

## 6. Prioritized Remediation Roadmap

| Priority | ID | Issue Summary | Target Component | Remediation Action |
| :---: | :---: | :--- | :--- | :--- |
| **P0** | SEC-P0-01 | Subprocess Environment Leakage | `sandbox.py`, `git.py`, `qe_tools.py` | Implement strict environment variable allowlisting; remove `{**os.environ}`. |
| **P0** | SEC-P0-02 | Broken Object-Level Authorization (BOLA) | `src/backend/api/harness.py` | Enforce `auth.can_see_project()` and `auth.can_write()` on all harness routes. |
| **P0** | SEC-P0-03 | Quality Gate Timeout Fail-Open | `src/backend/harness/harness_agent.py` | Change HITL approval timeout from fail-open to fail-closed (`abort`). |
| **P0** | SEC-P0-04 | Assertion Deletion in Guardrail Heuristic | `src/backend/harness/qe_guardrails.py` | Replace count-only assertion check with set-inclusion / AST comparison. |
| **P1** | SEC-P1-01 | Unsalted Fernet Key Derivation | `src/backend/core/security.py` | Upgrade `_key()` derivation to PBKDF2HMAC (600,000 iterations). |
| **P1** | SEC-P1-02 | Protected Path Bypass in Sandbox Write | `src/backend/repos/sandbox.py` | Pass `for_write=True` to `safe_path()` in `create_file()`. |
| **P1** | SEC-P1-03 | Git Remote SSRF Vulnerability | `src/backend/repos/git.py` | Validate and resolve hostnames, blocking RFC1918 and Cloud Metadata IPs. |
| **P1** | SEC-P1-04 | In-Memory Account Lockout DoS | `src/backend/core/auth.py` | Implement persistent IP-based rate limiting with exponential backoff. |
| **P2** | SEC-P2-01 | Incomplete Secret Scanner Patterns | `src/backend/core/security.py` | Add Cloudflare, GCP, Stripe, and Slack regexes; tokenize lines > 2000 chars. |
| **P2** | SEC-P2-02 | Denylist Scrubbing in `clean_env` | `src/backend/qe/execution.py` | Convert `clean_env()` to strict allowlist. |
| **P2** | SEC-P2-03 | Multi-line Assertion Bypass | `src/backend/qe/execution.py` | Normalize multi-line assertions using AST comparison. |
| **P2** | SEC-P2-04 | Origin Guard GET Exemptions | `src/backend/app.py` | Add standard FastAPI CORSMiddleware with explicit origin bindings. |
