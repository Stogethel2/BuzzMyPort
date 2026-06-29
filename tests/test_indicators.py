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
