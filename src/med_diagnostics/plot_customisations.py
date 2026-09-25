def shade_top_10pct(ax, data):
    """Shade where the timeseries is above its 90th percentile."""
    threshold = float(data.quantile(0.9))
    ax.axhline(
        threshold, color="tab:red", linestyle="--", linewidth=1, label="90th percentile"
    )
    ax.fill_between(
        data["time"].values,
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
    threshold = float(data.quantile(0.1))
    ax.axhline(
        threshold,
        color="tab:blue",
        linestyle="--",
        linewidth=1,
        label="10th percentile",
    )
    ax.fill_between(
        data["time"].values,
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
    """Fill betwen +- 0.4 degrees indicating El Nino (red) or La Nina (blue)"""
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
        Plot kwargs for ``analysis.analyse_and_plot``.
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
