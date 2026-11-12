"""Build the Azure proposal workbook (and one CSV per sheet) from the live Azure Retail Prices fetch.

python build_proposal.py <retail.json> <out.xlsx> <csv dir>
"""
import csv
import json
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from proposal_content import ARCH, ASSUME, EVIDENCE, GAPS, STEPS, UI, lines, options, proposal_rows  # noqa: E402

retail, out_xlsx, csv_dir = json.load(open(sys.argv[1])), Path(sys.argv[2]), Path(sys.argv[3])
FETCHED = retail["fetched_utc"]
API = "https://prices.azure.com/api/retail/prices"

FONT = "Arial"
BASE = Font(name=FONT, size=10)
BOLD = Font(name=FONT, size=10, bold=True)
TITLE = Font(name=FONT, size=14, bold=True)
INPUT = Font(name=FONT, size=10, color="0000FF")
LINK = Font(name=FONT, size=10, color="008000")
HEAD_FILL = PatternFill("solid", fgColor="D9D9D9")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(wrap_text=True, vertical="top")
USD = '"$"#,##0.00;("$"#,##0.00);"-"'
USD4 = '"$"#,##0.0000;("$"#,##0.0000);"-"'
INR = '"₹"#,##0.00;("₹"#,##0.00);"-"'
INR4 = '"₹"#,##0.0000;("₹"#,##0.0000);"-"'
NUM = '#,##0.00;(#,##0.00);"-"'

wb = Workbook()
sheets = {}


def sheet(name, widths):
    ws = wb.active if not sheets else wb.create_sheet()
    ws.title = name
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.sheet_view.showGridLines = False
    sheets[name] = ws
    return ws


def header(ws, row, values):
    for c, v in enumerate(values, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.font, cell.fill, cell.border, cell.alignment = BOLD, HEAD_FILL, BOX, WRAP
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def put(ws, row, values, fonts=None, formats=None):
    for c, v in enumerate(values, 1):
        cell = ws.cell(row=row, column=c, value=v)
        cell.font = (fonts or {}).get(c, BASE)
        cell.border, cell.alignment = BOX, WRAP
        if formats and c in formats:
            cell.number_format = formats[c]


def table(ws, start, head, rows):
    header(ws, start, head)
    for i, r in enumerate(rows, start + 1):
        put(ws, i, r)
    return start + len(rows)


def pick(key, sku, meter, tier=0.0, product=None):
    found = {}
    for cur in ("USD", "INR"):
        rows = [r for r in retail["items"][f"{key}|{cur}"] if r["skuName"] == sku and r["meterName"] == meter
                and float(r["tierMinimumUnits"]) == tier and (product is None or r["productName"] == product)]
        if len(rows) != 1:
            raise SystemExit(f"expected one row for {key} {sku} {meter} {tier} {cur}, got {len(rows)}")
        found[cur] = rows[0]
    return found


ev = sheet("Price Evidence", [14, 30, 44, 20, 34, 14, 12, 13, 13, 13, 13])
ev["A1"], ev["A1"].font = "Price evidence: Azure Retail Prices API, East US 2, pay-as-you-go", TITLE
ev["A2"], ev["A2"].font = f"Retrieved {FETCHED} from {API} with currencyCode=USD and currencyCode=INR. Prices exclude taxes (GST in India).", BASE
EV_HEAD = ["Key", "Service", "Product", "SKU", "Meter", "Unit", "Tier from", "USD price", "INR price", "INR per USD", "Effective from"]
header(ev, 4, EV_HEAD)
ROW = {}
for i, (key, rk, sku, meter, tier, product) in enumerate(EVIDENCE, 5):
    p = pick(rk, sku, meter, tier, product)
    u, n = p["USD"], p["INR"]
    put(ev, i, [key, u["serviceName"], u["productName"], u["skuName"], u["meterName"], u["unitOfMeasure"], u["tierMinimumUnits"],
                u["unitPrice"], n["unitPrice"], f"=IFERROR(I{i}/H{i},\"-\")", u["effectiveStartDate"][:10]],
        fonts={8: INPUT, 9: INPUT}, formats={7: "#,##0", 8: USD4, 9: INR4, 10: "0.00"})
    ROW[key] = i
last_ev = 4 + len(EVIDENCE)
r = last_ev + 2
ev.cell(row=r, column=1, value="How to re-check").font = BOLD
ev.cell(row=r + 1, column=1, value="Query: GET " + API + "?$filter=armRegionName eq 'eastus2' and priceType eq 'Consumption' and skuName eq 'B1'&currencyCode=INR").font = BASE
ev.cell(row=r + 2, column=1, value="Blue figures are the API's unit prices as retrieved; replace them to re-price the whole workbook. INR per USD is implied by Azure's own two price lists, not a bank rate.").font = BASE


def price(key, cur):
    col = "H" if cur == "USD" else "I"
    return f"'Price Evidence'!${col}${ROW[key]}"


asum = sheet("Assumptions", [44, 14, 12, 70])
asum["A1"], asum["A1"].font = "Assumptions (blue cells are inputs; change them to re-price)", TITLE
header(asum, 3, ["Assumption", "Value", "Unit", "Basis"])
A = {}
for i, (key, label, value, unit, basis) in enumerate(ASSUME, 4):
    put(asum, i, [label, value, unit, basis], fonts={2: INPUT}, formats={2: "#,##0.00"})
    A[key] = f"Assumptions!$B${i}"

cost = sheet("Cost Estimate", [36, 30, 13, 13, 12, 12, 14, 14, 50])
cost["A1"], cost["A1"].font = "Monthly cost estimate, East US 2 (standard deployment)", TITLE
cost["A2"], cost["A2"].font = f"Unit prices link to 'Price Evidence' (retrieved {FETCHED}); quantities link to 'Assumptions'. Excludes taxes and model tokens.", BASE
header(cost, 4, ["Resource", "Meter", "USD per unit", "INR per unit", "Quantity", "Unit", "USD per month", "INR per month", "Note"])
first = 5
LINES = lines(A)
for i, (name, meter, key, qty, unit, note) in enumerate(LINES, first):
    put(cost, i, [name, meter, f"={price(key, 'USD')}", f"={price(key, 'INR')}", f"={qty}", unit, f"=C{i}*E{i}", f"=D{i}*E{i}", note],
        fonts={3: LINK, 4: LINK, 5: LINK}, formats={3: USD4, 4: INR4, 5: NUM, 7: USD, 8: INR})
last = first + len(LINES) - 1
tot = last + 1
put(cost, tot, ["Total per month", "", "", "", "", "", f"=SUM(G{first}:G{last})", f"=SUM(H{first}:H{last})", "Owner cap: USD 25 a month."],
    fonts={1: BOLD, 7: BOLD, 8: BOLD}, formats={7: USD, 8: INR})
put(cost, tot + 1, ["Per year", "", "", "", "", "", f"=G{tot}*12", f"=H{tot}*12", ""], formats={7: USD, 8: INR})
put(cost, tot + 2, ["Within the USD 25 cap?", "", "", "", "", "", f"=IF(G{tot}<=25,\"Yes\",\"No\")", "", ""], fonts={7: BOLD})
put(cost, tot + 3, ["Per person per month", "", "", "", "", "", f"=G{tot}/{A['USERS']}", f"=H{tot}/{A['USERS']}", "Divided by 'People using the web app'."],
    formats={7: USD, 8: INR})

# scenarios
s0 = tot + 6
cost.cell(row=s0 - 1, column=1, value="Options compared (same storage, Blob and Key Vault lines)").font = BOLD
header_row = s0
for c, v in enumerate(["Option", "Plan", "USD plan", "USD database", "USD other", "", "USD per month", "INR per month", "Within cap?"], 1):
    cell = cost.cell(row=header_row, column=c, value=v)
    cell.font, cell.fill, cell.border, cell.alignment = BOLD, HEAD_FILL, BOX, WRAP
other_usd = f"SUM(G{first + 2}:G{last})"
other_inr = f"SUM(H{first + 2}:H{last})"
for i, (name, plan, app, app_h, db, db_h) in enumerate(options(A), header_row + 1):
    put(cost, i, [name, plan, f"={price(app, 'USD')}*{app_h}", f"={price(db, 'USD')}*{db_h}", f"={other_usd}", "",
                  f"=C{i}+D{i}+E{i}", f"={price(app, 'INR')}*{app_h}+{price(db, 'INR')}*{db_h}+{other_inr}", f"=IF(G{i}<=25,\"Yes\",\"No (needs owner's yes)\")"],
        formats={3: USD, 4: USD, 5: USD, 7: USD, 8: INR})

pro = sheet("Proposal", [30, 100])
wb.move_sheet("Proposal", offset=-(len(wb.sheetnames) - 1))
pro["A1"], pro["A1"].font = "Agentic QE Platform: Azure hosting proposal (East US 2)", TITLE
pro["A2"], pro["A2"].font = f"Prepared 2026-11-12. Prices verified live against the Azure Retail Prices API at {FETCHED}.", BASE
for i, (k, v) in enumerate(proposal_rows(FETCHED, tot, header_row), 4):
    put(pro, i, [k, v], fonts={1: BOLD})
    if k.startswith(("Monthly cost (USD", "Yearly cost (USD", "Always-on")):
        pro.cell(row=i, column=2).number_format = USD
        pro.cell(row=i, column=2).font = BOLD
        pro.cell(row=i, column=2).alignment = Alignment(horizontal="left")
    if k.startswith(("Monthly cost (INR", "Yearly cost (INR")):
        pro.cell(row=i, column=2).number_format = INR
        pro.cell(row=i, column=2).font = BOLD
        pro.cell(row=i, column=2).alignment = Alignment(horizontal="left")
    if k == "Within the USD 25 cap":
        pro.cell(row=i, column=2).font = BOLD

arch = sheet("Architecture", [26, 34, 26, 60, 44])
arch["A1"], arch["A1"].font = "Architecture: what we use and why", TITLE
table(arch, 3, ["Component", "Azure service", "Size / SKU", "Why we use it", "Alternatives considered"], ARCH)

dep = sheet("Deployment Steps", [7, 20, 34, 62, 44])
dep["A1"], dep["A1"].font = "Deployment steps (Azure portal), in order", TITLE
dep["A2"], dep["A2"].font = "Replace <unique> with your own short tag. Full text: docs/AZURE_DEPLOYMENT_GUIDE.md in the repository.", BASE
table(dep, 4, ["Step", "Phase", "Where (portal path)", "Action and values", "Verify"], [(i,) + s for i, s in enumerate(STEPS, 1)])

ui = sheet("UI Guide", [7, 22, 18, 66, 40])
ui["A1"], ui["A1"].font = "UI guide: step by step for each person", TITLE
ui["A2"], ui["A2"].font = "The same pages run on Azure, locally and in the desktop app. Screenshots: docs/evidence in the repository.", BASE
table(ui, 4, ["Step", "Page", "Who", "What to do", "You should see"], [(i,) + s for i, s in enumerate(UI, 1)])

gap = sheet("Gaps and Fixes", [7, 44, 60, 16])
gap["A1"], gap["A1"].font = "Review of the Azure guide against live prices (2026-11-12)", TITLE
table(gap, 3, ["#", "Gap found", "Fix", "State"], GAPS)

for ws in wb.worksheets:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0

ORDER = ["Proposal", "Cost Estimate", "Assumptions", "Price Evidence", "Architecture", "Deployment Steps", "UI Guide", "Gaps and Fixes"]
wb._sheets = [wb[n] for n in ORDER]
wb.active = 0
out_xlsx.parent.mkdir(parents=True, exist_ok=True)
wb.save(out_xlsx)
print("saved", out_xlsx, wb.sheetnames)
