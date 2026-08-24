from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

ET_TZ = "America/New_York"
MARKET_TICKERS = ("QQQ", "SPY")
MARKET_BULL_TH = 0.008
MARKET_BEAR_TH = -0.008
STOCK_BULL_TH = 0.010
STOCK_BEAR_TH = -0.010

MATRIX_DAY1 = pd.DataFrame(
    [[0.20, 0.25, 0.35], [0.25, 0.40, 0.60], [0.35, 0.60, 0.85]],
    index=["Bull", "Neutral", "Bear"],
    columns=["Bull", "Neutral", "Bear"],
)


def flatten(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df


def previous_close_and_atr(ticker: str) -> tuple[float, float]:
    hist = flatten(yf.download(ticker, period="3mo", interval="1d", auto_adjust=False, progress=False, threads=False))
    required = ["Open", "High", "Low", "Close"]
    if hist.empty or any(c not in hist for c in required):
        return np.nan, np.nan
    hist = hist.dropna(subset=required).copy()
    today_et = datetime.now(ZoneInfo(ET_TZ)).date()
    if getattr(hist.index, "tz", None) is not None:
        hist.index = hist.index.tz_convert(ET_TZ)
    prior = hist[hist.index.date < today_et]
    if prior.empty:
        prior = hist
    tr = pd.concat([
        prior["High"] - prior["Low"],
        (prior["High"] - prior["Close"].shift(1)).abs(),
        (prior["Low"] - prior["Close"].shift(1)).abs(),
    ], axis=1).max(axis=1)
    return float(prior["Close"].iloc[-1]), float(tr.rolling(14).mean().iloc[-1])


def price_at_10(ticker: str) -> float:
    intraday = flatten(yf.download(ticker, period="7d", interval="1m", auto_adjust=False, progress=False, threads=False, prepost=False))
    if intraday.empty or "Close" not in intraday:
        return np.nan
    idx = intraday.index
    idx = idx.tz_localize("UTC").tz_convert(ET_TZ) if idx.tz is None else idx.tz_convert(ET_TZ)
    intraday = intraday.copy()
    intraday.index = idx
    today = datetime.now(ZoneInfo(ET_TZ)).date()
    day = intraday[intraday.index.date == today]
    if day.empty:
        return np.nan
    target = pd.Timestamp(f"{today} 10:00", tz=ET_TZ)
    exact = day[day.index == target]
    if not exact.empty and "Open" in exact:
        return float(exact["Open"].iloc[-1])
    eligible = day[day.index < target]
    return float(eligible["Close"].iloc[-1]) if not eligible.empty else np.nan


def classify_market(gap: float) -> str:
    if not np.isfinite(gap):
        return "Neutral"
    if gap > MARKET_BULL_TH:
        return "Bull"
    if gap < MARKET_BEAR_TH:
        return "Bear"
    return "Neutral"


def classify_stock(gap: float) -> str:
    if not np.isfinite(gap):
        return "Neutral"
    if gap > STOCK_BULL_TH:
        return "Bull"
    if gap < STOCK_BEAR_TH:
        return "Bear"
    return "Neutral"


def market_state() -> str:
    gaps = []
    for ticker in MARKET_TICKERS:
        close, _ = previous_close_and_atr(ticker)
        current = price_at_10(ticker)
        if np.isfinite(close) and np.isfinite(current) and close > 0:
            gaps.append((current - close) / close)
    return classify_market(float(np.mean(gaps))) if gaps else "Neutral"


def security_snapshot(ticker: str) -> dict:
    close, atr = previous_close_and_atr(ticker)
    current = price_at_10(ticker)
    gap = (current - close) / close if np.isfinite(current) and np.isfinite(close) and close > 0 else np.nan
    return {"ticker": ticker, "close_y": close, "atr": atr, "reference_price": current, "gap": gap, "stock_state": classify_stock(gap)}


def k1_for(market: str, stock: str) -> float:
    return float(MATRIX_DAY1.loc[market, stock])

