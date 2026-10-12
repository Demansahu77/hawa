"""Pure pandas transforms. Each function takes a frame and returns a frame,
so every step can be tested on a few hand-made rows."""

import pandas as pd

# 24-hour PM2.5 limits in micrograms per cubic metre.
NAAQS_DAILY = 60  # India's National Ambient Air Quality Standard
WHO_DAILY = 15  # WHO 2021 guideline
NAAQS_ANNUAL = 40
WHO_ANNUAL = 5

# A day needs this many hourly readings before its mean counts.
MIN_HOURS = 18

# Main Diwali evening (Lakshmi Puja) in each study year.
DIWALI = {2023: "2023-11-12", 2024: "2024-10-31", 2025: "2025-10-20"}

WINTER, MONSOON = (11, 12, 1), (6, 7, 8)


def load(path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["time"])


def daily_means(hourly: pd.DataFrame) -> pd.DataFrame:
    """Collapse hourly rows to one mean per city per day.

    Days with fewer than MIN_HOURS readings are dropped: a mean built from a
    handful of night-time hours would overstate the day.
    """
    grouped = hourly.assign(date=hourly["time"].dt.normalize()).groupby(["city", "date"])
    daily = grouped["pm2_5"].agg(pm2_5="mean", hours="count").reset_index()
    return daily.loc[daily["hours"] >= MIN_HOURS, ["city", "date", "pm2_5"]].reset_index(drop=True)


def city_summary(daily: pd.DataFrame) -> pd.DataFrame:
    """Per city: mean level, how it compares with both annual limits, and the
    share of days over each daily limit. Sorted worst first."""
    summary = daily.groupby("city")["pm2_5"].agg(
        mean="mean",
        pct_days_over_naaqs=lambda s: (s > NAAQS_DAILY).mean() * 100,
        pct_days_over_who=lambda s: (s > WHO_DAILY).mean() * 100,
    )
    summary["times_who_annual"] = summary["mean"] / WHO_ANNUAL
    summary["times_naaqs_annual"] = summary["mean"] / NAAQS_ANNUAL
    return summary.sort_values("mean", ascending=False)


def monthly_profile(daily: pd.DataFrame) -> pd.DataFrame:
    """Mean PM2.5 as a city-by-month table (months 1 to 12 as columns)."""
    return daily.assign(month=daily["date"].dt.month).pivot_table(
        index="city", columns="month", values="pm2_5", aggfunc="mean"
    )


def seasonal_ratio(daily: pd.DataFrame) -> pd.Series:
    """Winter (Nov to Jan) mean divided by monsoon (Jun to Aug) mean, per city."""
    month = daily["date"].dt.month
    winter = daily[month.isin(WINTER)].groupby("city")["pm2_5"].mean()
    monsoon = daily[month.isin(MONSOON)].groupby("city")["pm2_5"].mean()
    return (winter / monsoon).sort_values(ascending=False).rename("winter_to_monsoon")


def diurnal_profile(hourly: pd.DataFrame, relative: bool = True) -> pd.DataFrame:
    """Mean PM2.5 by hour of day, one column per city.

    With relative=True each city is divided by its own overall mean, so the
    shape of the day can be compared between a clean and a dirty city.
    """
    profile = hourly.assign(hour=hourly["time"].dt.hour).pivot_table(
        index="hour", columns="city", values="pm2_5", aggfunc="mean"
    )
    return profile / profile.mean() if relative else profile


def yearly_means(daily: pd.DataFrame) -> pd.DataFrame:
    """Mean PM2.5 as a city-by-year table."""
    return daily.assign(year=daily["date"].dt.year).pivot_table(
        index="city", columns="year", values="pm2_5", aggfunc="mean"
    )


def longest_streak(daily: pd.DataFrame, threshold: float = NAAQS_DAILY) -> pd.Series:
    """Longest run of consecutive calendar days above the threshold, per city."""

    def longest(group: pd.DataFrame) -> int:
        over = group.set_index("date")["pm2_5"].asfreq("D") > threshold
        # A new run starts wherever the flag flips; count the days inside each "over" run.
        runs = over.groupby((over != over.shift()).cumsum()).sum()
        return int(runs.max()) if len(runs) else 0

    return (
        daily.groupby("city")[["date", "pm2_5"]]
        .apply(longest)
        .sort_values(ascending=False)
        .rename("longest_streak_days")
    )


def diwali_effect(daily: pd.DataFrame, dates: dict[int, str] = DIWALI) -> pd.DataFrame:
    """Compare Diwali night with the week before it.

    "festival" is the mean of Diwali day and the day after, since fireworks
    start in the evening and the smoke lingers into the next day. "baseline"
    is the mean of the seven days ending two days before Diwali. The ratio is
    festival / baseline.
    """
    rows = []
    for year, day in dates.items():
        diwali = pd.Timestamp(day)
        offset = (daily["date"] - diwali).dt.days
        festival = daily[offset.isin([0, 1])].groupby("city")["pm2_5"].mean()
        baseline = daily[offset.between(-8, -2)].groupby("city")["pm2_5"].mean()
        rows.append(
            pd.DataFrame({"year": year, "baseline": baseline, "festival": festival}).reset_index()
        )
    result = pd.concat(rows, ignore_index=True)
    result["ratio"] = result["festival"] / result["baseline"]
    return result
