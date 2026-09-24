import xarray as xr

from med_diagnostics import analysis, plot_customisations


def recipe_nino34_averaged_timeseries(
    ds: xr.Dataset, variable: str = "o2", depth: float = 0
):
    """Area-weighted mean of a variable in the Niño 3.4 region over time."""
    ds = ds.sel(st_ocean=depth, method="nearest")
    ds = analysis.extract_region(
        ds, region="nino34", lon_dim="xt_ocean", lat_dim="yt_ocean"
    )

    # Weight by cell area so that small cells don't count as much as large ones.
    # Land cells are NaN and are skipped automatically.
    data = ds[variable]
    if "area_t" in ds:
        data = data.weighted(ds["area_t"].fillna(0))
    timeseries = data.mean(dim=["yt_ocean", "xt_ocean"])

    timeseries.name = f"Niño 3.4 {variable} (~{depth}m)"
    units = ds[variable].attrs.get("units", "")

    plot_kwargs = {
        "color": "tab:blue",
        "figsize": (8, 6),
        "title": timeseries.name,
        "ax_kwargs": {"xlabel": "Time", "ylabel": f"{variable} ({units})"},
        "customise": [
            plot_customisations._shade_top_10pct,
            plot_customisations._shade_bottom_10pct,
        ],
    }
    return timeseries, plot_kwargs
