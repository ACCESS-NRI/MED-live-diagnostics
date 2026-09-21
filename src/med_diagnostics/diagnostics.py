# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for diagnostic recipes / scripting"""

import matplotlib.pyplot as plt
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
    selectors = {d: extra_dim_selectors.get(d, 0) for d in extra_dims}
    if selectors:
        data = data.sel(selectors, method="nearest")
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


def sst_anomaly_nino34(dataset, x_dim, y_dim, var, extra_dim_selectors=None):
    """Compute and plot the normalized, rolling-mean Niño 3.4 SST anomaly index.

    x_dim/y_dim/var are passed through so this works against any model's
    native coordinate names (e.g. lon/lat or xt_ocean/yt_ocean).

    extra_dim_selectors optionally maps any other dimension on var (e.g. a
    depth dim like st_ocean/deptht/lev) to the value to select; any such
    dimension left unspecified defaults to the level nearest 0 (the surface).

    Returns the matplotlib Figure so callers (e.g. ui.py) can embed it.
    """
    nino34_ds = nino34(dataset, x_dim, y_dim)
    anomalies = calc_anomolies(
        nino34_ds, x_dim, y_dim, var, extra_dim_selectors=extra_dim_selectors
    )
    anomolies_rolling_mean = anomalies.rolling(time=5, center=True).mean()
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
