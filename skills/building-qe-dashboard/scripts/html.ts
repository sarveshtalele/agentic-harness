/** HTML-escapes any value for text and attribute contexts. Shared by the report and dashboard builders. */
export const esc = (v: unknown): string => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));

/** Only http(s) links and plain relative paths become links; anything else (javascript:, data:, //host) stays text. */
const safeHref = (u: string): string | null => (/^https?:\/\/[^\s"'<>]+$/i.test(u) || /^(?![a-z][a-z0-9+.-]*:|\/\/)[\w./#%-]+$/i.test(u) ? u : null);

/** Maps a Markdown image path to the URL the page may load it from, or null to leave it unrendered. */
export type ImageUrl = (src: string) => string | null;

/** Inline Markdown on already-escaped text: `code`, ![alt](img), **bold**, *em*, [text](url). */
function inlineMd(s: string, img?: ImageUrl): string {
  const codes: string[] = [];
  let t = esc(s).replace(/`([^`]+)`/g, (_, c) => `\u0000${codes.push(`<code>${c}</code>`) - 1}\u0000`);
  // images only through the caller's resolver (same-origin evidence URLs); otherwise the alt text stays visible
  t = t.replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, (_m, alt, src) => {
    const u = img?.(src.replace(/&amp;/g, "&"));
    return `\u0000${codes.push(u ? `<span class="figure"><img src="${esc(u)}" alt="${alt}" loading="lazy"><span class="cap">${alt}</span></span>` : `<span class="img-missing">Image not available: ${alt || src}</span>`) - 1}\u0000`;
  });
  t = t.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, txt, url) => {
    const h = safeHref(url.replace(/&amp;/g, "&"));
    return h ? `<a href="${esc(h)}">${txt}</a>` : m;
  });
  t = t.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>");
  // the two HTML forms the generated tables use: <br> line breaks and character entities (&gt;, &#39;); nothing else passes
  t = t.replace(/&lt;br\s*\/?&gt;/gi, "<br>").replace(/&amp;(lt|gt|amp|quot|apos|nbsp|#\d{1,6}|#x[0-9a-f]{1,6});/gi, "&$1;");
  return t.replace(/\u0000(\d+)\u0000/g, (_, i) => codes[Number(i)]);
}

const cells = (row: string) => row.trim().replace(/^\||\|$/g, "").split(/(?<!\\)\|/).map((c) => c.trim().replace(/\\\|/g, "|"));

/**
 * Small, safe Markdown renderer for the generated QE documents: front matter, headings, tables, lists, quotes,
 * fenced code, rules and paragraphs. Everything is escaped first. ponytail: no nested lists or HTML passthrough.
 */
export function renderMarkdown(src: string, opts: { img?: ImageUrl } = {}): { meta: Record<string, string>; html: string } {
  const inline = (t: string) => inlineMd(t, opts.img);
  const meta: Record<string, string> = {};
  let text = src.replace(/\r\n/g, "\n");
  const fm = /^---\n([\s\S]*?)\n---\n?/.exec(text);
  if (fm) {
    for (const l of fm[1].split("\n")) { const m = /^([\w-]+):\s*(.*)$/.exec(l); if (m) meta[m[1]] = m[2]; }
    text = text.slice(fm[0].length);
  }
  const lines = text.split("\n");
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const body: string[] = [];
      for (i++; i < lines.length && !/^```/.test(lines[i]); i++) body.push(lines[i]);
      out.push(`<pre><code>${esc(body.join("\n"))}</code></pre>`);
    } else if (/^#{1,6}\s/.test(l)) {
      const n = Math.min(6, l.match(/^#+/)![0].length + 2);
      out.push(`<h${n}>${inline(l.replace(/^#+\s*/, ""))}</h${n}>`);
    } else if (/^\s*\|/.test(l) && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1] ?? "")) {
      const head = cells(l);
      const rows: string[][] = [];
      for (i += 2; i < lines.length && /^\s*\|/.test(lines[i]); i++) rows.push(cells(lines[i]));
      i--;
      out.push(`<div class="scroll"><table><thead><tr>${head.map((h) => `<th>${inline(h)}</th>`).join("")}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
    } else if (/^\s*([-*+]|\d+[.)])\s+/.test(l)) {
      // nested by indentation: a deeper item opens a list inside the previous item
      const ITEM = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
      const stack: { indent: number; tag: string }[] = [];
      let html = "";
      for (; i < lines.length && ITEM.test(lines[i]); i++) {
        const [, sp, mark, body] = ITEM.exec(lines[i])!;
        const indent = sp.replace(/\t/g, "  ").length, tag = /\d/.test(mark) ? "ol" : "ul";
        while (stack.length && indent < stack[stack.length - 1].indent) html += `</li></${stack.pop()!.tag}>`;
        if (stack.length && indent === stack[stack.length - 1].indent && tag !== stack[stack.length - 1].tag) html += `</li></${stack.pop()!.tag}>`; // - then 1.: a new list
        if (!stack.length || indent > stack[stack.length - 1].indent) { html += `<${tag}>`; stack.push({ indent, tag }); }
        else html += "</li>";
        html += `<li>${inline(body)}`;
      }
      while (stack.length) html += `</li></${stack.pop()!.tag}>`;
      i--;
      out.push(html);
    } else if (/^>\s?/.test(l)) {
      const q: string[] = [];
      for (; i < lines.length && /^>\s?/.test(lines[i]); i++) q.push(lines[i].replace(/^>\s?/, ""));
      i--;
      out.push(`<blockquote>${inline(q.join(" "))}</blockquote>`);
    } else if (/^\s*(-{3,}|\*{3,})\s*$/.test(l)) out.push("<hr>");
    else if (l.trim()) {
      const p: string[] = [];
      // the first line is always taken, so a line no other block accepts ("| not a table") cannot stall the loop (AQE140-001)
      for (; i < lines.length && lines[i].trim() && (!p.length || !/^(#{1,6}\s|```|>|\s*\||\s*([-*+]|\d+[.)])\s)/.test(lines[i])); i++) p.push(lines[i]);
      i--;
      out.push(`<p>${inline(p.join(" "))}</p>`);
    }
  }
  return { meta, html: out.join("\n") };
}

/** RFC 4180-ish CSV parser (quoted fields, doubled quotes, embedded newlines). */
export function parseCsv(src: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [], f = "", q = false;
  for (let i = 0; i < src.length; i++) {
    const c = src[i];
    if (q) { if (c === '"') { if (src[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
    else if (c === '"') q = true;
    else if (c === ",") { row.push(f); f = ""; }
    else if (c === "\n" || c === "\r") { if (c === "\r" && src[i + 1] === "\n") i++; row.push(f); rows.push(row); row = []; f = ""; }
    else f += c;
  }
  if (f || row.length) { row.push(f); rows.push(row); }
  return rows.filter((r) => r.some((x) => x !== ""));
}

/** "test_cases" / "testCases" / "tc_id" -> "Test cases" / "Test cases" / "TC ID". */
export const humanize = (k: string): string => {
  const w = k.replace(/([a-z0-9])([A-Z])/g, "$1 $2").replace(/[_-]+/g, " ").trim().toLowerCase();
  return w.replace(/\b(id|tc|fr|us|ac|qe|api|url|ui|e2e|sha|csv|json|md)\b/g, (x) => x.toUpperCase()).replace(/^./, (c) => c.toUpperCase());
};
const isScalar = (v: unknown): boolean => v === null || ["string", "number", "boolean"].includes(typeof v);
/** One table cell: scalars as text, short scalar lists joined, anything deeper as compact "key: value" text. */
const cellText = (v: unknown): string => {
  if (isScalar(v)) return v === null ? "" : String(v);
  if (Array.isArray(v)) return v.every(isScalar) ? v.join(", ") : v.map(cellText).join("; ");
  return Object.entries(v as object).map(([k, x]) => `${humanize(k)}: ${cellText(x)}`).join("; ");
};
const cellHtml = (v: unknown): string => esc(cellText(v)).replace(/\n/g, "<br>");

/**
 * A JSON document as a readable page, never as raw JSON: `_meta` becomes the metadata table, scalar fields a
 * key/value table, arrays of objects a data table (or one card per item when they are wide), scalar arrays a list,
 * nested objects a titled subsection. Everything escaped.
 */
export function renderJsonDoc(value: unknown): string {
  const out: string[] = [];
  const kvTable = (pairs: [string, unknown][]) => pairs.length ? `<table class="kv-table"><tbody>${pairs.map(([k, v]) => `<tr><th>${esc(humanize(k))}</th><td>${cellHtml(v)}</td></tr>`).join("")}</tbody></table>` : "";
  const arrayHtml = (a: unknown[], depth: number): string => {
    if (!a.length) return `<p class="muted">None.</p>`;
    if (a.every(isScalar)) return `<ul>${a.map((x) => `<li>${cellHtml(x)}</li>`).join("")}</ul>`;
    const objs = a.filter((x) => x && typeof x === "object" && !Array.isArray(x)) as Record<string, unknown>[];
    const keys = [...new Set(objs.flatMap((o) => Object.keys(o)))];
    if (keys.length <= 7 && objs.length === a.length) {
      return `<div class="scroll"><table class="data"><thead><tr>${keys.map((k) => `<th>${esc(humanize(k))}</th>`).join("")}</tr></thead><tbody>${objs.map((o) => `<tr>${keys.map((k) => `<td>${cellHtml(o[k])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    }
    // wide records: one card each, titled by its id or name
    return a.slice(0, 500).map((x, i) => {
      if (!x || typeof x !== "object" || Array.isArray(x)) return `<p>${cellHtml(x)}</p>`;
      const o = x as Record<string, unknown>;
      const idKey = Object.keys(o).find((k) => /^(tc_?id|case_?id|id|key|name|title)$/i.test(k));
      const title = idKey ? String(o[idKey]) : `Item ${i + 1}`;
      const sub = Object.keys(o).find((k) => /^(scenario|title|text|name|behavior|summary)$/i.test(k) && k !== idKey);
      return `<section class="rec"><h4>${esc(title)}${sub ? ` <span class="muted">${esc(cellText(o[sub]))}</span>` : ""}</h4>${objectHtml(o, depth + 1, [idKey, sub].filter(Boolean) as string[])}</section>`;
    }).join("") + (a.length > 500 ? `<p class="muted">${a.length - 500} more items not shown.</p>` : "");
  };
  const objectHtml = (o: Record<string, unknown>, depth: number, skip: string[] = []): string => {
    const entries = Object.entries(o).filter(([k]) => k !== "_meta" && !skip.includes(k));
    // short scalar lists read better inline in the key/value table
    const flat = entries.filter(([, v]) => isScalar(v) || (Array.isArray(v) && v.every(isScalar) && v.join(", ").length < 120));
    const deep = entries.filter((e) => !flat.includes(e));
    const h = `h${Math.min(6, depth + 3)}`;
    return kvTable(flat) + deep.map(([k, v]) => `<${h}>${esc(humanize(k))}${Array.isArray(v) ? ` <span class="count">${v.length}</span>` : ""}</${h}>${Array.isArray(v) ? arrayHtml(v, depth) : depth > 4 ? `<p>${cellHtml(v)}</p>` : objectHtml(v as Record<string, unknown>, depth + 1)}`).join("");
  };
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const meta = (value as Record<string, unknown>)._meta;
    if (meta && typeof meta === "object") out.push(`<table class="meta"><tbody>${Object.entries(meta).map(([k, v]) => `<tr><th>${esc(k)}</th><td>${cellHtml(v)}</td></tr>`).join("")}</tbody></table>`);
    out.push(objectHtml(value as Record<string, unknown>, 0));
  } else if (Array.isArray(value)) out.push(arrayHtml(value, 0));
  else out.push(`<p>${cellHtml(value)}</p>`);
  return out.join("");
}
