# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""
Analysis recipes for MED: dataset cleaning, regional/spatial helpers, the
Niño 3.4 index, global ocean scalar comparisons and xclim indicator wrappers.
"""

import csv
import hashlib
import inspect
import itertools
import os
import types
from contextlib import nullcontext
from importlib import resources

import intake
import matplotlib.pyplot as plt
import nc_time_axis  # noqa: F401 - registers matplotlib's cftime unit converter
import numpy as np
import xarray as xr
import xclim.indicators
from xclim.core.indicator import Indicator
from xclim.core.utils import InputKind

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

# Direct 1-to-1 renames (access_var -> (cmip_var, units)) that master_map.csv
# doesn't provide because it only defines these CMIP6 variables as
# calculations from 3D fields. MOM5 also outputs them precomputed as scalars.
SUPPLEMENTARY_DIRECT_MAPPINGS = {
    "temp_global_ave": ("thetaoga", "degC"),
    "temp_surface_ave": ("tosga", "degC"),
    "sst": ("tosga", "degC"),
    "tosmax": ("tos_max", "degC"),
    "tosmin": ("tos_min", "degC"),
    "zosmin": ("zos_min", "m"),
    "zosmax": ("zos_max", "m"),
    "sosmin": ("sos_min", "0.001"),
    "sosmax": ("sos_max", "0.001"),
}

# Named lat/lon bounding boxes accepted by `extract_region`
PREDEFINED_REGIONS = {
    "nino34": {"lat": (-5, 5), "lon": (-170, -120)},
    "nino3": {"lat": (-5, 5), "lon": (-150, -90)},
    "nino4": {"lat": (-5, 5), "lon": (160, -150)},
    "tasmania": {"lat": (-44, -39), "lon": (143, 149)},
}

# Default variables for `plot_ocean_global_scalars`
OM3_GLOBAL_SCALARS = ["masso", "thetaoga", "soga", "tosga", "sosga"]

# Default variables for `plot_ocean_gridded_extremes`
OM3_GRIDDED_MAX_PLOTS = ["tos_max", "zos_max", "sos_max"]
OM3_GRIDDED_MIN_PLOTS = ["tos_min", "zos_min", "sos_min"]

# {"model name": "path to intake-esm datastore JSON"}
DEFAULT_REFERENCE_CATALOGS = {
    "MC_25km_jra_iaf-1.0-beta-5165c0f8": "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf-1.0-beta-5165c0f8/datastore.json",
    "MC_25km_jra_iaf+wombatlite-test3v2-00532b88": "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test3v2-00532b88/datastore.json",
    "cm3-datastore": "/g/data/zv30/non-cmip/ACCESS-CM3/cm3-run-03-06-2026/cm3-datastore/cm3-datastore.json",
    "MC_25km_jra_iaf+wombatlite-test4-d28e0359": "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test4-d28e0359/datastore.json",
}

# The ACCESS-OM2 run loaded from the ACCESS-NRI catalog as a scalar reference
OM2_REFERENCE_NAME = "025deg_jra55_iaf_omip2_cycle1"

# Folder for cached global series, created in the working directory alongside
# data.py's live_diagnostics_tmp_catalog.json
SCALAR_CACHE_DIRNAME = "live_diagnostics_cache"


# --------------------------------------------------------------------------
# Dataset cleaning
# --------------------------------------------------------------------------


def clean_access_dataset(dataset, master_map_path=None):
    """
    Rename ACCESS variables to CMIP6 names and units using master_map.csv.

    Parameters
    ----------
    dataset : xarray.Dataset
        Raw ACCESS model output.
    master_map_path : str or path-like, optional
        Custom master_map.csv. Defaults to the copy bundled with the package.

    Returns
    -------
    xarray.Dataset
        Dataset with CMIP6 variable names and ``units`` attrs, ready for xclim.

    Notes
    -----
    Source map: https://github.com/ACCESS-Community-Hub/APP4/blob/master/input_files/master_map.csv
    """
    stash_to_cmip = {}
    cmip_units = {}

    # importlib.resources resolves the bundled file regardless of the caller's
    # working directory or how the package was installed (wheel, editable...)
    if master_map_path is None:
        map_file_ctx = resources.as_file(
            resources.files("med_diagnostics").joinpath("master_map.csv")
        )
    else:
        map_file_ctx = nullcontext(master_map_path)

    # 1. Parse master_map.csv into translation dictionaries
    with map_file_ctx as map_path, open(map_path, mode="r") as file:
        # Skip commented header lines and read as CSV
        reader = csv.reader(filter(lambda row: not row.startswith("#"), file))

        for row in reader:
            # Skip rows missing any of the columns used below
            if len(row) < 5:
                continue

            cmip_var = row[0].strip()
            access_vars = row[2].strip()
            calculation = row[3].strip()
            units = row[4].strip()

            # Only map direct 1-to-1 translations: no spaces (multiple input
            # vars) and no calculation string.
            if " " not in access_vars and not calculation:
                # Several stash codes can map to one cmip_var (e.g. CM2- and
                # ESM-specific codes for zg500) - keep every pairing.
                stash_to_cmip[access_vars] = cmip_var
                cmip_units[cmip_var] = units

    for access_var, (cmip_var, units) in SUPPLEMENTARY_DIRECT_MAPPINGS.items():
        stash_to_cmip.setdefault(access_var, cmip_var)
        cmip_units.setdefault(cmip_var, units)

    # 2. Build a collision-safe rename dictionary
    rename_dict = {}

    # Track existing names to prevent overwriting native variables
    used_cmip_names = set(dataset.variables)

    # Keyed by the *final* name, so a fallback-renamed variable (e.g.
    # 'hus_fld_s00i010') still gets its units, not just the plain 'hus'.
    units_by_final_name = {}

    for stash_var, cmip_var in stash_to_cmip.items():
        if stash_var in dataset.variables:
            if cmip_var not in used_cmip_names:
                # Primary choice: clean CMIP6 name (e.g. 'hus')
                final_name = cmip_var
            else:
                # Fallback: append the stash code (e.g. 'hus_fld_s00i010')
                final_name = f"{cmip_var}_{stash_var}"

            rename_dict[stash_var] = final_name
            used_cmip_names.add(final_name)
            units_by_final_name[final_name] = cmip_units[cmip_var]

    # 3. Rename variables found in the dataset
    clean_ds = dataset.rename(rename_dict)

    # 4. Assign CMIP6 units - xclim requires them explicitly in attrs
    for var in clean_ds.data_vars:
        if var in units_by_final_name:
            clean_ds[var].attrs["units"] = units_by_final_name[var]

    # 5. Keep scalar lon/lat as length-1 dims so they aren't squeezed out
    # later (e.g. a Tasmania bounding box reducing to one longitude point)
    for dim in ["lon", "lat"]:
        if dim not in clean_ds.dims and dim in clean_ds.coords:
            clean_ds = clean_ds.expand_dims(dim)

    return clean_ds


# --------------------------------------------------------------------------
# Spatial and dimension helpers
# --------------------------------------------------------------------------


def extract_region(dataset, region, lon_dim="lon", lat_dim="lat"):
    """
    Extract a lat/lon bounding box, on regular or curvilinear grids.

    Parameters
    ----------
    dataset : xarray.Dataset or xarray.DataArray
        Data to subset.
    region : str or dict
        A key of ``PREDEFINED_REGIONS``, or ``{"lat": (min, max), "lon": (min, max)}``.
    lon_dim, lat_dim : str, default "lon", "lat"
        Longitude/latitude coordinate names (e.g. "xt_ocean" or 2D "TLON").

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        The subset within the bounding box.
    """
    # 1. Resolve the region into lat/lon bounds
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

    lon_coord = dataset[lon_dim]
    lat_coord = dataset[lat_dim]

    # 2. Handle 0-360 vs -180-180 longitude grids
    if lon_coord.max() > 180:
        lon_min = lon_min % 360
        lon_max = lon_max % 360

    # 3. Sort bounds - slicing/masking max to min returns empty arrays
    lon_lo, lon_hi = min(lon_min, lon_max), max(lon_min, lon_max)
    lat_lo, lat_hi = min(lat_min, lat_max), max(lat_min, lat_max)

    # 4a. Curvilinear/tripolar grids (e.g. ACCESS-OM2/CICE TLAT/TLON): `.sel()`
    # can't slice a 2D coordinate, so mask and drop instead.
    if lon_coord.ndim > 1 or lat_coord.ndim > 1:
        in_region = (
            (lon_coord >= lon_lo)
            & (lon_coord <= lon_hi)
            & (lat_coord >= lat_lo)
            & (lat_coord <= lat_hi)
        )
        # `where(..., drop=True)` refuses a dask-backed boolean mask (the
        # result shape would be unknown). The mask is grid-sized with no time
        # dimension, so computing it eagerly is cheap.
        return dataset.where(in_region.compute(), drop=True)

    # 4b. Regular 1D grids: fast slice-based selection
    return dataset.sel({lat_dim: slice(lat_lo, lat_hi), lon_dim: slice(lon_lo, lon_hi)})


def select_extra_dims(data, exclude_dims, extra_dim_selectors=None):
    """
    Collapse every dimension not in ``exclude_dims`` to a single level.

    Parameters
    ----------
    data : xarray.DataArray
        Variable to reduce (e.g. with an ocean depth dim like st_ocean/lev).
    exclude_dims : set of str
        Dimensions to leave untouched (e.g. time, lat, lon).
    extra_dim_selectors : dict, optional
        ``{dim: value}`` to select exactly. Unlisted numeric dims default to
        the level nearest 0 (the surface); non-numeric dims to their first entry.

    Returns
    -------
    xarray.DataArray
        ``data`` with only ``exclude_dims`` remaining.
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
            # Non-numeric dim (e.g. ensemble member IDs): nearest-value isn't
            # meaningful, so take the first entry - matches controller.py's
            # member handling convention.
            data = data.isel({d: 0})
    return data


def spatial_reduction_dims(dataset, *coord_names):
    """
    Return the real dimensions underlying one or more spatial coordinates.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset containing the coordinates.
    *coord_names : str
        Coordinate names, e.g. "lat", "lon" or 2D "TLAT", "TLON".

    Returns
    -------
    list of str
        Unique dimension names, e.g. ["lat", "lon"] or ["nj", "ni"].
    """
    # On a regular grid 'lat' is indexed by dim 'lat'. On a curvilinear grid,
    # TLAT is indexed by e.g. 'nj'/'ni', and passing "TLAT" to `.mean(dim=...)`
    # would be a no-op at best and a KeyError at worst.
    dims = []
    for name in coord_names:
        for dim in dataset[name].dims:
            if dim not in dims:
                dims.append(dim)
    return dims


# --------------------------------------------------------------------------
# Time helpers
# --------------------------------------------------------------------------


def median_timestep_days(time_da):
    """
    Return the median spacing between consecutive time steps, in days.

    Parameters
    ----------
    time_da : xarray.DataArray
        Time coordinate (numpy datetime64 or cftime).

    Returns
    -------
    float
        Median timestep length in days.
    """
    diffs = np.diff(time_da.values)
    # cftime axes (e.g. 360_day/noleap) diff to datetime.timedelta objects
    # rather than numpy.timedelta64, so they need separate handling
    if diffs.dtype == object:
        return np.median([d.days + d.seconds / 86400 for d in diffs])
    return np.median(diffs / np.timedelta64(1, "D"))


def rolling_window_size(time_da, target_days=150):
    """
    Convert a target rolling window length in days to native timesteps.

    Parameters
    ----------
    time_da : xarray.DataArray
        Time coordinate of the data to smooth.
    target_days : float, default 150
        Desired window length (150 days is roughly 5 months).

    Returns
    -------
    int
        Window size in timesteps, clamped to ``[1, len(time_da)]``.
    """
    # A fixed window of 5 assumes monthly data: too short for daily data and
    # can exceed short yearly records, where bottleneck's rolling mean raises
    # ValueError. Sizing from the real timestep avoids both.
    n = time_da.size
    if n <= 1:
        return 1
    step_days = median_timestep_days(time_da)
    window = max(1, round(target_days / step_days)) if step_days > 0 else 5
    return min(window, n)


# --------------------------------------------------------------------------
# Niño 3.4 index
# --------------------------------------------------------------------------


def calc_anomolies(dataset, lon_dim, lat_dim, var, extra_dim_selectors=None):
    """
    Compute the area-weighted mean monthly anomaly of ``var``.

    Parameters
    ----------
    dataset : xarray.Dataset
        Data already subset to the region of interest.
    lon_dim, lat_dim : str
        Longitude/latitude coordinate names.
    var : str
        Variable to compute anomalies for.
    extra_dim_selectors : dict, optional
        Passed to `select_extra_dims` (e.g. to pick a depth level).

    Returns
    -------
    xarray.DataArray
        Time series of anomalies from the monthly climatology.
    """
    # Collapse any dims beyond time/lat/lon (e.g. ocean depth) to one level
    data = select_extra_dims(
        dataset[var],
        exclude_dims={"time", lat_dim, lon_dim},
        extra_dim_selectors=extra_dim_selectors,
    )

    # Anomalies from the monthly climatology
    gb = data.groupby("time.month")
    anomalies = gb - gb.mean(dim="time")

    # Weight by cos(latitude) to account for grid cell area
    weights = np.cos(np.deg2rad(dataset[lat_dim]))
    weights.name = "weights"

    return anomalies.weighted(weights).mean(dim=[lat_dim, lon_dim])


def sst_anomaly_nino34(
    dataset, x_dim, y_dim, var, extra_dim_selectors=None, start_date=None
):
    """
    Plot the normalised, rolling-mean Niño 3.4 index for ``var``.

    Parameters
    ----------
    dataset : xarray.Dataset
        Model output containing ``var``.
    x_dim, y_dim : str
        Native longitude/latitude names (e.g. "lon"/"lat" or "xt_ocean"/"yt_ocean").
    var : str
        Temperature variable to use (e.g. "tos").
    extra_dim_selectors : dict, optional
        Passed to `select_extra_dims`; unlisted depth dims default to the surface.
    start_date : str, optional
        Drop time steps before this date (e.g. "1920-01-01") to exclude spinup.

    Returns
    -------
    matplotlib.figure.Figure
        The Niño 3.4 index plot.
    """
    # Trim before any computation so spinup doesn't skew the climatology,
    # anomaly or normalisation - not just the plotted window
    if start_date is not None:
        dataset = dataset.sel(time=slice(start_date, None))

    nino34_ds = extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = calc_anomolies(
        nino34_ds, x_dim, y_dim, var, extra_dim_selectors=extra_dim_selectors
    )

    # Rolling needs the whole time axis in one chunk
    anomalies = anomalies.chunk({"time": -1})
    window = rolling_window_size(anomalies["time"])
    rolling_mean = anomalies.rolling(time=window, center=True).mean()
    index_plot = (rolling_mean / anomalies.std()).compute()

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


# --------------------------------------------------------------------------
# Global ocean scalars
# --------------------------------------------------------------------------


def _global_series(dataset, var, x_dim, y_dim, extra_dim_selectors, reduction):
    """
    Lazily reduce ``dataset[var]`` to a single global value per timestep.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset containing ``var``.
    var : str
        Variable to reduce.
    x_dim, y_dim : str
        Spatial coordinate names.
    extra_dim_selectors : dict or None
        Passed to `select_extra_dims`.
    reduction : {"mean", "max", "min"}
        Area-weighted mean, or plain spatial max/min.

    Returns
    -------
    xarray.DataArray
        Lazy time series (unchanged if ``var`` is already scalar).
    """
    try:
        real_spatial_dims = set(spatial_reduction_dims(dataset, x_dim, y_dim))
    except KeyError:
        real_spatial_dims = {x_dim, y_dim}

    data = select_extra_dims(
        dataset[var],
        exclude_dims={"time"} | real_spatial_dims,
        extra_dim_selectors=extra_dim_selectors,
    )

    present_spatial_dims = [d for d in real_spatial_dims if d in data.dims]
    if present_spatial_dims and reduction == "mean":
        weights = np.cos(np.deg2rad(dataset[y_dim]))
        data = data.weighted(weights).mean(dim=present_spatial_dims, keep_attrs=True)
    elif present_spatial_dims:
        # Land cells are NaN and skipped by max/min
        data = getattr(data, reduction)(dim=present_spatial_dims, keep_attrs=True)
    return data


def _cached_global_series(
    cache_dir, label, dataset, var, x_dim, y_dim, extra_dim_selectors, reduction
):
    """
    Return the computed global series, reusing and extending an on-disk cache.

    Parameters
    ----------
    cache_dir : str
        Folder holding one netCDF file per run/variable/reduction.
    label : str
        Run label - identifies the run in the cache, so keep it unique per run.
    dataset, var, x_dim, y_dim, extra_dim_selectors, reduction
        As for `_global_series`.

    Returns
    -------
    xarray.DataArray
        The in-memory global series.
    """
    # Hash everything that changes the result, so e.g. a different depth
    # level or reduction never reuses the wrong file
    key = f"{label}|{var}|{reduction}|{extra_dim_selectors!r}"
    safe_label = "".join(c if c.isalnum() or c in "-_+" else "_" for c in label)
    digest = hashlib.md5(key.encode()).hexdigest()[:8]
    path = os.path.join(cache_dir, f"{safe_label}__{var}__{reduction}__{digest}.nc")

    lazy = _global_series(dataset, var, x_dim, y_dim, extra_dim_selectors, reduction)
    data = None

    if os.path.exists(path):
        # Decode the cached times the same way as the data (cftime vs
        # datetime64), otherwise the comparisons below never match
        coder = xr.coders.CFDatetimeCoder(use_cftime=lazy["time"].dtype == object)
        with xr.open_dataarray(path, decode_times=coder) as cached:
            cached = cached.load()
        times = lazy["time"].values
        try:
            same_run = times[0] == cached["time"].values[0]
            # Spatial reductions are independent per timestep, so a growing
            # live run only needs its new timesteps computed and appended
            new = np.flatnonzero(times > cached["time"].values[-1])
        except TypeError:
            # Time types differ (e.g. datetime64 vs cftime) - not the same run
            same_run = False
        if same_run and new.size == 0:
            return cached
        if same_run:
            data = xr.concat([cached, lazy.isel(time=new).compute()], dim="time")
        else:
            print(f"Cache for {label}/{var} doesn't match this data - recomputing")

    if data is None:
        data = lazy.compute()

    # Source-file encodings (chunk sizes, compression) don't fit the reduced
    # 1D series; keep only what's needed to round-trip the time axis
    data.encoding = {}
    data["time"].encoding = {
        k: v for k, v in data["time"].encoding.items() if k in ("units", "calendar")
    }
    # Write then rename, so an interrupted write never leaves a corrupt cache
    os.makedirs(cache_dir, exist_ok=True)
    data.to_netcdf(path + ".tmp", format="NETCDF4")
    os.replace(path + ".tmp", path)
    return data


def plot_ocean_global_scalars(
    datasets=None,
    variables=None,
    x_dim="xt_ocean",
    y_dim="yt_ocean",
    extra_dim_selectors=None,
    include_default_references=True,
    show_rolling_mean=True,
    rolling_target_days=365,
    reference_catalogs=None,
    spatial_reductions=None,
    cache=True,
):
    """
    Compare global ocean scalar diagnostics across runs and reference models.

    Parameters
    ----------
    datasets : dict of {str: xarray.Dataset}, optional
        Your own runs, keyed by label.
    variables : list of str, optional
        Variables to plot. Defaults to ``OM3_GLOBAL_SCALARS``.
    x_dim, y_dim : str, default "xt_ocean", "yt_ocean"
        Spatial coordinate names, used if data still needs a spatial mean.
    extra_dim_selectors : dict, optional
        Passed to `select_extra_dims`.
    include_default_references : bool, default True
        Whether to load reference models alongside your runs.
    show_rolling_mean : bool, default True
        Overlay a rolling mean on a faded raw line.
    rolling_target_days : float, default 365
        Rolling window length in days.
    reference_catalogs : dict of {str: str}, optional
        Datastore paths that replace all default references.
    spatial_reductions : dict of {str: str}, optional
        ``{var: "max" | "min"}`` for gridded variables; unlisted ones use the
        area-weighted mean.
    cache : bool, default True
        Save each computed series to ``./live_diagnostics_cache`` and reuse it,
        computing only timesteps newer than the cache. Keep labels unique per run.

    Returns
    -------
    matplotlib.figure.Figure
        One subplot per variable.
    """
    # Copy so the references added below don't leak into the caller's dict
    datasets = dict(datasets or {})
    variables = variables or list(OM3_GLOBAL_SCALARS)
    spatial_reductions = spatial_reductions or {}

    # --- Load reference models ---
    if include_default_references:
        # 1. ACCESS-OM2 reference (skipped when references are overridden)
        if reference_catalogs is None and OM2_REFERENCE_NAME not in datasets:
            try:
                datastore = intake.cat.access_nri[OM2_REFERENCE_NAME]
                datastore = datastore.search(file_id="ocean.1mon.nv:2.scalar_axis:1")
                datasets[OM2_REFERENCE_NAME] = clean_access_dataset(datastore.to_dask())
            except (KeyError, ValueError, OSError) as e:
                print(f"Warning: Could not load OM2 reference - {e}")

        # 2. ACCESS-OM3/CM3 reference datastores (or the user's overrides)
        if reference_catalogs is None:
            reference_catalogs = DEFAULT_REFERENCE_CATALOGS

        # Lets intake-esm combine files whose non-time coords/vars differ
        xarray_kwargs = {
            "compat": "override",
            "data_vars": "minimal",
            "coords": "minimal",
        }

        for name, path in reference_catalogs.items():
            if name in datasets:
                continue
            try:
                ds = intake.open_esm_datastore(
                    path, columns_with_iterables=["variable"]
                )
                # Datastores index the raw output names (e.g. "tosmax"), not
                # the cleaned CMIP6 ones, so search for both
                raw_names = [
                    access_var
                    for access_var, (
                        cmip_var,
                        _,
                    ) in SUPPLEMENTARY_DIRECT_MAPPINGS.items()
                    if cmip_var in variables
                ]
                search_names = variables + raw_names
                ds = ds.search(variable=search_names)
                if len(ds) == 1:
                    dataset = ds.to_dask(xarray_combine_by_coords_kwargs=xarray_kwargs)
                else:
                    # The variables can be split across files that differ in
                    # e.g. temporal_label (max and min fields in separate
                    # files), so load each group and keep only the wanted
                    # variables - first group found wins for any duplicate
                    pieces = {}
                    groups = ds.to_dataset_dict(
                        xarray_combine_by_coords_kwargs=xarray_kwargs,
                        progressbar=False,
                    )
                    for group in groups.values():
                        for var in search_names:
                            if var in group.data_vars:
                                pieces.setdefault(var, group[var])
                    dataset = xr.merge(pieces.values(), join="outer", compat="override")
                datasets[name] = clean_access_dataset(dataset)
            except (KeyError, ValueError, OSError) as e:
                print(f"Warning: Could not load {name} - {e}")

    # --- Plot ---
    fig, axes = plt.subplots(
        len(variables), 1, figsize=(10, 3 * len(variables)), sharex=True, squeeze=False
    )
    axes = axes[:, 0]

    # Shared across subplots so each dataset keeps the same colour on every
    # variable's plot, rather than a fresh colour cycle per subplot
    color_cycle = itertools.cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])
    label_colors = {}

    # Runs mix numpy datetime64 and cftime axes in different calendars, but a
    # shared matplotlib axis holds one time converter - so every series is
    # converted to the calendar of the first one plotted
    target_calendar = None

    for ax, var in zip(axes, variables):
        long_name = None
        units = None
        plotted_any = False

        for label, dataset in datasets.items():
            if var not in dataset.variables:
                continue

            reduction = spatial_reductions.get(var, "mean")
            if cache:
                data = _cached_global_series(
                    os.path.join(os.getcwd(), SCALAR_CACHE_DIRNAME),
                    label,
                    dataset,
                    var,
                    x_dim,
                    y_dim,
                    extra_dim_selectors,
                    reduction,
                )
            else:
                data = _global_series(
                    dataset, var, x_dim, y_dim, extra_dim_selectors, reduction
                ).compute()

            # Drop the NaN padding added when a reference merged variables
            # from files with different time axes
            data = data.dropna("time", how="all")
            target_calendar = target_calendar or data["time"].dt.calendar
            # align_on is only used (and required) for 360_day conversions
            data = data.convert_calendar(
                target_calendar, use_cftime=True, align_on="date"
            )
            plotted_any = True
            units = units or data.attrs.get("units")
            long_name = long_name or data.attrs.get("long_name")
            color = label_colors.setdefault(label, next(color_cycle))

            if show_rolling_mean:
                window = rolling_window_size(
                    data["time"], target_days=rolling_target_days
                )
                smoothed = data.rolling(time=window, center=True).mean()
                # Faded raw series underneath the bold smoothed line
                ax.plot(
                    data["time"].values,
                    data.values,
                    color=color,
                    alpha=0.4,
                    linewidth=1,
                )
                ax.plot(
                    smoothed["time"].values,
                    smoothed.values,
                    color=color,
                    linewidth=2,
                    label=label,
                )
            else:
                ax.plot(data["time"].values, data.values, color=color, label=label)

        title = f"{var}: {long_name}" if long_name else var
        if var in spatial_reductions:
            title += f" (global {spatial_reductions[var]})"
        ax.set_title(title)
        if units:
            ax.set_ylabel(units)
        if plotted_any:
            ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))
        else:
            ax.text(
                0.5,
                0.5,
                f"'{var}' not found in any dataset",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )

    axes[-1].set_xlabel("Time")
    fig.tight_layout()
    return fig


def plot_ocean_gridded_extremes(
    datasets=None,
    max_variables=None,
    min_variables=None,
    x_dim="xh",
    y_dim="yh",
    **plot_kwargs,
):
    """
    Compare global max/min of gridded extreme fields across runs and references.

    Parameters
    ----------
    datasets : dict of {str: xarray.Dataset}, optional
        Your own cleaned runs. Variables none of them contain are skipped.
    max_variables : list of str, optional
        Variables reduced by spatial max. Defaults to ``OM3_GRIDDED_MAX_PLOTS``.
    min_variables : list of str, optional
        Variables reduced by spatial min. Defaults to ``OM3_GRIDDED_MIN_PLOTS``.
    x_dim, y_dim : str, default "xh", "yh"
        Longitude/latitude coordinate names.
    **plot_kwargs
        Passed to `plot_ocean_global_scalars` (e.g. ``show_rolling_mean``).

    Returns
    -------
    matplotlib.figure.Figure
        One subplot per variable.
    """
    max_variables = max_variables or list(OM3_GRIDDED_MAX_PLOTS)
    min_variables = min_variables or list(OM3_GRIDDED_MIN_PLOTS)

    # Skip variables none of your runs have: a reference-only subplot compares
    # nothing, and reducing the references' daily 2D fields is the slow part
    if datasets:
        missing = [
            var
            for var in max_variables + min_variables
            if not any(var in ds.variables for ds in datasets.values())
        ]
        if missing:
            print(f"Skipping {missing} - not found in any of your datasets")
        max_variables = [var for var in max_variables if var not in missing]
        min_variables = [var for var in min_variables if var not in missing]
        if not max_variables + min_variables:
            raise ValueError(
                "None of the requested variables are in your datasets - "
                "did you run clean_access_dataset first?"
            )

    # Each *_max field is reduced by its spatial max and each *_min by its
    # spatial min - the most extreme cell each timestep. An area mean would
    # smooth out the single-cell blow-ups these fields are useful for spotting.
    spatial_reductions = {var: "max" for var in max_variables}
    spatial_reductions.update({var: "min" for var in min_variables})

    return plot_ocean_global_scalars(
        datasets=datasets,
        variables=max_variables + min_variables,
        x_dim=x_dim,
        y_dim=y_dim,
        spatial_reductions=spatial_reductions,
        **plot_kwargs,
    )


# --------------------------------------------------------------------------
# xclim wrappers
# --------------------------------------------------------------------------


def tg_days_above_below_helper(
    dataset, var, xdim, ydim, thresh_kelvin, freq="YS", op=">"
):
    """
    Plot the count of days above/below a threshold of the spatial mean.

    Parameters
    ----------
    dataset : xarray.Dataset
        Output of `clean_access_dataset`, so ``var`` has CMIP6 units.
    var : str
        Temperature variable.
    xdim, ydim : str
        Longitude/latitude dimension names.
    thresh_kelvin : float
        Threshold, in the units of ``var``.
    freq : str, default "YS"
        Resampling frequency for the count.
    op : str, default ">"
        Comparison operator; "<", "lt", "<=", "le" count days below.

    Returns
    -------
    matplotlib.figure.Figure
        Count per period.
    """
    thresh = f"{thresh_kelvin} {dataset[var].attrs['units']}"
    indicator_name = (
        "tg_days_below" if op in ["<", "lt", "<=", "le"] else "tg_days_above"
    )

    # Same lenient options as simulate_ui_run, so monthly data or an
    # incomplete final year (a still-running model) is logged, not rejected
    with xclim.set_options(data_validation="log", check_missing="skip"):
        periods_per_freq = run_xclim_indicator(
            dataset,
            "atmos",
            indicator_name,
            xdim,
            ydim,
            var_mapping={"tas": var},
            thresh=thresh,
            freq=freq,
            op=op,
        )

    fig, ax = plt.subplots(figsize=(12, 6))
    periods_per_freq.plot(ax=ax, color="black")

    ax.set_title(f"Periods per {freq} {op} {thresh_kelvin}K")
    ax.set_ylabel("Count")

    return fig


def get_indicator_groups() -> list[str]:
    """
    List the indicator groups available in ``xclim.indicators``.

    Returns
    -------
    list of str
        Realms and virtual modules, e.g. "atmos", "land", "icclim", "anuclim".
    """
    return [
        name
        for name in dir(xclim.indicators)
        if isinstance(getattr(xclim.indicators, name), types.ModuleType)
        and not name.startswith("_")
    ]


def get_realm_indicators(realm: str) -> list[str]:
    """
    List the indicator names available in an xclim realm.

    Parameters
    ----------
    realm : str
        Indicator group, e.g. "atmos" (see `get_indicator_groups`).

    Returns
    -------
    list of str
        Indicator names in the realm.
    """
    submodule = getattr(xclim.indicators, realm, None)

    if submodule is None:
        valid_realms = [p for p in dir(xclim.indicators) if not p.startswith("_")]
        raise ValueError(f"Invalid realm '{realm}'. Choose from: {valid_realms}")

    # Keep only real Indicator instances, not helper functions/modules
    return [
        name
        for name in dir(submodule)
        if isinstance(getattr(submodule, name), Indicator)
    ]


def get_indicator_inputs(realm: str, indicator_name: str) -> dict:
    """
    Return all parameters of an xclim indicator.

    Parameters
    ----------
    realm : str
        Indicator group, e.g. "atmos".
    indicator_name : str
        Indicator name, e.g. "tg_mean".

    Returns
    -------
    dict
        ``{name: xclim Parameter}`` for every input.
    """
    submodule = getattr(xclim.indicators, realm, None)
    if submodule is None:
        raise ValueError(f"Realm '{realm}' not found.")

    indicator = getattr(submodule, indicator_name, None)
    if not isinstance(indicator, Indicator):
        raise TypeError(f"'{indicator_name}' is not a valid Indicator in '{realm}'.")

    return indicator.parameters


def get_indicator_data_requirements(realm, indicator_name):
    """
    Return the mandatory climate-variable inputs of an xclim indicator.

    Parameters
    ----------
    realm : str
        Indicator group, e.g. "atmos".
    indicator_name : str
        Indicator name, e.g. "tg_mean".

    Returns
    -------
    list of str
        CF variable names the indicator requires, e.g. ["tas"].
    """
    indicator = getattr(getattr(xclim.indicators, realm), indicator_name)

    # Parameter.kind is an InputKind enum. Only VARIABLE inputs are mandatory;
    # OPTIONAL_VARIABLE inputs (e.g. snow depth) default to None. Mirrors the
    # variable_args check in run_xclim_indicator.
    return [
        arg_name
        for arg_name, param in indicator.parameters.items()
        if param.kind == InputKind.VARIABLE
    ]


def get_indicator_kwarg_options(realm, indicator_name):
    """
    Describe every parameter of an xclim indicator, e.g. for a UI form.

    Parameters
    ----------
    realm : str
        Indicator group, e.g. "atmos".
    indicator_name : str
        Indicator name, e.g. "tg_days_above".

    Returns
    -------
    list of dict
        One dict per parameter with keys ``name``, ``kind``, ``required``,
        ``default``, ``choices``, ``units`` and ``description``.
    """
    indicator = getattr(getattr(xclim.indicators, realm), indicator_name)

    kwarg_options = []
    for name, param in indicator.parameters.items():
        if param.kind == InputKind.VARIABLE:
            # Mandatory climate-variable input (e.g. tas)
            required = True
        elif param.kind in (InputKind.OPTIONAL_VARIABLE, InputKind.KWARGS):
            # Optional variables default to None. KWARGS (e.g. `indexer`) use
            # the same "no default" sentinel as mandatory args, but are an
            # open-ended passthrough, so are never required.
            required = False
        else:
            # Required only if xclim has no usable default for it
            required = param.default is inspect.Parameter.empty

        kwarg_options.append(
            {
                "name": name,
                "kind": param.kind.name,
                "required": required,
                "default": (
                    None if param.default is inspect.Parameter.empty else param.default
                ),
                # A choice set can include None (e.g. "no season method"),
                # so sort by string form to avoid comparing None to a str
                "choices": (
                    sorted(param.choices, key=str) if "choices" in param else None
                ),
                "units": param.units if "units" in param else None,
                "description": param.description or None,
            }
        )

    return kwarg_options


def get_indicator_expected_freq(realm, ind_name):
    """
    Return the input frequency an xclim indicator is designed for.

    Parameters
    ----------
    realm : str
        Indicator group, e.g. "atmos".
    ind_name : str
        Indicator name.

    Returns
    -------
    list of str or None
        e.g. ["D"] for a daily indicator, or None if frequency-agnostic.
    """
    # Purely informational (e.g. "this indicator expects daily data").
    # Deliberately not used to filter `discover_indicators`: with
    # data_validation="log", a mismatch is only logged, and filtering
    # previously hid indicators (e.g. tg_mean on monthly data) that ran fine.
    # Read from xclim's own src_freq so it stays correct as xclim changes.
    indicator = getattr(getattr(xclim.indicators, realm), ind_name)
    src_freq = indicator.src_freq

    if src_freq is None:
        return None

    return [src_freq] if isinstance(src_freq, str) else list(src_freq)


def discover_indicators(dataset, realm):
    """
    Split a realm's indicators by whether ``dataset`` has their inputs.

    Parameters
    ----------
    dataset : xarray.Dataset
        Cleaned dataset (see `clean_access_dataset`).
    realm : str
        Indicator group, e.g. "atmos".

    Returns
    -------
    auto_ready : list of str
        Indicators whose required variables are all present.
    needs_mapping : dict of {str: list of str}
        Remaining indicators mapped to their missing variables.
    """
    available_vars = set(dataset.data_vars)
    auto_ready = []
    needs_mapping = {}

    for ind_name in get_realm_indicators(realm):
        required_vars = get_indicator_data_requirements(realm, ind_name)
        missing_vars = [var for var in required_vars if var not in available_vars]

        if missing_vars:
            needs_mapping[ind_name] = missing_vars
        else:
            auto_ready.append(ind_name)

    return auto_ready, needs_mapping


def run_xclim_indicator(
    dataset,
    realm,
    indicator_name,
    xdim,
    ydim,
    var_mapping=None,
    spatial_mean=True,
    **kwargs,
):
    """
    Run any ``xclim.indicators`` indicator, optionally on the spatial mean.

    Parameters
    ----------
    dataset : xarray.Dataset
        Output of `clean_access_dataset`, so CMIP6 names match xclim arg names.
    realm : str
        Indicator group, e.g. "atmos", "land", "seaIce".
    indicator_name : str
        Indicator name, e.g. "tg_days_above".
    xdim, ydim : str
        Spatial coordinate names (grid-dependent, e.g. "lon" or "xt_ocean").
    var_mapping : dict of {str: str}, optional
        Overrides ``{xclim_arg: dataset_var}``, e.g. {"tasmin": "tasmin_fld_s30i206"}.
    spatial_mean : bool, default True
        Reduce each input to an area-weighted spatial mean first.
    **kwargs
        Extra arguments for the indicator (e.g. ``thresh``, ``freq``).

    Returns
    -------
    xarray.DataArray or tuple of xarray.DataArray
        The indicator output.
    """
    submodule = getattr(xclim.indicators, realm, None)
    if submodule is None:
        raise ValueError(f"'{realm}' is not a valid xclim.indicators realm.")

    indicator = getattr(submodule, indicator_name, None)
    if not isinstance(indicator, Indicator):
        raise TypeError(f"'{indicator_name}' is not a valid Indicator in '{realm}'.")

    # Default to an identity mapping (CMIP6 name == xclim arg name) for every
    # variable argument present in the dataset. Explicit var_mapping entries
    # win - needed when clean_access_dataset used a collision-safe fallback
    # name, or a variable was never renamed (multi-variable calculations).
    variable_args = {
        name
        for name, param in indicator.parameters.items()
        if param.kind in (InputKind.VARIABLE, InputKind.OPTIONAL_VARIABLE)
    }
    default_var_mapping = {
        arg: arg for arg in variable_args if arg in dataset.variables
    }
    var_mapping = {**default_var_mapping, **(var_mapping or {})}

    # Spatial weights and reduction dims are shared by every input
    if spatial_mean:
        weights = np.cos(np.deg2rad(dataset[ydim]))
        reduce_dims = spatial_reduction_dims(dataset, xdim, ydim)

    for xclim_arg, dataset_var in var_mapping.items():
        data = dataset[dataset_var]

        if spatial_mean:
            data = data.weighted(weights).mean(dim=reduce_dims, keep_attrs=True)

            # Load eagerly - the spatial mean is small. Run-length-encoding
            # indicators (spell duration, heat-wave, growing-season...)
            # resample then shift/pad along time, which hits a dask-only
            # ZeroDivisionError when a resample group has very few timesteps
            # (e.g. the current period of a still-running model). Rechunking
            # does not avoid it; loading does.
            data = data.load()

        kwargs[xclim_arg] = data

    return indicator(**kwargs)


def simulate_ui_run(
    dataset, realm, indicator_name, manual_mapping=None, spatial_mean=True, **kwargs
):
    """
    Simulate a UI run of an xclim indicator with auto + manual variable mapping.

    Parameters
    ----------
    dataset : xarray.Dataset
        Cleaned dataset with "lon"/"lat" coordinates.
    realm : str
        Indicator group, e.g. "atmos".
    indicator_name : str
        Indicator name.
    manual_mapping : dict of {str: str}, optional
        User-chosen ``{xclim_arg: dataset_var}``, e.g. {"tas": "tas_fld_s00i010"}.
    spatial_mean : bool, default True
        Passed to `run_xclim_indicator`.
    **kwargs
        Extra arguments for the indicator.

    Returns
    -------
    xarray.DataArray or tuple of xarray.DataArray
        The indicator output.
    """
    manual_mapping = manual_mapping or {}
    available_vars = set(dataset.data_vars)
    required_vars = get_indicator_data_requirements(realm, indicator_name)

    final_mapping = {}
    for req_var in required_vars:
        if req_var in manual_mapping:
            # User explicitly mapped this input
            final_mapping[req_var] = manual_mapping[req_var]
        elif req_var in available_vars:
            # Auto-matched from the cleaned dataset
            final_mapping[req_var] = req_var
        else:
            raise ValueError(
                f"Missing input: '{req_var}'. The dataset does not contain this variable, "
                f"and it was not provided in the manual_mapping dictionary."
            )

    print(f"Executing {indicator_name} with mapping: {final_mapping}")

    # Log (don't raise) on frequency/units mismatches, and skip missing-value
    # checks, so live partially-complete output still runs
    with xclim.set_options(data_validation="log", check_missing="skip"):
        result = run_xclim_indicator(
            dataset=dataset,
            realm=realm,
            indicator_name=indicator_name,
            var_mapping=final_mapping,
            xdim="lon",
            ydim="lat",
            spatial_mean=spatial_mean,
            **kwargs,
        )

    return result
