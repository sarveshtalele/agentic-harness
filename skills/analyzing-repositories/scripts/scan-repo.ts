import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { isMain } from "../../../hooks/src/hook-common.ts";

const SKIP_DIRS = new Set(["node_modules", ".git", "dist", "build", ".venv", ".qe", "docs", "bin", "obj"]);
const SOURCE_RE = /\.(ts|tsx|js|jsx|mjs|py|java|go|rs|rb|cs)$/;
const TEST_RE = /(\.(test|spec)\.[a-z]+$|^test_.*\.py$|_test\.(py|go)$|Test\.java$|Tests?\.cs$)/;

/** .NET manifests met while walking: solution files and project files. */
interface DotNet { sln: string[]; csproj: string[] }

function countFiles(dir: string, acc = { source: 0, test: 0 }, net: DotNet = { sln: [], csproj: [] }): { source: number; test: number } {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) {
      if (!SKIP_DIRS.has(e.name)) countFiles(join(dir, e.name), acc, net);
    } else if (/\.(sln|slnx)$/.test(e.name)) net.sln.push(join(dir, e.name));
    else if (e.name.endsWith(".csproj")) net.csproj.push(join(dir, e.name));
    else if (SOURCE_RE.test(e.name)) {
      if (TEST_RE.test(e.name)) acc.test++;
      else acc.source++;
    }
  }
  return acc;
}

export interface ScanResult {
  languages: string[];
  frameworks: string[];
  testRunners: string[];
  manifests: string[];
  sourceFileCount: number;
  testFileCount: number;
  /** brownfield = source or tests exist; greenfield = nothing to scan yet */
  mode: "greenfield" | "brownfield";
}

export function scanRepository(repoPath: string): ScanResult {
  const result: ScanResult = {
    languages: [],
    frameworks: [],
    testRunners: [],
    manifests: [],
    sourceFileCount: 0,
    testFileCount: 0,
    mode: "greenfield"
  };

  if (!existsSync(repoPath)) {
    throw new Error(`Repository path '${repoPath}' does not exist.`);
  }

  const checkPackageJson = (pkgPath: string) => {
    if (existsSync(pkgPath)) {
      result.manifests.push("package.json");
      if (!result.languages.includes("TypeScript")) result.languages.push("TypeScript", "JavaScript");
      try {
        const pkg = JSON.parse(readFileSync(pkgPath, "utf-8"));
        const allDeps = { ...pkg.dependencies, ...pkg.devDependencies };
        if (allDeps.next && !result.frameworks.includes("Next.js")) result.frameworks.push("Next.js");
        if (allDeps.react && !result.frameworks.includes("React")) result.frameworks.push("React");
        if (allDeps.express && !result.frameworks.includes("Express")) result.frameworks.push("Express");
        if (allDeps.vitest && !result.testRunners.includes("vitest")) result.testRunners.push("vitest");
        if (allDeps.jest && !result.testRunners.includes("jest")) result.testRunners.push("jest");
        if (allDeps["@playwright/test"] && !result.testRunners.includes("playwright")) result.testRunners.push("playwright");
      } catch {}
    }
  };

  // Check root and frontend workspace
  checkPackageJson(join(repoPath, "package.json"));
  checkPackageJson(join(repoPath, "frontend/package.json"));

  const pyprojectPath = join(repoPath, "pyproject.toml");
  if (existsSync(pyprojectPath)) {
    result.manifests.push("pyproject.toml");
    if (!result.languages.includes("Python")) result.languages.push("Python");
    if (!result.testRunners.includes("pytest")) result.testRunners.push("pytest");
  }

  const net: DotNet = { sln: [], csproj: [] };
  const counts = countFiles(repoPath, undefined, net);
  // .NET: solution and project files name the language, web framework and test runner (NUnit, xUnit, MSTest via dotnet test)
  if (net.sln.length || net.csproj.length) {
    if (!result.languages.includes("C#")) result.languages.push("C#");
    for (const f of net.sln.slice(0, 5)) result.manifests.push(relative(repoPath, f).replace(/\\/g, "/"));
    if (net.csproj.length) result.manifests.push(`${net.csproj.length} .csproj project${net.csproj.length === 1 ? "" : "s"}`);
    for (const f of net.csproj) {
      let x = "";
      try { x = readFileSync(f, "utf-8"); } catch { continue; }
      if (/Sdk="Microsoft\.NET\.Sdk\.(Web|Razor)"/.test(x) && !result.frameworks.includes("ASP.NET Core")) result.frameworks.push("ASP.NET Core");
      for (const [pkg, runner] of [["NUnit", "nunit"], ["xunit", "xunit"], ["MSTest", "mstest"]] as const)
        if (new RegExp(`PackageReference Include="${pkg}(\\.|")`, "i").test(x) && !result.testRunners.includes(runner)) result.testRunners.push(runner);
    }
    if (result.testRunners.some((r) => ["nunit", "xunit", "mstest"].includes(r)) && !result.testRunners.includes("dotnet test")) result.testRunners.push("dotnet test");
  }
  result.sourceFileCount = counts.source;
  result.testFileCount = counts.test;
  if (counts.source + counts.test > 0 || result.manifests.length > 0) result.mode = "brownfield";

  return result;
}

if (isMain(import.meta.url)) {
  const dir = process.argv[2];
  if (!dir) {
    console.error("usage: node scan-repo.ts <repo-dir>");
    process.exit(2);
  }
  try {
    console.log(JSON.stringify(scanRepository(dir), null, 2));
  } catch (e) {
    console.error((e as Error).message);
    process.exit(1);
  }
}
