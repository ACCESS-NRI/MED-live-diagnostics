def _shade_top_10pct(ax, data):
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


def _shade_bottom_10pct(ax, data):
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
