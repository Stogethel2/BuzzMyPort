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

    assert signals["stoch_k"] == 20.0
    assert signals["stoch_d"] == 13.3
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
