#!/usr/bin/env python3
"""Packaging tool for Agent Skills. Validates structure and creates distribution ZIP."""
from __future__ import annotations

import argparse
import json
import os
import zipfile
from pathlib import Path


def package_skill(skill_dir: Path, out_zip: Path | None = None) -> dict:
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")

    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        raise ValueError(f"SKILL.md missing in {skill_dir}")

    content = skill_md.read_text(encoding="utf-8")
    if not content.startswith("---"):
        raise ValueError(f"Invalid frontmatter in {skill_md}")

    skill_name = skill_dir.name
    zip_path = out_zip or (skill_dir.parent / f"{skill_name}.zip")

    files_added = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(skill_dir):
            for file in files:
                if file.endswith((".pyc", ".DS_Store")) or "__pycache__" in root:
                    continue
                full_path = Path(root) / file
                rel_path = full_path.relative_to(skill_dir)
                zf.write(full_path, arcname=str(rel_path))
                files_added.append(str(rel_path))

    return {
        "status": "packaged",
        "skill": skill_name,
        "zip_path": str(zip_path),
        "file_count": len(files_added),
        "files": files_added,
    }


def main():
    parser = argparse.ArgumentParser(description="Package an Agent Skill into a ZIP bundle")
    parser.add_argument("--skill-dir", required=True, help="Path to skill folder")
    parser.add_argument("--out", default=None, help="Output ZIP file path")
    args = parser.parse_args()

    result = package_skill(Path(args.skill_dir), Path(args.out) if args.out else None)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
