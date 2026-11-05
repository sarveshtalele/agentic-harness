// The dashboard's browser side: page, stylesheet and script as strings, served by dashboard-server.ts.
// No inline script or style (CSP), no external resources. The script avoids backticks and "${" so it can live in String.raw.
// Layout follows enterprise dashboard practice (IBM Carbon): UI shell with header and side nav, F-pattern hierarchy
// (verdict and KPIs first, then the release gates), status shown by icon + shape + colour + label, flat tiles.

export const PAGE_HTML = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="qe-token" content="__TOKEN__">
<title>Agentic QE</title>
<link rel="stylesheet" href="/app.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header id="top" class="shell-header"></header>
<div class="shell">
<nav id="nav" class="side-nav" aria-label="Sections"></nav>
<main id="main" tabindex="-1"></main>
</div>
<div id="toast" class="toast" role="status" aria-live="polite"></div>
<noscript><p>The QE dashboard needs JavaScript.</p></noscript>
<script src="/app.js"></script>
</body>
</html>
`;

const LIGHT = "--bg:#f4f4f4;--layer:#ffffff;--layer-2:#f4f4f4;--layer-hover:#e8e8e8;--line:#e0e0e0;--line-strong:#8d8d8d;--fg:#161616;--fg-2:#525252;--fg-3:#6f6f6f;--accent:#0f62fe;--accent-hover:#0353e9;--accent-soft:#edf5ff;--ok:#198038;--ok-bg:#defbe6;--bad:#da1e28;--bad-bg:#fff1f1;--warn:#8e6a00;--warn-bg:#fcf4d6;--info:#0043ce;--info-bg:#edf5ff;--head:#161616;--head-fg:#f4f4f4;--shadow:0 1px 2px rgba(0,0,0,.06)";
const DARK = "--bg:#161616;--layer:#262626;--layer-2:#1f1f1f;--layer-hover:#333333;--line:#393939;--line-strong:#6f6f6f;--fg:#f4f4f4;--fg-2:#c6c6c6;--fg-3:#a8a8a8;--accent:#78a9ff;--accent-hover:#a6c8ff;--accent-soft:#1c2a44;--ok:#42be65;--ok-bg:#0e3a1d;--bad:#fa4d56;--bad-bg:#3d1215;--warn:#f1c21b;--warn-bg:#3a3010;--info:#78a9ff;--info-bg:#1c2a44;--head:#0b0b0b;--head-fg:#f4f4f4;--shadow:0 1px 2px rgba(0,0,0,.5)";

export const APP_CSS = `
:root{${LIGHT};--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",sans-serif}
@media(prefers-color-scheme:dark){:root:not([data-theme="light"]){${DARK}}}
:root[data-theme="dark"]{${DARK}}
*{box-sizing:border-box}
html{color-scheme:light dark}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 var(--sans);-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
code,pre,textarea{font-family:var(--mono);font-size:12.5px}
:not(pre)>code{background:var(--layer-2);border:1px solid var(--line);padding:0 4px;border-radius:2px}
pre{background:var(--layer-2);border:1px solid var(--line);padding:12px;border-radius:4px;overflow:auto;margin:8px 0}
[hidden]{display:none!important}
.skip{position:absolute;left:-999px}.skip:focus{left:8px;top:8px;background:var(--layer);padding:6px 10px;z-index:30}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}

/* UI shell */
.shell-header{position:sticky;top:0;z-index:20;height:48px;display:flex;align-items:center;gap:12px;padding:0 16px;background:var(--head);color:var(--head-fg);border-bottom:1px solid #393939}
.shell-header .product{font-weight:600;letter-spacing:.01em;white-space:nowrap}.shell-header .product b{font-weight:400;color:#c6c6c6}
.shell-header .crumb{color:#c6c6c6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.shell-header .grow{flex:1}
.hbtn{font:inherit;font-size:13px;height:32px;padding:0 12px;border:1px solid #525252;background:transparent;color:var(--head-fg);border-radius:2px;cursor:pointer;display:inline-flex;align-items:center;gap:6px;white-space:nowrap;text-decoration:none}
.hbtn:hover{background:#353535;text-decoration:none}
.live{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#c6c6c6;white-space:nowrap}
.live i{width:8px;height:8px;border-radius:50%;background:#6f6f6f}.live.on i{background:#42be65;box-shadow:0 0 0 3px rgba(66,190,101,.25)}
#menu{display:none}
.shell{display:grid;grid-template-columns:248px minmax(0,1fr);min-height:calc(100vh - 48px)}
.side-nav{background:var(--layer);border-right:1px solid var(--line);padding:12px 0;position:sticky;top:48px;height:calc(100vh - 48px);overflow:auto}
.side-nav h2{font-size:12px;font-weight:600;color:var(--fg-3);margin:16px 16px 4px;letter-spacing:.02em}
.side-nav a{display:flex;align-items:center;gap:10px;min-height:36px;padding:6px 16px;color:var(--fg-2);border-left:3px solid transparent;text-decoration:none;font-size:14px}
.side-nav a:hover{background:var(--layer-hover);color:var(--fg)}
.side-nav a[aria-current="page"]{background:var(--layer-hover);color:var(--fg);font-weight:600;border-left-color:var(--accent)}
.side-nav .nst{display:inline-flex;color:var(--fg-3)}.side-nav .nst svg{width:16px;height:16px}.nst.ok{color:var(--ok)}.nst.bad{color:var(--bad)}
.side-nav .count{margin-left:auto;font-size:12px;color:var(--fg-3)}
main{min-width:0;outline:none;padding:24px 32px 48px;max-width:1440px}

/* page header */
.crumbs{font-size:13px;color:var(--fg-2);margin-bottom:8px}.crumbs a{color:var(--accent)}
.page-head{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:flex-end;justify-content:space-between;margin-bottom:24px}
.page-head h1{font-size:28px;font-weight:400;line-height:1.25;margin:0}
.page-head p{margin:4px 0 0;color:var(--fg-2)}
h2.section{font-size:20px;font-weight:400;margin:32px 0 12px}
h3{font-size:16px;font-weight:600;margin:0}

/* tiles */
.tile{background:var(--layer);border:1px solid var(--line);border-radius:4px;padding:16px;box-shadow:var(--shadow);min-width:0}
.kpis{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:12px}
.kpi{display:block;color:var(--fg);text-decoration:none}.kpi:hover{border-color:var(--line-strong);text-decoration:none}
.kpi .label{font-size:12px;color:var(--fg-2)}.kpi .value{font-size:32px;font-weight:300;line-height:1.2;margin-top:4px}
.kpi.bad .value{color:var(--bad)}.kpi.ok .value{color:var(--ok)}
.verdict{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;align-items:center;border-left:4px solid var(--fg-3)}
.verdict.PASS{border-left-color:var(--ok)}.verdict.FAIL{border-left-color:var(--bad)}.verdict.INCONCLUSIVE{border-left-color:var(--warn)}
.verdict .v{font-size:36px;font-weight:300;grid-row:span 2}.verdict.PASS .v{color:var(--ok)}.verdict.FAIL .v{color:var(--bad)}.verdict.INCONCLUSIVE .v{color:var(--warn)}
.verdict .why{font-weight:600}.verdict .sub{color:var(--fg-2);font-size:13px}
.top-row{display:grid;grid-template-columns:minmax(260px,1fr) 2fr;gap:12px;margin-bottom:12px}

/* gate cards */
.gates{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.gate-card{display:flex;flex-direction:column;gap:12px;color:var(--fg);text-decoration:none;border-top:3px solid var(--line-strong);transition:border-color .1s,background .1s}
.gate-card:hover{background:var(--layer-hover);text-decoration:none}
.gate-card.APPROVED{border-top-color:var(--ok)}.gate-card.REJECTED{border-top-color:var(--bad)}.gate-card.REOPENED{border-top-color:#f1c21b}.gate-card.PENDING{border-top-color:var(--line-strong)}
.gate-card .gnum{font-size:12px;color:var(--fg-2);letter-spacing:.02em}.gate-card h3{font-size:18px;font-weight:400}
.gate-card .meta-row{display:flex;justify-content:space-between;gap:8px;font-size:12.5px;color:var(--fg-2);border-top:1px solid var(--line);padding-top:10px}
.gate-card .go{color:var(--accent);font-size:13px}
.bar{height:4px;background:var(--line);border-radius:2px;overflow:hidden}.bar i{display:block;height:100%;background:var(--accent)}

/* status tags (icon + shape + colour + label) */
.tag{display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 8px 0 6px;border-radius:12px;font-size:12px;font-weight:500;white-space:nowrap;background:var(--layer-2);color:var(--fg-2);border:1px solid var(--line)}
.tag svg{width:14px;height:14px;flex:none}
.tag.ok{background:var(--ok-bg);color:var(--ok);border-color:transparent}.tag.bad{background:var(--bad-bg);color:var(--bad);border-color:transparent}
.tag.warn{background:var(--warn-bg);color:var(--warn);border-color:transparent}.tag.info{background:var(--info-bg);color:var(--info);border-color:transparent}
.tag.plain{padding:0 8px}

/* notifications */
.note{display:flex;gap:12px;align-items:flex-start;padding:12px 16px;border:1px solid var(--line);border-left:3px solid var(--info);background:var(--layer);border-radius:2px;margin:0 0 12px}
.note svg{width:20px;height:20px;flex:none;margin-top:1px}.note .t{font-weight:600}.note>div{min-width:0;flex:1}
.note.ok{border-left-color:var(--ok)}.note.ok svg{color:var(--ok)}.note.bad{border-left-color:var(--bad)}.note.bad svg{color:var(--bad)}
.note.warn{border-left-color:#f1c21b}.note.warn svg{color:var(--warn)}.note.info svg{color:var(--info)}

/* buttons, commands */
.btn{font:inherit;font-size:14px;min-height:32px;padding:4px 14px;border-radius:2px;border:1px solid transparent;background:var(--accent);color:#fff;cursor:pointer;display:inline-flex;align-items:center;gap:6px;text-decoration:none;white-space:nowrap}
.btn:hover{background:var(--accent-hover);text-decoration:none}
.btn.ghost{background:transparent;color:var(--accent);border-color:transparent}.btn.ghost:hover{background:var(--layer-hover)}
.btn.secondary{background:var(--layer);color:var(--fg);border-color:var(--line-strong)}.btn.secondary:hover{background:var(--layer-hover)}
.btn.danger{background:var(--bad)}
.btn:disabled{opacity:.5;cursor:not-allowed}
.cmd{display:flex;align-items:stretch;border:1px solid var(--line);border-radius:2px;overflow:hidden;margin:6px 0;max-width:640px;background:var(--layer-2)}
.cmd small{display:flex;align-items:center;padding:0 10px;font-size:12px;color:var(--fg-2);border-right:1px solid var(--line);white-space:nowrap}
.cmd code{flex:1;padding:7px 10px;background:transparent;border:0;word-break:break-all;font-size:13px}
.cmd button{border:0;border-left:1px solid var(--line);background:var(--layer);color:var(--accent);font:inherit;font-size:13px;padding:0 12px;cursor:pointer}.cmd button:hover{background:var(--layer-hover)}

/* artifact cards inside a gate */
.artifacts{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}
.artifact{padding:0;display:flex;flex-direction:column}
.artifact>button.head{all:unset;cursor:pointer;display:flex;gap:12px;align-items:flex-start;padding:16px}
.artifact>button.head:hover{background:var(--layer-hover)}
.artifact .ico{width:36px;height:36px;border-radius:4px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#fff;flex:none;background:#6f6f6f}
.artifact .ico.md{background:#0f62fe}.artifact .ico.json{background:#8a3ffc}.artifact .ico.csv{background:#198038}.artifact .ico.report{background:#005d5d}
.artifact .name{font-weight:600;word-break:break-word}.artifact .sub{font-size:12px;color:var(--fg-2)}
.artifact.open{grid-column:1/-1}
.artifact .body{border-top:1px solid var(--line);padding:16px 20px}
.artifact .toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between;margin-bottom:12px}
.missing{opacity:.65}.missing .ico{background:var(--line-strong)}

/* rendered documents */
.doc{max-width:1100px;line-height:1.6}
.doc h3,.doc h4,.doc h5,.doc h6{margin:20px 0 8px;font-weight:600}.doc h3{font-size:18px}.doc h4{font-size:15px}.doc h5,.doc h6{font-size:14px}
.doc p{margin:8px 0}.doc ul,.doc ol{padding-left:22px}.doc blockquote{margin:8px 0;padding:4px 16px;border-left:3px solid var(--accent);color:var(--fg-2)}
.doc table{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:13.5px}
.doc th,.doc td{text-align:left;padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
.doc thead th{background:var(--layer-2);font-weight:600;font-size:12.5px;color:var(--fg)}
.doc table.meta,.doc table.kv-table{width:auto;min-width:min(520px,100%)}
.doc table.meta th,.doc table.kv-table th{background:var(--layer-2);color:var(--fg-2);font-weight:500;width:1%;white-space:nowrap}
.doc table.meta{font-size:12px;margin-bottom:20px}
.doc .rec{border:1px solid var(--line);border-radius:4px;padding:4px 16px 8px;margin:8px 0;background:var(--layer)}
.doc .rec h4{margin:10px 0 6px}.doc .count{display:inline-block;min-width:22px;padding:0 6px;border-radius:10px;background:var(--layer-2);border:1px solid var(--line);font-size:12px;font-weight:500;text-align:center;color:var(--fg-2)}
.doc .figure{display:block;margin:12px 0;border:1px solid var(--line);border-radius:4px;overflow:hidden;background:var(--layer-2);max-width:960px}
.doc .figure img{display:block;width:100%;height:auto}.doc .figure .cap{display:block;padding:6px 10px;font-size:12px;color:var(--fg-2);border-top:1px solid var(--line);background:var(--layer)}
.doc .img-missing{display:inline-block;padding:8px 12px;border:1px dashed var(--bad);color:var(--bad);border-radius:4px}
.scroll{overflow-x:auto}.muted{color:var(--fg-2)}

/* editor */
.editor{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.editor textarea{width:100%;min-height:60vh;resize:vertical;padding:12px;border:1px solid var(--line-strong);border-bottom:2px solid var(--line-strong);border-radius:0;background:var(--layer-2);color:var(--fg);tab-size:2;line-height:1.5}
.editor textarea:focus{outline:2px solid var(--accent);outline-offset:-2px}
.editor .preview{border:1px solid var(--line);border-radius:4px;padding:12px 16px;overflow:auto;max-height:60vh;background:var(--layer)}
.editor .label{font-size:12px;color:var(--fg-2);margin-bottom:4px}

/* data tables, filters, lists */
.toolbar-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.toolbar-row input,.toolbar-row select{font:inherit;height:40px;padding:0 12px;border:0;border-bottom:1px solid var(--line-strong);background:var(--layer);color:var(--fg);border-radius:0;min-width:180px}
table.data{border-collapse:collapse;width:100%;font-size:13.5px}
table.data th{background:var(--layer-2);text-align:left;font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
table.data td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
table.data tr:hover td{background:var(--layer-hover)}
.id{font-family:var(--mono);font-size:12.5px;font-weight:600;white-space:nowrap}
details.case{background:var(--layer);border:1px solid var(--line);border-radius:4px;margin-bottom:6px}
details.case>summary{cursor:pointer;padding:10px 14px;display:flex;gap:12px;align-items:center;flex-wrap:wrap;list-style:none}
details.case>summary::-webkit-details-marker{display:none}
details.case>summary .grow{flex:1;min-width:200px}
details.case .body{padding:12px 16px 16px;border-top:1px solid var(--line)}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:6px 20px;margin:0}dl.kv dt{color:var(--fg-2)}dl.kv dd{margin:0;word-break:break-word}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:12px}
.shot{padding:0;overflow:hidden}.shot img{display:block;width:100%;height:auto;border-bottom:1px solid var(--line);background:var(--layer-2)}.shot .cap{padding:10px 14px;display:flex;justify-content:space-between;gap:8px;align-items:center}
.pipeline{display:flex;flex-wrap:wrap;gap:0;margin:0;padding:0;list-style:none}
.pipeline li{display:flex;align-items:center;gap:6px;padding:6px 12px 6px 8px;font-size:12.5px;color:var(--fg-2);border-bottom:2px solid var(--line)}
.pipeline li.done{color:var(--fg);border-bottom-color:var(--ok)}.pipeline li.next{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
.pipeline svg{width:14px;height:14px}
.toast{position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:10px 18px;border-radius:2px;opacity:0;pointer-events:none;transition:opacity .2s;z-index:40}.toast.on{opacity:1}
@media(max-width:960px){.top-row{grid-template-columns:minmax(0,1fr)}.editor{grid-template-columns:minmax(0,1fr)}}
@media(max-width:820px){
.shell{grid-template-columns:minmax(0,1fr)}
#menu{display:inline-flex}
.side-nav{display:none;position:fixed;top:48px;left:0;bottom:0;width:260px;z-index:15;height:auto;box-shadow:0 4px 16px rgba(0,0,0,.3)}body.nav-open .side-nav{display:block}
main{padding:16px}
.shell-header .crumb,.shell-header .live,.hide-sm{display:none}
.shell-header{gap:8px;padding:0 10px}.hbtn{padding:0 10px}
.page-head h1{font-size:24px}
}
`;

export const APP_JS = String.raw`(function () {
'use strict';
var TOKEN = (document.querySelector('meta[name="qe-token"]') || {}).content || '';
// read-only snapshot (dashboard.html): everything comes from the embedded JSON
var STATIC = (function () { var el = document.getElementById('qe-static'); try { return el ? JSON.parse(el.textContent) : null; } catch (e) { return null; } })();
var S = null, flash = null, editor = null, live = false, lastHash = location.hash, refreshTimer = 0, openCards = {};
var PHASE_OF = ['intake', 'discovery', 'requirements', 'requirements', 'plan', 'design', 'generation', 'execution', 'healing', 'traceability', 'release'];

// ---- dom helpers
function add(el, c) {
  if (c == null || c === false) return;
  if (Array.isArray(c)) c.forEach(function (x) { add(el, x); });
  else el.appendChild(c.nodeType ? c : document.createTextNode(String(c)));
}
function h(tag, a) {
  var el = document.createElement(tag);
  a = a || {};
  Object.keys(a).forEach(function (k) {
    var v = a[k];
    if (v == null || v === false) return;
    if (k === 'class') el.className = v;
    else if (k === 'text') el.textContent = v;
    else if (k === 'html') el.innerHTML = v; // only for static icon markup and server-escaped document HTML
    else if (k.indexOf('on') === 0) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? '' : v);
  });
  for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
  return el;
}
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
function when(iso) { var d = new Date(iso); return isNaN(d) ? String(iso || '') : d.toLocaleString(); }
function size(n) { return n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(1) + ' MB'; }
function plural(n, w) { return n + ' ' + w + (n === 1 ? '' : 's'); }

// ---- icons (static SVG; status uses icon + shape + colour + label)
var IC = {
  ok: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="currentColor"/><path d="M4.8 8.2l2.1 2.1 4.3-4.4" stroke="#fff" stroke-width="1.6" fill="none"/></svg>',
  bad: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 1h6l4 4v6l-4 4H5l-4-4V5z" fill="currentColor"/><path d="M5.5 5.5l5 5M10.5 5.5l-5 5" stroke="#fff" stroke-width="1.6"/></svg>',
  warn: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 1l7 13H1z" fill="#f1c21b"/><path d="M8 6v4M8 11.5v1.2" stroke="#161616" stroke-width="1.5"/></svg>',
  pending: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6.3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-dasharray="3 2"/></svg>',
  info: '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="currentColor"/><path d="M8 7v4.5M8 4.5v1.3" stroke="#fff" stroke-width="1.6"/></svg>'
};
var KIND = { PASS: 'ok', PASSED: 'ok', APPROVED: 'ok', FAIL: 'bad', FAILED: 'bad', REJECTED: 'bad', REOPENED: 'warn', 'PARTLY RUN': 'warn', INCONCLUSIVE: 'warn', SKIPPED: 'warn', PENDING: 'pending', 'NOT RUN': 'pending', 'NO TESTS': 'pending' };
function tag(text, kind) {
  kind = kind || KIND[text] || 'plain';
  var t = h('span', { class: 'tag ' + (kind === 'pending' ? '' : kind) });
  if (IC[kind]) t.appendChild(h('span', { html: IC[kind], style: null }).firstChild);
  add(t, text);
  if (kind === 'plain') t.className = 'tag plain';
  return t;
}
function note(kind, title, body) {
  return h('div', { class: 'note ' + kind, role: kind === 'bad' ? 'alert' : 'status' }, h('span', { html: IC[kind === 'ok' ? 'ok' : kind === 'bad' ? 'bad' : kind === 'warn' ? 'warn' : 'info'] }).firstChild, h('div', null, title ? h('div', { class: 't', text: title }) : null, body));
}

// ---- small widgets
function toast(msg) {
  var t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast on';
  clearTimeout(toast.t); toast.t = setTimeout(function () { t.className = 'toast'; }, 1800);
}
function copy(text) {
  function fallback() {
    var ta = h('textarea', { 'aria-hidden': 'true' }); ta.value = text; document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); toast('Copied'); } catch (e) { toast('Copy failed'); }
    ta.remove();
  }
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(function () { toast('Copied'); }, fallback);
  else fallback();
}
function cmdBox(label, text) {
  return h('div', { class: 'cmd' }, h('small', { text: label }), h('code', { text: text }), h('button', { type: 'button', 'aria-label': 'Copy ' + text, onclick: function () { copy(text); } }, 'Copy'));
}
function staticApi(path) {
  var u = new URL(path, 'http://snapshot'), p = u.searchParams.get('path');
  if (u.pathname === '/api/state') return Promise.resolve(STATIC.state);
  if (u.pathname === '/api/render') return STATIC.renders[p] != null ? Promise.resolve({ html: STATIC.renders[p] }) : Promise.reject(new Error('Not included in this snapshot.'));
  if (u.pathname === '/api/gate-report') return Promise.resolve({ html: STATIC.reports[u.searchParams.get('gate')] || '' });
  var e = new Error('This is a read-only snapshot.'); e.status = 404; return Promise.reject(e);
}
function imgUrl(p) { return STATIC ? (STATIC.images[p] || '') : '/api/file?path=' + encodeURIComponent(p); }
function api(path, opt) {
  if (STATIC) return staticApi(path);
  opt = opt || {}; opt.credentials = 'same-origin';
  return fetch(path, opt).then(function (r) {
    var json = (r.headers.get('content-type') || '').indexOf('json') >= 0;
    return (json ? r.json() : r.text()).then(function (b) {
      if (!r.ok) { var e = new Error((b && b.error) || r.statusText); e.status = r.status; e.body = b; throw e; }
      return b;
    });
  });
}
function hashOf(view, params) {
  var q = new URLSearchParams();
  Object.keys(params || {}).forEach(function (k) { if (params[k]) q.set(k, params[k]); });
  var s = q.toString();
  return '#/' + view + (s ? '?' + s : '');
}
function docHash(p) { return hashOf('doc', { path: p }); }
function pageHead(crumbs, title, sub, right) {
  var c = h('div', { class: 'crumbs' });
  crumbs.forEach(function (x, i) { if (i) add(c, ' / '); add(c, x[1] ? h('a', { href: x[1], text: x[0] }) : x[0]); });
  return [crumbs.length ? c : null, h('div', { class: 'page-head' }, h('div', null, h('h1', { text: title }), sub ? h('p', { text: sub }) : null), right || null)];
}

// ---- derived data
function caseStatus(c) { return c.result ? c.result.status : 'NOT RUN'; }
function counts() {
  var by = { PASS: 0, FAIL: 0, SKIPPED: 0, 'NOT RUN': 0 }, lv = {};
  S.cases.forEach(function (c) { by[caseStatus(c)]++; var l = c.level || 'Other'; lv[l] = (lv[l] || 0) + 1; });
  return { by: by, lv: lv };
}
function phaseDone(id) { return S.phases.some(function (p) { return p.id === id && p.docs.some(function (d) { return d.exists; }); }); }
function nextStep() { for (var i = 0; i < S.pipeline.length; i++) if (!phaseDone(PHASE_OF[i])) return S.pipeline[i]; return null; }
function nextGate() { for (var i = 0; i < S.gates.length; i++) if (S.gates[i].status !== 'APPROVED') return S.gates[i]; return null; }
// why every gate reads pending: an untrusted ledger is ignored, and the page must say so
function trustNote() {
  if (!S.trust || S.trust.trusted || S.gates.some(function (g) { return g.recorded; }) || /no \.qe/.test(S.trust.reason || '')) return null;
  return note('bad', 'Approvals not shown: the ledger is not trusted', S.trust.reason + '. Gates read as pending until this is fixed. Run /agentic-qe:qe-doctor. Do not edit run state by hand.');
}
function coverageNote() {
  var c = S.coverage;
  if (!c) return null;
  var n = c.counts, inv = c.inventory || { tests: 0, files: 0, existing: 0, generated: 0, manual: 0 };
  var head = 'requirements ' + n.requirements + ' · plan scenarios ' + n.scenarios + ' · designed cases ' + n.cases + ' · test files ' + n.tests + ' · results ' + n.results +
    ' · tests in repo ' + inv.tests + ' (existing ' + inv.existing + ', generated ' + inv.generated + ', added by hand ' + inv.manual + ')' +
    (c.validation ? ' · pandas/numpy validator, gate ' + c.validation.gate + ': ' + (c.validation.ok ? 'PASS' : 'FAIL' + (c.validation.error ? ' (' + c.validation.error + ')' : ' (' + c.validation.errors.map(function (e) { return e.message; }).join('; ') + ')')) : '');
  var next = S.gates.findIndex(function (g) { return g.status !== 'APPROVED'; });
  var chk = next > 0 ? c.checks[next - 1] : null;
  if (!chk || chk.ok) return note('ok', 'Coverage', head + (chk ? ' · Gate ' + chk.gate + ' check passes' : ''));
  return note('bad', 'Coverage: Gate ' + chk.gate + ' cannot be approved yet', head + '. Missing: ' + chk.gaps.join('; ') + (chk.more ? ' and ' + chk.more + ' more (coverage-map.md)' : ''));
}
function gatePhases(g) { return S.phases.filter(function (p) { return g.covers.indexOf(p.title) >= 0; }); }
function gateDocs(g) { var out = []; gatePhases(g).forEach(function (p) { p.docs.forEach(function (d) { out.push({ d: d, p: p }); }); }); return out; }
function reportOf(n) { return (S.reports || [])[n] || { missing: [], broken: [] }; }
function guardrailProblems() {
  var r5 = reportOf(5), ev = S.evidence || { valid: [], invalid: [] }, out = [];
  if (r5.exists && r5.missing.length) out.push(plural(r5.missing.length, 'screenshot') + ' in 06-execution/evidence/ not shown in the saved Gate 5 report: ' + r5.missing.join(', '));
  (S.reports || []).forEach(function (r) { if (r.broken.length) out.push('Gate ' + r.gate + ' report links ' + plural(r.broken.length, 'image') + ' that cannot be shown: ' + r.broken.join(', ')); });
  ev.invalid.forEach(function (i) { out.push(i.path + ': ' + i.reason); });
  return out;
}

// ---- shell
function theme() { try { return localStorage.getItem('qe-theme') || 'auto'; } catch (e) { return 'auto'; } }
function applyTheme(t) {
  if (t === 'auto') document.documentElement.removeAttribute('data-theme'); else document.documentElement.setAttribute('data-theme', t);
  try { localStorage.setItem('qe-theme', t); } catch (e) { /* private mode */ }
}
function renderTop() {
  var top = document.getElementById('top'), t = theme();
  top.textContent = '';
  add(top, [
    h('button', { id: 'menu', class: 'hbtn', type: 'button', 'aria-label': 'Toggle navigation', onclick: function () { document.body.classList.toggle('nav-open'); } }, 'Menu'),
    h('span', { class: 'product' }, 'Agentic ', h('b', { text: 'QE' })),
    S ? h('span', { class: 'crumb', text: (S.app || 'no app yet') + '  ·  ' + (/brownfield/i.test(S.mode) ? 'Brownfield' : /greenfield/i.test(S.mode) ? 'Greenfield' : S.mode) }) : null,
    h('span', { class: 'grow' }),
    STATIC ? h('span', { class: 'live', title: 'Read-only snapshot' }, 'Snapshot ' + when(STATIC.exportedAt)) : h('span', { class: 'live' + (live ? ' on' : ''), title: live ? 'Updates live as files change' : 'Live updates disconnected' }, h('i'), live ? 'Live' : 'Offline'),
    STATIC ? null : h('a', { class: 'hbtn', href: '/api/download.zip', download: '', 'aria-label': 'Download ZIP of all artifacts' }, h('span', { class: 'hide-sm', text: 'Download ' }), 'ZIP'),
    h('button', { class: 'hbtn', type: 'button', 'aria-label': 'Theme: ' + t + '. Click to change', onclick: function () { applyTheme({ auto: 'light', light: 'dark', dark: 'auto' }[theme()]); renderTop(); } }, h('span', { class: 'hide-sm', text: 'Theme: ' }), t === 'auto' ? 'Auto' : t === 'light' ? 'Light' : 'Dark')
  ]);
}
function renderNav(r) {
  var nav = document.getElementById('nav');
  nav.textContent = '';
  function item(href, text, cur, extra) { return h('a', { href: href, 'aria-current': cur ? 'page' : null }, extra || null, h('span', { text: text })); }
  add(nav, item('#/overview', 'Overview', r.view === 'overview'));
  add(nav, h('h2', { text: 'Release gates' }));
  if (S) S.gates.forEach(function (g) {
    var k = KIND[g.status] || 'pending';
    add(nav, item('#/gate/' + g.gate, 'Gate ' + g.gate + '  ' + g.name, r.view === 'gate' && r.arg === String(g.gate), h('span', { html: IC[k], class: 'nst ' + k, title: g.status })));
  });
  add(nav, h('h2', { text: 'Insights' }));
  [['requirements', 'Requirements', S && S.requirements.length], ['cases', 'Test cases', S && S.cases.length], ['trace', 'Traceability'], ['results', 'Results'], ['defects', 'Defects', S && S.defects.length], ['evidence', 'Evidence', S && S.evidence && S.evidence.valid.length], ['activity', 'Activity']].forEach(function (x) {
    var a = item('#/' + x[0], x[1], r.view === x[0]);
    if (x[2] != null) a.appendChild(h('span', { class: 'count', text: String(x[2]) }));
    add(nav, a);
  });
}

// ---- overview
function viewOverview() {
  var c = counts(), v = S.verdict, ns = nextStep(), ng = nextGate(), probs = guardrailProblems();
  var out = pageHead([], 'Quality engineering overview', (S.app || 'No app yet') + ' · ' + (S.meta.commit ? 'commit ' + S.meta.commit + ' · ' : '') + 'updated ' + when(S.generatedAt));
  if (STATIC) out.push(note('info', 'Read-only snapshot', 'Exported ' + when(STATIC.exportedAt) + '. Open the live dashboard (/agentic-qe:qe-panel --serve) to edit documents or see later changes.'));
  if (S.gates.some(function (g) { return g.recorded; })) out.push(note('info', 'Recorded gate decisions', 'This folder has no run ledger (an example or a copied run). Gate states are the decisions recorded in its saved gate reports. In a live run they come from the signed ledger and update here as soon as you approve.'));
  add(out, trustNote());
  add(out, coverageNote());
  if ((S.lowPasses || []).length) out.push(note('warn', 'Passes not counted as verified', S.lowPasses.length + ' passing case(s) have low confidence from the independent review: ' + S.lowPasses.join(', ')));
  if (probs.length) out.push(note('bad', 'Screenshot guardrail', h('ul', null, probs.map(function (p) { return h('li', { text: p }); }))));
  var action = h('div');
  if (ng) add(action, [h('div', { text: 'Gate ' + ng.gate + ' (' + ng.name + ') is ' + ng.status.toLowerCase() + '. Review its artifacts, then type in your agent session:' }), cmdBox('Approve', ng.phrase), h('a', { href: '#/gate/' + ng.gate, class: 'btn', style: null }, 'Open Gate ' + ng.gate)]);
  else add(action, h('div', { text: 'All gates are approved.' }));
  if (ns) add(action, [h('div', { class: 'muted', text: 'Next command in the pipeline:' }), cmdBox('Claude Code', '/agentic-qe:' + ns + ' ' + (S.app || '<app>'))]);
  out.push(note(ng && ng.status === 'REOPENED' ? 'warn' : 'info', 'Next action', action));
  var kpis = h('div', { class: 'kpis' });
  [['Requirements', S.requirements.length, '#/requirements'], ['Test cases', S.cases.length, '#/cases'], ['Passed', c.by.PASS, hashOf('cases', { status: 'PASS' }), 'ok'], ['Failed', c.by.FAIL, hashOf('cases', { status: 'FAIL' }), c.by.FAIL ? 'bad' : ''], ['Defects', S.defects.length, '#/defects', S.defects.length ? 'bad' : ''], ['Screenshots', (S.evidence || { valid: [] }).valid.length, '#/evidence']].concat(S.confidence && (S.confidence.design || S.confidence.code) ? [['Low-confidence cases', S.cases.filter(function (x) { var k = confOf(x); return k && k.low; }).length, hashOf('cases', { conf: 'Low confidence' }), ''], [S.confidence.design ? 'Average design confidence' : 'Average test confidence', (S.confidence.design || S.confidence.code).average, '#/cases']] : [['Confidence', 'Not reviewed', '#/cases']]).forEach(function (k) {
    kpis.appendChild(h('a', { class: 'tile kpi ' + (k[3] || ''), href: k[2] }, h('div', { class: 'label', text: k[0] }), h('div', { class: 'value', text: String(k[1]) })));
  });
  out.push(h('div', { class: 'top-row' }, h('section', { class: 'tile verdict ' + v.verdict, 'aria-label': 'Release verdict' }, h('div', { class: 'v', text: v.verdict }), h('div', { class: 'why', text: 'Release verdict' }), h('div', { class: 'sub', text: v.reason })), kpis));
  out.push(h('h2', { class: 'section', text: 'Release gates' }));
  var grid = h('div', { class: 'gates' });
  S.gates.forEach(function (g) {
    var docs = gateDocs(g), have = docs.filter(function (x) { return x.d.exists; }).length;
    grid.appendChild(h('a', { class: 'tile gate-card ' + g.status, href: '#/gate/' + g.gate, 'aria-label': 'Gate ' + g.gate + ' ' + g.name + ', ' + g.status.toLowerCase() },
      h('div', { style: null }, h('div', { class: 'gnum', text: 'GATE ' + g.gate }), h('h3', { text: g.name })),
      h('div', null, tag(g.status), g.recorded ? h('span', { class: 'muted', text: '  recorded in report' }) : null),
      h('div', { class: 'muted', text: g.covers.join(' · ') || 'Run start' }),
      h('div', null, h('div', { class: 'bar', title: have + ' of ' + docs.length + ' artifacts' }, h('i', { style: null })), h('div', { class: 'muted', style: null, text: have + ' of ' + docs.length + ' artifacts' })),
      h('div', { class: 'meta-row' }, h('span', { text: g.timestamp ? when(g.timestamp) : 'No decision yet' }), h('span', { class: 'go', text: 'Open gate →' }))));
    var bar = grid.lastChild.querySelector('.bar i'); bar.style.width = (docs.length ? Math.round(100 * have / docs.length) : 0) + '%';
  });
  out.push(grid);
  out.push(h('h2', { class: 'section', text: 'Pipeline' }));
  var pipe = h('ol', { class: 'pipeline' });
  S.pipeline.forEach(function (cmd, i) { var done = phaseDone(PHASE_OF[i]); pipe.appendChild(h('li', { class: done ? 'done' : cmd === ns ? 'next' : '' }, done ? h('span', { html: IC.ok, style: null }).firstChild : null, cmd.replace('qe-', ''))); });
  out.push(h('section', { class: 'tile' }, pipe));
  var lv = h('div', { class: 'kpis' });
  Object.keys(c.lv).forEach(function (l) { lv.appendChild(h('a', { class: 'tile kpi', href: hashOf('cases', { level: l }) }, h('div', { class: 'label', text: l + ' cases' }), h('div', { class: 'value', text: String(c.lv[l]) }))); });
  out.push(h('h2', { class: 'section', text: 'Test levels' }), lv);
  return out;
}

// ---- documents: clean render (server-escaped HTML), images resolved by the server
function renderInto(el, path) {
  el.textContent = 'Loading...'; el.setAttribute('data-path', path);
  return api('/api/render?path=' + encodeURIComponent(path)).then(function (r) { el.innerHTML = r.html; }, function (e) { el.textContent = 'Could not render: ' + e.message; });
}
function kindOf(name) { var m = /\.([a-z]+)$/i.exec(name); return m ? m[1].toLowerCase() : ''; }

// client preview while editing: Markdown and JSON as clean documents (same shapes as the server renderer)
function inl(t, base) {
  return esc(t).replace(/\x60([^\x60]+)\x60/g, '<code>$1</code>').replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (m, alt, src) {
    var p = resolveRel(base, src.replace(/&amp;/g, '&'));
    return p && /\.(png|jpe?g)$/i.test(p) ? '<span class="figure"><img alt="' + alt + '" src="/api/file?path=' + encodeURIComponent(p) + '"><span class="cap">' + alt + '</span></span>' : '<span class="img-missing">Image not available: ' + alt + '</span>';
  }).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/&lt;br\s*\/?&gt;/gi, '<br>');
}
function resolveRel(base, src) {
  if (/^[a-z][a-z0-9+.-]*:|^\/\//i.test(src) || src.charAt(0) === '/') return null;
  var parts = base.split('/'); parts.pop();
  try { src = decodeURI(src); } catch (e) { return null; }
  src.split('/').forEach(function (s) { if (s === '..') parts.pop(); else if (s && s !== '.') parts.push(s); });
  return parts.join('/');
}
function mdPreview(src, base) {
  src = src.replace(/\r/g, '').replace(/^---\n[\s\S]*?\n---\n?/, '');
  var out = [], lines = src.split('\n'), i = 0, LI = /^\s*([-*]|\d+\.)\s/;
  while (i < lines.length) {
    var l = lines[i], m;
    if (/^\x60\x60\x60/.test(l)) { var b = []; for (i++; i < lines.length && !/^\x60\x60\x60/.test(lines[i]); i++) b.push(lines[i]); i++; out.push('<pre><code>' + esc(b.join('\n')) + '</code></pre>'); continue; }
    if ((m = /^(#{1,6})\s+(.*)$/.exec(l))) { var n = Math.min(6, m[1].length + 2); out.push('<h' + n + '>' + inl(m[2], base) + '</h' + n + '>'); i++; continue; }
    if (/^\s*\|/.test(l)) {
      var rows = []; while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(lines[i++]);
      out.push('<div class="scroll"><table>' + rows.filter(function (r) { return !/^\s*\|?\s*:?-{2,}/.test(r); }).map(function (r, k) {
        var tg = k ? 'td' : 'th';
        return '<tr>' + r.trim().replace(/^\||\|$/g, '').split(/(?<!\\)\|/).map(function (c) { return '<' + tg + '>' + inl(c.trim().replace(/\\\|/g, '|'), base) + '</' + tg + '>'; }).join('') + '</tr>';
      }).join('') + '</table></div>'); continue;
    }
    if (LI.test(l)) { var li = []; while (i < lines.length && LI.test(lines[i])) li.push('<li>' + inl(lines[i++].replace(LI, ''), base) + '</li>'); out.push('<ul>' + li.join('') + '</ul>'); continue; }
    if (l.trim()) { var p = []; while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|\x60\x60\x60|\s*\|)/.test(lines[i]) && !LI.test(lines[i])) p.push(lines[i++]); if (!p.length) p.push(lines[i++]); out.push('<p>' + inl(p.join(' '), base) + '</p>'); continue; }
    i++;
  }
  return out.join('\n');
}
function human(k) { return String(k).replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[_-]+/g, ' ').trim().toLowerCase().replace(/\b(id|tc|fr|us|ac|qe|api|url|ui|e2e|sha|csv|json|md)\b/g, function (x) { return x.toUpperCase(); }).replace(/^./, function (c) { return c.toUpperCase(); }); }
function scalar(v) { return v === null || ['string', 'number', 'boolean'].indexOf(typeof v) >= 0; }
function cellText(v) { if (scalar(v)) return v === null ? '' : String(v); if (Array.isArray(v)) return v.map(cellText).join(v.every(scalar) ? ', ' : '; '); return Object.keys(v).map(function (k) { return human(k) + ': ' + cellText(v[k]); }).join('; '); }
function cell(v) { return esc(cellText(v)).replace(/\n/g, '<br>'); }
function jsonPreview(v) {
  function kv(pairs) { return pairs.length ? '<table class="kv-table"><tbody>' + pairs.map(function (p) { return '<tr><th>' + esc(human(p[0])) + '</th><td>' + cell(p[1]) + '</td></tr>'; }).join('') + '</tbody></table>' : ''; }
  function arr(a, d) {
    if (!a.length) return '<p class="muted">None.</p>';
    if (a.every(scalar)) return '<ul>' + a.map(function (x) { return '<li>' + cell(x) + '</li>'; }).join('') + '</ul>';
    var keys = []; a.forEach(function (o) { if (o && typeof o === 'object') Object.keys(o).forEach(function (k) { if (keys.indexOf(k) < 0) keys.push(k); }); });
    if (keys.length <= 7) return '<div class="scroll"><table class="data"><thead><tr>' + keys.map(function (k) { return '<th>' + esc(human(k)) + '</th>'; }).join('') + '</tr></thead><tbody>' + a.map(function (o) { return '<tr>' + keys.map(function (k) { return '<td>' + cell(o && o[k]) + '</td>'; }).join('') + '</tr>'; }).join('') + '</tbody></table></div>';
    return a.slice(0, 200).map(function (o, i) { var id = Object.keys(o || {}).filter(function (k) { return /^(tc_?id|case_?id|id|key|name|title)$/i.test(k); })[0]; return '<section class="rec"><h4>' + esc(id ? o[id] : 'Item ' + (i + 1)) + '</h4>' + obj(o, d + 1) + '</section>'; }).join('');
  }
  function obj(o, d) {
    if (!o || typeof o !== 'object') return '<p>' + cell(o) + '</p>';
    var ks = Object.keys(o).filter(function (k) { return k !== '_meta'; });
    var flat = ks.filter(function (k) { var x = o[k]; return scalar(x) || (Array.isArray(x) && x.every(scalar) && x.join(', ').length < 120); });
    var hd = 'h' + Math.min(6, d + 3);
    return kv(flat.map(function (k) { return [k, o[k]]; })) + ks.filter(function (k) { return flat.indexOf(k) < 0; }).map(function (k) { var x = o[k]; return '<' + hd + '>' + esc(human(k)) + (Array.isArray(x) ? ' <span class="count">' + x.length + '</span>' : '') + '</' + hd + '>' + (Array.isArray(x) ? arr(x, d) : d > 4 ? '<p>' + cell(x) + '</p>' : obj(x, d + 1)); }).join('');
  }
  return Array.isArray(v) ? arr(v, 0) : obj(v, 0);
}

// ---- in-gate editor (the only place documents are edited)
function buildEditor(body, f, after) {
  var base = f.content;
  editor = { path: f.path, sha: f.sha, dirty: false };
  var ta = h('textarea', { spellcheck: 'false', 'aria-label': 'Edit ' + f.path }); ta.value = f.content;
  var prev = h('div', { class: 'preview doc', 'aria-label': 'Preview' });
  var msg = h('div', { 'aria-live': 'polite' });
  var mark = h('span', { hidden: true }, tag('Unsaved changes', 'warn'));
  function paint() {
    editor.dirty = ta.value !== base; mark.hidden = !editor.dirty;
    if (f.kind === 'json') { try { prev.innerHTML = jsonPreview(JSON.parse(ta.value)); } catch (e) { prev.textContent = ''; prev.appendChild(note('bad', 'Invalid JSON', e.message)); } }
    else if (f.kind === 'md') prev.innerHTML = mdPreview(ta.value, f.path);
    else { prev.textContent = ''; prev.appendChild(h('pre', { text: ta.value })); }
  }
  function show(node) { msg.textContent = ''; msg.appendChild(node); }
  function save() {
    if (f.kind === 'json') { try { JSON.parse(ta.value); } catch (e) { show(note('bad', 'Not saved', 'Invalid JSON: ' + e.message)); return; } }
    api('/api/file', { method: 'PUT', headers: { 'Content-Type': 'application/json', 'X-QE-Token': TOKEN }, body: JSON.stringify({ path: f.path, content: ta.value, baseSha: editor.sha }) }).then(function (r) {
      editor.dirty = false;
      var n = h('div', null, 'Saved ' + f.path + '.');
      if (r.reopened.length) {
        add(n, h('div', { text: 'Reopened ' + r.reopened.map(function (g) { return 'Gate ' + g; }).join(', ') + '. Re-approve in your agent session, in order:' }));
        r.reopened.forEach(function (g) { add(n, cmdBox('Gate ' + g, g === 0 ? 'approve gate 0 for ' + (S.app || '<app>') : 'approve gate ' + g)); });
      }
      editor = null; toast('Saved');
      after(note(r.reopened.length ? 'warn' : 'ok', 'Saved', n));
    }, function (e) {
      if (e.status === 409) show(note('bad', 'Changed on disk', h('span', null, 'The file changed since you opened it. ', h('button', { class: 'btn secondary', type: 'button', onclick: function () { editor = null; after(null, true); } }, 'Reload (discards your edits)'))));
      else show(note('bad', 'Not saved', e.message));
    });
  }
  ta.addEventListener('input', paint);
  ta.addEventListener('keydown', function (e) { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') { e.preventDefault(); save(); } });
  body.textContent = '';
  add(body, [h('div', { class: 'toolbar' }, h('div', null, h('strong', { text: 'Editing' }), ' ', h('span', { class: 'muted', text: f.path })), h('div', null, mark, ' ', h('button', { class: 'btn', type: 'button', onclick: save }, 'Save'), ' ', h('button', { class: 'btn secondary', type: 'button', onclick: function () { if (editor && editor.dirty && !confirm('Discard unsaved changes?')) return; editor = null; after(null); } }, 'Cancel'))),
    note('info', null, 'Ctrl/Cmd+S saves. Saving reopens this gate and every later approved gate; you then re-approve them in order.'), msg,
    h('div', { class: 'editor' }, h('div', null, h('div', { class: 'label', text: f.kind === 'json' ? 'JSON source' : 'Markdown source' }), ta), h('div', null, h('div', { class: 'label', text: 'Preview' }), prev))]);
  paint(); editor.dirty = false;
}

// an artifact card: closed shows what it is; open shows the clean rendered document, with Edit inside the gate
function artifactCard(title, sub, kind, path, opts) {
  opts = opts || {};
  var key = opts.key || path, card = h('section', { class: 'tile artifact' + (opts.missing ? ' missing' : '') });
  var body = h('div', { class: 'body' });
  var headBtn = h('button', { class: 'head', type: 'button', 'aria-expanded': 'false', disabled: opts.missing ? true : null },
    h('span', { class: 'ico ' + kind, text: kind === 'report' ? 'RPT' : kind.toUpperCase() }), h('span', null, h('div', { class: 'name', text: title }), h('div', { class: 'sub', text: sub })));
  function open(msg) {
    // a save notice survives the live refresh that follows the save
    if (msg) flash = { key: key, node: msg, until: Date.now() + 10000 };
    else if (flash && flash.key === key && flash.until > Date.now()) msg = flash.node;
    card.classList.add('open'); headBtn.setAttribute('aria-expanded', 'true'); openCards[key] = true;
    body.textContent = '';
    var bar = h('div', { class: 'toolbar' }, h('span', { class: 'muted', text: path || '' }), h('span'));
    var doc = h('div', { class: 'doc' });
    add(body, [msg || null, bar, doc]);
    if (opts.load) opts.load(doc); else renderInto(doc, path);
    if (opts.editable) {
      api('/api/file?path=' + encodeURIComponent(path)).then(function (f) {
        if (!f.editable) { bar.lastChild.appendChild(h('span', { class: 'muted', title: f.reason || '', text: 'Read-only: ' + (f.reason || '') })); return; }
        bar.lastChild.appendChild(h('button', { class: 'btn secondary', type: 'button', onclick: function () { buildEditor(body, f, function (n) { open(n); }); } }, 'Edit'));
      }, function () { /* render error already shown */ });
    }
    if (!card.contains(body)) card.appendChild(body);
  }
  function close() { if (editor && editor.dirty && !confirm('Discard unsaved changes?')) return; editor = null; card.classList.remove('open'); headBtn.setAttribute('aria-expanded', 'false'); delete openCards[key]; if (card.contains(body)) card.removeChild(body); }
  headBtn.addEventListener('click', function () { if (card.classList.contains('open')) close(); else open(); });
  card.appendChild(headBtn);
  if (openCards[key] && !opts.missing) open();
  return card;
}

// ---- gate page
function viewGate(r) {
  var g = S.gates[Number(r.arg)];
  if (!g) return [h('p', { text: 'Unknown gate.' })];
  var out = pageHead([['Overview', '#/overview'], ['Gate ' + g.gate]], 'Gate ' + g.gate + ': ' + g.name, 'Approves ' + (g.covers.join(', ') || 'the run start'), tag(g.status));
  var act = h('div');
  if (g.status === 'APPROVED') add(act, h('div', { text: 'Approved ' + when(g.timestamp) + (g.recorded ? ' (recorded in the gate report; this folder has no run ledger).' : '.') }));
  else add(act, [h('div', { text: g.status === 'REOPENED' ? 'A document in this gate was edited after approval. Review it, then approve again:' : 'Review the artifacts below, then type in your agent session:' }), cmdBox('Approve', g.phrase)]);
  add(act, [h('div', { class: 'muted', text: 'Command that produces these artifacts:' }), cmdBox('Claude Code', '/agentic-qe:' + g.cmd + ' ' + (S.app || '<app>')), h('div', { class: 'muted', text: 'Approvals come only from your typed message. This page cannot approve.' })]);
  out.push(note(g.status === 'APPROVED' ? 'ok' : g.status === 'REOPENED' ? 'warn' : g.status === 'REJECTED' ? 'bad' : 'info', g.status === 'APPROVED' ? 'Gate approved' : 'Approval needed', act));
  if (g.gate === 5) guardrailProblems().forEach(function (p) { out.push(note('bad', 'Screenshot guardrail', p)); });
  var rep = reportOf(g.gate);
  out.push(h('h2', { class: 'section', text: 'Gate report' }));
  var rg = h('div', { class: 'artifacts' });
  // the saved report is the snapshot written at approval; while the gate is not approved, a live preview shows what it will say
  if (rep.exists) rg.appendChild(artifactCard('gate-' + g.gate + '-report.md', 'Saved at approval · ' + rep.rel, 'report', rep.path, { key: 'report-' + g.gate }));
  if (!rep.exists || g.status !== 'APPROVED') rg.appendChild(artifactCard('Live gate report', 'Built now from the current documents and results', 'report', rep.path, { key: 'live-' + g.gate, load: function (doc) { doc.textContent = 'Loading...'; doc.setAttribute('data-path', rep.path); api('/api/gate-report?gate=' + g.gate).then(function (x) { doc.innerHTML = x.html; }, function (e) { doc.textContent = e.message; }); } }));
  out.push(rg);
  gatePhases(g).forEach(function (p) {
    out.push(h('h2', { class: 'section', text: p.title + '  ·  ' + p.dir }));
    var grid = h('div', { class: 'artifacts' });
    p.docs.forEach(function (d) {
      var k = kindOf(d.file);
      grid.appendChild(artifactCard(d.file, d.exists ? size(d.size) + ' · updated ' + when(d.mtime) : 'Not produced yet', k === 'md' || k === 'json' || k === 'csv' ? k : 'md', d.path, { editable: true, missing: !d.exists }));
    });
    out.push(grid);
  });
  return out;
}

// ---- insights
function table(head, rows) { return h('div', { class: 'tile scroll', style: null }, rows.length ? h('table', { class: 'data' }, h('thead', null, h('tr', null, head.map(function (t) { return h('th', { text: t }); }))), h('tbody', null, rows)) : h('p', { class: 'muted', text: 'Nothing to show yet.' })); }
// the independent review: the weaker of the design and code scores decides what the case shows
function confOf(c) {
  var x = c.confidence || {}, items = [x.design, x.code].filter(Boolean), rank = { APPROVED: 0, REVISE: 1, REJECT: 2 };
  if (!items.length) return null;
  var w = items.slice().sort(function (a, b) { return rank[b.effective] - rank[a.effective] || a.total - b.total; })[0];
  return { total: w.total, verdict: w.effective, low: items.some(function (i) { return i.low; }) };
}
function confTag(c) {
  var k = confOf(c);
  return k ? tag(k.total + " " + k.verdict, KIND[k.verdict]) : tag('Not reviewed', 'pending');
}
function confMatches(c, want) { var k = confOf(c); return want === 'Low confidence' ? !!(k && k.low) : (k ? k.verdict : 'Not reviewed') === want; }
function resultTag(c) {
  var st = caseStatus(c), k = confOf(c);
  return st === 'PASS' && k && k.low ? tag('PASS (low confidence)', 'warn') : tag(st);
}
function confDetail(title, it, stamp) {
  var box = h('div'), kv = h('dl', { class: 'kv' });
  var comp = it.component || {};
  [['Component', comp.file ? comp.file + (comp.line ? ':' + comp.line : '') + (comp.symbol ? '  ' + comp.symbol : '') : ''], ['Test file', it.file], ['Evidence', it.evidence === 'verified' ? 'Every citation exists in the repository' : it.evidence === 'missing' ? 'A citation was not found in the repository' : stamp || 'Source not in this folder, so citations were not checked here']].forEach(function (p) { if (p[1]) { kv.appendChild(h('dt', { text: p[0] })); kv.appendChild(h('dd', { text: p[1] })); } });
  Object.keys(it.scores || {}).forEach(function (d) { kv.appendChild(h('dt', { text: human(d) })); kv.appendChild(h('dd', { text: String(it.scores[d]) })); });
  add(box, [h('h3', null, title + '  ', tag(it.total + ' ' + it.effective, KIND[it.effective])), kv]);
  if (it.lowReason) add(box, note('warn', 'Low confidence: a pass here is not counted as verified', it.lowReason));
  (it.flaws || []).forEach(function (fl) { add(box, note('warn', human(fl.dimension || 'Flaw') + '  ' + (fl.evidence || ''), fl.fix || '')); });
  (it.problems || []).forEach(function (p) { add(box, note('bad', 'Review record', p)); });
  return box;
}

function viewRequirements(r) {
  var f = r.q.get('verdict') || '';
  var sel = h('select', { 'aria-label': 'Filter by verdict', onchange: function () { location.hash = hashOf('requirements', { verdict: sel.value }); } },
    ['', 'PASSED', 'FAILED', 'PARTLY RUN', 'NOT RUN', 'NO TESTS'].map(function (v) { var o = h('option', { value: v, text: v || 'All verdicts' }); if (v === f) o.selected = true; return o; }));
  var rows = S.requirements.filter(function (x) { return !f || x.verdict === f; }).map(function (x) {
    return h('tr', null, h('td', null, h('span', { class: 'id', text: x.control })), h('td', null, h('div', { text: x.text || x.title || '' }), x.evidence ? h('div', { class: 'muted', text: x.evidence }) : null), h('td', { text: x.priority || '' }),
      h('td', null, x.cases.map(function (id) { return [h('a', { href: hashOf('cases', { tc: id }), text: id }), ' ']; })), h('td', null, tag(x.verdict)));
  });
  var out = pageHead([['Overview', '#/overview'], ['Requirements']], 'Requirements', S.requirements.length + ' requirements, ' + S.stories.length + ' user stories');
  out.push(h('div', { class: 'toolbar-row' }, sel), table(['Control ID', 'Requirement', 'Priority', 'Cases', 'Verdict'], rows));
  if (S.stories.length) {
    out.push(h('h2', { class: 'section', text: 'User stories' }));
    S.stories.forEach(function (s) { out.push(h('details', { class: 'case' }, h('summary', null, h('span', { class: 'id', text: s.id }), h('span', { class: 'grow', text: s.text })), h('div', { class: 'body' }, h('ol', null, s.acceptance.map(function (a, i) { return h('li', null, h('span', { class: 'id', text: s.id + '-AC' + (i + 1) }), ' ' + a); }))))); });
  }
  return out;
}
function caseBody(c) {
  var b = h('div', { class: 'body' }), kv = h('dl', { class: 'kv' });
  [['Requirement', c.requirement], ['Type', c.type], ['Priority', c.priority], ['Precondition', c.precondition], ['Test data', c.test_data], ['Expected', c.expected], ['Automation', c.automation], ['Remarks', c.remarks]].forEach(function (p) { if (p[1]) { kv.appendChild(h('dt', { text: p[0] })); kv.appendChild(h('dd', { text: String(p[1]) })); } });
  add(b, kv);
  if (c.steps && c.steps.length) add(b, [h('h3', { text: 'Steps', style: null }), h('ol', null, c.steps.map(function (s) { return h('li', { text: s }); }))]);
  if (c.files.length) add(b, [h('h3', { text: 'Generated tests' }), h('ul', null, c.files.map(function (p) { return h('li', null, h('a', { href: docHash(p), text: p })); }))]);
  if (c.result) add(b, h('p', null, 'Result ', tag(c.result.status), ' ', h('span', { class: 'muted', text: c.result.file })));
  if (c.result && c.result.message) add(b, note('bad', 'Why it failed', h('pre', { text: c.result.message })));
  if (c.healer) {
    var hk = h('dl', { class: 'kv' });
    [['Classification', c.healer.classification], ['Root cause', c.healer.detail], ['How to fix', c.healer.fix], ['Severity', c.healer.severity]].forEach(function (p) { if (p[1]) { hk.appendChild(h('dt', { text: p[0] })); hk.appendChild(h('dd', { text: p[1] })); } });
    add(b, [h('h3', { text: 'Healer diagnosis' }), hk]);
  }
  if (c.confidence && c.confidence.design) add(b, confDetail('Design confidence', c.confidence.design, S.confidence.design && S.confidence.design.stamp));
  if (c.confidence && c.confidence.code) add(b, confDetail('Generated test confidence', c.confidence.code, S.confidence.code && S.confidence.code.stamp));
  if (!confOf(c)) add(b, note('info', 'Not reviewed', 'The independent confidence review has not scored this case.'));
  var shots = ((S.evidence || {}).valid || []).filter(function (p) { return p.indexOf(c.tc_id) >= 0; });
  if (shots.length) add(b, [h('h3', { text: 'Screenshots' }), h('div', { class: 'gallery' }, shots.map(shotCard))]);
  return b;
}
function viewCases(r) {
  var f = { status: r.q.get('status') || '', level: r.q.get('level') || '', conf: r.q.get('conf') || '', q: r.q.get('q') || '', tc: r.q.get('tc') || '' };
  var levels = []; S.cases.forEach(function (c) { if (c.level && levels.indexOf(c.level) < 0) levels.push(c.level); });
  var list = h('div'), count = h('p', { class: 'muted' });
  var items = S.cases.map(function (c) {
    var d = h('details', { class: 'case', id: 'case-' + c.tc_id }, h('summary', null, h('span', { class: 'id', text: c.tc_id }), h('span', { class: 'grow', text: c.scenario || '' }), h('span', { class: 'muted', text: [c.level, c.type, c.priority].filter(Boolean).join(' · ') }), confTag(c), resultTag(c)));
    d.addEventListener('toggle', function () { if (d.open && d.children.length === 1) d.appendChild(caseBody(c)); });
    return { c: c, el: d };
  });
  items.forEach(function (i) { list.appendChild(i.el); });
  function apply() {
    var n = 0;
    items.forEach(function (i) {
      var ok = (!f.status || caseStatus(i.c) === f.status) && (!f.level || i.c.level === f.level) && (!f.conf || confMatches(i.c, f.conf)) && (!f.tc || i.c.tc_id === f.tc) && (!f.q || (i.c.tc_id + ' ' + (i.c.scenario || '') + ' ' + (i.c.story_id || '')).toLowerCase().indexOf(f.q.toLowerCase()) >= 0);
      i.el.hidden = !ok; if (ok) n++;
    });
    count.textContent = n + ' of ' + items.length + ' cases';
    history.replaceState(null, '', hashOf('cases', f)); lastHash = location.hash;
  }
  function select(label, key, opts) { var s = h('select', { 'aria-label': label, onchange: function () { f[key] = s.value; f.tc = ''; apply(); } }, [h('option', { value: '', text: label })].concat(opts.map(function (o) { var e = h('option', { value: o, text: o }); if (o === f[key]) e.selected = true; return e; }))); return s; }
  var search = h('input', { type: 'search', placeholder: 'Search ID, scenario or requirement', 'aria-label': 'Search test cases', value: f.q, oninput: function () { f.q = search.value; f.tc = ''; apply(); } });
  var out = pageHead([['Overview', '#/overview'], ['Test cases']], 'Test cases', S.cases.length + ' designed cases');
  out.push(h('div', { class: 'toolbar-row' }, select('All results', 'status', ['PASS', 'FAIL', 'SKIPPED', 'NOT RUN']), select('All levels', 'level', levels), select('All confidence', 'conf', ['Low confidence', 'APPROVED', 'REVISE', 'REJECT', 'Not reviewed']), search), count, list);
  apply();
  if (f.tc) { var hit = items.filter(function (i) { return i.c.tc_id === f.tc; })[0]; if (hit) { hit.el.open = true; setTimeout(function () { hit.el.scrollIntoView(); }, 0); } }
  return out;
}
function viewTrace() {
  var rows = [];
  S.requirements.forEach(function (rq) {
    var mine = S.cases.filter(function (c) { return rq.cases.indexOf(c.tc_id) >= 0; });
    if (!mine.length) rows.push(h('tr', null, h('td', { class: 'id', text: rq.control }), h('td', { class: 'muted', text: 'no test case' }), h('td'), h('td'), h('td'), h('td', null, tag(rq.verdict))));
    mine.forEach(function (c) { rows.push(h('tr', null, h('td', { class: 'id', text: rq.control }), h('td', null, h('a', { href: hashOf('cases', { tc: c.tc_id }), text: c.tc_id })), h('td', { text: c.level || '' }), h('td', null, confTag(c)), h('td', null, resultTag(c)), h('td', null, tag(rq.verdict)))); });
  });
  return pageHead([['Overview', '#/overview'], ['Traceability']], 'Traceability', 'Requirement to test case to result').concat([table(['Requirement', 'Case', 'Level', 'Confidence', 'Result', 'Requirement verdict'], rows)]);
}
function viewResults() {
  var out = pageHead([['Overview', '#/overview'], ['Results']], 'Results', 'Runs recorded in results/');
  out.push(table(['Run', 'Total', 'Passed', 'Failed', 'Skipped', 'Duration', 'Status'], S.executions.map(function (e) { return h('tr', null, h('td', { text: e.label || e.file }), h('td', { text: e.total }), h('td', { text: e.passed }), h('td', { text: e.failed }), h('td', { text: e.skipped }), h('td', { text: (e.durationMs / 1000).toFixed(1) + ' s' }), h('td', null, tag(e.status))); })));
  var failed = S.cases.filter(function (c) { return caseStatus(c) === 'FAIL'; });
  if (failed.length) {
    out.push(h('h2', { class: 'section', text: 'Failed cases' }));
    out.push(table(['Case', 'Scenario', 'Why it failed'], failed.map(function (c) { return h('tr', null, h('td', null, h('a', { href: hashOf('cases', { tc: c.tc_id }), text: c.tc_id })), h('td', { text: c.scenario || '' }), h('td', { text: (c.result.message || '').split('\n')[0] })); })));
  }
  return out;
}
function viewDefects() {
  var out = pageHead([['Overview', '#/overview'], ['Defects']], 'Defects', S.defects.length ? plural(S.defects.length, 'application defect') + ' found by the run' : 'No application defects');
  S.defects.forEach(function (d) {
    var kv = h('dl', { class: 'kv' });
    [['Case', d.tc_id], ['Requirement', d.requirement], ['Why it failed', d.message || d.evidence], ['Root cause', d.root_cause], ['How to fix', d.fix], ['Test file', d.test_file]].forEach(function (p) {
      if (!p[1]) return;
      kv.appendChild(h('dt', { text: p[0] }));
      kv.appendChild(h('dd', null, p[0] === 'Case' ? h('a', { href: hashOf('cases', { tc: p[1] }), text: p[1] }) : p[0] === 'Test file' ? h('a', { href: docHash(String(p[1]).split(':')[0]), text: p[1] }) : String(p[1])));
    });
    out.push(h('section', { class: 'tile', style: null }, h('div', { class: 'toolbar' }, h('h3', { text: d.scenario || d.tc_id }), d.severity ? tag(String(d.severity), 'bad') : null), kv));
    out[out.length - 1].style.marginBottom = '12px';
  });
  return out;
}
function shotCard(p) {
  var name = p.split('/').pop();
  return h('figure', { class: 'tile shot', style: null }, h('img', { src: imgUrl('docs/qe/' + S.app + '/' + p), alt: 'Screenshot ' + name, loading: 'lazy' }), h('figcaption', { class: 'cap' }, h('span', { class: 'id', text: name.replace(/\.(png|jpe?g)$/i, '') }), h('span', { class: 'muted', text: p.split('/').slice(-2, -1)[0] || '' })));
}
function viewEvidence() {
  var ev = S.evidence || { valid: [], invalid: [] }, probs = guardrailProblems();
  var out = pageHead([['Overview', '#/overview'], ['Evidence']], 'Evidence', plural(ev.valid.length, 'screenshot') + ' in 06-execution/evidence/');
  out.push(probs.length ? note('bad', 'Screenshot guardrail', h('ul', null, probs.map(function (p) { return h('li', { text: p }); }))) : note('ok', 'Screenshot guardrail', ev.valid.length ? 'Every screenshot is shown in the Gate 5 report and here.' : 'No screenshots yet. After the UI suite, run collect-evidence.ts to copy them from the Playwright report.'));
  out.push(h('div', { class: 'gallery' }, ev.valid.map(shotCard)));
  return out;
}
function viewActivity() {
  var rows = S.ledger.slice().reverse().map(function (e) { return h('tr', null, h('td', { class: 'muted', text: when(e.time) }), h('td', null, tag(e.kind, 'plain')), h('td', { text: e.detail })); });
  return pageHead([['Overview', '#/overview'], ['Activity']], 'Activity', S.ledgerTotal + ' ledger events, newest first').concat([table(['Time', 'Event', 'Detail'], rows)]);
}
// read-only document view for links (test sources, results); editing happens only inside a gate
function viewDoc(r) {
  var p = r.q.get('path') || '', doc = h('div', { class: 'doc' });
  if (/\.(png|jpe?g)$/i.test(p)) doc.appendChild(h('img', { src: imgUrl(p), alt: p, style: null }));
  else renderInto(doc, p);
  return pageHead([['Overview', '#/overview'], ['Document']], p.split('/').pop() || 'Document', p).concat([note('info', null, 'Read-only view. Documents are edited inside their gate.'), h('section', { class: 'tile' }, doc)]);
}

// ---- routing and live updates
function route() {
  var raw = location.hash.replace(/^#\/?/, ''), i = raw.indexOf('?');
  var parts = (i < 0 ? raw : raw.slice(0, i)).split('/');
  return { view: parts[0] || 'overview', arg: parts[1], q: new URLSearchParams(i < 0 ? '' : raw.slice(i + 1)) };
}
var VIEWS = { overview: viewOverview, gate: viewGate, requirements: viewRequirements, cases: viewCases, trace: viewTrace, results: viewResults, defects: viewDefects, evidence: viewEvidence, activity: viewActivity, doc: viewDoc };
function render() {
  var r = route(), main = document.getElementById('main');
  renderTop(); renderNav(r);
  if (!S) return;
  editor = null;
  var y = window.scrollY;
  main.textContent = '';
  add(main, (VIEWS[r.view] || viewOverview)(r));
  document.body.classList.remove('nav-open');
  document.title = 'Agentic QE · ' + (S.app || 'no app');
  if (render.same) window.scrollTo(0, y);
}
function refresh() {
  return api('/api/state').then(function (x) {
    S = x;
    if (editor) { renderTop(); renderNav(route()); return; } // never replace an open editor
    render.same = true; render(); render.same = false;
  }, function (e) {
    document.getElementById('main').textContent = e.status === 401 ? 'Not signed in. Open the link the plugin opened in your browser at the run start, or run /agentic-qe:qe-panel --serve --link to print it again.' : 'Could not load: ' + e.message;
  });
}
function connect() {
  var es = new EventSource('/api/events');
  es.onopen = function () { var back = !live; live = true; renderTop(); if (back) refresh(); }; // catch up on anything missed while disconnected
  es.onerror = function () { live = false; renderTop(); };
  es.addEventListener('change', function () {
    if (editor && editor.dirty) toast('Files changed on disk. Your unsaved edits are kept.');
    clearTimeout(refreshTimer); refreshTimer = setTimeout(refresh, 200);
  });
}
window.addEventListener('hashchange', function () {
  if (editor && editor.dirty && !confirm('Discard unsaved changes?')) { history.replaceState(null, '', lastHash || '#/overview'); return; }
  if (route().view !== 'gate') openCards = {};
  lastHash = location.hash; editor = null; render(); window.scrollTo(0, 0);
});
// relative links inside a rendered document open the read-only document view instead of leaving the app
document.addEventListener('click', function (e) {
  var a = e.target.closest && e.target.closest('.doc a[href]'), host = a && a.closest('[data-path]');
  if (!a || !host) return;
  var href = a.getAttribute('href');
  if (/^(https?:|#|mailto:)/i.test(href)) { if (/^https?:/i.test(href)) a.setAttribute('target', '_blank'), a.setAttribute('rel', 'noopener noreferrer'); return; }
  var p = resolveRel(host.getAttribute('data-path'), href.split('#')[0]);
  e.preventDefault();
  if (p) location.hash = docHash(p);
});
window.addEventListener('beforeunload', function (e) { if (editor && editor.dirty) { e.preventDefault(); e.returnValue = ''; } });
applyTheme(theme());
renderTop();
refresh().then(function () { if (!STATIC) connect(); });
})();
`;
