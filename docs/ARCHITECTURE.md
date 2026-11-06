# Platform Architecture & System Design Pointer

> [!IMPORTANT]
> The architectural documentation across this repository has been consolidated into a single canonical, production-grade document:
>
> **👉 [System Architecture, Design & Specification (`docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`)](./SYSTEM_ARCHITECTURE_AND_DESIGN.md)**

Please refer to [`docs/SYSTEM_ARCHITECTURE_AND_DESIGN.md`](./SYSTEM_ARCHITECTURE_AND_DESIGN.md) for the complete, canonical architecture and system design, including:
- High-level platform architecture and Next.js / FastAPI full-stack design
- Microsoft Agent Framework (MAF 2.0) orchestration engine, workflow definitions, and checkpoint durability
- Repository AST Discovery, Code Packs, and AST Symbol Extraction
- Dual-layer sandboxing: isolated Git worktrees and `clean_env` credential scrubbing
- Autonomous QE Lifecycle pipeline: Intake (G0), Discovery, Requirements (G1), Test Plan (G2), Test Design & Data (G3), Test Code Generation (G4), Prepare, Execute, Self-Healing, Traceability, Release Sign-off (G5)
- Component interaction flow diagrams (Mermaid) and data models
- Complete consolidated functional and non-functional requirements traceability matrix (PRJ, BA, GOV, REP, BUG, CHG, QE, CHAT, AGT, ARC, DEP, SBX, NAV, DOC, USR, ACC, LIVE, OBS, RUN, NF, SKL, INT, ERR, OPS, MDL, ROL, PLG, CNF, TST, EVL).
