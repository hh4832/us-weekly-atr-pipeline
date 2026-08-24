from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd

DAY_ORDER = {"Day1": 1, "Day2": 2, "Day3": 3}


@dataclass(frozen=True)
class StageDecision:
    stage: str
    reason: str
    pending_tickers: tuple[str, ...]


def normalize_ticker(value: object) -> str:
    return str(value).strip().upper()


def validate_targets(rows: Iterable[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows).copy()
    required = {"ticker", "target_dollar"}
    if not required.issubset(df.columns):
        raise ValueError("程式輸入必須包含 ticker 與 target_dollar。")
    df = df[["ticker", "target_dollar"]]
    df["ticker"] = df["ticker"].map(normalize_ticker)
    df["target_dollar"] = pd.to_numeric(df["target_dollar"], errors="coerce")
    df = df[(df["ticker"] != "") & df["target_dollar"].notna()]
    df = df[df["target_dollar"] > 0].copy()
    if df.empty:
        raise ValueError("沒有可用的 target dollar。")
    if df["ticker"].duplicated().any():
        dupes = ", ".join(df.loc[df["ticker"].duplicated(False), "ticker"].unique())
        raise ValueError(f"ticker 重複：{dupes}")
    df["target_dollar"] = df["target_dollar"].round(2)
    return df.reset_index(drop=True)


def validate_filled_prices(orders: pd.DataFrame, day: str) -> list[str]:
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


def pending_after_confirmation(orders: pd.DataFrame) -> tuple[str, ...]:
    prices = pd.to_numeric(orders["filled_price"], errors="coerce")
    return tuple(orders.loc[prices.isna(), "ticker"].map(normalize_ticker))


def decide_stage(
    plan_tickers: Iterable[str],
    executions: pd.DataFrame,
    confirmations: pd.DataFrame,
    today: date,
) -> StageDecision:
    tickers = tuple(normalize_ticker(t) for t in plan_tickers)
    if executions.empty:
        return StageDecision("Day1", "本週尚未產生訂單。", tickers)

    work = executions.copy()
    work["day_no"] = work["day"].map(DAY_ORDER)
    latest_no = int(work["day_no"].max())
    latest_day = f"Day{latest_no}"
    latest = work[work["day_no"] == latest_no].copy()
    latest_date = pd.to_datetime(latest["order_date"], errors="coerce").dt.date.max()

    confirmed = False
    if not confirmations.empty:
        c = confirmations.copy()
        c["confirmed"] = c["confirmed"].astype(str).str.upper().isin({"TRUE", "1", "YES"})
        confirmed = bool(((c["day"] == latest_day) & c["confirmed"]).any())

    if not confirmed:
        return StageDecision(latest_day, f"{latest_day} 尚未完成每日核對。", tuple(latest["ticker"]))

    pending = pending_after_confirmation(latest)
    if not pending:
        return StageDecision("Completed", "所有計畫訂單均已成交。", ())
    if latest_no == 3:
        return StageDecision("Blocked", "Day3 仍有未填成交價的訂單。", pending)
    if latest_date is not None and today <= latest_date:
        return StageDecision("Waiting", "同一個美東交易日不會自動進入下一日。", pending)
    return StageDecision(f"Day{latest_no + 1}", f"{latest_day} 未成交標的進入下一階段。", pending)


def choose_order_type(calculated_limit: float, current_price: float, day: str) -> str:
    if day == "Day3":
        return "MARKET"
    if np.isfinite(calculated_limit) and np.isfinite(current_price) and calculated_limit >= current_price:
        return "MARKET"
    return "LIMIT"

