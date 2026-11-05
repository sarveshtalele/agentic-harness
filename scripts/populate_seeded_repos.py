"""Populate seeded repositories with realistic code, manifests, tests, and git commits,
then record complete analysis records in SQLite repo_sources.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PROJECTS_DIR = DATA_DIR / "projects"
DB_PATH = DATA_DIR / "atlas.sqlite3"


def run_git(cmd: list[str], cwd: Path) -> str:
    res = subprocess.run(["git", *cmd], cwd=cwd, capture_output=True, text=True, check=True)
    return res.stdout.strip()


def init_git(repo: Path, commit_msg: str) -> str:
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Agentic QE Platform"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "agentic-qe@localhost"], cwd=repo, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    # Check if anything to commit
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True).stdout.strip()
    if status:
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=repo, check=True)
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()


def populate_agentic_qe():
    repo = PROJECTS_DIR / "prj_agentic_qe" / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    # 1. README.md
    (repo / "README.md").write_text("""# Agentic QE Platform & Framework

Enterprise autonomous test engineering platform featuring:
- 8 Quality Gates verification lifecycle (Gates 0-8)
- MAF 2.0 multi-agent collaboration (BA, QA, Diagnostician, Copilot)
- Grounded AST static analysis and deterministic test oracles
- Real-time execution telemetry and cryptographic audit ledger
""", encoding="utf-8")

    # 2. .gitignore
    (repo / ".gitignore").write_text("""__pycache__/
*.pyc
node_modules/
.venv/
dist/
.coverage
.pytest_cache/
""", encoding="utf-8")

    # 3. package.json
    (repo / "package.json").write_text(json.dumps({
        "name": "agentic-qe-frontend",
        "version": "2.0.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "test": "vitest run",
            "test:e2e": "playwright test"
        },
        "dependencies": {
            "next": "^14.2.0",
            "react": "^18.3.0",
            "react-dom": "^18.3.0",
            "lucide-react": "^0.395.0",
            "zod": "^3.23.0"
        },
        "devDependencies": {
            "@playwright/test": "^1.44.0",
            "@types/react": "^18.3.0",
            "typescript": "^5.4.0",
            "vitest": "^1.6.0"
        }
    }, indent=2), encoding="utf-8")

    # 4. requirements.txt
    (repo / "requirements.txt").write_text("""fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
""", encoding="utf-8")

    # 5. pyproject.toml
    (repo / "pyproject.toml").write_text("""[project]
name = "agentic-qe-harness"
version = "2.0.0"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.6.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
""", encoding="utf-8")

    # 6. CI workflow
    ci_dir = repo / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    (ci_dir / "ci.yml").write_text("""name: Quality Gates CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run Pytest
        run: pytest
      - name: Run Playwright
        run: npx playwright test
""", encoding="utf-8")

    # 7. backend code
    be_dir = repo / "backend" / "app"
    be_dir.mkdir(parents=True, exist_ok=True)

    (be_dir / "__init__.py").write_text("", encoding="utf-8")

    (be_dir / "main.py").write_text("""from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

app = FastAPI(title="Agentic QE Engine", version="2.0.0")

class GateEvaluation(BaseModel):
    gate_id: int
    name: str
    status: str
    score: float
    reasons: List[str]

GATES_DB = {
    0: {"name": "Intake & Discovery", "status": "approved", "score": 1.0},
    1: {"name": "Requirements Verification", "status": "approved", "score": 0.98},
    2: {"name": "Test Strategy & Risk Matrix", "status": "approved", "score": 0.96},
    3: {"name": "Deterministic Design", "status": "approved", "score": 0.95},
    4: {"name": "Automation Suites", "status": "pending", "score": 0.90},
    5: {"name": "Sandboxed Execution", "status": "pending", "score": 0.0},
    6: {"name": "Autonomous Healing", "status": "pending", "score": 0.0},
    7: {"name": "Coverage & Mutation Audit", "status": "pending", "score": 0.0},
    8: {"name": "Release Confidence Gate", "status": "pending", "score": 0.0},
}

@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/gates")
def list_gates() -> List[Dict[str, Any]]:
    return [{"gate_id": gid, **data} for gid, data in GATES_DB.items()]

@app.get("/api/gates/{gate_id}")
def get_gate(gate_id: int) -> Dict[str, Any]:
    if gate_id not in GATES_DB:
        raise HTTPException(status_code=404, detail="Gate not found")
    return {"gate_id": gate_id, **GATES_DB[gate_id]}

@app.post("/api/runs")
def trigger_run(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {"run_id": "run_demo_01", "status": "started", "workflow": payload.get("workflow", "qe")}
""", encoding="utf-8")

    (be_dir / "gates.py").write_text("""\"\"\"Quality Gate Evaluator Engine.\"\"\"
from typing import Dict, Any

def evaluate_gate(gate_id: int, telemetry: Dict[str, Any]) -> Dict[str, Any]:
    thresholds = {0: 0.9, 1: 0.95, 2: 0.9, 3: 0.92, 4: 0.88, 5: 0.95, 6: 0.99, 7: 0.9, 8: 0.95}
    score = telemetry.get("score", 0.0)
    passed = score >= thresholds.get(gate_id, 0.9)
    return {
        "gate_id": gate_id,
        "score": score,
        "passed": passed,
        "status": "approved" if passed else "rejected"
    }
""", encoding="utf-8")

    (be_dir / "orchestrator.py").write_text("""\"\"\"Multi-agent MAF orchestrator.\"\"\"
class MAFOrchestrator:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.agents = ["business-analyst", "requirements-analyst", "principal-test-architect"]

    def dispatch(self, task_name: str) -> dict:
        return {"project_id": self.project_id, "task": task_name, "status": "dispatched"}
""", encoding="utf-8")

    # 8. frontend code
    fe_dir = repo / "frontend" / "src"
    fe_dir.mkdir(parents=True, exist_ok=True)
    (fe_dir / "index.ts").write_text("""export interface Gate {
  id: number;
  name: str;
  status: 'pending' | 'approved' | 'rejected';
  score: number;
}
""", encoding="utf-8")

    (fe_dir / "QualityGates.tsx").write_text("""import React from 'react';

export function QualityGates({ gates }: { gates: any[] }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {gates.map((g) => (
        <div key={g.id} className="p-4 border rounded shadow-sm">
          <h3 className="font-bold text-lg">{g.name}</h3>
          <p className="text-sm text-gray-600">Status: {g.status}</p>
        </div>
      ))}
    </div>
  );
}
""", encoding="utf-8")

    # 9. tests
    tests_dir = repo / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    (tests_dir / "test_gates.py").write_text("""import pytest
from backend.app.gates import evaluate_gate

def test_gate_evaluation_passed():
    res = evaluate_gate(0, {"score": 0.95})
    assert res["passed"] is True
    assert res["status"] == "approved"

def test_gate_evaluation_rejected():
    res = evaluate_gate(1, {"score": 0.80})
    assert res["passed"] is False
    assert res["status"] == "rejected"
""", encoding="utf-8")

    (tests_dir / "test_api.py").write_text("""from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_list_gates():
    res = client.get("/api/gates")
    assert res.status_code == 200
    assert len(res.json()) == 9
""", encoding="utf-8")

    e2e_dir = tests_dir / "e2e"
    e2e_dir.mkdir(parents=True, exist_ok=True)
    (e2e_dir / "harness.spec.ts").write_text("""import { test, expect } from '@playwright/test';

test('verify gate summary loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toContainText('Agentic QE');
});
""", encoding="utf-8")

    commit = init_git(repo, "feat: Initial commit for Agentic QE Platform and Framework harness")
    print(f"prj_agentic_qe initialized at commit {commit}")
    return commit


def populate_fintech_gateway():
    repo = PROJECTS_DIR / "prj_fintech_gateway" / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    # 1. README.md
    (repo / "README.md").write_text("""# Zero-Trust Financial Gateway

High-throughput payment orchestration and tokenization engine with PCI-DSS compliance.
- Zero-trust tokenization vault with cryptographic PAN isolation
- Strict idempotency key enforcement and distributed replay defense
- Comprehensive transaction lifecycle: Authorize, Capture, Void, and Refund
""", encoding="utf-8")

    # 2. .gitignore
    (repo / ".gitignore").write_text("""__pycache__/
*.pyc
.env
.pytest_cache/
.coverage
""", encoding="utf-8")

    # 3. requirements.txt
    (repo / "requirements.txt").write_text("""fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
pytest>=8.0.0
httpx>=0.27.0
cryptography>=42.0.0
sqlalchemy>=2.0.0
""", encoding="utf-8")

    # 4. pyproject.toml
    (repo / "pyproject.toml").write_text("""[project]
name = "fintech-zero-trust-gateway"
version = "1.0.0"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn>=0.28.0",
    "pydantic>=2.6.0",
    "cryptography>=42.0.0",
    "sqlalchemy>=2.0.0"
]

[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "httpx>=0.27.0"
]
""", encoding="utf-8")

    # 5. CI workflow
    ci_dir = repo / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    (ci_dir / "ci.yml").write_text("""name: Fintech Gateway CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Pytest
        run: pytest
""", encoding="utf-8")

    # 6. Source code
    src_dir = repo / "src" / "gateway"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "__init__.py").write_text("", encoding="utf-8")

    (src_dir / "main.py").write_text("""from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid

app = FastAPI(title="Zero-Trust Financial Gateway", version="1.0.0")

class TokenizeRequest(BaseModel):
    card_number: str
    exp_month: int
    exp_year: int
    cvv: str

class PaymentRequest(BaseModel):
    token: str
    amount: float
    currency: str = "USD"
    reference_id: str

TOKENS_STORE = {}
TXN_STORE = {}

@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "fintech-gateway"}

@app.post("/api/v1/tokens/tokenize")
def tokenize_card(req: TokenizeRequest) -> Dict[str, str]:
    token = f"tok_{uuid.uuid4().hex[:16]}"
    masked = f"****-****-****-{req.card_number[-4:]}"
    TOKENS_STORE[token] = {"masked": masked, "exp": f"{req.exp_month}/{req.exp_year}"}
    return {"token": token, "masked_card": masked}

@app.post("/api/v1/payments/authorize")
def authorize_payment(req: PaymentRequest, x_idempotency_key: Optional[str] = Header(None)) -> Dict[str, Any]:
    if req.token not in TOKENS_STORE:
        raise HTTPException(status_code=400, detail="Invalid payment token")
    if req.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    txn_id = f"txn_{uuid.uuid4().hex[:12]}"
    txn = {
        "transaction_id": txn_id,
        "token": req.token,
        "amount": req.amount,
        "currency": req.currency,
        "status": "authorized"
    }
    TXN_STORE[txn_id] = txn
    return txn

@app.post("/api/v1/payments/capture")
def capture_payment(txn_id: str) -> Dict[str, Any]:
    if txn_id not in TXN_STORE:
        raise HTTPException(status_code=404, detail="Transaction not found")
    TXN_STORE[txn_id]["status"] = "captured"
    return TXN_STORE[txn_id]

@app.get("/api/v1/transactions/{transaction_id}")
def get_transaction(transaction_id: str) -> Dict[str, Any]:
    if transaction_id not in TXN_STORE:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TXN_STORE[transaction_id]
""", encoding="utf-8")

    (src_dir / "vault.py").write_text("""\"\"\"Zero-Trust Token Vault.\"\"\"
import hashlib
import os

class TokenVault:
    def __init__(self, secret_key: bytes | None = None):
        self.secret_key = secret_key or os.urandom(32)

    def mask_pan(self, pan: str) -> str:
        clean = "".join(c for c in pan if c.isdigit())
        if len(clean) < 4:
            return "****"
        return f"{'*' * (len(clean) - 4)}{clean[-4:]}"

    def generate_token(self, pan: str) -> str:
        digest = hashlib.sha256(self.secret_key + pan.encode()).hexdigest()
        return f"tok_{digest[:24]}"
""", encoding="utf-8")

    (src_dir / "idempotency.py").write_text("""\"\"\"Idempotency key enforcement.\"\"\"
from typing import Dict, Any

class IdempotencyGuard:
    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def check(self, key: str) -> Any | None:
        return self._cache.get(key)

    def store(self, key: str, response: Any) -> None:
        self._cache[key] = response
""", encoding="utf-8")

    # 7. tests
    tests_dir = repo / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")

    (tests_dir / "test_payments.py").write_text("""from fastapi.testclient import TestClient
from src.gateway.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "fintech-gateway"

def test_tokenize_and_authorize():
    tok_res = client.post("/api/v1/tokens/tokenize", json={
        "card_number": "4111111111111234",
        "exp_month": 12,
        "exp_year": 2028,
        "cvv": "123"
    })
    assert tok_res.status_code == 200
    token = tok_res.json()["token"]
    assert token.startswith("tok_")

    pay_res = client.post("/api/v1/payments/authorize", json={
        "token": token,
        "amount": 99.50,
        "currency": "USD",
        "reference_id": "order_123"
    })
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "authorized"
""", encoding="utf-8")

    (tests_dir / "test_vault.py").write_text("""from src.gateway.vault import TokenVault

def test_pan_masking():
    vault = TokenVault()
    masked = vault.mask_pan("4111222233334444")
    assert masked.endswith("4444")
    assert "4111" not in masked

def test_token_generation():
    vault = TokenVault(b"test_key_32_bytes_long_123456789")
    tok1 = vault.generate_token("4111222233334444")
    tok2 = vault.generate_token("4111222233334444")
    assert tok1 == tok2
    assert tok1.startswith("tok_")
""", encoding="utf-8")

    commit = init_git(repo, "feat: Initial commit for Zero-Trust Financial Gateway and Token Vault")
    print(f"prj_fintech_gateway initialized at commit {commit}")
    return commit


def populate_ecommerce_core():
    repo = PROJECTS_DIR / "prj_ecommerce_core" / "repo"
    repo.mkdir(parents=True, exist_ok=True)

    # 1. README.md
    (repo / "README.md").write_text("""# Enterprise Cloud Checkout Service

Global distributed shopping cart, inventory locking, and multi-currency checkout engine.
- High-concurrency cart synchronization with Redis TTL
- Distributed inventory reservations with auto-expiring locks
- Multi-currency rate conversion and dynamic tax computation
""", encoding="utf-8")

    # 2. .gitignore
    (repo / ".gitignore").write_text("""node_modules/
dist/
coverage/
.env
""", encoding="utf-8")

    # 3. package.json
    (repo / "package.json").write_text(json.dumps({
        "name": "ecommerce-core-checkout",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "build": "tsc",
            "start": "node dist/server.js",
            "test": "vitest run"
        },
        "dependencies": {
            "express": "^4.19.0",
            "redis": "^4.6.0",
            "zod": "^3.23.0"
        },
        "devDependencies": {
            "@types/express": "^4.17.0",
            "@types/node": "^20.12.0",
            "typescript": "^5.4.0",
            "vitest": "^1.6.0"
        }
    }, indent=2), encoding="utf-8")

    # 4. tsconfig.json
    (repo / "tsconfig.json").write_text(json.dumps({
        "compilerOptions": {
            "target": "ES2022",
            "module": "commonjs",
            "rootDir": "./src",
            "outDir": "./dist",
            "strict": True,
            "esModuleInterop": True
        },
        "include": ["src/**/*"]
    }, indent=2), encoding="utf-8")

    # 5. CI workflow
    ci_dir = repo / ".github" / "workflows"
    ci_dir.mkdir(parents=True, exist_ok=True)
    (ci_dir / "ci.yml").write_text("""name: Checkout Core CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install dependencies
        run: npm install
      - name: Run Vitest
        run: npm test
""", encoding="utf-8")

    # 6. Source code
    src_dir = repo / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "server.ts").write_text("""import express, { Request, Response } from 'express';
import { CartService } from './cart/service';
import { InventoryLock } from './inventory/lock';

export const app = express();
app.use(express.json());

const cartService = new CartService();
const inventoryLock = new InventoryLock();

app.get('/api/health', (req: Request, res: Response) => {
  res.json({ status: 'ok', service: 'ecommerce-checkout' });
});

app.post('/api/cart/items', async (req: Request, res: Response) => {
  const { cartId, productId, quantity, price } = req.body;
  const cart = await cartService.addItem(cartId, productId, quantity, price);
  res.json(cart);
});

app.get('/api/cart/:cartId', async (req: Request, res: Response) => {
  const cart = await cartService.getCart(req.params.cartId);
  res.json(cart);
});

app.post('/api/inventory/lock', async (req: Request, res: Response) => {
  const { productId, quantity, holdSeconds } = req.body;
  const lock = await inventoryLock.acquireLock(productId, quantity, holdSeconds || 600);
  res.json(lock);
});

app.post('/api/checkout/session', async (req: Request, res: Response) => {
  const { cartId, currency } = req.body;
  res.json({ sessionId: `chk_${Date.now()}`, cartId, currency, status: 'ready' });
});
""", encoding="utf-8")

    cart_dir = src_dir / "cart"
    cart_dir.mkdir(parents=True, exist_ok=True)
    (cart_dir / "service.ts").write_text("""export interface CartItem {
  productId: string;
  quantity: number;
  price: number;
}

export class CartService {
  private carts: Map<string, CartItem[]> = new Map();

  async addItem(cartId: string, productId: string, quantity: number, price: number) {
    const items = this.carts.get(cartId) || [];
    items.push({ productId, quantity, price });
    this.carts.set(cartId, items);
    return { cartId, items, total: items.reduce((sum, i) => sum + i.price * i.quantity, 0) };
  }

  async getCart(cartId: string) {
    const items = this.carts.get(cartId) || [];
    return { cartId, items, total: items.reduce((sum, i) => sum + i.price * i.quantity, 0) };
  }
}
""", encoding="utf-8")

    inv_dir = src_dir / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)
    (inv_dir / "lock.ts").write_text("""export class InventoryLock {
  private locks: Map<string, number> = new Map();

  async acquireLock(productId: string, quantity: number, holdSeconds: number) {
    const current = this.locks.get(productId) || 0;
    this.locks.set(productId, current + quantity);
    return { productId, lockedQuantity: quantity, expiresAt: Date.now() + holdSeconds * 1000 };
  }
}
""", encoding="utf-8")

    # 7. tests
    tests_dir = repo / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "cart.test.ts").write_text("""import { describe, it, expect } from 'vitest';
import { CartService } from '../src/cart/service';

describe('CartService', () => {
  it('adds items and calculates total correctly', async () => {
    const service = new CartService();
    const result = await service.addItem('cart_1', 'item_101', 2, 19.99);
    expect(result.items.length).toBe(1);
    expect(result.total).toBeCloseTo(39.98);
  });
});
""", encoding="utf-8")

    commit = init_git(repo, "feat: Initial commit for Enterprise Cloud Checkout and Distributed Cart Service")
    print(f"prj_ecommerce_core initialized at commit {commit}")
    return commit


def sync_db_records():
    """Scan each repo and update repo_sources with complete analysis and real commit."""
    from backend.repos import scan, git
    import datetime

    projects = ["prj_agentic_qe", "prj_fintech_gateway", "prj_ecommerce_core", "prj_mcp_market"]
    con = sqlite3.connect(str(DB_PATH))
    cur = con.cursor()

    for pid in projects:
        rdir = PROJECTS_DIR / pid / "repo"
        if not rdir.exists():
            print(f"Skipping {pid}: repo_dir does not exist")
            continue

        analysis = scan.analyze(rdir)
        commit = git.head(rdir)
        now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Update or insert into repo_sources
        cur.execute(
            "INSERT OR REPLACE INTO repo_sources (project_id, kind, url, ref, credential_id, commit_sha, analysis, scanned_at) "
            "VALUES (?, ?, (SELECT url FROM repo_sources WHERE project_id=?), 'main', NULL, ?, ?, ?)",
            (pid, "git", pid, commit, json.dumps(analysis), now_ts)
        )
        print(f"Updated repo_sources for {pid}: commit={commit[:7]}, files={analysis['total_files']}, languages={list(analysis['languages'].keys())}")

    con.commit()
    con.close()


if __name__ == "__main__":
    populate_agentic_qe()
    populate_fintech_gateway()
    populate_ecommerce_core()
    sync_db_records()
    print("All seeded projects successfully populated and synchronized!")
