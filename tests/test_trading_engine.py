from datetime import date

import pandas as pd

from trading_engine import decide_stage, validate_filled_prices, validate_targets


def test_targets_are_cleaned():
    out = validate_targets([{"ticker": " nvda ", "target_dollar": "280"}])
    assert out.iloc[0].to_dict() == {"ticker": "NVDA", "target_dollar": 280.0}


def test_unconfirmed_day_does_not_advance():
    execution = pd.DataFrame([{"ticker": "NVDA", "day": "Day1", "order_date": "2026-08-24", "filled_price": ""}])
    d = decide_stage(["NVDA"], execution, pd.DataFrame(), date(2026, 8, 25))
    assert d.stage == "Day1"


def test_confirmed_blank_advances_next_trading_date():
    execution = pd.DataFrame([{"ticker": "NVDA", "day": "Day1", "order_date": "2026-08-24", "filled_price": ""}])
    confirmations = pd.DataFrame([{"day": "Day1", "confirmed": True}])
    d = decide_stage(["NVDA"], execution, confirmations, date(2026, 8, 25))
    assert d.stage == "Day2"
    assert d.pending_tickers == ("NVDA",)


def test_confirmed_fill_completes():
    execution = pd.DataFrame([{"ticker": "NVDA", "day": "Day1", "order_date": "2026-08-24", "filled_price": "210.5"}])
    confirmations = pd.DataFrame([{"day": "Day1", "confirmed": True}])
    d = decide_stage(["NVDA"], execution, confirmations, date(2026, 8, 25))
    assert d.stage == "Completed"


def test_day3_requires_price():
    orders = pd.DataFrame([{"ticker": "NVDA", "filled_price": ""}])
    assert validate_filled_prices(orders, "Day3")

