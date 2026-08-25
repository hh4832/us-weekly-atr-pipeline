from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from gspread.http_client import BackOffHTTPClient

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SHEET_HEADERS = {
    "設定": ["parameter", "value", "description"],
    "每週計畫": ["plan_id", "created_at_et", "ticker", "target_dollar", "plan_status", "source_sheet"],
    "執行紀錄": [
        "plan_id", "order_date", "ticker", "day", "target_dollar", "order_type",
        "limit_price", "reference_price", "shares", "market_state", "stock_state",
        "k1", "k_used", "close_y", "atr", "filled_price", "filled_date", "notes",
    ],
    "每日確認": ["plan_id", "day", "order_date", "confirmed", "confirmed_at_et", "blank_count", "notes"],
    "程式輸入": ["ticker", "target_dollar", "duplicate_count"],
}


def _credentials() -> Credentials:
    raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if raw:
        return Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    path = Path(os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json"))
    if not path.exists():
        raise FileNotFoundError(
            "找不到 Google service account。請設定 GOOGLE_SERVICE_ACCOUNT_FILE "
            "或 GOOGLE_SERVICE_ACCOUNT_JSON。"
        )
    return Credentials.from_service_account_file(path, scopes=SCOPES)


class GoogleSheetsStore:
    def __init__(self, spreadsheet_id: str):
        # BackOffHTTPClient retries transient 429/5xx responses with exponential backoff.
        self.client = gspread.authorize(_credentials(), http_client=BackOffHTTPClient)
        self.book = self.client.open_by_key(spreadsheet_id)
        self._worksheet_cache: dict[str, gspread.Worksheet] = {}

    def worksheet(self, title: str) -> gspread.Worksheet:
        """Reuse worksheet objects so gspread does not fetch spreadsheet metadata repeatedly."""
        if title not in self._worksheet_cache:
            self._worksheet_cache[title] = self.book.worksheet(title)
        return self._worksheet_cache[title]

    def ensure_schema(self) -> None:
        worksheets = self.book.worksheets()
        self._worksheet_cache.update({ws.title: ws for ws in worksheets})
        existing = set(self._worksheet_cache)
        for title, headers in SHEET_HEADERS.items():
            if title not in existing:
                ws = self.book.add_worksheet(title=title, rows=2000, cols=max(20, len(headers) + 2))
                self._worksheet_cache[title] = ws
                ws.append_row(headers, value_input_option="RAW")
                ws.freeze(rows=1)
                ws.format("1:1", {"backgroundColor": {"red": 0.09, "green": 0.33, "blue": 0.46}, "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}})
        self._seed_settings()
        self._seed_program_input()

    def _seed_settings(self) -> None:
        ws = self.worksheet("設定")
        if len(ws.get_all_values()) == 1:
            ws.append_rows([
                ["source_sheet_name", os.getenv("SOURCE_SHEET_NAME", "計算"), "原始配置工作表"],
                ["source_ticker_column", os.getenv("SOURCE_TICKER_COLUMN", "A"), "ticker 欄"],
                ["source_target_column", os.getenv("SOURCE_TARGET_COLUMN", "P"), "target dollar 欄"],
                ["day1_day2_order_type", "LIMIT", "Day1/Day2 固定 LIMIT，保留最高成交價保護"],
                ["day2_k_multiplier", 0.6, "Day2 k = Day1 k × 0.6"],
                ["timezone", "America/New_York", "交易日判斷時區"],
            ], value_input_option="USER_ENTERED")
        else:
            values = ws.get_all_values()
            for row_no, row in enumerate(values[1:], start=2):
                if row and row[0] in {"market_immediate_rule", "day1_day2_order_type"}:
                    ws.update(range_name=f"A{row_no}:C{row_no}", values=[[
                        "day1_day2_order_type", "LIMIT", "Day1/Day2 固定 LIMIT，保留最高成交價保護",
                    ]], value_input_option="USER_ENTERED")
                    break

    def _seed_program_input(self) -> None:
        ws = self.worksheet("程式輸入")
        if len(ws.get_all_values()) == 1:
            formulas = []
            source = os.getenv("SOURCE_SHEET_NAME", "計算")
            for row in range(2, 102):
                formulas.append([
                    f"='{source}'!A{row}",
                    f"='{source}'!P{row}",
                    f'=IF(A{row}="",0,COUNTIF($A$2:$A$101,A{row}))',
                ])
            ws.update(range_name="A2:C101", values=formulas, value_input_option="USER_ENTERED")

    def read_df(self, title: str) -> pd.DataFrame:
        values = self.worksheet(title).get_all_records(default_blank="")
        return pd.DataFrame(values)

    def read_targets(self) -> pd.DataFrame:
        df = self.read_df("程式輸入")
        if df.empty:
            return pd.DataFrame(columns=["ticker", "target_dollar"])
        df["target_dollar"] = pd.to_numeric(df["target_dollar"], errors="coerce")
        return df[df["ticker"].astype(str).str.strip().ne("") & df["target_dollar"].gt(0)].copy()

    def append_rows(self, title: str, rows: list[dict]) -> None:
        if not rows:
            return
        headers = SHEET_HEADERS[title]
        payload = [[row.get(h, "") for h in headers] for row in rows]
        self.worksheet(title).append_rows(payload, value_input_option="USER_ENTERED")

    def current_plan(self, plan_id: str) -> pd.DataFrame:
        df = self.read_df("每週計畫")
        return df[df.get("plan_id", pd.Series(dtype=str)).astype(str) == plan_id].copy() if not df.empty else df

    def executions(self, plan_id: str) -> pd.DataFrame:
        df = self.read_df("執行紀錄")
        return df[df.get("plan_id", pd.Series(dtype=str)).astype(str) == plan_id].copy() if not df.empty else df

    def confirmations(self, plan_id: str) -> pd.DataFrame:
        df = self.read_df("每日確認")
        return df[df.get("plan_id", pd.Series(dtype=str)).astype(str) == plan_id].copy() if not df.empty else df

    def update_execution_manual_fields(self, plan_id: str, day: str) -> pd.DataFrame:
        """Read only. The user edits filled_price/filled_date/notes directly in Google Sheets."""
        df = self.executions(plan_id)
        return df[df["day"] == day].copy()

    def confirm_day(self, plan_id: str, day: str, order_date: str, blank_count: int, notes: str = "") -> None:
        existing = self.confirmations(plan_id)
        if not existing.empty and ((existing["day"] == day) & existing["confirmed"].astype(str).str.upper().isin({"TRUE", "1", "YES"})).any():
            return
        self.append_rows("每日確認", [{
            "plan_id": plan_id,
            "day": day,
            "order_date": order_date,
            "confirmed": True,
            "confirmed_at_et": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="seconds"),
            "blank_count": blank_count,
            "notes": notes,
        }])

    def stamp_filled_dates(self, plan_id: str, day: str, filled_date: str) -> None:
        """Fill only missing filled_date cells for rows whose user-entered filled_price is valid."""
        ws = self.worksheet("執行紀錄")
        values = ws.get_all_values()
        if len(values) < 2:
            return
        header = values[0]
        idx = {name: header.index(name) for name in ("plan_id", "day", "filled_price", "filled_date")}
        for row_no, row in enumerate(values[1:], start=2):
            padded = row + [""] * (len(header) - len(row))
            if padded[idx["plan_id"]] != plan_id or padded[idx["day"]] != day:
                continue
            raw_price = padded[idx["filled_price"]].strip()
            raw_date = padded[idx["filled_date"]].strip()
            try:
                valid_price = float(raw_price) > 0
            except (TypeError, ValueError):
                valid_price = False
            if valid_price and not raw_date:
                ws.update_cell(row_no, idx["filled_date"] + 1, filled_date)
