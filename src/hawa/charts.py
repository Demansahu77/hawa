"""Render the four figures used in the README.

Run with:  uv run python -m hawa.charts
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from hawa import analysis
from hawa.fetch import RAW_PATH

OUT = Path(__file__).resolve().parents[2] / "charts"

SURFACE, INK, INK_SOFT, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, ORANGE, AQUA, GREY = "#2a78d6", "#eb6834", "#1baf7a", "#c3c2b7"
# One hue, light to dark, for magnitude.
BLUES = LinearSegmentedColormap.from_list("blues", ["#eaf2fd", "#86b6ef", "#2a78d6", "#0d366b"])

plt.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.size": 11,
        "text.color": INK,
        "axes.labelcolor": INK_SOFT,
        "axes.edgecolor": GREY,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK_SOFT,
        "ytick.labelcolor": INK_SOFT,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
    }
)


def titled(ax, title: str, subtitle: str) -> None:
    ax.set_title(title, loc="left", fontsize=14, fontweight="bold", pad=34)
    ax.text(0, 1.035, subtitle, transform=ax.transAxes, va="bottom", color=INK_SOFT, fontsize=10.5)


def save(fig, name: str) -> None:
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / name, dpi=160, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)


def ranking(daily) -> None:
    summary = analysis.city_summary(daily).iloc[::-1]  # worst at the top
    fig, ax = plt.subplots(figsize=(8.5, 5))
    bars = ax.barh(summary.index, summary["mean"], color=BLUE, height=0.62)
    ax.bar_label(bars, fmt="%.0f", padding=5, color=INK, fontsize=10.5,
                 bbox={"facecolor": SURFACE, "edgecolor": "none", "pad": 1.5})
    for limit, label in ((analysis.NAAQS_ANNUAL, "India limit, 40"), (analysis.WHO_ANNUAL, "WHO guideline, 5")):
        ax.axvline(limit, color=INK_SOFT, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
        ax.text(limit + 0.8, len(summary) - 0.3, label, ha="left", va="center", color=INK_SOFT, fontsize=9.5)

    ax.set_xlim(0, summary["mean"].max() * 1.1)
    ax.set_ylim(-0.6, len(summary) + 0.1)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("Mean PM2.5, micrograms per cubic metre")
    titled(ax, "Five of ten cities exceed India's own annual limit",
           "Mean PM2.5, 2023 to 2025. Dashed lines mark the annual limits.")
    save(fig, "1-ranking.png")


def heatmap(daily) -> None:
    order = analysis.city_summary(daily).index
    table = analysis.monthly_profile(daily).loc[order]
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    fig, ax = plt.subplots(figsize=(9.5, 5))
    image = ax.imshow(table.to_numpy(), cmap=BLUES, aspect="auto", vmin=0)
    ax.set_xticks(range(12), months)
    ax.set_yticks(range(len(order)), order)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    # White gaps between cells.
    ax.set_xticks([x - 0.5 for x in range(1, 12)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(1, len(order))], minor=True)
    ax.grid(which="minor", color=SURFACE, linewidth=2)
    ax.tick_params(which="minor", length=0)

    threshold = table.to_numpy().max() * 0.55
    for (row, col), value in zip(
        [(r, c) for r in range(table.shape[0]) for c in range(12)], table.to_numpy().ravel()
    ):
        ax.text(col, row, f"{value:.0f}", ha="center", va="center", fontsize=9.5,
                color="white" if value > threshold else INK)

    bar = fig.colorbar(image, ax=ax, fraction=0.03, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(length=0)
    titled(ax, "Every city is dirtiest in winter and cleanest in the monsoon",
           "Mean PM2.5 by month, micrograms per cubic metre, 2023 to 2025.")
    save(fig, "2-months.png")


def diurnal(hourly) -> None:
    profile = analysis.diurnal_profile(hourly)
    highlight = {"Delhi": BLUE, "Bhilai": ORANGE, "Mumbai": AQUA}
    nudge = {"Bhilai": 0.022, "Delhi": -0.022}  # the two lines end almost together

    fig, ax = plt.subplots(figsize=(9, 5))
    for city in profile.columns.difference(list(highlight)):
        ax.plot(profile.index, profile[city], color=GREY, linewidth=1.2)
    for city, colour in highlight.items():
        ax.plot(profile.index, profile[city], color=colour, linewidth=2.2)
        ax.text(23.35, profile[city].iloc[-1] + nudge.get(city, 0), city, color=INK, va="center",
                fontsize=10.5, fontweight="bold")
        ax.plot(23, profile[city].iloc[-1], "o", color=colour, markersize=6,
                markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax.text(23.35, 1.1, "seven other\ncities in grey", color=MUTED, va="center", fontsize=9.5)

    ax.axhline(1, color=INK_SOFT, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ax.set_xlim(0, 27.5)
    ax.set_xticks(range(0, 24, 3), [f"{h:02d}:00" for h in range(0, 24, 3)])
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_ylabel("PM2.5 relative to the city's own average")
    ax.set_xlabel("Hour of day, India time")
    titled(ax, "Nights are dirtier than afternoons, except in Mumbai",
           "Each line is one city's average day. 1.0 is that city's overall mean.")
    save(fig, "3-hours.png")


def diwali(daily) -> None:
    effect = analysis.diwali_effect(daily)
    order = list(analysis.city_summary(daily).index[::-1])
    colours = {2023: BLUE, 2024: ORANGE, 2025: AQUA}

    fig, ax = plt.subplots(figsize=(8.5, 5))
    for year, colour in colours.items():
        rows = effect[effect["year"] == year].set_index("city").loc[order]
        ax.scatter(rows["ratio"], range(len(order)), s=70, color=colour, label=str(year),
                   edgecolor=SURFACE, linewidth=1.5, zorder=3)
    ax.axvline(1, color=INK_SOFT, linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ax.text(1.03, len(order) - 0.35, "same as the week before", ha="left", va="center",
            color=INK_SOFT, fontsize=9.5)

    ax.set_xscale("log")
    ticks = [0.33, 0.5, 1, 2, 4]
    ax.set_xticks(ticks, ["one third", "half", "equal", "double", "4 times"])
    ax.minorticks_off()
    ax.set_yticks(range(len(order)), order)
    ax.set_ylim(-0.6, len(order) + 0.1)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.set_xlabel("PM2.5 on Diwali and the day after, against the week before")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncols=3,
              handletextpad=0.2, columnspacing=1.6)
    titled(ax, "This dataset shows no consistent Diwali spike",
           "Dots left of the line mean the air was cleaner on Diwali than in the week before.")
    save(fig, "4-diwali.png")


if __name__ == "__main__":
    hourly = analysis.load(RAW_PATH)
    daily = analysis.daily_means(hourly)
    ranking(daily)
    heatmap(daily)
    diurnal(hourly)
    diwali(daily)
    print(f"Wrote 4 charts to {OUT}")
