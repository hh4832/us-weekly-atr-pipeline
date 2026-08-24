import fs from "node:fs/promises";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2];
await fs.mkdir(outputDir, { recursive: true });

const wb = Workbook.create();
const navy = "#174A66";
const blue = "#DCEAF2";
const input = "#FFF2CC";
const green = "#E2F0D9";
const red = "#FCE4D6";

function header(sheet, range) {
  sheet.getRange(range).format = {
    fill: navy,
    font: { bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "bottom", style: "medium", color: "#174A66" },
  };
}

function common(sheet, freezeRows = 1) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(freezeRows);
  sheet.getUsedRange().format.font = { name: "Aptos", size: 10 };
  sheet.getUsedRange().format.autofitRows();
}

const guide = wb.worksheets.add("使用說明");
guide.getRange("A1:F1").merge();
guide.getRange("A1").values = [["US Equity 3-Day ATR Pipeline | Google Sheet Template"]];
guide.getRange("A1:F1").format = { fill: navy, font: { bold: true, color: "#FFFFFF", size: 16 }, rowHeight: 32 };
guide.getRange("A3:B9").values = [
  ["When", "Required action"],
  ["Sunday", "Update market values, ETF weights, and target dollars in column P of the existing calculation sheet."],
  ["Day1", "Generate orders; enter actual fills in filled_price on the execution log."],
  ["After Day1", "Verify that every remaining blank truly means unfilled, then complete daily reconciliation in the app."],
  ["Day2", "Process only Day1 blanks; k = Day1 k x 0.6."],
  ["Day3", "Submit remaining orders as MARKET and still enter every actual filled_price."],
  ["Safety", "No reconciliation, no next day. Re-running on the same ET date never advances or duplicates orders."],
];
header(guide, "A3:B3");
guide.getRange("A4:A9").format = { fill: blue, font: { bold: true } };
guide.getRange("B4:B9").format.wrapText = true;
guide.getRange("A11:F11").merge();
guide.getRange("A11").values = [["Yellow: user input | Blue: program managed | Green: completed | Red: action required"]];
guide.getRange("A11:F11").format = { fill: "#F3F6F8", font: { italic: true, color: "#44546A" } };
guide.getRange("A:A").format.columnWidth = 18;
guide.getRange("B:B").format.columnWidth = 72;
common(guide, 3);

const settings = wb.worksheets.add("設定");
settings.getRange("A1:C7").values = [
  ["parameter", "value", "description"],
  ["source_sheet_name", "計算", "Existing allocation sheet"],
  ["source_ticker_column", "A", "Ticker column"],
  ["source_target_column", "P", "Target-dollar column"],
  ["market_immediate_rule", "calculated_limit >= current_price", "Switch to MARKET when true"],
  ["day2_k_multiplier", 0.6, "Day2 k = Day1 k × 0.6"],
  ["timezone", "America/New_York", "Trading-date timezone"],
];
header(settings, "A1:C1");
settings.getRange("B2:B7").format = { fill: input, font: { color: "#0000FF" } };
settings.getRange("A:C").format.columnWidth = 28;
settings.getRange("C:C").format.columnWidth = 42;
common(settings);

const inputSheet = wb.worksheets.add("程式輸入");
inputSheet.getRange("A1:C13").values = [
  ["ticker", "target_dollar", "duplicate_count"], ["AVGO", 220, null], ["CEG", 140, null], ["FRO", 80, null], ["GOOGL", 200, null],
  ["HWM", 180, null], ["LLY", 300, null], ["NVDA", 280, null], ["RKLB", 160, null], ["TKO", 80, null],
  ["TSLA", 220, null], ["WMT", 80, null], ["XOM", 60, null],
];
inputSheet.getRange("C2").formulas = [["=IF(A2=\"\",0,COUNTIF($A$2:$A$101,A2))"]];
inputSheet.getRange("C2:C101").fillDown();
header(inputSheet, "A1:C1");
inputSheet.getRange("A2:B13").format = { fill: blue, font: { color: "#008000" } };
inputSheet.getRange("B2:B13").format.numberFormat = "$#,##0.00;[Red]($#,##0.00);-";
inputSheet.getRange("D1:E3").values = [["檢查", "結果"], ["target dollar 合計", null], ["計畫檔數", null]];
inputSheet.getRange("E2").formulas = [["=SUM(B2:B101)"]];
inputSheet.getRange("E3").formulas = [["=COUNTA(A2:A101)"]];
header(inputSheet, "D1:E1");
inputSheet.getRange("E2").format.numberFormat = "$#,##0.00";
inputSheet.getRange("A:C").format.columnWidth = 20;
inputSheet.getRange("D:E").format.columnWidth = 22;
common(inputSheet);

const plan = wb.worksheets.add("每週計畫");
plan.getRange("A1:F4").values = [
  ["plan_id", "created_at_et", "ticker", "target_dollar", "plan_status", "source_sheet"],
  ["2026-W35", "2026-08-24T10:05:00-04:00", "AVGO", 220, "LOCKED", "程式輸入"],
  ["2026-W35", "2026-08-24T10:05:00-04:00", "CEG", 140, "LOCKED", "程式輸入"],
  ["2026-W35", "2026-08-24T10:05:00-04:00", "NVDA", 280, "LOCKED", "程式輸入"],
];
header(plan, "A1:F1");
plan.getRange("D2:D100").format.numberFormat = "$#,##0.00";
plan.getRange("E2:E100").format.fill = blue;
plan.getRange("A:F").format.columnWidth = 22;
common(plan);

const log = wb.worksheets.add("執行紀錄");
const logHeaders = ["plan_id", "order_date", "ticker", "day", "target_dollar", "order_type", "limit_price", "reference_price", "shares", "market_state", "stock_state", "k1", "k_used", "close_y", "atr", "filled_price", "filled_date", "notes"];
log.getRange("A1:R3").values = [
  logHeaders,
  ["2026-W35", "2026-08-24", "AVGO", "Day1", 220, "LIMIT", 360.39, 362.1, 0.6104, "Neutral", "Bear", 0.6, 0.6, 368.45, 13.4404, 359.8, "2026-08-24", ""],
  ["2026-W35", "2026-08-24", "CEG", "Day1", 140, "LIMIT", 268.92, 271.2, 0.5206, "Neutral", "Neutral", 0.4, 0.4, 272.75, 9.5696, null, null, "Blank = unfilled; advances after reconciliation"],
];
header(log, "A1:R1");
log.getRange("P2:Q1000").format = { fill: input, font: { color: "#0000FF" } };
log.getRange("E2:E1000").format.numberFormat = "$#,##0.00";
log.getRange("G2:H1000").format.numberFormat = "$0.00";
log.getRange("I2:I1000").format.numberFormat = "0.0000";
log.getRange("L2:M1000").format.numberFormat = "0.00";
log.getRange("N2:P1000").format.numberFormat = "$0.0000";
log.getRange("A:R").format.columnWidth = 16;
log.getRange("R:R").format.columnWidth = 38;
common(log);

const confirm = wb.worksheets.add("每日確認");
confirm.getRange("A1:G3").values = [
  ["plan_id", "day", "order_date", "confirmed", "confirmed_at_et", "blank_count", "notes"],
  ["2026-W35", "Day1", "2026-08-24", true, "2026-08-24T16:20:00-04:00", 1, "FT reconciled"],
  ["2026-W35", "Day2", "2026-08-25", false, null, null, "Unconfirmed; Day3 blocked"],
];
header(confirm, "A1:G1");
confirm.getRange("D2:G1000").format.fill = input;
confirm.getRange("D2").format.fill = green;
confirm.getRange("D3").format.fill = red;
confirm.getRange("A:G").format.columnWidth = 22;
confirm.getRange("G:G").format.columnWidth = 38;
common(confirm);

const checks = wb.worksheets.add("檢查");
checks.getRange("A1:F6").values = [
  ["Check", "Actual", "Expected", "Difference", "Status", "Fix"],
  ["Target dollar total", null, 2000, null, null, "Confirm this week's budget"],
  ["Duplicate tickers", null, 0, null, null, "Each ticker must be unique"],
  ["Blank Day3 filled prices", null, 0, null, null, "Enter every actual MARKET fill"],
  ["Unreconciled days", null, 0, null, null, "Reconcile the preceding day"],
  ["Model status", null, null, null, null, "Proceed only when every check is OK"],
];
checks.getRange("B2").formulas = [["='程式輸入'!E2"]];
checks.getRange("D2").formulas = [["=B2-C2"]];
checks.getRange("E2").formulas = [["=IF(ABS(D2)<0.01,\"OK\",\"CHECK\")"]];
checks.getRange("B3").formulas = [["=COUNTIF('程式輸入'!C2:C101,\">1\")"]];
checks.getRange("D3").formulas = [["=B3-C3"]];
checks.getRange("E3").formulas = [["=IF(D3=0,\"OK\",\"CHECK\")"]];
checks.getRange("B4").formulas = [["=COUNTIFS('執行紀錄'!D2:D1000,\"Day3\",'執行紀錄'!P2:P1000,\"\")"]];
checks.getRange("D4").formulas = [["=B4-C4"]];
checks.getRange("E4").formulas = [["=IF(D4=0,\"OK\",\"CHECK\")"]];
checks.getRange("B5").formulas = [["=COUNTIFS('每日確認'!A2:A1000,\"<>\",'每日確認'!D2:D1000,FALSE)"]];
checks.getRange("D5").formulas = [["=B5-C5"]];
checks.getRange("E5").formulas = [["=IF(D5=0,\"OK\",\"CHECK\")"]];
checks.getRange("E6").formulas = [["=IF(COUNTIF(E2:E5,\"CHECK\")=0,\"OK\",\"CHECK\")"]];
header(checks, "A1:F1");
checks.getRange("A2:A6").format = { fill: blue, font: { bold: true } };
checks.getRange("B2:D6").format.numberFormat = "#,##0.00;[Red](#,##0.00);-";
checks.getRange("E2:E6").format.font = { bold: true };
checks.getRange("A:F").format.columnWidth = 25;
checks.getRange("F:F").format.columnWidth = 44;
common(checks);

const inspect = await wb.inspect({ kind: "table", range: "執行紀錄!A1:R3", include: "values,formulas", tableMaxRows: 5, tableMaxCols: 18 });
console.log(inspect.ndjson);
const errors = await wb.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 100 }, summary: "formula error scan" });
console.log(errors.ndjson);

for (const sheetName of ["使用說明", "設定", "程式輸入", "每週計畫", "執行紀錄", "每日確認", "檢查"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outputDir}/preview_${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}

const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${outputDir}/google_sheet_pipeline_template.xlsx`);
