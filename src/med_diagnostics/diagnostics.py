# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for diagnostic recipes / scripting"""

import matplotlib.pyplot as plt
import nc_time_axis  # noqa: F401 - registers matplotlib's cftime unit converter
import numpy as np


def nino34(dataset, lon_dim, lat_dim):
    """Returns dataset selected for the Niño 3.4 region (5N-5S, 170W-120W).

    Detects whether lon_dim uses a 0-360 or -180-180 convention so the same
    call works across model grids (e.g. ocean xt_ocean vs atmos lon).
    """
    if dataset[lon_dim].max() > 180:
        lon_slice = slice(190, 240)
    else:
        lon_slice = slice(-170, -120)
    nino34_ds = dataset.sel({lat_dim: slice(-5, 5), lon_dim: lon_slice})
    return nino34_ds


def select_extra_dims(data, exclude_dims, extra_dim_selectors=None):
    """Collapse any dimensions on data beyond exclude_dims to a single level.

    Handles dimensions not every model shares, e.g. ocean depth (st_ocean,
    deptht, lev, depth...) that atmos variables don't have. Any such
    dimension not given an explicit value in extra_dim_selectors defaults to
    the level nearest 0 (the surface, for depth-like coordinates).
    """
    extra_dim_selectors = extra_dim_selectors or {}
    extra_dims = [d for d in data.dims if d not in exclude_dims]
    for d in extra_dims:
        if d in extra_dim_selectors:
            # Caller gave an explicit value (numeric or label) - match it exactly
            data = data.sel({d: extra_dim_selectors[d]})
        elif np.issubdtype(data[d].dtype, np.number):
            # Depth/level-type dim: nearest to 0 is the surface
            data = data.sel({d: 0}, method="nearest")
        else:
            # Non-numeric dim (e.g. ensemble member IDs): nearest-value
            # selection isn't meaningful, so just take the first entry -
            # matches controller.py's own convention for member handling.
            data = data.isel({d: 0})
    return data


def calc_anomolies(dataset, lon_dim, lat_dim, var, extra_dim_selectors=None):
    # Collapse any dims beyond time/lat/lon (e.g. ocean depth) to one level
    data = select_extra_dims(
        dataset[var],
        exclude_dims={"time", lat_dim, lon_dim},
        extra_dim_selectors=extra_dim_selectors,
    )

    # Calculate anomalies from the monthly climatology
    gb = data.groupby("time.month")
    sst_nino34_anom = gb - gb.mean(dim="time")

    # Create weights based on the cosine of the latitude
    weights = np.cos(np.deg2rad(dataset[lat_dim]))
    weights.name = "weights"

    # Apply the latitude weights and calculate the spatial mean
    index_nino34 = sst_nino34_anom.weighted(weights).mean(dim=[lat_dim, lon_dim])

    return index_nino34


def rolling_window_size(time_da, target_days=150):
    """Approximate a 5-month (~150 day) rolling window in native timesteps.

    A hardcoded window of 5 assumes monthly data: it's far too short to
    smooth daily data, and can exceed the record length entirely for
    yearly/short records - xarray's bottleneck-accelerated rolling mean
    raises ValueError (not just NaNs) when window > len(time). Inferring
    the actual timestep lets the same ~5-month smoothing target apply
    across daily/monthly/yearly data, and the result is always clamped to
    the available record length.
    """
    n = time_da.size
    if n <= 1:
        return 1
    diffs = np.diff(time_da.values)
    if diffs.dtype == object:
        # cftime diffs are datetime.timedelta objects
        step_days = np.median([d.days + d.seconds / 86400 for d in diffs])
    else:
        step_days = np.median(diffs / np.timedelta64(1, "D"))
    window = max(1, round(target_days / step_days)) if step_days > 0 else 5
    return min(window, n)


def sst_anomaly_nino34(
    dataset, x_dim, y_dim, var, extra_dim_selectors=None, start_date=None
):
    """Compute and plot the normalized, rolling-mean Niño 3.4 SST anomaly index.

    x_dim/y_dim/var are passed through so this works against any model's
    native coordinate names (e.g. lon/lat or xt_ocean/yt_ocean).

    extra_dim_selectors optionally maps any other dimension on var (e.g. a
    depth dim like st_ocean/deptht/lev) to the value to select; any such
    dimension left unspecified defaults to the level nearest 0 (the surface).

    start_date optionally drops all time steps before it (e.g. "1920-01-01")
    before any computation, so model spinup years don't skew the climatology,
    anomaly, or normalization - not just the plotted window.

    Returns the matplotlib Figure so callers (e.g. ui.py) can embed it.
    """
    if start_date is not None:
        dataset = dataset.sel(time=slice(start_date, None))

    nino34_ds = nino34(dataset, x_dim, y_dim)
    anomalies = calc_anomolies(
        nino34_ds, x_dim, y_dim, var, extra_dim_selectors=extra_dim_selectors
    )
    window = rolling_window_size(anomalies["time"])
    anomolies_rolling_mean = anomalies.rolling(time=window, center=True).mean()
    std_dev = anomalies.std()
    normalized_index_nino34_rolling_mean = anomolies_rolling_mean / std_dev
    # Compute the data into memory first
    index_plot = normalized_index_nino34_rolling_mean.compute()

    # Extract the raw NumPy arrays
    time_vals = index_plot.time.values
    y_vals = index_plot.values

    fig, ax = plt.subplots(figsize=(12, 6))

    # Red fill for El Niño
    ax.fill_between(
        time_vals,
        y_vals,
        0.4,
        where=(y_vals >= 0.4),
        interpolate=True,
        color="red",
        alpha=0.9,
    )

    # Blue fill for La Niña
    ax.fill_between(
        time_vals,
        y_vals,
        -0.4,
        where=(y_vals <= -0.4),
        interpolate=True,
        color="blue",
        alpha=0.9,
    )

    ax.plot(time_vals, y_vals, color="black")
    ax.axhline(0, color="black", lw=0.5)
    ax.axhline(0.4, color="black", linewidth=0.5, linestyle="dotted")
    ax.axhline(-0.4, color="black", linewidth=0.5, linestyle="dotted")
    ax.set_title("Niño 3.4 Index")
    ax.set_ylabel("SST Anomaly (°C)")

    return fig
