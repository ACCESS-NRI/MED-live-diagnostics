import warnings
from functools import cache
from pathlib import Path
from typing import Annotated

import intake
import numpy as np
import pandas as pd
import xarray as xr
from intake_esm.source import ESMDataSourceError

from med_diagnostics import plot_customisations

PREDEFINED_REGIONS = {
    # ENSO regions, from NOAA CPC: https://cpc.ncep.noaa.gov/products/CDB/Tropics/figt5.shtml
    "nino12": {"lat": (-10, 0), "lon": (-90, -80)},
    "nino3": {"lat": (-5, 5), "lon": (-150, -90)},
    "nino34": {"lat": (-5, 5), "lon": (-170, -120)},
    "nino4": {"lat": (-5, 5), "lon": (160, -150)},  # Note: crosses the 180 dateline
    # Indian Ocean Dipole (IOD) poles, from Saji et al. (1999), doi:10.1038/43854
    "iod_west": {"lat": (-10, 10), "lon": (50, 70)},
    "iod_east": {"lat": (-10, 0), "lon": (90, 110)},
    # Atlantic indices, from NOAA State of the Ocean (NOAA PSL's TNA box is slightly smaller): https://stateoftheocean.osmc.noaa.gov/sur/atl/tna.php
    "tna": {"lat": (5, 25), "lon": (-55, -15)},  # Tropical North Atlantic
    "tsa": {"lat": (-20, 0), "lon": (-30, 10)},  # Tropical South Atlantic
    # Hemispheres & Global Bounds (no single standard, e.g. tropics are often ±23.4°)
    "global": {"lat": (-90, 90), "lon": (-180, 180)},
    "nh": {"lat": (0, 90), "lon": (-180, 180)},  # Northern Hemisphere
    "sh": {"lat": (-90, 0), "lon": (-180, 180)},  # Southern Hemisphere
    "tropics": {"lat": (-20, 20), "lon": (-180, 180)},
    # Continents & Specific Geographic Regions (hand-drawn boxes, not standard; polar edges are the polar circles)
    "tasmania": {"lat": (-44, -39), "lon": (143, 149)},
    "australia": {"lat": (-44, -10), "lon": (112, 154)},
    "maritime_continent": {"lat": (-10, 10), "lon": (90, 150)},
    "southern_ocean": {"lat": (-90, -50), "lon": (-180, 180)},
    "arctic": {"lat": (66.5, 90), "lon": (-180, 180)},
    "antarctic": {"lat": (-90, -66.5), "lon": (-180, 180)},
}


# Reference runs from https://github.com/ACCESS-Community-Hub/access-om3-paper-1/blob/main/notebooks/timeseries.ipynb
OM3_TIMESERIES_REF_CATALOGS = [
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf-1.0-beta-5165c0f8/datastore.json",
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test3v2-00532b88/datastore.json",
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test4-d28e0359/datastore.json",
    "/g/data/ol01/outputs/access-om3-100km/MC_100km_jra_ryf+wombatlite-1e74abf-11f9df5c/experiment_datastore.json",
]
# RYF runs have made-up years, so they're moved to start in the user data's first year
OM3_TIMESERIES_RYF_EXPTS = ["MC_100km_jra_ryf+wombatlite-1e74abf-11f9df5c"]
# Use "025deg_jra55_ryf9091_gadi" for RYF runs
OM3_TIMESERIES_OM2_EXPT = "025deg_jra55_iaf_omip2_cycle1"
OM3_TIMESERIES_IAF = True

# OM3 name -> (OM2 name or None, plot label)
OM3_TIMESERIES_FIELDS = {
    "masso": (None, "Mass of liquid ocean"),
    "soga": ("salt_global_ave", "Global Mean Ocean Salinity"),
    "thetaoga": ("temp_global_ave", "Global Mean Ocean Potential Temperature"),
    "tosga": ("temp_surface_ave", "Sea Surface Temperature"),
    "sosga": ("salt_surface_ave", "Global Mean Sea Surface Salinity"),
    "speed_max": (None, "Maximum Ocean Current Speed"),
    "mlotst_max": (None, "Maximum Ocean Mixed Layer Thickness"),
    "tos_max": (None, "Maximum Sea Surface Temperature"),
    "tos_min": (None, "Minimum Sea Surface Temperature"),
    "sos_max": (None, "Maximum Sea Surface Salinity"),
    "sos_min": (None, "Minimum Sea Surface Salinity"),
    "zos_max": (None, "Maximum Sea Surface Height"),
    "zos_min": (None, "Minimum Sea Surface Height"),
    "total_salt_Flux_Added": (None, "Total Salt Flux Added"),
    "total_salt_Flux_In": (None, "Total Salt Flux In"),
    "total_salt_flux": (None, "Total Salt Flux"),
    "net_fresh_water_global_adjustment": (None, "Net Fresh Water Global Adjustment"),
    "salt_flux_global_restoring_adjustment": (
        None,
        "Salt Flux Global Restoring Adjustment",
    ),
    "total_wfo": (None, "Total Water Flux Into Ocean"),
    "total_evs": (None, "Total Evaporation"),
    "total_fsitherm": (None, "Total Thermodynamic Sea Ice Flux"),
    "total_precip": (None, "Total Precipitation"),
    "total_prsn": (None, "Total Snowfall"),
    "total_lprec": (None, "Total Liquid Precipitation"),
    "total_ficeberg": (None, "Total Iceberg Melt"),
    "total_friver": (None, "Total River Runoff"),
    "total_net_massout": (None, "Total Net Mass Out"),
    "total_net_massin": (None, "Total Net Mass In"),
}

# Same search order as the paper notebook, narrowed until each search finds one dataset
OM3_TIMESERIES_REF_SEARCHES = [
    {},
    {"frequency": "1mon", "variable_cell_methods": ".*time: mean.*"},
    {"variable_cell_methods": ".*time: mean.*"},
    {"variable_cell_methods": ".*time: point.*"},
    {"variable_cell_methods": ".*time: min.*"},
    {"variable_cell_methods": ".*time: max.*"},
]
OM3_TIMESERIES_COMBINE_KWARGS = {
    "compat": "override",
    "data_vars": "minimal",
    "coords": "minimal",
}


# --------------------------------------------------------------------------
# General helpers - reusable in custom recipes for any grid
# --------------------------------------------------------------------------


def extract_region(dataset, region, lon_dim="lon", lat_dim="lat"):
    """
    Helper to extract a lat/lon bounding box, on regular or curvilinear grids.

    Parameters
    ----------
    dataset : xarray.Dataset or xarray.DataArray
        Data to subset.
    region : str or dict
        A key of ``PREDEFINED_REGIONS``, or ``{"lat": (min, max), "lon": (west, east)}``.
    lon_dim, lat_dim : str, default "lon", "lat"
        Longitude/latitude coordinate names (e.g. "xt_ocean" or 2D "TLON").

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        The subset within the bounding box.
    """
    # Resolve the region into lat/lon bounds
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

    lon_west, lon_east = bounds["lon"]
    lat_lo, lat_hi = sorted(bounds["lat"])

    lon_coord = dataset[lon_dim]
    lat_coord = dataset[lat_dim]

    if lon_east - lon_west >= 360:
        in_lon = xr.ones_like(lon_coord, dtype=bool)
    else:
        # Shift the region's longitudes into the grid's own 360° window.
        grid_lon_min = float(lon_coord.min())
        lon_west = (lon_west - grid_lon_min) % 360 + grid_lon_min
        lon_east = (lon_east - grid_lon_min) % 360 + grid_lon_min

        if lon_west <= lon_east:
            in_lon = (lon_coord >= lon_west) & (lon_coord <= lon_east)
        else:
            in_lon = (lon_coord >= lon_west) | (lon_coord <= lon_east)

    in_lat = (lat_coord >= lat_lo) & (lat_coord <= lat_hi)

    if lon_coord.ndim > 1 or lat_coord.ndim > 1:
        return dataset.where((in_lon & in_lat).compute(), drop=True)

    return dataset.isel(
        {lat_coord.dims[0]: in_lat.values, lon_coord.dims[0]: in_lon.values}
    )


def median_timestep_days(time_da):
    """
    Helper to return the median spacing between consecutive time steps, in days.

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
    # cftime axes diff to datetime.timedelta, not numpy.timedelta64
    if diffs.dtype == object:
        return np.median([d.days + d.seconds / 86400 for d in diffs])
    return np.median(diffs / np.timedelta64(1, "D"))


def _rolling_window_size(time_da, target_days=150):
    """
    Helper to convert a target rolling window length in days to native timesteps.

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
    # Size the window from the timestep, as a fixed window breaks on daily or short yearly data
    n = time_da.size
    if n <= 1:
        return 1
    step_days = median_timestep_days(time_da)
    window = max(1, round(target_days / step_days)) if step_days > 0 else 5
    return min(window, n)


def calc_anomalies(dataset, lon_dim, lat_dim, var):
    """
    Helper to compute the area-weighted mean monthly anomaly of ``var``.

    Parameters
    ----------
    dataset : xarray.Dataset
        Data already subset to the region of interest.
    lon_dim, lat_dim : str
        Longitude/latitude coordinate names.
    var : str
        Variable to compute anomalies for.
    Returns
    -------
    xarray.DataArray
        Time series of anomalies from the monthly climatology.
    """
    data = dataset[var]
    # Anomalies from the monthly climatology
    gb = data.groupby("time.month")
    anomalies = gb - gb.mean(dim="time")

    # Weight by cos(latitude) to account for grid cell area
    weights = np.cos(np.deg2rad(dataset[lat_dim]))
    weights.name = "weights"

    return anomalies.weighted(weights).mean(dim=[lat_dim, lon_dim])


def require_coords(ds, variable, coords, grid):
    """
    Raise a readable error if ``ds`` isn't the grid a recipe targets.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset passed to the recipe.
    variable : str
        Variable the recipe will use.
    coords : list of str
        Coordinates the recipe needs on ``variable``, e.g. ["yt_ocean", "xt_ocean"].
    grid : str
        Grid name for the error message, e.g. "MOM5".

    Raises
    ------
    KeyError
        If ``variable`` isn't in ``ds``.
    ValueError
        If ``variable`` is missing any of ``coords``.
    """
    if variable not in ds:
        raise KeyError(f"Variable '{variable}' not found in the dataset.")
    missing = [c for c in coords if c not in ds[variable].coords]
    if missing:
        raise ValueError(
            f"This recipe expects {grid} output with coords {coords}, but "
            f"'{variable}' is missing {missing}. For other grids, write a custom "
            "recipe using the helpers in med_diagnostics.recipes."
        )


def _cell_area(ds, da):
    """
    Helper to return the cell area of ``da``, from its ``cell_measures`` or ``areacello``.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset that should hold the cell area variable.
    da : xarray.DataArray
        Variable whose ``cell_measures`` attribute is read.

    Returns
    -------
    xarray.DataArray or None
        The cell area, or None if the dataset has none.
    """
    # e.g. cell_measures = "area: area_t volume: volcello"
    parts = da.attrs.get("cell_measures", "").replace(":", " ").split()
    for key, name in zip(parts[::2], parts[1::2], strict=False):
        if key == "area" and name in ds:
            return ds[name]
    return ds.get("areacello")


def global_mean(ds, variable, dim, how="mean"):
    """
    Helper to reduce a scalar or 2D ``ds[variable]`` to a timeseries over ``dim``, in its own units.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing ``variable``.
    variable : str
        Variable to reduce.
    dim : str
        Dimension to keep, usually time.
    how : {"mean", "max", "min"}, default "mean"
        Mean weighted by cell area, or the global maximum/minimum.

    Returns
    -------
    xarray.DataArray
        The computed timeseries. Already-scalar data is returned as is.

    Raises
    ------
    ValueError
        If ``ds[variable]`` is gridded in more than two dimensions besides ``dim``.
    """
    da = ds[variable]

    other_dims = [d for d in da.dims if d != dim]
    # Size-1 dims, like MOM's scalar_axis, aren't a grid
    gridded = [d for d in other_dims if da.sizes[d] > 1]
    if not gridded:
        return da.squeeze(other_dims, drop=True).compute()
    # Area weights only suit 2D fields, as in the OM3 paper notebook
    if len(gridded) > 2:
        raise ValueError(
            f"'{variable}' is gridded in {len(gridded)} dimensions {tuple(gridded)}, "
            "but global means only support scalar or 2D fields"
        )
    if how in ("max", "min"):
        return getattr(da, how)(other_dims).compute()

    # Area weights only, matching xgcm's grid.average in the OM3 paper notebook
    weights = _cell_area(ds, da)
    if weights is None:
        warnings.warn(
            f"No cell area found for '{variable}', so its mean is unweighted",
            stacklevel=2,
        )
        return da.mean(other_dims).compute()
    return da.weighted(weights.fillna(0)).mean(other_dims).compute()


# --------------------------------------------------------------------------
# OM3 timeseries helpers - used by the recipe_om3_timeseries* recipes
# --------------------------------------------------------------------------


def _om3_timeseries_reduction(da, name, dim, strict=False):
    """
    Helper to choose how to reduce an OM3 timeseries field, from its ``cell_methods``.

    Parameters
    ----------
    da : xarray.DataArray
        Data to be reduced.
    name : str
        ``OM3_TIMESERIES_FIELDS`` name it stands in for, e.g. "soga" or "tos_max".
    dim : str
        Time dimension of ``da``.
    strict : bool, default False
        Raise, rather than warn and use the mean, when gridded data has no time
        mean, max or min.

    Returns
    -------
    {"mean", "max", "min"}
        The time method in ``cell_methods``, as the paper uses. Without
        ``cell_methods``, "max"/"min" for ``*_max``/``*_min`` fields, otherwise "mean".

    Raises
    ------
    ValueError
        If ``strict`` and gridded data has no time mean, max or min.
    """
    expected = name.rsplit("_", 1)[-1] if name.endswith(("_max", "_min")) else "mean"
    cell_methods = da.attrs.get("cell_methods")
    # Scalars aren't reduced, so there is nothing to choose or warn about
    if cell_methods is None or all(da.sizes[d] == 1 for d in da.dims if d != dim):
        return expected
    # Same order as the paper notebook
    how = next(
        (h for h in ("mean", "max", "min") if f"time: {h}" in cell_methods), None
    )
    if how is None and strict:
        raise ValueError(
            f"'{da.name}' is gridded but has cell_methods '{cell_methods}', with no "
            "time mean, max or min, so it can't be reduced to a timeseries. Use "
            "'OM3 timeseries suite (custom variable mapping)' to plot its spatial mean"
        )
    if how is None:
        warnings.warn(
            f"'{da.name}' has cell_methods '{cell_methods}', with no time mean, max "
            "or min, so its spatial mean is plotted",
            stacklevel=2,
        )
        return "mean"
    if how != expected:
        warnings.warn(
            f"{name} is a spatial {expected}, but '{da.name}' has cell_methods "
            f"'{cell_methods}', so its spatial {how} is plotted",
            stacklevel=2,
        )
    return how


def _require_om3_totals_are_timeseries(ds, chosen, dim):
    """
    Helper to reject gridded variables chosen for the OM3 global-total fields.

    ``masso`` and ``total_*`` are already global totals in OM3 output. Averaging a
    gridded field instead would be off by roughly the ocean area.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing the chosen variables.
    chosen : dict
        ``OM3_TIMESERIES_FIELDS`` name -> dataset variable.
    dim : str
        Time dimension of ``ds``.

    Raises
    ------
    ValueError
        If a total field's variable has a dimension longer than 1 other than ``dim``.
    """
    for name, variable in chosen.items():
        if name != "masso" and not name.startswith("total_"):
            continue
        # Model scalars often keep a size-1 dim (MOM's scalar_axis), which is fine
        da = ds[variable]
        other_dims = [d for d in da.dims if d != dim and da.sizes[d] > 1]
        if other_dims:
            raise ValueError(
                f"{name} is a global total, so it needs a timeseries that is already "
                f"totalled; '{variable}' also has dimensions {tuple(other_dims)}"
            )


# Cached so a suite run opens the catalogs once, not once per variable
@cache
def _om3_timeseries_datastores():
    """
    Helper to open the OM3 timeseries reference catalogs.

    Returns
    -------
    tuple of (dict, intake_esm.esm_datastore or None)
        The OM3 reference datastores as {experiment: datastore}, and the OM2
        comparison experiment from the ACCESS-NRI catalogue. Any that can't be
        opened are reported and left out, so the rest are still plotted.
    """
    datastores = {}
    for c in OM3_TIMESERIES_REF_CATALOGS:
        name = Path(c).parent.name
        try:
            datastores[name] = intake.open_esm_datastore(
                c, columns_with_iterables=["variable"]
            )
        # Missing or unreadable file (OSError), or a malformed catalog (ValueError)
        except (OSError, ValueError) as err:
            warnings.warn(f"{name} failed: {err}", stacklevel=2)
    try:
        om2cat = intake.cat.access_nri[OM3_TIMESERIES_OM2_EXPT]
    # Left broad: how the catalogue fails off Gadi depends on the access-nri-intake version
    except Exception as err:  # noqa: BLE001
        warnings.warn(f"{OM3_TIMESERIES_OM2_EXPT} failed: {err}", stacklevel=2)
        om2cat = None
    return datastores, om2cat


def _catalog_years(dates):
    """
    Helper to read the years from a catalog date column.

    Parameters
    ----------
    dates : pandas.Series
        Catalog ``start_date`` or ``end_date`` values, e.g. "1958-01-01, 00:00:00".

    Returns
    -------
    pandas.Series
        The years, NaN where a file has no date.
    """
    return pd.to_numeric(dates.astype(str).str[:4], errors="coerce")


def _search_in_years(search, first, last):
    """
    Helper to keep only the files of an intake-esm search that overlap the years ``first`` to ``last``.

    Parameters
    ----------
    search : intake_esm.esm_datastore
        Search result to narrow.
    first, last : int
        First and last years to keep.

    Returns
    -------
    intake_esm.esm_datastore
        The narrowed search, or ``search`` as is if its catalog has no dates.
    """
    df = search.df
    if "start_date" not in df:
        return search
    start = _catalog_years(df["start_date"])
    end = _catalog_years(df["end_date"]).fillna(start) if "end_date" in df else start
    # Undated files (e.g. static grid data) are kept, as in data._select_year_files
    keep = ((start <= last) & (end >= first)) | start.isna()
    # Same subset construction as intake-esm's search, so the dataset key still matches
    return search.__class__({"esmcat": search.esmcat.model_dump(), "df": df[keep]})


def _load_om3_timeseries_var(datastores, var, first, last):
    """
    Helper to open one variable from each OM3 reference datastore, over the user data's years.

    Parameters
    ----------
    datastores : dict
        OM3 reference datastores, as {experiment: datastore}.
    var : str
        Variable to open.
    first, last : int
        First and last years of the user data. RYF runs open the same number of
        years from their own start.

    Returns
    -------
    dict
        {experiment: xarray.Dataset} for the datastores that have ``var`` in those
        years. Datastores that fail to open are reported and left out.
    """
    datastores = dict(datastores)
    for extra in OM3_TIMESERIES_REF_SEARCHES:
        try:
            searches = {
                n: cat.search(variable=var, **extra) for n, cat in datastores.items()
            }
            # As in the paper notebook, one ambiguous datastore moves all to the next search
            if any(len(s) > 1 for s in searches.values()):
                continue
            found = {}
            for n, s in searches.items():
                if not len(s):
                    continue
                years = (first, last)
                if n in OM3_TIMESERIES_RYF_EXPTS and "start_date" in s.df:
                    ryf_first = int(_catalog_years(s.df["start_date"]).min())
                    years = (ryf_first, ryf_first + last - first)
                # Only the user data's years are opened, as whole runs are slow to open
                s = _search_in_years(s, *years)
                if not len(s):
                    warnings.warn(
                        f"{var} reference {n} has no data in the user data's time range",
                        stacklevel=2,
                    )
                    continue
                try:
                    found[n] = s.to_dask(
                        xarray_combine_by_coords_kwargs=OM3_TIMESERIES_COMBINE_KWARGS
                    )
                # intake-esm re-raises any failure to open the files as this
                except ESMDataSourceError as err:
                    warnings.warn(f"{var} failed for {n}: {err}", stacklevel=2)
                    del datastores[n]
        # Searches that still match several datasets when opened also move on
        except ValueError:
            continue
        return found
    warnings.warn(f"{var} failed", stacklevel=2)
    return {}


def _load_om3_timeseries_reference(var, start, end):
    """
    Helper to load the reference timeseries for one OM3 variable, over the user data's time range.

    Parameters
    ----------
    var : str
        ``OM3_TIMESERIES_FIELDS`` name to load.
    start, end : tuple of (int, int)
        (year, month) of the user data's first and last timesteps.

    Returns
    -------
    dict
        {experiment: xarray.DataArray} of global timeseries, including OM2 where
        it has a matching variable. References with no data in the range are left out.
    """
    datastores, om2cat = _om3_timeseries_datastores()
    d = _load_om3_timeseries_var(datastores, var, start[0], end[0])
    if not d:
        return {}
    om2_var = OM3_TIMESERIES_FIELDS[var][0]
    if om2_var and om2cat is not None:
        # Match OM2's frequency to OM3's, otherwise the search finds two datasets
        freq = next(iter(d.values())).attrs["intake_esm_attrs:frequency"]
        try:
            om2 = _search_in_years(
                om2cat.search(variable=om2_var, frequency=freq), start[0], end[0]
            )
            if len(om2):
                om2 = om2.to_dask().rename({om2_var: var})
                d = {OM3_TIMESERIES_OM2_EXPT: om2} | d
            else:
                warnings.warn(
                    f"{var} reference {OM3_TIMESERIES_OM2_EXPT} has no data in the "
                    "user data's time range",
                    stacklevel=2,
                )
        # Ambiguous search or variable missing (ValueError), or files failed to open
        except (ValueError, ESMDataSourceError) as err:
            warnings.warn(
                f"{var} failed for {OM3_TIMESERIES_OM2_EXPT}: {err}", stacklevel=2
            )
    if OM3_TIMESERIES_IAF:
        d = {
            n: ds.convert_calendar("proleptic_gregorian", use_cftime=True)
            for n, ds in d.items()
        }
    window = slice(f"{start[0]:04d}-{start[1]:02d}", f"{end[0]:04d}-{end[1]:02d}")
    references = {}
    for n, ds in d.items():
        if n in OM3_TIMESERIES_RYF_EXPTS:
            years = start[0] - int(ds["time"].dt.year[0])
            ds = ds.assign_coords(
                time=[t.replace(year=t.year + years) for t in ds.indexes["time"]]
            )
        # Cut before reducing, so only the user data's years are read
        ds = ds.sel(time=window)
        if not ds.sizes["time"]:
            warnings.warn(
                f"{var} reference {n} has no data in the user data's time range",
                stacklevel=2,
            )
            continue
        how = _om3_timeseries_reduction(ds[var], var, "time")
        references[n] = global_mean(ds, var, "time", how)
    return references


def _om3_timeseries(ds, variable, name, dim, strict=False):
    """
    Helper to build one OM3 timeseries plot, overlaid on the reference runs.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing ``variable``.
    variable : str
        Dataset variable to plot.
    name : str
        The ``OM3_TIMESERIES_FIELDS`` name it stands in for.
    dim : str
        Time dimension of ``ds``.
    strict : bool, default False
        Passed to ``_om3_timeseries_reduction``.

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The timeseries and its plot kwargs.
    """
    require_coords(ds, variable, [dim], "time-varying")
    label = OM3_TIMESERIES_FIELDS[name][1]
    how = _om3_timeseries_reduction(ds[variable], name, dim, strict)
    data = global_mean(ds, variable, dim, how)
    try:
        years, months = data[dim].dt.year.values, data[dim].dt.month.values
    except AttributeError as err:
        raise ValueError(
            f"'{dim}' must hold dates to compare with the reference runs"
        ) from err
    references = _load_om3_timeseries_reference(
        name, (years[0], months[0]), (years[-1], months[-1])
    )

    # Styled as in the OM3 paper notebook: thin raw lines, labelled yearly means
    plot_kwargs = {
        "figsize": (10, 5),
        "title": f"{name}: {label}",
        "linewidth": 0.7,
        "ax_kwargs": {"xlabel": ""},
        "customise": [
            lambda ax, data: plot_customisations.add_yearly_mean(
                ax, data, dim, label="User data"
            ),
            lambda ax, data: plot_customisations.add_reference_timeseries(
                ax, references
            ),
        ],
    }
    return data, plot_kwargs


# --------------------------------------------------------------------------
# Recipes
# --------------------------------------------------------------------------


def recipe_sst_anomaly_nino34(
    dataset: xr.Dataset,
    var: Annotated[
        str,
        {
            "name": "Select Variable",
            "kind": "data variable",
            "description": "Sea surface temperature variable in this dataset (default tos)",
        },
    ] = "tos",
    x_dim: Annotated[
        str,
        {
            "name": "Select Longitude Dim",
            "kind": "dimension",
            "description": "Longitude dimension",
        },
    ] = "xt_ocean",
    y_dim: Annotated[
        str,
        {
            "name": "Select Latitude Dim",
            "kind": "dimension",
            "description": "Latitude dimension",
        },
    ] = "yt_ocean",
):
    """
    Niño 3.4 index for sea surface temperature

    For analysis of sea surface temperature anomaly in the Niño 3.4 region.

    Parameters
    ----------
    dataset : xarray.Dataset
        Model output containing ``var``.
    var : str, default "tos"
        Sea surface temperature variable.
    x_dim : str, default "xt_ocean"
        Longitude dimension, e.g. "lon" or "xt_ocean".
    y_dim : str, default "yt_ocean"
        Latitude dimension, e.g. "lat" or "yt_ocean".

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The Niño 3.4 index and its plot kwargs.
    """
    require_coords(dataset, var, [y_dim, x_dim, "time"], "lat/lon gridded")
    # With one year each month is its own climatology, so every anomaly is zero
    if np.unique(dataset["time"].dt.year).size < 2:
        raise ValueError(
            "The Niño 3.4 index needs at least 2 years of data to compare each "
            "month against its average. Load more years."
        )

    nino34_ds = extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = calc_anomalies(nino34_ds, x_dim, y_dim, var)

    # Rolling needs the whole time axis in one chunk
    anomalies = anomalies.chunk({"time": -1})
    window = _rolling_window_size(anomalies["time"])
    rolling_mean = anomalies.rolling(time=window, center=True).mean()
    index_plot = rolling_mean.compute()

    plot_kwargs = {
        "title": "Niño 3.4 Index",
        "color": "black",
        "linewidth": 1.5,  # overrides the 1D default of 2 to match plain ax.plot
        "ax_kwargs": {"xlabel": "Year", "ylabel": "Niño 3.4 SST Anomaly (°C)"},
        "customise": [
            plot_customisations.nino_fills,
            plot_customisations.nino_reference_lines,
        ],
    }

    return index_plot, plot_kwargs


def recipe_regional_mean_mom5(
    ds: xr.Dataset,
    variable: Annotated[
        str, {"kind": "data variable", "description": "Variable to average"}
    ] = "temp",
    region: Annotated[
        str,
        {
            "kind": "choice",
            "choices": list(PREDEFINED_REGIONS),
            "description": "Region to average over",
        },
    ] = "tasmania",
    lon_dim: Annotated[
        str, {"kind": "dimension", "description": "Longitude coordinate"}
    ] = "xt_ocean",
    lat_dim: Annotated[
        str, {"kind": "dimension", "description": "Latitude coordinate"}
    ] = "yt_ocean",
    lvl_dim: Annotated[
        str | None, {"kind": "dimension", "description": "Depth coordinate, if any"}
    ] = "st_ocean",
    depth: Annotated[
        float, {"kind": "float", "units": "m", "description": "Nearest level is used"}
    ] = 0.0,
    smooth_steps: Annotated[
        int,
        {"kind": "int", "description": "Rolling-mean window in timesteps (1 = off)"},
    ] = 1,
    show_trend: Annotated[
        bool, {"kind": "bool", "description": "Overlay a linear trend"}
    ] = True,
    show_percentiles: Annotated[
        bool,
        {
            "name": "",
            "kind": "bool",
            "description": "Overlay top and bottom 10 percentiles",
        },
    ] = True,
    threshold: Annotated[
        str, {"kind": "str", "description": "Optional reference value, blank for none"}
    ] = "",
):
    """
    Timeseries of a variable over a chosen region (Area-weighted mean).

    For MOM5 output (ACCESS-OM2, ACCESS-ESM1.6).

    Parameters
    ----------
    ds : xarray.Dataset
        Model output containing ``variable``.
    variable : str, default "temp"
        Variable to average.
    region : str, default "tasmania"
        Key of ``PREDEFINED_REGIONS`` to average over.
    lon_dim, lat_dim : str, default "xt_ocean", "yt_ocean"
        Longitude and latitude dimensions.
    lvl_dim : str or None, default "st_ocean"
        Depth dimension, or None for surface fields.
    depth : float, default 0.0
        Depth in metres; the nearest level is used.
    smooth_steps : int, default 1
        Rolling-mean window in timesteps (1 = no smoothing).
    show_trend : bool, default True
        Overlay a linear trend.
    show_percentiles : bool, default True
        Shade the top and bottom 10 percentiles.
    threshold : str, default ""
        Reference value to draw as a line, blank for none.

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The regional mean timeseries and its plot kwargs.
    """
    # Fail with a readable message if this isn't the grid we expect
    require_coords(ds, variable, [lat_dim, lon_dim], "MOM5")
    used_depth = None
    data = ds[variable]
    # Surface fields have no depth to select
    if lvl_dim is not None and lvl_dim in data.dims:
        data = data.sel({lvl_dim: depth}, method="nearest")
        used_depth = float(data[lvl_dim])

    data = extract_region(data, region, lon_dim=lon_dim, lat_dim=lat_dim)
    area = _cell_area(ds, ds[variable])
    if area is not None:
        weights = extract_region(area, region, lon_dim=lon_dim, lat_dim=lat_dim)
        weights = weights.fillna(0)
    else:
        warnings.warn(
            f"No cell area found for '{variable}', so it is weighted by cos(latitude)",
            stacklevel=2,
        )
        weights = np.cos(np.deg2rad(data[lat_dim]))
    timeseries = data.weighted(weights).mean(dim=[lat_dim, lon_dim])

    if smooth_steps > 1:
        timeseries = timeseries.rolling(time=smooth_steps, center=True).mean()

    # Compute once here, so the plot and every customise function reuse it
    timeseries = timeseries.compute()
    timeseries.name = f"{region.title()} mean {variable}"

    # Build the list of extra plot steps from the user's choices
    customise = []
    if show_percentiles:
        customise.append(plot_customisations.shade_top_10pct)
        customise.append(plot_customisations.shade_bottom_10pct)
    if show_trend:
        customise.append(plot_customisations.add_trend)
    if threshold.strip():

        def threshold_wrapper(ax, *args, **kwargs):
            return plot_customisations.add_threshold(ax, value=float(threshold))

        customise.append(threshold_wrapper)
    title = timeseries.name
    if used_depth is not None:
        title += f" ({used_depth:g} m)"
    plot_kwargs = {
        "title": title,
        "color": "black",
        "linewidth": 1,
        "ax_kwargs": {
            "xlabel": "Year",
            "ylabel": f"{variable} ({data.attrs.get('units', '')})",
        },
        "customise": customise,
    }
    return timeseries, plot_kwargs


def recipe_om3_timeseries(
    ds: xr.Dataset,
    dim: Annotated[
        str,
        {
            "kind": "dimension",
            "name": "Select Time Dimension",
            "description": "Dimension to display on the x-axis, associated with time, taking the mean over all remaining dimensions",
        },
    ] = "time",
):
    """
    OM3 timeseries suite (OM3 variable names)

    For ACCESS-OM3 output that uses OM3 variable names (e.g. soga, thetaoga). Automatically plots every variable in ``OM3_TIMESERIES_FIELDS`` found in the dataset, overlaid with select reference runs not currently available in the intake catalogue. Gridded datasets can also be plotted but takes significantly longer as global mean must be calculated. Part of the suite of analysis based on the timeseries plots generated for access-om3-paper-1-figures (https://access-om3-paper-1.readthedocs.io/). Analysis adapted from analysis created by Andrew Kiss, Christopher Bull.

    Parameters
    ----------
    ds : xarray.Dataset
        Model output with OM3 variable names.
    dim : str, default "time"
        Time dimension; every other dimension is averaged over.

    Returns
    -------
    list of tuple of (xarray.DataArray, dict)
        One timeseries and its plot kwargs per OM3 variable found.

    Raises
    ------
    ValueError
        If the dataset has none of the OM3 variable names, or every variable is skipped.

    Warns
    -----
    UserWarning
        For each variable skipped, e.g. a gridded ``masso`` or ``total_*`` variable,
        or a grid with no time mean, max or min.
    """
    names = [name for name in OM3_TIMESERIES_FIELDS if name in ds]
    if not names:
        raise ValueError(
            "No OM3 variable names (e.g. soga, thetaoga) found in this dataset; "
            "use 'OM3 timeseries suite (custom variable mapping)' to choose them"
        )
    results = []
    for name in names:
        try:
            _require_om3_totals_are_timeseries(ds, {name: name}, dim)
            results.append(_om3_timeseries(ds, name, name, dim, strict=True))
        # Skip just this plot, so the rest of the suite still draws
        except ValueError as err:
            warnings.warn(f"{name} skipped: {err}", stacklevel=2)
    if not results:
        raise ValueError("None of the OM3 variables in this dataset could be plotted")
    return results


def recipe_om3_timeseries_mapped(
    ds: xr.Dataset,
    masso_var: Annotated[
        str | None,
        {
            "name": "'masso' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Mass of liquid ocean' in this dataset",
        },
    ] = None,
    soga_var: Annotated[
        str | None,
        {
            "name": "'soga' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Global Mean Ocean Salinity' in this dataset",
        },
    ] = None,
    thetaoga_var: Annotated[
        str | None,
        {
            "name": "'thetaoga' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Global Mean Ocean Potential Temperature' in this dataset",
        },
    ] = None,
    tosga_var: Annotated[
        str | None,
        {
            "name": "'tosga' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Sea Surface Temperature' in this dataset",
        },
    ] = None,
    sosga_var: Annotated[
        str | None,
        {
            "name": "'sosga' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Global Mean Sea Surface Salinity' in this dataset",
        },
    ] = None,
    speed_max_var: Annotated[
        str | None,
        {
            "name": "'speed_max' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Maximum Ocean Current Speed' in this dataset",
        },
    ] = None,
    mlotst_max_var: Annotated[
        str | None,
        {
            "name": "'mlotst_max' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Maximum Ocean Mixed Layer Thickness' in this dataset",
        },
    ] = None,
    tos_max_var: Annotated[
        str | None,
        {
            "name": "'tos_max' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Maximum Sea Surface Temperature' in this dataset",
        },
    ] = None,
    tos_min_var: Annotated[
        str | None,
        {
            "name": "'tos_min' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Minimum Sea Surface Temperature' in this dataset",
        },
    ] = None,
    sos_max_var: Annotated[
        str | None,
        {
            "name": "'sos_max' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Maximum Sea Surface Salinity' in this dataset",
        },
    ] = None,
    sos_min_var: Annotated[
        str | None,
        {
            "name": "'sos_min' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Minimum Sea Surface Salinity' in this dataset",
        },
    ] = None,
    zos_max_var: Annotated[
        str | None,
        {
            "name": "'zos_max' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Maximum Sea Surface Height' in this dataset",
        },
    ] = None,
    zos_min_var: Annotated[
        str | None,
        {
            "name": "'zos_min' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Minimum Sea Surface Height' in this dataset",
        },
    ] = None,
    total_salt_Flux_Added_var: Annotated[
        str | None,
        {
            "name": "'total_salt_Flux_Added' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Salt Flux Added' in this dataset",
        },
    ] = None,
    total_salt_Flux_In_var: Annotated[
        str | None,
        {
            "name": "'total_salt_Flux_In' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Salt Flux In' in this dataset",
        },
    ] = None,
    total_salt_flux_var: Annotated[
        str | None,
        {
            "name": "'total_salt_flux' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Salt Flux' in this dataset",
        },
    ] = None,
    net_fresh_water_global_adjustment_var: Annotated[
        str | None,
        {
            "name": "'net_fresh_water_global_adjustment' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Net Fresh Water Global Adjustment' in this dataset",
        },
    ] = None,
    salt_flux_global_restoring_adjustment_var: Annotated[
        str | None,
        {
            "name": "'salt_flux_global_restoring_adjustment' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Salt Flux Global Restoring Adjustment' in this dataset",
        },
    ] = None,
    total_wfo_var: Annotated[
        str | None,
        {
            "name": "'total_wfo' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Water Flux Into Ocean' in this dataset",
        },
    ] = None,
    total_evs_var: Annotated[
        str | None,
        {
            "name": "'total_evs' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Evaporation' in this dataset",
        },
    ] = None,
    total_fsitherm_var: Annotated[
        str | None,
        {
            "name": "'total_fsitherm' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Thermodynamic Sea Ice Flux' in this dataset",
        },
    ] = None,
    total_precip_var: Annotated[
        str | None,
        {
            "name": "'total_precip' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Precipitation' in this dataset",
        },
    ] = None,
    total_prsn_var: Annotated[
        str | None,
        {
            "name": "'total_prsn' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Snowfall' in this dataset",
        },
    ] = None,
    total_lprec_var: Annotated[
        str | None,
        {
            "name": "'total_lprec' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Liquid Precipitation' in this dataset",
        },
    ] = None,
    total_ficeberg_var: Annotated[
        str | None,
        {
            "name": "'total_ficeberg' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Iceberg Melt' in this dataset",
        },
    ] = None,
    total_friver_var: Annotated[
        str | None,
        {
            "name": "'total_friver' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total River Runoff' in this dataset",
        },
    ] = None,
    total_net_massout_var: Annotated[
        str | None,
        {
            "name": "'total_net_massout' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Net Mass Out' in this dataset",
        },
    ] = None,
    total_net_massin_var: Annotated[
        str | None,
        {
            "name": "'total_net_massin' Variable",
            "kind": "data variable",
            "description": "the variable associated with 'Total Net Mass In' in this dataset",
        },
    ] = None,
    dim: Annotated[
        str,
        {
            "kind": "dimension",
            "name": "Select Time Dimension",
            "description": "Dimension to display on the x-axis, associated with time, taking the mean over all remaining dimensions",
        },
    ] = "time",
):
    """
    OM3 timeseries suite (custom variable mapping)

    For ACCESS ocean output of any grid, choosing which variable stands in for each OM3 name. Empty variable dropdowns will not be plotted. Mass and total_* fields need a variable that is already a global total over time, not a gridded field. OM3 timeseries suite overlaid with select reference runs not currently available in the intake catalogue. Gridded datasets can also be plotted but takes significantly longer as global mean must be calculated. Part of the suite of analysis based on the timeseries plots generated for access-om3-paper-1-figures (https://access-om3-paper-1.readthedocs.io/).

    Parameters
    ----------
    ds : xarray.Dataset
        Model output to plot.
    masso_var, soga_var, ..., total_net_massin_var : str or None, default None
        Variable in ``ds`` standing in for each ``OM3_TIMESERIES_FIELDS`` name
        (the parameter name minus ``_var``). None skips that plot.
    dim : str, default "time"
        Time dimension; every other dimension is averaged over.

    Returns
    -------
    list of tuple of (xarray.DataArray, dict)
        One timeseries and its plot kwargs per chosen variable.

    Raises
    ------
    ValueError
        If the variable chosen for ``masso`` or a ``total_*`` field is
        gridded (a dimension longer than 1 besides ``dim``).
    """
    chosen = {
        "masso": masso_var,
        "soga": soga_var,
        "thetaoga": thetaoga_var,
        "tosga": tosga_var,
        "sosga": sosga_var,
        "speed_max": speed_max_var,
        "mlotst_max": mlotst_max_var,
        "tos_max": tos_max_var,
        "tos_min": tos_min_var,
        "sos_max": sos_max_var,
        "sos_min": sos_min_var,
        "zos_max": zos_max_var,
        "zos_min": zos_min_var,
        "total_salt_Flux_Added": total_salt_Flux_Added_var,
        "total_salt_Flux_In": total_salt_Flux_In_var,
        "total_salt_flux": total_salt_flux_var,
        "net_fresh_water_global_adjustment": net_fresh_water_global_adjustment_var,
        "salt_flux_global_restoring_adjustment": salt_flux_global_restoring_adjustment_var,
        "total_wfo": total_wfo_var,
        "total_evs": total_evs_var,
        "total_fsitherm": total_fsitherm_var,
        "total_precip": total_precip_var,
        "total_prsn": total_prsn_var,
        "total_lprec": total_lprec_var,
        "total_ficeberg": total_ficeberg_var,
        "total_friver": total_friver_var,
        "total_net_massout": total_net_massout_var,
        "total_net_massin": total_net_massin_var,
    }
    chosen = {name: variable for name, variable in chosen.items() if variable}
    # Checked up front so a bad choice fails before any slow global means
    _require_om3_totals_are_timeseries(ds, chosen, dim)
    return [
        _om3_timeseries(ds, variable, name, dim) for name, variable in chosen.items()
    ]
