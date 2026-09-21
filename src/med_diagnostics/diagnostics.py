# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for diagnostic recipes / scripting"""

import matplotlib.pyplot as plt
import nc_time_axis  # noqa: F401 - registers matplotlib's cftime unit converter
import numpy as np
import xclim.indices as xcl

PREDEFINED_REGIONS = {
    "nino34": {"lat": (-5, 5), "lon": (-170, -120)},
    "nino3": {"lat": (-5, 5), "lon": (-150, -90)},
    "nino4": {"lat": (-5, 5), "lon": (160, -150)},
    "tasmania": {"lat": (-44, -39), "lon": (143, 149)},
}


def extract_region(dataset, region, lon_dim="lon", lat_dim="lat"):
    """
    Extracts a spatial bounding box from an xarray Dataset or DataArray.

    Parameters:
    - dataset: xarray object
    - region: String (key from PREDEFINED_REGIONS) OR a dictionary mapping 'lat' and 'lon' to tuples.
    - lon_dim: Name of longitude dimension (e.g., "xt_ocean" or "lon")
    - lat_dim: Name of latitude dimension (e.g., "yt_ocean" or "lat")
    """
    # check region that is passed in
    if isinstance(region, str):
        region_key = region.lower()
        if region_key not in PREDEFINED_REGIONS:
            raise ValueError(
                f"Region '{region}' not found. Available: {list(PREDEFINED_REGIONS.keys())}"
            )
        bounds = PREDEFINED_REGIONS[region_key]
    elif isinstance(region, dict) and "lat" in region and "lon" in region:
        bounds = region
    else:
        raise TypeError(
            "Region must be a valid string or a dictionary with 'lat' and 'lon' tuples."
        )

    lon_min, lon_max = bounds["lon"]
    lat_min, lat_max = bounds["lat"]

    # 2. Dynamically handle 0-360 vs -180-180 longitude grids
    if dataset[lon_dim].max() > 180:
        lon_min = lon_min % 360
        lon_max = lon_max % 360

    # 3. Sort slices to ensure xarray returns data
    # (Slicing max to min returns empty arrays in xarray)
    lon_slice = slice(min(lon_min, lon_max), max(lon_min, lon_max))
    lat_slice = slice(min(lat_min, lat_max), max(lat_min, lat_max))

    return dataset.sel({lat_dim: lat_slice, lon_dim: lon_slice})


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
    """Compute and plot the normalized, rolling-mean Niño 3.4 index for a given variable.

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

    nino34_ds = extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = calc_anomolies(
        nino34_ds, x_dim, y_dim, var, extra_dim_selectors=extra_dim_selectors
    )

    anomalies = anomalies.chunk({"time": -1})
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

    return fig


def tg_days_above_below_helper(
    dataset, var, xdim, ydim, thresh_kelvin, freq="YS", op=">"
):

    weights = np.cos(np.deg2rad(dataset[ydim]))
    spatial_mean = dataset[var].weighted(weights).mean(dim=[xdim, ydim])

    spatial_mean.attrs["units"] = "degK"

    if op in ["<", "lt", "<=", "le"]:
        convective_periods_per_year = xcl.tg_days_below(
            tas=spatial_mean, thresh=f"{thresh_kelvin} degK", freq=freq, op=op
        )
    else:
        convective_periods_per_year = xcl.tg_days_above(
            tas=spatial_mean, thresh=f"{thresh_kelvin} degK", freq=freq, op=op
        )

    fig, ax = plt.subplots(figsize=(12, 6))
    convective_periods_per_year.compute().plot(ax=ax, color="black")

    ax.set_title(f"Periods per {freq} {op} {thresh_kelvin}K")
    ax.set_ylabel("Count")

    return fig
