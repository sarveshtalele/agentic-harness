# Created 2026-11-03 15:50 IST by agentic-qe 1.6.0.
"""Validates a QE run with pandas and numpy: plan, design, generated tests and results, gate by gate.

Reads one JSON object on stdin, {"gate": N, "coverage": {...}} (built by hooks/src/coverage.ts from the documents on disk),
and prints one JSON verdict. Exact checks are pandas joins (anti-joins find what is missing); statistical checks use numpy
(score inflation, distribution drift, thin tests); a TF-IDF model built with numpy marks cases that do not read like the
scenario they claim, so the coverage-auditor reviews those first and the hand-off to the model stays short.

usage: python qe_validate.py < bundle.json        python qe_validate.py --probe   (prints versions; exit 0 when usable)
"""
from __future__ import annotations

import json
import re
import sys

import numpy as np
import pandas as pd

VERSION = "1.6.0"
LEVELS = ["Unit", "Integration", "E2E"]
SCENARIO_ID = re.compile(r"^SC-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3,}$")
SUSPECT_BELOW = 0.08   # cosine similarity of a case to its scenario under which the pair is "suspect"
DUPLICATE_AT = 0.95    # near-duplicate cases or scenarios
DRIFT_ABOVE = 0.25     # designed share of an area minus its planned share
THIN_BELOW = 0.25      # assertions under this fraction of the level's median
PAIRWISE_MAX = 1500    # duplicate search is n x n; above this many rows it is skipped (and said so in the metrics)
STOP = set("a an the and or of to in on for with by is are be as at from that this it its into not no when then given user users system should must can will".split())


def frame(rows, cols):
    """A table with at least these columns (missing fields become None)."""
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=cols)
    for c in cols:
        if c not in df.columns:
            df[c] = None
    return df


def id_ranges(ids, limit=400):
    """SC-API-004, SC-API-005, ... -> SC-API-004..006: the long id lists the model reads become short."""
    out, groups = [], {}
    for i in sorted(set(ids)):
        m = re.match(r"^(.*?)(\d+)$", i)
        if not m:
            out.append(i)
            continue
        groups.setdefault(m.group(1), []).append((int(m.group(2)), len(m.group(2))))
    for prefix, nums in groups.items():
        nums.sort()
        start = prev = nums[0]
        for n in nums[1:] + [None]:
            if n is not None and n[0] == prev[0] + 1:
                prev = n
                continue
            fmt = lambda x: f"{prefix}{str(x[0]).zfill(x[1])}"
            out.append(fmt(start) if start == prev else f"{fmt(start)}..{fmt(prev)}")
            if n is not None:
                start = prev = n
    out.sort()
    return out[:limit] + ([f"... {len(out) - limit} more"] if len(out) > limit else [])


def tokens(text):
    return [w for w in re.findall(r"[a-z][a-z0-9]+", str(text).lower()) if w not in STOP and len(w) > 1]


def tfidf(texts):
    """TF-IDF vectors (rows L2-normalised) for a list of texts, numpy only."""
    docs = [tokens(t) for t in texts]
    vocab = {w: i for i, w in enumerate(sorted({w for d in docs for w in d}))}
    if not vocab:
        return np.zeros((len(texts), 1))
    m = np.zeros((len(docs), len(vocab)))
    for r, d in enumerate(docs):
        for w in d:
            m[r, vocab[w]] += 1.0
    df = (m > 0).sum(axis=0)
    idf = np.log((1 + len(docs)) / (1 + df)) + 1.0
    m = m * idf
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms


class Report:
    def __init__(self, gate):
        self.gate, self.errors, self.warnings, self.metrics, self.suspects, self.groups = gate, [], [], {}, [], []

    def error(self, check, message, ids=()):
        self.errors.append({"check": check, "message": message, "ids": id_ranges(list(ids))})

    def warn(self, check, message, ids=()):
        self.warnings.append({"check": check, "message": message, "ids": id_ranges(list(ids))})

    def out(self):
        brief = [f"Gate {self.gate} validation: {'PASS' if not self.errors else 'FAIL'} ({len(self.errors)} errors, {len(self.warnings)} warnings)."]
        for e in self.errors[:12]:
            brief.append(f"- {e['message']}" + (f": {', '.join(e['ids'][:30])}" if e["ids"] else ""))
        if self.suspects:
            brief.append(f"Audit these case/scenario pairs first (low similarity): {', '.join(s['case'] for s in self.suspects[:20])}")
        return {"validator": VERSION, "gate": self.gate, "ok": not self.errors, "errors": self.errors, "warnings": self.warnings,
                "metrics": self.metrics, "suspects": self.suspects, "duplicates": self.groups, "brief": "\n".join(brief)}


def inflated(reviews):
    """True when a set of reviews looks hand-tuned rather than measured: every total 100 and no spread in any dimension."""
    if len(reviews) < 5:
        return False
    totals = np.array([r.get("total", np.nan) for r in reviews], dtype=float)
    if np.isnan(totals).any() or not np.all(totals == 100):
        return False
    dims = pd.DataFrame([r.get("scores", {}) for r in reviews]).apply(pd.to_numeric, errors="coerce")
    return dims.empty or bool((dims.std(ddof=0).fillna(0) == 0).all())


def validate(gate, cov):
    rep = Report(gate)
    req = frame(cov.get("requirements", []), ["id", "priority", "evidence", "text"])
    sc = frame(cov.get("scenarios", []), ["id", "area", "level", "priority", "requirementIds", "text"])
    cs = frame(cov.get("cases", []), ["id", "scenarioIds", "level", "type", "text", "audit", "codeAudit"])
    ts = frame(cov.get("tests", []), ["path", "caseIds", "exists", "markers", "tests", "assertions", "level"])
    results = cov.get("results", {})
    inv = cov.get("inventory", {})
    rep.metrics.update({"requirements": len(req), "scenarios": len(sc), "cases": len(cs), "test_files": len(ts), "results": len(results),
                        "repo_test_files": inv.get("files", 0), "repo_tests": inv.get("tests", 0), "existing": inv.get("existing", 0),
                        "generated": inv.get("generated", 0), "manual": inv.get("manual", 0)})

    # ---- Gate 1: requirements
    if gate >= 1:
        if req.empty:
            rep.error("requirements.present", "no requirements in 02-requirements/requirements.json")
        else:
            dup = req[req["id"].duplicated(keep=False)]["id"].unique()
            if len(dup):
                rep.error("requirements.unique", "duplicate requirement ids", dup)
            if "evidence" in req:
                rep_ids = req.loc[~req["evidence"].fillna(False).astype(bool), "id"]
                if len(rep_ids):
                    rep.error("requirements.evidence", "requirements without source evidence", rep_ids)
            bad = req[~req["priority"].fillna("").astype(str).str.upper().isin(["P0", "P1", "P2", "P3", "CRITICAL", "HIGH", "MEDIUM", "LOW"])]
            if len(bad):
                rep.warn("requirements.priority", "requirements with no P0-P3 priority (treated as P0/P1)", bad["id"])

    # ---- Gate 2: plan
    if gate >= 2:
        if sc.empty:
            rep.error("plan.scenarios", 'plan.json lists no scenarios with ids (SC-<AREA>-NNN)')
        else:
            bad_id = sc[~sc["id"].astype(str).str.match(SCENARIO_ID)]["id"]
            if len(bad_id):
                rep.error("plan.ids", "scenario ids not in the form SC-<AREA>-NNN", bad_id)
            dup = sc[sc["id"].duplicated(keep=False)]["id"].unique()
            if len(dup):
                rep.error("plan.unique", "duplicate scenario ids", dup)
            no_level = sc[~sc["level"].isin(LEVELS)]["id"]
            if len(no_level):
                rep.error("plan.level", "scenarios without a level", no_level)
            declared = cov.get("declaredScenarios")
            if declared is not None and declared != len(sc):
                rep.error("plan.total", f"the plan says {declared} scenarios but lists {len(sc)}")
            skipped = {str(s.get("level", "")).lower() for s in cov.get("skippedLevels", []) if len(str(s.get("reason", "")).strip()) >= 10}
            for lv in LEVELS:
                if not (sc["level"] == lv).any() and lv.lower() not in skipped and not (lv == "E2E" and "e2e" in skipped):
                    rep.error("plan.levels", f"no {lv} scenarios and no written reason in plan.skippedLevels")
            # requirement -> scenario anti-join
            links = sc[["id", "requirementIds"]].explode("requirementIds").dropna()
            covered = set(links["requirementIds"])
            if not req.empty:
                high = req["priority"].fillna("").astype(str).str.upper().isin(["", "P0", "P1", "CRITICAL", "HIGH"])
                missing_high = req[high & ~req["id"].isin(covered)]["id"]
                if len(missing_high):
                    rep.error("plan.requirements", "P0/P1 requirements with no plan scenario", missing_high)
                missing_low = req[~high & ~req["id"].isin(covered)]["id"]
                if len(missing_low):
                    rep.warn("plan.requirements", "P2/P3 requirements with no plan scenario", missing_low)
            unknown = links[~links["requirementIds"].isin(set(req["id"]))]["id"].unique() if not req.empty else []
            if len(unknown):
                rep.error("plan.links", "scenarios naming a requirement id that does not exist", unknown)
            pivot = sc.pivot_table(index="area", columns="level", values="id", aggfunc="count", fill_value=0)
            rep.metrics["plan_by_area_level"] = {a: {k: int(v) for k, v in row.items()} for a, row in pivot.iterrows()}
            # near-duplicate scenarios
            if 1 < len(sc) <= PAIRWISE_MAX and sc["text"].fillna("").str.len().sum():
                v = tfidf(sc["text"].fillna("").tolist())
                sim = v @ v.T
                np.fill_diagonal(sim, 0)
                pairs = np.argwhere(np.triu(sim) >= DUPLICATE_AT)
                if len(pairs):
                    rep.warn("plan.duplicates", "scenarios that read the same (merge them or tell them apart)", [sc["id"].iat[int(i)] for p in pairs for i in p])

    # ---- Gate 3: design
    if gate >= 3:
        links = cs[["id", "scenarioIds"]].explode("scenarioIds").dropna() if not cs.empty else pd.DataFrame(columns=["id", "scenarioIds"])
        designed = set(links["scenarioIds"])
        if not sc.empty:
            undesigned = sc[~sc["id"].isin(designed)]
            if len(undesigned):
                rep.error("design.coverage", f"plan scenarios with no designed case ({len(sc) - len(undesigned)} of {len(sc)} designed)", undesigned["id"])
            per_area = sc.assign(designed=sc["id"].isin(designed)).groupby("area")["designed"].agg(["sum", "count"])
            rep.metrics["design_coverage_by_area"] = {a: round(100.0 * r["sum"] / r["count"], 1) for a, r in per_area.iterrows()}
            empty_areas = [a for a, r in per_area.iterrows() if r["sum"] == 0]
            if empty_areas:
                rep.error("design.areas", "plan areas with no designed case at all", empty_areas)
        unknown = links[~links["scenarioIds"].isin(set(sc["id"]))]["id"].unique() if not sc.empty else links["id"].unique()
        no_link = cs[cs["scenarioIds"].apply(lambda v: not v)]["id"] if not cs.empty else []
        if len(unknown) or len(no_link):
            rep.error("design.links", "cases whose planScenarioIds are missing or not in the plan", list(unknown) + list(no_link))
        if not cs.empty and not sc.empty:
            j = links.merge(sc[["id", "area", "level", "text"]].rename(columns={"id": "scenarioIds", "level": "planLevel", "text": "scenarioText"}), on="scenarioIds", how="inner")
            j = j.merge(cs[["id", "level", "type", "text"]], on="id", how="left")
            # every area with 3 or more scenarios needs positive, negative and boundary cases
            types = j.assign(t=j["type"].fillna("").astype(str).str.lower()).groupby("area")["t"].agg(lambda s: set(" ".join(s).replace("(", " ").replace(")", " ").split()))
            sizes = sc.groupby("area")["id"].count()
            for area, have in types.items():
                if sizes.get(area, 0) >= 3:
                    lack = [t for t in ("positive", "negative", "boundary") if t not in have]
                    if lack:
                        rep.error("design.types", f"area {area} has no {', '.join(lack)} case", [area])
            mism = j[(j["level"].notna()) & (j["planLevel"].notna()) & (j["level"] != j["planLevel"])]["id"].unique()
            if len(mism):
                rep.warn("design.level", "cases at a different level from their scenario", mism)
            # design drift: designed share per area against planned share
            planned = sc.groupby("area")["id"].count() / max(1, len(sc))
            designed_share = j.drop_duplicates("id").groupby("area")["id"].count() / max(1, j["id"].nunique())
            drift = (designed_share.reindex(planned.index, fill_value=0) - planned).abs()
            drifting = drift[drift > DRIFT_ABOVE].index.tolist()
            if drifting:
                rep.warn("design.drift", "areas whose share of cases is far from their share of the plan", drifting)
            rep.metrics["cases_per_scenario"] = {"mean": round(float(links.groupby("scenarioIds")["id"].count().mean()), 2) if len(links) else 0.0}
            # similarity model: a case that does not read like its scenario is suspect until the auditor clears it
            texts = j["text"].fillna("").tolist() + j["scenarioText"].fillna("").tolist()
            if any(texts):
                v = tfidf(texts)
                n = len(j)
                sims = np.einsum("ij,ij->i", v[:n], v[n:])
                j = j.assign(similarity=np.round(sims, 3))
                has_text = (j["text"].fillna("").str.len() > 0) & (j["scenarioText"].fillna("").str.len() > 0)
                low = j[has_text & (j["similarity"] < SUSPECT_BELOW)]
                audit = dict(zip(cs["id"], cs["audit"])) if "audit" in cs else {}
                for _, r in low.iterrows():
                    rep.suspects.append({"case": r["id"], "scenario": r["scenarioIds"], "similarity": float(r["similarity"]), "audit": audit.get(r["id"])})
                uncleared = [s["case"] for s in rep.suspects if s["audit"] != "COVERS"]
                if uncleared:
                    rep.error("design.suspects", "cases that do not read like their scenario and no auditor verdict COVERS them", uncleared)
                rep.metrics["similarity_median"] = round(float(np.median(sims)), 3) if n else 0.0
            # near-duplicate cases
            if 1 < len(cs) <= PAIRWISE_MAX:
                v = tfidf(cs["text"].fillna("").tolist())
                sim = v @ v.T
                np.fill_diagonal(sim, 0)
                seen, groups = set(), []
                for i in range(len(cs)):
                    if i in seen:
                        continue
                    g = [k for k in np.where(sim[i] >= DUPLICATE_AT)[0] if k not in seen]
                    if g:
                        seen.update(g + [i])
                        groups.append([cs["id"].iat[i]] + [cs["id"].iat[int(k)] for k in g])
                if groups:
                    rep.groups = groups
                    rep.warn("design.duplicates", f"{len(groups)} groups of near-identical cases", [x for g in groups for x in g])
        if inflated(cov.get("reviews", {}).get("design", [])):
            rep.error("design.reviews", "design reviews look hand-tuned: every total 100 with no spread in any dimension (run the confidence-reviewer again)")

    # ---- Gate 4: generated tests
    if gate >= 4:
        marks = ts[["path", "markers"]].explode("markers").dropna() if not ts.empty else pd.DataFrame(columns=["path", "markers"])
        if not cs.empty:
            ungenerated = cs[~cs["id"].isin(set(marks["markers"]))]["id"]
            if len(ungenerated):
                rep.error("generate.coverage", f"designed cases with no test file naming them ({len(cs) - len(ungenerated)} of {len(cs)} generated)", ungenerated)
            rep.metrics["to_generate"] = int(len(ungenerated))
        foreign = marks[~marks["markers"].isin(set(cs["id"]))]["markers"].unique() if not cs.empty else marks["markers"].unique()
        if len(foreign):
            rep.error("generate.markers", "CASE_ID markers that are not designed case ids", foreign)
        if not ts.empty:
            missing = ts[~ts["exists"].astype(bool)]["path"]
            if len(missing):
                rep.error("generate.files", "manifest lists test files that do not exist", missing)
            existing = ts[ts["exists"].astype(bool)]
            empty = existing[existing["assertions"].fillna(0) == 0]["path"]
            if len(empty):
                rep.error("generate.assertions", "test files with no assertion", empty)
            if len(existing) >= 3:
                med = existing.groupby(existing["level"].fillna("Unit"))["assertions"].transform("median")
                thin = existing[(existing["assertions"] > 0) & (existing["assertions"] < THIN_BELOW * med)]["path"]
                if len(thin):
                    rep.warn("generate.thin", "test files with far fewer assertions than others at their level", thin)
        for p in inv.get("markedNotInManifest", []):
            rep.warn("generate.manifest", "test files that name designed cases but are not in the manifest", [p])
        if inflated(cov.get("reviews", {}).get("code", [])):
            rep.error("generate.reviews", "code reviews look hand-tuned: every total 100 with no spread in any dimension")

    # ---- Gate 5: results
    if gate >= 5 and not cs.empty:
        unrun = cs[~cs["id"].isin(set(results))]["id"]
        if len(unrun):
            rep.error("results.coverage", f"designed cases with no test result ({len(cs) - len(unrun)} of {len(cs)} executed)", unrun)
        failed = [k for k, v in results.items() if str(v).upper() == "FAIL"]
        if failed:
            rep.warn("results.failures", "cases whose latest result is FAIL", failed)
        rep.metrics["passed"] = sum(1 for v in results.values() if str(v).upper() == "PASS")
        rep.metrics["failed"] = len(failed)
    return rep.out()


def main():
    if "--probe" in sys.argv:
        print(json.dumps({"validator": VERSION, "pandas": pd.__version__, "numpy": np.__version__, "python": sys.version.split()[0]}))
        return 0
    bundle = json.load(sys.stdin)
    print(json.dumps(clean(validate(int(bundle.get("gate", 0)), bundle.get("coverage", {}))), allow_nan=False))
    return 0


def clean(v):
    """JSON the Node side can parse: numpy scalars to Python, NaN and infinity to null."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [clean(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        v = v.item()
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return None
    return v if isinstance(v, (str, int, float, bool)) or v is None else str(v)


if __name__ == "__main__":
    sys.exit(main())
