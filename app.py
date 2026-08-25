from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from google_sheets_store import GoogleSheetsStore
from market_data import ET_TZ, k1_for, market_state, security_snapshot
from trading_engine import choose_order_type, decide_stage, validate_targets

load_dotenv()
st.set_page_config(page_title="美股三日 ATR 執行 Pipeline", layout="wide")
st.title("美股三日 ATR 執行 Pipeline")
st.caption("Google Sheet target dollar → Day1 ATR → Day2 k×0.6 → Day3 MARKET")


@st.cache_resource
def get_store() -> GoogleSheetsStore:
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    store = GoogleSheetsStore(sheet_id)
    store.ensure_schema()
    return store


def plan_id_for_today() -> str:
    now = datetime.now(ZoneInfo(ET_TZ))
    iso = now.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def validate_filled_prices(orders: pd.DataFrame, day: str) -> list[str]:
    """Hard validation only; unusual LIMIT fills are handled as warnings below."""
    errors: list[str] = []
    prices = pd.to_numeric(orders.get("filled_price"), errors="coerce")
    raw = orders.get("filled_price", pd.Series(index=orders.index, dtype=object))
    invalid = raw.notna() & raw.astype(str).str.strip().ne("") & prices.isna()
    nonpositive = prices.notna() & (prices <= 0)
    if invalid.any():
        errors.append("成交價必須是數字：" + ", ".join(orders.loc[invalid, "ticker"]))
    if nonpositive.any():
        errors.append("成交價必須大於 0：" + ", ".join(orders.loc[nonpositive, "ticker"]))
    if day == "Day3" and prices.isna().any():
        errors.append("Day3 為 MARKET 執行，所有列都必須填入真實成交價。")
    return errors


def filled_price_warnings(orders: pd.DataFrame, day: str) -> list[str]:
    """Warnings require a second confirmation but do not block progress."""
    warnings: list[str] = []
    if day in {"Day1", "Day2"} and "limit_price" in orders.columns:
        prices = pd.to_numeric(orders.get("filled_price"), errors="coerce")
        limits = pd.to_numeric(orders["limit_price"], errors="coerce")
        above_limit = prices.notna() & limits.notna() & (prices > limits + 0.01)
        if above_limit.any():
            warnings.append(
                "成交價高於程式產生時的參考限價："
                + ", ".join(orders.loc[above_limit, "ticker"])
                + "。可能是盤中調整委託價；請確認成交價記錄正確。"
            )
    return warnings


def create_plan(store: GoogleSheetsStore, plan_id: str) -> pd.DataFrame:
    existing = store.current_plan(plan_id)
    if not existing.empty:
        return existing
    targets = validate_targets(store.read_targets().to_dict("records"))
    created = datetime.now(ZoneInfo(ET_TZ)).isoformat(timespec="seconds")
    rows = [{
        "plan_id": plan_id,
        "created_at_et": created,
        "ticker": r.ticker,
        "target_dollar": float(r.target_dollar),
        "plan_status": "LOCKED",
        "source_sheet": "程式輸入",
    } for r in targets.itertuples(index=False)]
    store.append_rows("每週計畫", rows)
    return store.current_plan(plan_id)


def generate_orders(store: GoogleSheetsStore, plan: pd.DataFrame, plan_id: str, day: str, tickers: tuple[str, ...]) -> pd.DataFrame:
    today = datetime.now(ZoneInfo(ET_TZ)).date().isoformat()
    prior = store.executions(plan_id)
    market = market_state() if day == "Day1" else "Saved"
    rows = []
    data_issues: list[str] = []
    for ticker in tickers:
        target = float(pd.to_numeric(plan.loc[plan["ticker"] == ticker, "target_dollar"], errors="coerce").iloc[0])
        snap = security_snapshot(ticker)
        if day == "Day1":
            k1 = k1_for(market, snap["stock_state"])
            k_used = k1
        else:
            first = prior[(prior["ticker"] == ticker) & (prior["day"] == "Day1")]
            if first.empty:
                data_issues.append(f"{ticker}: 找不到 Day1 的 k1")
                continue
            k1 = float(pd.to_numeric(first["k1"], errors="coerce").iloc[0])
            k_used = k1 * 0.6 if day == "Day2" else np.nan

        required_values = (
            {"close_y": snap["close_y"], "atr": snap["atr"], "k1": k1, "k_used": k_used}
            if day in {"Day1", "Day2"}
            else {"reference_price": snap["reference_price"]}
        )
        missing = [name for name, value in required_values.items() if not np.isfinite(value)]
        if missing:
            data_issues.append(f"{ticker}: " + ", ".join(missing))
            continue

        if day == "Day3":
            calculated = np.nan
            order_type = "MARKET"
        else:
            calculated = snap["close_y"] - k_used * snap["atr"]
            order_type = choose_order_type(calculated, snap["reference_price"], day)
        execution_price = snap["reference_price"] if order_type == "MARKET" else calculated
        shares = round(target / execution_price, 4) if np.isfinite(execution_price) and execution_price > 0 else np.nan
        rows.append({
            "plan_id": plan_id, "order_date": today, "ticker": ticker, "day": day,
            "target_dollar": round(target, 2), "order_type": order_type,
            "limit_price": "" if not np.isfinite(calculated) else round(calculated, 2),
            "reference_price": "" if not np.isfinite(snap["reference_price"]) else round(snap["reference_price"], 2),
            "shares": "" if not np.isfinite(shares) else shares,
            "market_state": market, "stock_state": snap["stock_state"], "k1": k1,
            "k_used": "" if not np.isfinite(k_used) else k_used,
            "close_y": round(snap["close_y"], 4), "atr": round(snap["atr"], 4),
            "filled_price": "", "filled_date": "", "notes": "",
        })
    if data_issues:
        raise ValueError(
            "行情或前一日資料不完整，尚未寫入任何訂單。請稍後重試。缺少欄位："
            + "；".join(data_issues)
        )
    store.append_rows("執行紀錄", rows)
    return pd.DataFrame(rows)


def save_confirmation(store: GoogleSheetsStore, plan_id: str, day: str, latest: pd.DataFrame, blank_count: int) -> None:
    order_date = str(latest["order_date"].iloc[0])
    store.stamp_filled_dates(plan_id, day, order_date)
    store.confirm_day(plan_id, day, order_date, blank_count)


try:
    store = get_store()
    plan_id = st.sidebar.text_input("本週 Plan ID", value=plan_id_for_today())
    if st.sidebar.button("從 Google Sheet 建立／讀取本週計畫", type="primary"):
        create_plan(store, plan_id)
        st.cache_data.clear()

    plan = store.current_plan(plan_id)
    if plan.empty:
        st.info("尚未建立本週計畫。請先確認原 Google Sheet P 欄，再按「建立／讀取」。")
        st.stop()

    executions = store.executions(plan_id)
    confirmations = store.confirmations(plan_id)
    decision = decide_stage(plan["ticker"], executions, confirmations, datetime.now(ZoneInfo(ET_TZ)).date())
    c1, c2, c3 = st.columns(3)
    c1.metric("Plan", plan_id)
    c2.metric("當前階段", decision.stage)
    c3.metric("待處理", len(decision.pending_tickers))
    st.info(decision.reason)

    if decision.stage in {"Day1", "Day2", "Day3"}:
        stage_existing = executions[executions["day"] == decision.stage] if not executions.empty else pd.DataFrame()
        if stage_existing.empty:
            if st.button(f"產生 {decision.stage} 訂單", type="primary"):
                with st.spinner("抓取行情並計算訂單…"):
                    generate_orders(store, plan, plan_id, decision.stage, decision.pending_tickers)
                st.rerun()
        else:
            display_cols = ["ticker", "day", "target_dollar", "order_type", "limit_price", "reference_price", "shares", "k_used", "filled_price", "filled_date"]
            st.dataframe(stage_existing[display_cols], use_container_width=True, hide_index=True)
            st.download_button(
                f"下載 {decision.stage} export.csv",
                stage_existing.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{plan_id}_{decision.stage}_export.csv",
                mime="text/csv",
            )
            # executions was already refreshed from Google Sheets at the top of this rerun.
            # Reuse it here instead of issuing a duplicate API read.
            latest = stage_existing.copy()
            prices = pd.to_numeric(latest["filled_price"], errors="coerce")
            blank_count = int(prices.isna().sum())
            st.warning(f"目前有 {blank_count} 檔成交價為空白。勾選後，空白列將在下一交易日進入下一階段。")
            checked = st.checkbox("我已在 FT 核對：有成交者皆已填入 filled_price，其餘空白者確實未成交。")
            warning_key = f"confirm_warning_{plan_id}_{decision.stage}"
            warnings = filled_price_warnings(latest, decision.stage)

            if st.session_state.get(warning_key):
                for warning in warnings:
                    st.warning(warning)
                confirm_exception = st.checkbox(
                    "我已再次確認：上述成交價為真實成交價，可能因盤中調整限價或改用 MARKET。",
                    key=f"confirm_exception_checkbox_{plan_id}_{decision.stage}",
                )
                if st.button("仍要完成今日核對", type="primary", disabled=not confirm_exception):
                    errors = validate_filled_prices(latest, decision.stage)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        save_confirmation(store, plan_id, decision.stage, latest, blank_count)
                        st.session_state.pop(warning_key, None)
                        st.success("核對已儲存。下一個美東交易日才會進入下一階段。")
                        st.rerun()
            elif st.button("完成今日核對", disabled=not checked):
                errors = validate_filled_prices(latest, decision.stage)
                if errors:
                    for error in errors:
                        st.error(error)
                elif warnings:
                    st.session_state[warning_key] = True
                    st.rerun()
                else:
                    save_confirmation(store, plan_id, decision.stage, latest, blank_count)
                    st.success("核對已儲存。下一個美東交易日才會進入下一階段。")
                    st.rerun()
    elif decision.stage == "Completed":
        st.success("本週計畫已完成。")
    elif decision.stage in {"Blocked", "Waiting"}:
        st.warning(decision.reason)

except Exception as exc:
    st.error(f"系統錯誤：{exc}")
    st.exception(exc)
