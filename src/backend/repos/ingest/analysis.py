"""Normalising stored repository analysis."""
from __future__ import annotations

from pathlib import Path
from backend.repos import scan


def normalize_analysis(analysis: dict | None, root: Path | None = None) -> dict:
    """Normalize repository analysis dict so all expected keys always exist with safe defaults."""
    if not isinstance(analysis, dict):
        analysis = {}

    mode = analysis.get("mode") or "brownfield"

    # Languages: normalize to dict {str: int}
    raw_langs = analysis.get("languages")
    if isinstance(raw_langs, dict):
        languages = {str(k): int(v) if isinstance(v, (int, float)) else 1 for k, v in raw_langs.items()}
    elif isinstance(raw_langs, list):
        languages = {str(k): 1 for k in raw_langs if k}
    else:
        languages = {}

    # Lines of code and file counts: stored values, or counted from the files on disk; never estimated
    raw_loc = analysis.get("lines_of_code")
    lines_of_code = {str(k): int(v) for k, v in raw_loc.items() if isinstance(v, (int, float))} if isinstance(raw_loc, dict) else {}
    test_files = list(analysis.get("test_files") or []) if isinstance(analysis.get("test_files"), list) else []
    test_file_count = int(analysis.get("test_file_count") if analysis.get("test_file_count") is not None else len(test_files))
    total_files = int(analysis.get("total_files") or 0)
    source_files = int(analysis.get("source_files") or 0)
    if root and root.is_dir() and not (lines_of_code and total_files and source_files):
        counted_loc, counted_total, counted_source = {}, 0, 0
        for path in scan.iter_files(root):  # ponytail: reads each file once; fine for repos the platform ingests
            counted_total += 1
            language = scan.LANGUAGES.get(path.suffix.lower())
            if language:
                counted_source += 1
                with path.open("rb") as handle:
                    counted_loc[language] = counted_loc.get(language, 0) + sum(1 for _ in handle)
        lines_of_code = lines_of_code or counted_loc
        total_files = total_files or counted_total
        source_files = source_files or counted_source

    # Lists
    frameworks = list(analysis.get("frameworks") or []) if isinstance(analysis.get("frameworks"), list) else []
    test_runners = list(analysis.get("test_runners") or []) if isinstance(analysis.get("test_runners"), list) else []
    routes = list(analysis.get("routes") or []) if isinstance(analysis.get("routes"), list) else []
    ci = list(analysis.get("ci") or []) if isinstance(analysis.get("ci"), list) else []
    entrypoints = list(analysis.get("entrypoints") or []) if isinstance(analysis.get("entrypoints"), list) else []
    docs = list(analysis.get("docs") or []) if isinstance(analysis.get("docs"), list) else []

    # Manifests
    manifests = analysis.get("manifests")
    if not isinstance(manifests, dict):
        manifests = {
            "dependencies": analysis.get("dependencies", {}) if isinstance(analysis.get("dependencies"), dict) else {},
            "scripts": analysis.get("scripts", {}) if isinstance(analysis.get("scripts"), dict) else {},
        }

    # Top imports: always a list
    raw_imports = analysis.get("top_imports")
    if isinstance(raw_imports, list):
        top_imports = raw_imports
    elif isinstance(raw_imports, dict):
        top_imports = list(raw_imports.keys())
    else:
        top_imports = []

    normalized = {
        **analysis,
        "mode": str(mode),
        "total_files": total_files,
        "source_files": source_files,
        "test_file_count": test_file_count,
        "test_files": test_files,
        "languages": languages,
        "lines_of_code": lines_of_code,
        "frameworks": frameworks,
        "test_runners": test_runners,
        "routes": routes,
        "ci": ci,
        "entrypoints": entrypoints,
        "manifests": manifests,
        "docs": docs,
        "top_imports": top_imports,
    }
    return normalized


def _is_partial_analysis(analysis: dict | None) -> bool:
    if not analysis or not isinstance(analysis, dict):
        return True
    if not analysis.get("lines_of_code"):
        return True
    if not analysis.get("source_files") or not analysis.get("total_files"):
        return True
    for key in ("mode", "languages", "frameworks", "test_runners", "test_files", "routes", "ci", "entrypoints"):
        if key not in analysis:
            return True
    return False
