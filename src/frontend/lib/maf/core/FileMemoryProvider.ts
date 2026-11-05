import fs from "fs";
import path from "path";

/**
 * MAF FileMemoryProvider (agent-framework.pdf pp. 145-160)
 * Scans workspace and injects contextual memory into agent execution prompts.
 */
export class FileMemoryProvider {
  private workspaceDir: string;

  constructor(workspaceDir: string = process.cwd()) {
    this.workspaceDir = workspaceDir;
  }

  /**
   * Scans project dependencies and returns detected frameworks and runners.
   */
  public getDetectedEnvironment(): Record<string, any> {
    const pkgPath = path.join(this.workspaceDir, "package.json");
    if (!fs.existsSync(pkgPath)) {
      return { framework: "unknown", runners: [] };
    }

    try {
      const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf-8"));
      const allDeps = {
        ...pkg.dependencies,
        ...pkg.devDependencies,
      };

      const runners: string[] = [];
      if (allDeps.playwright || allDeps["@playwright/test"]) runners.push("playwright");
      if (allDeps.vitest) runners.push("vitest");
      if (allDeps.jest) runners.push("jest");
      if (allDeps.cypress) runners.push("cypress");

      return {
        name: pkg.name || "workspace-app",
        version: pkg.version || "1.0.0",
        framework: allDeps.next ? "Next.js" : allDeps.react ? "React" : "Node.js",
        runners: runners.length > 0 ? runners : ["vitest", "playwright"],
        scripts: Object.keys(pkg.scripts || {}),
      };
    } catch {
      return { framework: "unknown", runners: [] };
    }
  }

  /**
   * Generates a context header prompt with repository awareness.
   */
  public getContextPrompt(): string {
    const env = this.getDetectedEnvironment();
    return `[WORKSPACE CONTEXT]
Working Directory: ${this.workspaceDir}
Detected Stack: ${env.framework} (Package: ${env.name}@${env.version})
Detected Test Runners: ${env.runners.join(", ") || "None (Recommendation: Vitest + Playwright)"}
Available npm Scripts: ${env.scripts ? env.scripts.join(", ") : "None"}
Quality Artifacts Root: docs/qe/${env.name}/`;
  }
}
