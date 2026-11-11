export interface GherkinStep {
  keyword: string; // Given, When, Then, And, But
  text: string;
  table?: string[][];
  docString?: string;
}

export interface GherkinScenario {
  id: string;
  type: "Scenario" | "Scenario Outline";
  name: string;
  tags: string[];
  steps: GherkinStep[];
  examples?: {
    header: string[];
    rows: string[][];
  };
}

export interface ParsedGherkin {
  featureName: string;
  featureDescription: string;
  featureTags: string[];
  background?: {
    steps: GherkinStep[];
  };
  scenarios: GherkinScenario[];
}

export function parseGherkinContent(raw: string): ParsedGherkin {
  const lines = raw.split("\n");
  const parsed: ParsedGherkin = {
    featureName: "Feature Specification",
    featureDescription: "",
    featureTags: [],
    scenarios: [],
  };

  let currentTags: string[] = [];
  let currentScenario: GherkinScenario | null = null;
  let inBackground = false;
  let backgroundSteps: GherkinStep[] = [];
  let inExamples = false;
  let exampleRows: string[][] = [];
  let featureFound = false;

  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    // Tags
    if (trimmed.startsWith("@")) {
      const tags = trimmed.split(/\s+/).filter((t) => t.startsWith("@"));
      currentTags.push(...tags);
      continue;
    }

    // Feature
    if (/^Feature:/i.test(trimmed)) {
      featureFound = true;
      parsed.featureName = trimmed.replace(/^Feature:\s*/i, "").trim();
      parsed.featureTags = [...currentTags];
      currentTags = [];
      // Collect description until next block
      const descLines: string[] = [];
      i++;
      while (i < lines.length) {
        const l = lines[i].trim();
        if (/^(Background:|Scenario:|Scenario Outline:|@)/i.test(l)) {
          i--;
          break;
        }
        if (l) descLines.push(l);
        i++;
      }
      parsed.featureDescription = descLines.join("\n");
      continue;
    }

    // Background
    if (/^Background:/i.test(trimmed)) {
      inBackground = true;
      inExamples = false;
      currentScenario = null;
      continue;
    }

    // Scenario / Scenario Outline
    if (/^(Scenario|Scenario Outline):/i.test(trimmed)) {
      if (currentScenario) {
        if (inExamples && exampleRows.length > 0) {
          currentScenario.examples = {
            header: exampleRows[0] || [],
            rows: exampleRows.slice(1),
          };
        }
        parsed.scenarios.push(currentScenario);
      }
      inBackground = false;
      inExamples = false;
      exampleRows = [];

      const isOutline = /^Scenario Outline:/i.test(trimmed);
      const name = trimmed.replace(/^(Scenario Outline|Scenario):\s*/i, "").trim();
      currentScenario = {
        id: `sc_${parsed.scenarios.length + 1}`,
        type: isOutline ? "Scenario Outline" : "Scenario",
        name: name || `Scenario ${parsed.scenarios.length + 1}`,
        tags: [...currentTags],
        steps: [],
      };
      currentTags = [];
      continue;
    }

    // Examples
    if (/^Examples:/i.test(trimmed)) {
      inExamples = true;
      exampleRows = [];
      continue;
    }

    // Table rows (in Examples or Step DataTables)
    if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
      const row = trimmed
        .slice(1, -1)
        .split("|")
        .map((c) => c.trim());
      if (inExamples && currentScenario) {
        exampleRows.push(row);
      } else if (currentScenario && currentScenario.steps.length > 0) {
        const lastStep = currentScenario.steps[currentScenario.steps.length - 1];
        lastStep.table = lastStep.table || [];
        lastStep.table.push(row);
      }
      continue;
    }

    // Steps
    const stepMatch = trimmed.match(/^(Given|When|Then|And|But)\s+(.*)$/i);
    if (stepMatch) {
      const keyword = stepMatch[1].toUpperCase();
      const text = stepMatch[2];
      const step: GherkinStep = { keyword, text };

      if (inBackground) {
        backgroundSteps.push(step);
      } else if (currentScenario) {
        currentScenario.steps.push(step);
      }
      continue;
    }
  }

  if (currentScenario) {
    if (inExamples && exampleRows.length > 0) {
      currentScenario.examples = {
        header: exampleRows[0] || [],
        rows: exampleRows.slice(1),
      };
    }
    parsed.scenarios.push(currentScenario);
  }

  if (backgroundSteps.length > 0) {
    parsed.background = { steps: backgroundSteps };
  }

  return parsed;
}
