# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for diagnostic recipes / scripting"""

import csv
import inspect
import itertools
import types
from contextlib import nullcontext
from importlib import resources

import matplotlib.pyplot as plt
import nc_time_axis  # noqa: F401 - registers matplotlib's cftime unit converter
import numpy as np
import xclim.indicators
import xclim.indices as xcl
from xclim.core.indicator import Indicator
from xclim.core.utils import InputKind

from . import data


def clean_access_dataset(dataset, master_map_path=None):
    """
    Cleans an ACCESS/UM dataset into a CMIP6-standard format for xclim
    by dynamically reading the ACCESS-NRI master_map.csv file.
    https://github.com/ACCESS-Community-Hub/APP4/blob/master/input_files/master_map.csv

    master_map_path: optional override to a custom master_map.csv. If omitted,
    the copy bundled with the med_diagnostics package is used, located via
    importlib.resources so it resolves correctly regardless of the caller's
    working directory (e.g. a notebook started from an arbitrary directory)
    or how the package was installed (wheel, editable install, zipped egg).
    """

    stash_to_cmip = {}
    cmip_units = {}

    if master_map_path is None:
        map_file_ctx = resources.as_file(
            resources.files("med_diagnostics").joinpath("master_map.csv")
        )
    else:
        map_file_ctx = nullcontext(master_map_path)

    # 1. Parse the master_map.csv to build translation dictionaries
    with map_file_ctx as map_path, open(map_path, mode="r") as file:
        # Skip commented header lines and read as CSV
        reader = csv.reader(filter(lambda row: not row.startswith("#"), file))

        for row in reader:
            # Check if row has enough columns based on the master_map structure
            if len(row) < 5:
                continue

            cmip_var = row[0].strip()
            access_vars = row[2].strip()
            calculation = row[3].strip()
            units = row[4].strip()

            # For lightweight UI sanitisation, we only automatically map
            # variables that are direct 1-to-1 translations
            # (i.e., no spaces indicating multiple vars, and no complex calculation strings)
            if " " not in access_vars and not calculation:
                # Multiple stash codes can map to the same cmip_var (e.g. a
                # CM2-specific and an ESM-specific stash code for zg500) -
                # keep every stash code -> cmip_var pairing rather than
                # letting a later row silently overwrite an earlier one.
                stash_to_cmip[access_vars] = cmip_var
                cmip_units[cmip_var] = units

    # 2. Safely build the rename dictionary to prevent Xarray conflicts
    rename_dict = {}

    # Track existing names to prevent overwriting native variables
    used_cmip_names = set(dataset.variables)

    # Units keyed by the *final* renamed name, so a fallback-renamed
    # variable (e.g. 'hus_fld_s00i010') still gets its units set, not just
    # whichever stash code won the plain 'hus' name.
    units_by_final_name = {}

    for stash_var, cmip_var in stash_to_cmip.items():
        if stash_var in dataset.variables:
            if cmip_var not in used_cmip_names:
                # Primary choice: clean CMIP6 name (e.g., 'hus')
                final_name = cmip_var
            else:
                # Fallback: append STASH code to prevent collision (e.g., 'hus_fld_s00i010')
                final_name = f"{cmip_var}_{stash_var}"

            rename_dict[stash_var] = final_name
            used_cmip_names.add(final_name)
            units_by_final_name[final_name] = cmip_units[cmip_var]

    # 3. Rename variables found in the dataset
    clean_ds = dataset.rename(rename_dict)

    # 4. Assign CMIP6 compliant units
    for var in clean_ds.data_vars:
        if var in units_by_final_name:
            # xclim requires units to be explicitly set in the attributes
            clean_ds[var].attrs["units"] = units_by_final_name[var]

    # 5. Safeguard spatial dimensions against being squeezed out later
    # (Fixes the issue where bounding boxes reduce Tasmania to 1 longitude point)
    for dim in ["lon", "lat"]:
        if dim not in clean_ds.dims and dim in clean_ds.coords:
            clean_ds = clean_ds.expand_dims(dim)

    return clean_ds


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
    - lon_dim: Name of longitude coordinate (e.g., "xt_ocean", "lon", or a
      curvilinear/tripolar grid's 2D auxiliary coordinate like "TLON")
    - lat_dim: Name of latitude coordinate (e.g., "yt_ocean", "lat", or "TLAT")

    Handles both regular 1D lat/lon grids (fast slice-based `.sel()`) and
    curvilinear/tripolar ocean grids (e.g. ACCESS-OM2/CICE's TLAT/TLON)
    where lat_dim/lon_dim are 2D auxiliary coordinates that vary over the
    underlying grid-index dimensions - `.sel()` can only build a slice
    index from a 1D coordinate, so those are masked and dropped instead.
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

    lon_coord = dataset[lon_dim]
    lat_coord = dataset[lat_dim]

    # 2. Dynamically handle 0-360 vs -180-180 longitude grids
    if lon_coord.max() > 180:
        lon_min = lon_min % 360
        lon_max = lon_max % 360

    # 3. Sort bounds to ensure xarray returns data
    # (Slicing/masking max to min returns empty arrays in xarray)
    lon_lo, lon_hi = min(lon_min, lon_max), max(lon_min, lon_max)
    lat_lo, lat_hi = min(lat_min, lat_max), max(lat_min, lat_max)

    if lon_coord.ndim > 1 or lat_coord.ndim > 1:
        in_region = (
            (lon_coord >= lon_lo)
            & (lon_coord <= lon_hi)
            & (lat_coord >= lat_lo)
            & (lat_coord <= lat_hi)
        )
        # `where(..., drop=True)` uses the mask as a fancy indexer, which
        # xarray refuses for a dask-backed boolean array (its shape after
        # indexing would be unknown ahead of time). The mask is only
        # grid-sized (no time dimension), so computing it eagerly is cheap
        # regardless of how large the full dataset is.
        return dataset.where(in_region.compute(), drop=True)

    return dataset.sel({lat_dim: slice(lat_lo, lat_hi), lon_dim: slice(lon_lo, lon_hi)})


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


def median_timestep_days(time_da):
    """Median spacing between consecutive time steps, in days.

    Cftime-safe: `numpy.diff` on an `object`-dtype cftime time axis (e.g.
    360_day/noleap calendars) yields `datetime.timedelta` objects rather
    than `numpy.timedelta64`, so the two dtypes need separate handling.
    Shared by `rolling_window_size` (window sizing) and `discover_indicators`
    (dataset frequency detection).
    """
    diffs = np.diff(time_da.values)
    if diffs.dtype == object:
        return np.median([d.days + d.seconds / 86400 for d in diffs])
    return np.median(diffs / np.timedelta64(1, "D"))


def rolling_window_size(time_da, target_days=150):
    """Approximate a 5-month (150 day) rolling window in native timesteps.

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
    step_days = median_timestep_days(time_da)
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


OM3_GLOBAL_SCALARS = ["masso", "thetaoga", "soga", "tosga", "sosga"]

# The 4 standard comparison experiments overlaid in the ACCESS-OM3 paper's
# timeseries notebook: the OM2 baseline, two OM3 test configurations, and
# the CM3 reference. Names as they appear in that notebook's own legend.
DEFAULT_OM3_TIMESERIES_REFERENCES = ["025deg_jra55_iaf_omip2_cycle1"]


def load_default_om3_reference_datasets(dataset_key="ocean.1mon.nv:2.scalar_axis:1"):
    """Load the 4 standard ACCESS-OM3-paper reference experiments (see
    DEFAULT_OM3_TIMESERIES_REFERENCES) via data.load_reference_dataset, as a
    ready-to-use {label: xarray.Dataset} dict for plot_ocean_global_scalars.

    dataset_key: the catalog dataset/variable-group key to load within each
    experiment (see data.load_reference_dataset) - defaults to the single
    guess "ocean_scalar" for the group holding precomputed global scalars
    (masso/thetaoga/soga/tosga/sosga). This couldn't be verified against a
    live catalog, so confirm/override it for your actual catalog schema.
    Pass a dict of {experiment_name: dataset_key} instead of a string if a
    different key is needed per experiment (e.g. the CM3 reference using a
    different naming convention to the OM3/OM2 ones).

    An experiment that fails to load (e.g. its name doesn't resolve in your
    catalog, or dataset_key is wrong for it) is skipped with a printed
    warning rather than failing the whole load, since not every reference is
    guaranteed reachable from every environment.
    """
    access_nri_cat = data._load_access_nri_catalog("OM2", filter=True)

    references = {}
    for name in DEFAULT_OM3_TIMESERIES_REFERENCES:
        model = access_nri_cat.search(name=name).to_source()
        references[name] = data._build_data_object(model, dataset_key)

    return references


def plot_ocean_global_scalars(
    datasets=None,
    variables=None,
    x_dim="xt_ocean",
    y_dim="yt_ocean",
    extra_dim_selectors=None,
    include_default_references=True,
    show_rolling_mean=True,
    rolling_target_days=365,
):
    """Compare global ocean scalar diagnostics across one or more datasets.

    Mirrors the ACCESS-OM3 timeseries-comparison notebook
    (https://access-om3-paper-1.readthedocs.io/.../notebooks/timeseries/),
    which overlays each experiment's global-mean ocean mass/temperature/
    salinity scalars on one plot per variable, with a smoothed trend line
    per dataset. That notebook's variables (masso, thetaoga, soga, tosga,
    sosga) are model-native precomputed scalars with no remaining spatial
    dims, so this reimplements the comparison natively rather than
    depending on the notebook's xgcm/intake stack (ruled out for MED's live
    dashboard - see MED-esmvaltool-integration-analysis.md for why heavy
    grid-metrics/batch dependencies don't fit MED's in-memory, per-click use
    case).

    datasets: dict mapping a label (e.g. experiment/model name) to an
    xarray.Dataset. Merged with the 4 standard reference experiments from
    the ACCESS-OM3 paper (see load_default_om3_reference_datasets) unless
    include_default_references=False; a label already present in datasets
    takes priority over a same-named default. A variable missing from a
    given dataset is skipped for that dataset only, since not every
    experiment reports every scalar.

    variables: list of variable names to compare; defaults to
    OM3_GLOBAL_SCALARS.

    x_dim/y_dim: ocean grid's horizontal dimension/coordinate names (e.g.
    'xt_ocean'/'yt_ocean' for MOM5, 'xh'/'yh' for MOM6, or a curvilinear
    grid's 2D aux coordinates like 'TLON'/'TLAT'). Only used as a fallback
    for variables that still carry spatial dims after select_extra_dims -
    those get a cos-latitude-weighted global mean, consistent with the rest
    of this module's spatial-reduction convention. True cell-area/volume
    weighting (as the notebook's xgcm grid metrics provide) isn't available
    here without that heavier dependency.

    extra_dim_selectors: as in select_extra_dims - value(s) to use for any
    other non-time, non-spatial dimension (e.g. a depth or scalar_axis dim)
    a variable might still carry.

    include_default_references: if True (default), auto-loads and overlays
    the 4 standard ACCESS-OM3-paper reference experiments alongside
    whatever's in datasets, to match the paper's own comparison figure out
    of the box. Set False to only plot exactly what's in datasets.

    show_rolling_mean: if True (default), overlays each dataset's smoothed
    rolling-mean trend line on top of its raw line (same color, thicker),
    using the same rolling_window_size-based smoothing sst_anomaly_nino34
    already uses elsewhere in this module - makes the underlying multi-year
    trend legible under the seasonal cycle, matching the reference figure's
    style. rolling_target_days sets the smoothing window (default ~365
    days/1 year, longer than sst_anomaly_nino34's ~150-day/5-month default
    since a multi-decade ocean-scalar record benefits from heavier
    smoothing than an ENSO index does).

    Returns the matplotlib Figure (one subplot per variable).
    """
    datasets = dict(datasets or {})
    if include_default_references:
        for label, dataset in load_default_om3_reference_datasets().items():
            datasets.setdefault(label, dataset)

    variables = variables or list(OM3_GLOBAL_SCALARS)

    fig, axes = plt.subplots(
        len(variables), 1, figsize=(10, 3 * len(variables)), sharex=True, squeeze=False
    )
    axes = axes[:, 0]

    # Shared across subplots so the same dataset gets the same color on
    # every variable's plot, not a fresh color cycle per subplot.
    color_cycle = itertools.cycle(plt.rcParams["axes.prop_cycle"].by_key()["color"])
    label_colors = {}

    for ax, var in zip(axes, variables):
        long_name = var
        units = None
        plotted_any = False

        for label, dataset in datasets.items():
            if var not in dataset.variables:
                continue

            try:
                real_spatial_dims = set(spatial_reduction_dims(dataset, x_dim, y_dim))
            except KeyError:
                # x_dim/y_dim aren't coordinates on this dataset at all -
                # e.g. an already-scalar diagnostic with no grid dims.
                real_spatial_dims = {x_dim, y_dim}

            data = select_extra_dims(
                dataset[var],
                exclude_dims={"time"} | real_spatial_dims,
                extra_dim_selectors=extra_dim_selectors,
            )

            present_spatial_dims = [d for d in real_spatial_dims if d in data.dims]
            if present_spatial_dims:
                weights = np.cos(np.deg2rad(dataset[y_dim]))
                data = data.weighted(weights).mean(
                    dim=present_spatial_dims, keep_attrs=True
                )

            data = data.compute()
            plotted_any = True
            units = units or data.attrs.get("units")
            long_name = data.attrs.get("long_name", long_name)
            color = label_colors.setdefault(label, next(color_cycle))

            if show_rolling_mean:
                window = rolling_window_size(
                    data["time"], target_days=rolling_target_days
                )
                smoothed = data.rolling(time=window, center=True).mean()
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

        ax.set_title(long_name)
        if units:
            ax.set_ylabel(units)
        if plotted_any:
            ax.legend()
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


def tg_days_above_below_helper(
    dataset, var, xdim, ydim, thresh_kelvin, freq="YS", op=">"
):
    """Assumes `dataset` has already been passed through clean_access_dataset,
    so `var` already carries CMIP6-compliant units in its attrs."""

    weights = np.cos(np.deg2rad(dataset[ydim]))
    spatial_mean = (
        dataset[var].weighted(weights).mean(dim=[xdim, ydim], keep_attrs=True)
    )

    thresh = f"{thresh_kelvin} {spatial_mean.attrs['units']}"

    if op in ["<", "lt", "<=", "le"]:
        convective_periods_per_year = xcl.tg_days_below(
            tas=spatial_mean, thresh=thresh, freq=freq, op=op
        )
    else:
        convective_periods_per_year = xcl.tg_days_above(
            tas=spatial_mean, thresh=thresh, freq=freq, op=op
        )

    fig, ax = plt.subplots(figsize=(12, 6))
    convective_periods_per_year.compute().plot(ax=ax, color="black")

    ax.set_title(f"Periods per {freq} {op} {thresh_kelvin}K")
    ax.set_ylabel("Count")

    return fig


def spatial_reduction_dims(dataset, *coord_names):
    """The real xarray dimensions underlying one or more spatial coordinates.

    For a regular 1D lat/lon grid, a coordinate's dim is itself (e.g. 'lat'
    is indexed by dim 'lat'). For a curvilinear/tripolar ocean grid (e.g.
    ACCESS-OM2/CICE's TLAT/TLON), lat/lon are 2D auxiliary coordinates
    indexed by differently-named grid-index dims (e.g. 'nj'/'ni') - passing
    the coordinate's own name to `.mean(dim=...)` in that case is a no-op
    at best and a KeyError at worst, since "TLAT" isn't an actual dimension.
    """
    dims = []
    for name in coord_names:
        for dim in dataset[name].dims:
            if dim not in dims:
                dims.append(dim)
    return dims


def run_xclim_index(
    dataset, var_name, index_name, xdim, ydim, xclim_arg="tas", **kwargs
):
    """
    Universal wrapper to run any xclim.indices function on a spatially averaged dataset.

    Assumes `dataset` has already been passed through clean_access_dataset, so
    `var_name` already carries CMIP6-compliant units in its attrs.

    Parameters:
    - index_name: String of the xclim function to use (e.g., 'tg_days_above').
    - xclim_arg: The variable name xclim expects (e.g., 'tas' for temp, 'pr' for precip).
    - **kwargs: Any extra arguments the specific xclim function requires (thresh, freq, etc.).
    """

    # Apply spatial weighting and mean, preserving the cleaned units attrs
    weights = np.cos(np.deg2rad(dataset[ydim]))
    spatial_mean = (
        dataset[var_name]
        .weighted(weights)
        .mean(dim=spatial_reduction_dims(dataset, xdim, ydim), keep_attrs=True)
        # Load eagerly - see the matching comment in run_xclim_indicator:
        # dask-backed input into a run-length-encoding-based xclim index
        # can hit a dask-only ZeroDivisionError when a resample group has
        # very few timesteps. `spatial_mean` is small by this point, so
        # loading it is cheap.
        .load()
    )

    # Retrieve the requested function dynamically from the xclim package
    try:
        xclim_function = getattr(xcl, index_name)
    except AttributeError:
        raise AttributeError(f"'{index_name}' is not a valid xclim.indices function.")

    # Inject the processed spatial mean into the kwargs (e.g., tas=spatial_mean)
    kwargs[xclim_arg] = spatial_mean

    # 5. Execute the xclim function with all provided arguments
    result = xclim_function(**kwargs)

    return result


# The xclim realms are only
def get_realm_indicators(realm: str) -> list[str]:
    """Dynamically return available indicator names for a given xclim realm."""
    submodule = getattr(xclim.indicators, realm, None)

    if submodule is None:
        valid_realms = [p for p in dir(xclim.indicators) if not p.startswith("_")]
        raise ValueError(f"Invalid realm '{realm}'. Choose from: {valid_realms}")

    # Filter submodule attributes to find active xclim Indicator instances
    return [
        name
        for name in dir(submodule)
        if isinstance(getattr(submodule, name), Indicator)
    ]


def get_indicator_inputs(realm: str, indicator_name: str) -> dict:
    """Dynamically returns the required inputs for a specific xclim indicator."""
    submodule = getattr(xclim.indicators, realm, None)
    if submodule is None:
        raise ValueError(f"Realm '{realm}' not found.")

    indicator = getattr(submodule, indicator_name, None)
    if not isinstance(indicator, Indicator):
        raise TypeError(f"'{indicator_name}' is not a valid Indicator in '{realm}'.")

    # The parameters attribute provides a dictionary of all inputs
    return indicator.parameters


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
    Universal wrapper to run any xclim.indicator on a spatially averaged dataset.

    Assumes `dataset` has already been passed through clean_access_dataset, so
    a variable's CMIP6 short name (e.g. 'tasmin') is also the xclim argument
    name it's meant for, and it already carries CMIP6-compliant units in its
    attrs.

    Parameters:
    - dataset: xarray.Dataset containing the data.
    - realm: String of the xclim realm (e.g., 'atmos', 'land', 'seaIce').
    - indicator_name: String of the xclim indicator to use (e.g., 'tg_days_above').
    - xdim, ydim: Strings of the spatial dimensions (e.g., 'lon', 'lat'). Not
      touched by clean_access_dataset - still model/grid-dependent (e.g.
      atmos 'lon'/'lat' vs ocean 'xt_ocean'/'yt_ocean').
    - var_mapping: Optional dictionary mapping an xclim argument name to a
                   different dataset variable name (e.g.,
                   {'tasmin': 'tasmin_fld_s30i206'}). Only needed to override
                   the default identity mapping - e.g. when
                   clean_access_dataset fell back to a collision-safe name,
                   or the variable was never auto-renamed to its CMIP6 name
                   (any stash code needing a multi-variable calculation).
    - **kwargs: Any extra arguments the specific xclim indicator requires (thresh, freq, etc.).
    """

    # Retrieve the requested realm submodule
    submodule = getattr(xclim.indicators, realm, None)
    if submodule is None:
        raise ValueError(f"'{realm}' is not a valid xclim.indicators realm.")

    # Retrieve the requested indicator dynamically
    indicator = getattr(submodule, indicator_name, None)
    if not isinstance(indicator, Indicator):
        raise TypeError(f"'{indicator_name}' is not a valid Indicator in '{realm}'.")

    # Default to an identity mapping (CMIP6 name == xclim arg name) for every
    # climate-variable argument the indicator takes that's actually present
    # in the dataset; explicit var_mapping entries override the default.
    variable_args = {
        name
        for name, param in indicator.parameters.items()
        if param.kind in (InputKind.VARIABLE, InputKind.OPTIONAL_VARIABLE)
    }
    default_var_mapping = {
        arg: arg for arg in variable_args if arg in dataset.variables
    }
    var_mapping = {**default_var_mapping, **(var_mapping or {})}

    # Calculate spatial weights and reduction dims once
    if spatial_mean:
        weights = np.cos(np.deg2rad(dataset[ydim]))
        reduce_dims = spatial_reduction_dims(dataset, xdim, ydim)

    # Process each variable in the mapping
    for xclim_arg, dataset_var in var_mapping.items():
        data = dataset[dataset_var]

        if spatial_mean:
            # Apply spatial weighting and mean, preserving the cleaned units attrs
            data = data.weighted(weights).mean(dim=reduce_dims, keep_attrs=True)

            # Load eagerly: by this point `data` is only a small
            # per-timestep spatial mean, cheap to bring into memory. Many
            # xclim indicators built on run-length encoding (spell
            # duration, heat-wave, growing-season, etc.) resample-then-
            # shift/pad along "time" internally, which hits a dask-only
            # `ZeroDivisionError` deep in dask's array-padding code - a
            # dask/xarray bug, not a data problem - whenever a resample
            # group has very few timesteps (e.g. the still-accumulating
            # current period of a live, still-running model). Loading
            # sidesteps it entirely; rechunking does not (verified: it
            # still reproduces on a single-chunk dask array).
            data = data.load()

        # Inject the processed variable into the kwargs
        kwargs[xclim_arg] = data

    # Execute the xclim indicator with all provided arguments
    result = indicator(**kwargs)

    return result


def get_indicator_groups() -> list[str]:
    """
    Returns a list of all indicator groups (realms and virtual modules)
    available in xclim.indicators (e.g., 'atmos', 'cf', 'icclim', 'anuclim').
    """
    return [
        name
        for name in dir(xclim.indicators)
        if isinstance(getattr(xclim.indicators, name), types.ModuleType)
        and not name.startswith("_")
    ]


def get_indicator_data_requirements(realm, indicator_name):
    """
    Extracts the expected CF variable names (e.g., 'tas', 'pr') that an xclim indicator requires.

    `indicator.parameters` maps arg name -> a `Parameter` object (not a dict,
    so it has no `.get()`), whose `.kind` is an `InputKind` enum value. Only
    `InputKind.VARIABLE` args are mandatory data inputs the caller must
    supply; `InputKind.OPTIONAL_VARIABLE` args (e.g. an optional snow-depth
    input) default to None and aren't required. This mirrors the
    `variable_args` check `run_xclim_indicator` already uses.
    """
    indicator = getattr(getattr(xclim.indicators, realm), indicator_name)

    return [
        arg_name
        for arg_name, param in indicator.parameters.items()
        if param.kind == InputKind.VARIABLE
    ]


def get_indicator_kwarg_options(realm, indicator_name):
    """
    Describes every parameter of an xclim indicator, for building a UI form:
    its kind (e.g. 'VARIABLE', 'QUANTIFIED', 'FREQ_STR'), whether it's
    required, its default (if any), the fixed set of valid choices (if
    constrained, e.g. `op`'s {'>', '>=', ...}), units, and description.

    A parameter is treated as required if it's a mandatory climate-variable
    input (`InputKind.VARIABLE`, e.g. `tas`), or if xclim has no usable
    default for it at all. `InputKind.KWARGS` params (e.g. `indexer`, an
    open-ended **kwargs passthrough) are never required even though xclim
    also represents "no default" for them with the same sentinel used for
    genuinely mandatory args, so they need their own branch below.
    Optional-variable params (`InputKind.OPTIONAL_VARIABLE`) default to None
    and are likewise never required.
    """
    indicator = getattr(getattr(xclim.indicators, realm), indicator_name)

    kwarg_options = []
    for name, param in indicator.parameters.items():
        if param.kind == InputKind.VARIABLE:
            required = True
        elif param.kind in (InputKind.OPTIONAL_VARIABLE, InputKind.KWARGS):
            required = False
        else:
            # xclim's own sentinel for "no default was provided" -
            # distinct from the sentinel it uses for unset units/choices.
            required = param.default is inspect._empty

        kwarg_options.append(
            {
                "name": name,
                "kind": param.kind.name,
                "required": required,
                "default": None if param.default is inspect._empty else param.default,
                # A choice set can itself include None as a valid option
                # (e.g. "no season method"), so sort by string form rather
                # than raw value to avoid comparing None to a str.
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
    Returns the input time-step frequency (or frequencies) an xclim
    indicator's compute function is designed for, e.g. 'D' for a
    daily-threshold indicator, or None if the indicator is
    frequency-agnostic. Purely informational (e.g. for a UI to show "this
    indicator expects daily data") - xclim itself doesn't refuse to run an
    indicator on a different frequency (with MED's `data_validation="log"`
    setting, a mismatch is only ever logged, never raised), so this is
    deliberately not used to filter `discover_indicators`'s results:
    doing so previously excluded indicators (e.g. `tg_mean`, `tg_days_above`
    on monthly data, `chill_units` on daily data) that ran and produced
    real output despite the nominal frequency mismatch.

    Sourced directly from xclim's own `Indicator.src_freq` rather than a
    hand-maintained allowlist, so every indicator is covered correctly
    (not just a handful of hardcoded names) and this stays correct as
    xclim's indicator set changes.
    """
    indicator = getattr(getattr(xclim.indicators, realm), ind_name)
    src_freq = indicator.src_freq

    if src_freq is None:
        return None

    return [src_freq] if isinstance(src_freq, str) else list(src_freq)


def discover_indicators(dataset, realm):
    """
    Scans a realm and separates indicators into those that can run automatically
    and those that require manual variable mapping.
    """
    available_vars = set(dataset.data_vars)
    all_indicators = get_realm_indicators(realm)

    auto_ready = []
    needs_mapping = {}

    for ind_name in all_indicators:
        required_vars = get_indicator_data_requirements(realm, ind_name)
        missing_vars = [var for var in required_vars if var not in available_vars]

        if missing_vars:
            needs_mapping[ind_name] = missing_vars
        else:
            auto_ready.append(ind_name)

    return auto_ready, needs_mapping


def simulate_ui_run(
    dataset, realm, indicator_name, manual_mapping=None, spatial_mean=True, **kwargs
):
    """
    Simulates the UI execution step. It auto-matches available variables
    and applies any manual mappings provided by the user.
    """
    manual_mapping = manual_mapping or {}
    available_vars = set(dataset.data_vars)
    required_vars = get_indicator_data_requirements(realm, indicator_name)

    final_mapping = {}

    for req_var in required_vars:
        if req_var in manual_mapping:
            # User manually mapped this input (e.g., they assigned 'tas_fld_s00i010' to 'tas')
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
