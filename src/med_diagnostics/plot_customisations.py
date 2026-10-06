import numpy as np


def shade_top_10pct(ax, data):
    """Shade where the timeseries is above its 90th percentile."""
    dim = "time"
    threshold = float(data.quantile(0.9))
    ax.axhline(
        threshold, color="tab:red", linestyle="--", linewidth=1, label="90th percentile"
    )
    ax.fill_between(
        data[dim].values,
        threshold,
        data.values,
        where=data.values >= threshold,
        interpolate=True,
        color="tab:red",
        alpha=0.3,
        label="Top 10%",
    )
    ax.legend()


def shade_bottom_10pct(ax, data):
    """Shade where the timeseries is below its 10th percentile."""
    dim = "time"
    threshold = float(data.quantile(0.1))
    ax.axhline(
        threshold,
        color="tab:blue",
        linestyle="--",
        linewidth=1,
        label="10th percentile",
    )
    ax.fill_between(
        data[dim].values,
        threshold,
        data.values,
        where=data.values <= threshold,
        interpolate=True,
        color="tab:blue",
        alpha=0.3,
        label="Bottom 10%",
    )
    ax.legend()


def nino_fills(ax, data):
    """Fill between +- 0.4 degrees indicating El Nino (red) or La Nina (blue)"""
    t, y = data.time.values, data.values
    ax.fill_between(
        t, y, 0.4, where=(y >= 0.4), interpolate=True, color="red", alpha=0.3
    )
    ax.fill_between(
        t, y, -0.4, where=(y <= -0.4), interpolate=True, color="blue", alpha=0.3
    )


def nino_reference_lines(ax, data):
    """Add reference lines for El Nino and La Nina"""
    ax.axhline(0, color="black", lw=0.5)
    ax.axhline(0.4, color="black", linewidth=0.5, linestyle="dotted")
    ax.axhline(-0.4, color="black", linewidth=0.5, linestyle="dotted")


def timeseries_plot_kwargs(timeseries, variable, units):
    """
    Standard plot kwargs for a regional timeseries, with the extremes shaded.

    Parameters
    ----------
    timeseries : xarray.DataArray
        The result being plotted; its name becomes the title.
    variable, units : str
        Used for the y-axis label.

    Returns
    -------
    dict
        Plot kwargs for ``analysis._analyse_and_plot``.
    """
    return {
        "color": "tab:blue",
        "figsize": (6, 4),
        "title": timeseries.name,
        "ax_kwargs": {"xlabel": "Time", "ylabel": f"{variable} ({units})"},
        "customise": [
            shade_top_10pct,
            shade_bottom_10pct,
        ],
    }


def add_trend(ax, data):
    """Overlay a least-squares linear trend."""
    # Smoothing leaves NaNs at the ends, which polyfit can't handle
    valid = data.dropna("time")
    x = np.arange(valid.sizes["time"])
    slope, intercept = np.polyfit(x, valid.values, 1)
    ax.plot(
        valid["time"].values,
        slope * x + intercept,
        color="grey",
        linestyle=":",
        label="Trend",
    )
    ax.legend()


def add_threshold(ax, value):
    """Adds a horizontal threshold line to a matplotlib axis."""
    ax.axhline(y=value, color="red", linestyle="--")


def add_rolling_mean(ax, data, window, dim="time"):
    """Overlay a centred rolling mean of ``window`` timesteps, in the colour of the last line drawn."""
    smoothed = data.rolling({dim: window}, center=True).mean().dropna(dim)
    color = ax.get_lines()[-1].get_color()
    ax.plot(smoothed[dim].values, smoothed.values, color=color, linewidth=2)


def add_reference_timeseries(ax, references):
    """Overlay reference timeseries ``{label: (data, window)}``, each with its rolling mean."""
    for label, (ref, window) in references.items():
        ax.plot(ref["time"].values, ref.values, alpha=0.6, linewidth=1, label=label)
        add_rolling_mean(ax, ref, window)
    ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
