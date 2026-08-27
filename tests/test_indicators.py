import pytest
import pandas as pd

from src import indicators


def _history(volumes, closes=None):
    closes = closes or [10] * len(volumes)
    return pd.DataFrame(
        {
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Close": closes,
            "Volume": volumes,
        },
        index=pd.date_range("2026-01-01", periods=len(volumes), freq="D"),
    )


def test_compute_signals_uses_adjusted_ohlc_when_available():
    closes = list(range(100, 125))
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 5 for x in closes],
            "Low": [x - 5 for x in closes],
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )
    df["Adj Close"] = [x * 0.5 if i < 20 else x for i, x in enumerate(closes)]

    ratio = df["Adj Close"] / df["Close"]
    expected_df = df.copy()
    for col in ("Open", "High", "Low", "Close"):
        expected_df[col] = expected_df[col] * ratio

    assert indicators.compute_signals(df)["d1"] == indicators._timeframe_signals(expected_df)


def test_timeframe_signals_include_stoch_d_and_cross():
    closes = [50] * 13 + [10, 10, 10, 10, 10, 20]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [100] * len(closes),
            "Low": [0] * len(closes),
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )

    signals = indicators._timeframe_signals(df)

    # raw %K จบที่ [10,10,10,10,10,20] -> slow %K = SMA3 = 13.3, %D = SMA3(%K) = 11.1
    assert signals["stoch_k"] == 13.3
    assert signals["stoch_d"] == 11.1
    assert signals["stoch_cross"] == "up"


def test_high_volume_alert_triggers_at_2x_avg20():
    alert = indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [200], [10] * 20 + [11]), 1000)

    assert alert["ticker"] == "PTT.BK"
    assert alert["latest_volume"] == 200
    assert alert["avg_volume_20"] == 100
    assert alert["volume_ratio"] == 2.0
    assert alert["price_change_pct"] == 10.0
    assert alert["position_value"] == 11000


def test_high_volume_alert_ignores_low_volume():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [199]), 1000) is None


def test_high_volume_alert_requires_21_days():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20), 1000) is None


def test_high_volume_alert_requires_latest_volume():
    assert indicators.high_volume_alert("PTT.BK", _history([100] * 20 + [200, None]), 1000) is None


def test_stoch_bias_available_on_first_valid_bar_without_cross():
    """หุ้นเข้าใหม่: (14,3,3) ให้ %D จุดแรกที่แท่งที่ 18 — ต้องรู้ Bull/Bear แม้ยังเทียบ cross ไม่ได้"""
    closes = list(range(10, 28))
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [100] * len(closes),
            "Low": [0] * len(closes),
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )

    signals = indicators._timeframe_signals(df)

    assert signals["stoch_k"] == 26.0 and signals["stoch_d"] == 25.0
    assert signals["stoch_bias"] == "bull"
    assert signals["stoch_cross"] is None


def test_stoch_k_and_d_always_come_from_the_same_bar():
    """Close ขาดไปแท่งนึงทำให้ %K กับ %D หมดอายุคนละแท่ง — ห้ามรายงานเลขข้ามแท่งกัน"""
    closes = [10 + (i * 7) % 23 for i in range(40)]
    df = pd.DataFrame(
        {
            "Open": closes,
            "High": [x + 3 for x in closes],
            "Low": [x - 3 for x in closes],
            "Close": closes,
            "Volume": [100] * len(closes),
        },
        index=pd.date_range("2026-01-01", periods=len(closes), freq="D"),
    )
    df.loc[df.index[-4], "Close"] = float("nan")  # ตำแหน่งนี้ทำให้ %K กับ %D หมดอายุห่างกัน 4 แท่ง

    signals = indicators._timeframe_signals(df)
    k, d = indicators.stochastic(df)
    same_bar = ((k.round(1) == signals["stoch_k"]) & (d.round(1) == signals["stoch_d"])).any()

    assert signals["stoch_k"] is not None
    assert same_bar, "K/D ที่รายงานไม่ได้เกิดขึ้นพร้อมกันในแท่งเดียว"


def test_rsi_matches_wilder_definition_on_short_series():
    """1W มีแค่ ~52 แท่ง — ถ้า seed ผิด (ewm เปล่า ๆ) ค่าจะเพี้ยนจากนิยาม Wilder"""
    closes = pd.Series([100 + (i * 13) % 17 - (i % 5) for i in range(52)], dtype=float)

    n = 14
    deltas = closes.diff().dropna()
    avg_gain = deltas[:n].clip(lower=0).mean()
    avg_loss = (-deltas[:n].clip(upper=0)).mean()
    for x in deltas[n:]:
        avg_gain = (avg_gain * (n - 1) + max(x, 0)) / n
        avg_loss = (avg_loss * (n - 1) + max(-x, 0)) / n
    expected = 100 - 100 / (1 + avg_gain / avg_loss)

    assert indicators.rsi(closes).iloc[-1] == pytest.approx(expected)
