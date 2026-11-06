"""
Intent Classifier for Agentic QE Harness.
Auto-classifies user prompts into engineering skills and agent policies.
"""
from typing import Dict, Any


def classify_prompt_intent(prompt: str) -> Dict[str, Any]:
    """
    Auto-classifies user prompt to select the optimal engineering skill and strategy
    without exposing internal persona roles to the UI.
    """
    p = prompt.lower().strip()
    if any(k in p for k in [
        "create skill", "build skill", "new skill", "scaffold skill",
        "make a skill", "skill creator", "skill-creator", "create a skill",
        "create_agent_skill", "scaffold-skill", "create-skill"
    ]):
        return {
            "intent": "Agent Skill Synthesis & Packaging",
            "skill": "skill-creator",
            "agent_id": "test-design-architect",
            "subgoal": "Agent Skill Generation & Packaging",
        }
    if any(k in p for k in ["evaluate skill", "eval skill", "test skill", "benchmark skill", "evaluator", "evaluate_agent_skill"]):
        return {
            "intent": "Agent Skill Deterministic Evaluation",
            "skill": "evaluator",
            "agent_id": "confidence-reviewer",
            "subgoal": "Skill Benchmark Scoring",
        }
    if any(k in p for k in ["brd", "business requirement", "user stor", "acceptance criteria", "gherkin", "spec", "prd"]):
        return {
            "intent": "Requirements & Specifications Baseline",
            "skill": "authoring-user-stories",
            "agent_id": "business-analyst",
            "subgoal": "G1 Requirements Specification",
        }
    if any(k in p for k in ["test plan", "strategy", "risk matrix", "coverage plan", "quality plan"]):
        return {
            "intent": "Test Planning & Level Allocation",
            "skill": "planning-tests",
            "agent_id": "principal-test-architect",
            "subgoal": "G2 Test Plan Formulation",
        }
    if any(k in p for k in ["generate test", "unit test", "integration test", "e2e test", "test case", "playwright", "vitest", "pytest"]):
        return {
            "intent": "Deterministic Test Automation",
            "skill": "designing-test-cases",
            "agent_id": "test-design-architect",
            "subgoal": "G3 & G4 Test Code Generation",
        }
    if any(k in p for k in ["run test", "execute test", "run vitest", "run pytest"]):
        return {
            "intent": "Sandboxed Test Suite Execution",
            "skill": "executing-tests",
            "agent_id": "qa-execution-engineer",
            "subgoal": "G4 Execution & Evidence",
        }
    if any(k in p for k in ["bug", "defect", "heal", "fix", "trace", "failure", "diagnostic", "error"]):
        return {
            "intent": "Defect Diagnosis & Automated Healing",
            "skill": "diagnosing-failures",
            "agent_id": "defect-diagnostician",
            "subgoal": "Selector & Assertion Healing",
        }
    if any(k in p for k in ["security", "specter", "cloudflare", "audit", "cve", "auth bypass", "vulnerability"]):
        return {
            "intent": "Security & Supply Chain Audit",
            "skill": "security-specter",
            "agent_id": "security-compliance-specialist",
            "subgoal": "Security & Gate Verification",
        }
    if any(k in p for k in ["gate", "signoff", "release", "quality gate", "g0", "g1", "g2", "g3", "g4", "g5"]):
        return {
            "intent": "Quality Gate Verification & Sign-off",
            "skill": "evaluating-quality-gates",
            "agent_id": "confidence-reviewer",
            "subgoal": "G5 Release Evaluation",
        }
    return {
        "intent": "Autonomous Quality Engineering",
        "skill": "analyzing-repositories",
        "agent_id": "principal-test-architect",
        "subgoal": "Continuous Quality Optimization",
    }
