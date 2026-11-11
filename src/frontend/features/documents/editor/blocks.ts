export type Block = { kind: "text" | "table"; raw: string; gap: string };

const SEPARATOR = /^\s*\|[\s:|-]+\|\s*$/;
const isRow = (line: string) => line.trimStart().startsWith("|");
const blank = (line: string) => !line.trim();
const splitRow = (line: string) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, "|"));
const cell = (value: string) => value.replace(/\|/g, "\\|");

/** Splits a document into blocks. Each keeps its exact text, so an unedited block is saved unchanged. */
export function parseBlocks(content: string, gherkin: boolean): Block[] {
  const lines = content.split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const start = i;
    let kind: Block["kind"] = "text";
    if (gherkin) {
      kind = isRow(lines[i]) ? "table" : "text";
      while (i < lines.length && isRow(lines[i]) === (kind === "table")) i++;
      blocks.push({ kind, raw: lines.slice(start, i).join("\n"), gap: i < lines.length ? "\n" : "" });
      continue;
    }
    if (blank(lines[i])) {
      i++;
      continue;
    }
    if (lines[i].startsWith("```")) {
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) i++;
      i = Math.min(i + 1, lines.length);
    } else if (isRow(lines[i]) && SEPARATOR.test(lines[i + 1] || "")) {
      kind = "table";
      while (i < lines.length && isRow(lines[i])) i++;
    } else if (/^#{1,6}\s/.test(lines[i])) {
      i++;
    } else {
      i++;
      while (i < lines.length && !blank(lines[i]) && !lines[i].startsWith("```") && !/^#{1,6}\s/.test(lines[i]) && !(isRow(lines[i]) && SEPARATOR.test(lines[i + 1] || ""))) i++;
    }
    const raw = lines.slice(start, i).join("\n");
    let blanks = 0;
    while (i < lines.length && blank(lines[i])) {
      blanks++;
      i++;
    }
    blocks.push({ kind, raw, gap: "\n".repeat(i < lines.length ? blanks + 1 : blanks) });
  }
  return blocks;
}

export const joinBlocks = (blocks: Block[]) => blocks.map((b) => b.raw + b.gap).join("");

export function tableRows(raw: string, gherkin: boolean): string[][] {
  const lines = raw.split("\n").filter((line) => line.trim());
  return (gherkin ? lines : lines.filter((_, i) => i !== 1)).map(splitRow);
}

export function tableText(rows: string[][], gherkin: boolean, indent: string): string {
  if (!gherkin) return [`| ${rows[0].map(cell).join(" | ")} |`, `| ${rows[0].map(() => "---").join(" | ")} |`, ...rows.slice(1).map((row) => `| ${row.map(cell).join(" | ")} |`)].join("\n");
  const widths = rows[0].map((_, c) => Math.max(...rows.map((row) => cell(row[c] || "").length)));
  return rows.map((row) => `${indent}| ${row.map((value, c) => cell(value).padEnd(widths[c])).join(" | ")} |`).join("\n");
}
