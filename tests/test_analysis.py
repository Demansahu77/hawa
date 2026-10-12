import pandas as pd
import pytest

from hawa import analysis


def hourly(city: str, day: str, values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "city": city,
            "time": pd.date_range(day, periods=len(values), freq="h"),
            "pm2_5": values,
        }
    )


def daily(city: str, start: str, values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"city": city, "date": pd.date_range(start, periods=len(values), freq="D"), "pm2_5": values}
    )


def test_daily_means_averages_each_day_and_drops_short_days():
    frame = pd.concat(
        [
            hourly("A", "2024-01-01", [10.0] * 12 + [30.0] * 12),  # full day, mean 20
            hourly("A", "2024-01-02", [99.0] * 5),  # only 5 hours: dropped
        ]
    )
    result = analysis.daily_means(frame)
    assert len(result) == 1
    assert result.loc[0, "pm2_5"] == pytest.approx(20.0)
    assert result.loc[0, "date"] == pd.Timestamp("2024-01-01")


def test_city_summary_counts_days_over_each_limit():
    frame = pd.concat(
        [daily("Dirty", "2024-01-01", [100, 80, 50, 10]), daily("Clean", "2024-01-01", [10, 10, 10, 10])]
    )
    summary = analysis.city_summary(frame)
    assert list(summary.index) == ["Dirty", "Clean"]  # worst first
    assert summary.loc["Dirty", "pct_days_over_naaqs"] == 50
    assert summary.loc["Dirty", "pct_days_over_who"] == 75
    assert summary.loc["Clean", "pct_days_over_who"] == 0
    assert summary.loc["Clean", "times_who_annual"] == pytest.approx(2.0)


def test_seasonal_ratio_divides_winter_by_monsoon():
    frame = pd.concat(
        [daily("A", "2024-07-01", [20.0] * 10), daily("A", "2024-12-01", [80.0] * 10)]
    )
    assert analysis.seasonal_ratio(frame)["A"] == pytest.approx(4.0)


def test_diurnal_profile_relative_has_mean_one():
    frame = hourly("A", "2024-01-01", [float(h) for h in range(24)] * 2)
    profile = analysis.diurnal_profile(frame)
    assert profile["A"].mean() == pytest.approx(1.0)
    assert analysis.diurnal_profile(frame, relative=False).loc[5, "A"] == 5.0


def test_longest_streak_counts_consecutive_days_only():
    #                                    over over      over over over
    values = [70, 90, 10, 61, 62, 63, 5]
    assert analysis.longest_streak(daily("A", "2024-01-01", values))["A"] == 3


def test_longest_streak_treats_a_missing_day_as_a_break():
    frame = daily("A", "2024-01-01", [70, 70, 70, 70])
    frame = frame.drop(index=2)  # 3 Jan missing: runs are 2 and 1
    assert analysis.longest_streak(frame)["A"] == 2


def test_longest_streak_is_zero_for_a_clean_city():
    assert analysis.longest_streak(daily("A", "2024-01-01", [5, 5, 5]))["A"] == 0


def test_diwali_effect_compares_festival_with_week_before():
    # 10 days at 40, then Diwali and the day after at 120.
    frame = daily("A", "2024-10-21", [40.0] * 10 + [120.0, 120.0])
    effect = analysis.diwali_effect(frame, {2024: "2024-10-31"})
    row = effect.iloc[0]
    assert row["baseline"] == pytest.approx(40.0)
    assert row["festival"] == pytest.approx(120.0)
    assert row["ratio"] == pytest.approx(3.0)
