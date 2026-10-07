from functools import cache
from pathlib import Path
from typing import Annotated

import intake
import numpy as np
import xarray as xr

from med_diagnostics import plot_customisations

PREDEFINED_REGIONS = {
    # ENSO Regions
    "nino12": {"lat": (-10, 0), "lon": (-90, -80)},
    "nino3": {"lat": (-5, 5), "lon": (-150, -90)},
    "nino34": {"lat": (-5, 5), "lon": (-170, -120)},
    "nino4": {"lat": (-5, 5), "lon": (160, -150)},  # Note: crosses the 180 dateline
    # Indian Ocean Dipole (IOD)
    "iod_west": {"lat": (-10, 10), "lon": (50, 70)},
    "iod_east": {"lat": (-10, 0), "lon": (90, 110)},
    # Atlantic Indices
    "tna": {"lat": (5, 25), "lon": (-55, -15)},  # Tropical North Atlantic
    "tsa": {"lat": (-20, 0), "lon": (-30, 10)},  # Tropical South Atlantic
    # Hemispheres & Global Bounds
    "global": {"lat": (-90, 90), "lon": (-180, 180)},
    "nh": {"lat": (0, 90), "lon": (-180, 180)},  # Northern Hemisphere
    "sh": {"lat": (-90, 0), "lon": (-180, 180)},  # Southern Hemisphere
    "tropics": {"lat": (-20, 20), "lon": (-180, 180)},
    # Continents & Specific Geographic Regions
    "tasmania": {"lat": (-44, -39), "lon": (143, 149)},
    "australia": {"lat": (-44, -10), "lon": (112, 154)},
    "maritime_continent": {"lat": (-10, 10), "lon": (90, 150)},
    "southern_ocean": {"lat": (-90, -50), "lon": (-180, 180)},
    "arctic": {"lat": (66.5, 90), "lon": (-180, 180)},
    "antarctic": {"lat": (-90, -66.5), "lon": (-180, 180)},
}

# Unit strings `global_mean` converts from Kelvin to degC
KELVIN_UNITS = {"k", "kelvin", "degk", "deg_k", "degrees_k", "degrees k"}

# Reference runs for the OM3 timeseries recipes, from the access-om3-paper-1
# timeseries notebook (https://github.com/ACCESS-Community-Hub/access-om3-paper-1/blob/main/notebooks/timeseries.ipynb)
OM3_TIMESERIES_REF_CATALOGS = [
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf-1.0-beta-5165c0f8/datastore.json",
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test3v2-00532b88/datastore.json",
    "/g/data/ol01/outputs/access-om3-25km/MC_25km_jra_iaf+wombatlite-test4-d28e0359/datastore.json",
]
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
    # cftime axes (e.g. 360_day/noleap) diff to datetime.timedelta objects
    # rather than numpy.timedelta64, so they need separate handling
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
    # A fixed window of 5 assumes monthly data: too short for daily data and
    # can exceed short yearly records, where bottleneck's rolling mean raises
    # ValueError. Sizing from the real timestep avoids both.
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


def _find_axis_dim(ds, da, axis, skip):
    """
    Helper to find which dimension of ``da`` is the X, Y or Z axis, from coordinate attributes.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset holding the coordinates of ``da``.
    da : xarray.DataArray
        Variable whose dimensions are searched.
    axis : {"X", "Y", "Z"}
        Axis to look for.
    skip : str
        Dimension to ignore, usually the time dimension being kept.

    Returns
    -------
    str or None
        Name of the matching dimension, or None if none match.
    """
    # Dim names differ between models (yt_ocean, yh, lat; st_ocean, z_l, lev),
    # so match on attributes rather than names
    for d in da.dims:
        if d == skip or d not in ds.coords:
            continue
        attrs = ds[d].attrs
        units = attrs.get("units", "").lower()
        # CF uses `axis`, MOM5 uses `cartesian_axis`
        if str(attrs.get("axis", attrs.get("cartesian_axis", ""))).upper() == axis:
            return d
        if axis == "Y" and (
            attrs.get("standard_name") == "latitude" or "north" in units
        ):
            return d
        if axis == "Z" and (
            attrs.get("positive") in ("up", "down")
            or attrs.get("standard_name") == "depth"
        ):
            return d
    return None


def _cell_measure(ds, da, measure):
    """
    Helper to return the cell area or volume variable named in ``da``'s ``cell_measures``.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset that should hold the cell measure variable.
    da : xarray.DataArray
        Variable whose ``cell_measures`` attribute is read.
    measure : {"area", "volume"}
        Cell measure to look for.

    Returns
    -------
    xarray.DataArray or None
        The cell measure, or None if it isn't named or isn't in ``ds``.
    """
    # e.g. cell_measures = "area: area_t volume: volcello"
    parts = da.attrs.get("cell_measures", "").replace(":", " ").split()
    for key, name in zip(parts[::2], parts[1::2], strict=False):
        if key == measure and name in ds:
            return ds[name]
    return None


def _layer_thickness(ds, z):
    """
    Helper to return the thickness of each depth layer along ``z``.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset holding the depth coordinate and any edges/bounds variable.
    z : str
        Depth dimension.

    Returns
    -------
    xarray.DataArray
        Layer thickness along ``z``, from the edges/bounds if present, otherwise
        from the midpoints between levels.
    """
    levels = ds[z]
    edges_name = levels.attrs.get("edges") or levels.attrs.get("bounds")  # MOM5 / CF
    if edges_name in ds:
        edges = ds[edges_name]
        if edges.ndim == 2:  # CF bounds, shape (z, 2)
            thickness = abs(
                edges.isel({edges.dims[1]: 1}) - edges.isel({edges.dims[1]: 0})
            )
        else:  # MOM5 edges, one longer than the levels
            thickness = np.abs(np.diff(edges.values))
            thickness = xr.DataArray(thickness, dims=[z], coords={z: levels})
        return thickness.drop_vars([c for c in thickness.coords if c != z])
    # No edges: place layer boundaries halfway between levels
    values = levels.values.astype(float)
    mids = (values[1:] + values[:-1]) / 2
    bounds = np.concatenate(
        [
            [values[0] - (mids[0] - values[0])],
            mids,
            [values[-1] + (values[-1] - mids[-1])],
        ]
    )
    bounds[0] = max(bounds[0], 0) if values[0] >= 0 else bounds[0]
    return xr.DataArray(np.abs(np.diff(bounds)), dims=[z], coords={z: levels})


def global_mean(ds, variable, dim, how="mean"):
    """
    Helper to reduce ``ds[variable]`` to a timeseries over ``dim``, in degC if it was in Kelvin.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing ``variable``.
    variable : str
        Variable to reduce.
    dim : str
        Dimension to keep, usually time.
    how : {"mean", "max", "min"}, default "mean"
        Volume-weighted mean, or the global maximum/minimum.

    Returns
    -------
    xarray.DataArray
        The computed timeseries. Already-scalar data is returned as is.
    """
    da = ds[variable]
    if da.attrs.get("units", "").strip().lower() in KELVIN_UNITS:
        da = (da - 273.15).assign_attrs(da.attrs, units="degC")

    other_dims = [d for d in da.dims if d != dim]
    if not other_dims:
        return da.compute()
    if how in ("max", "min"):
        return getattr(da, how)(other_dims).compute()

    # Prefer the dataset's own cell measures, otherwise weight by cos(latitude)
    # for area and by layer thickness for depth
    weights = _cell_measure(ds, da, "volume")
    if weights is None:
        weights = _cell_measure(ds, da, "area")
        if weights is None:
            y = _find_axis_dim(ds, da, "Y", dim)
            weights = (
                np.cos(np.deg2rad(ds[y]))
                if y
                else xr.ones_like(da.isel({dim: 0}, drop=True))
            )
        z = _find_axis_dim(ds, da, "Z", dim)
        if z:
            weights = weights * _layer_thickness(ds, z)

    return da.weighted(weights.fillna(0)).mean(other_dims).compute()


# --------------------------------------------------------------------------
# OM3 timeseries helpers - used by the recipe_om3_timeseries* recipes
# --------------------------------------------------------------------------


def _om3_timeseries_reduction(name):
    """
    Helper to choose how to reduce an OM3 timeseries field.

    Parameters
    ----------
    name : str
        ``OM3_TIMESERIES_FIELDS`` name, e.g. "soga" or "tos_max".

    Returns
    -------
    {"mean", "max", "min"}
        "max"/"min" for the paper's ``*_max``/``*_min`` fields, otherwise "mean".
    """
    return name.rsplit("_", 1)[-1] if name.endswith(("_max", "_min")) else "mean"


# Cached so a suite run opens the catalogs once, not once per variable
@cache
def _om3_timeseries_datastores():
    """
    Helper to open the OM3 timeseries reference catalogs.

    Returns
    -------
    tuple of (dict, intake_esm.esm_datastore)
        The OM3 reference datastores as {experiment: datastore}, and the OM2
        comparison experiment from the ACCESS-NRI catalogue.
    """
    datastores = {
        Path(c).parent.name: intake.open_esm_datastore(
            c, columns_with_iterables=["variable"]
        )
        for c in OM3_TIMESERIES_REF_CATALOGS
    }
    return datastores, intake.cat.access_nri[OM3_TIMESERIES_OM2_EXPT]


def _load_om3_timeseries_var(datastores, var):
    """
    Helper to open one variable from each OM3 reference datastore.

    Parameters
    ----------
    datastores : dict
        OM3 reference datastores, as {experiment: datastore}.
    var : str
        Variable to open.

    Returns
    -------
    dict
        {experiment: xarray.Dataset} for the datastores that have ``var``, or
        an empty dict if none could be opened.
    """
    for extra in OM3_TIMESERIES_REF_SEARCHES:
        try:
            found = {
                n: cat.search(variable=var, **extra) for n, cat in datastores.items()
            }
            return {
                n: s.to_dask(
                    xarray_combine_by_coords_kwargs=OM3_TIMESERIES_COMBINE_KWARGS
                )
                for n, s in found.items()
                if len(s)
            }
        except ValueError:
            continue
    print(f"{var} failed")
    return {}


def _load_om3_timeseries_reference(var):
    """
    Helper to load the reference timeseries for one OM3 variable.

    Parameters
    ----------
    var : str
        ``OM3_TIMESERIES_FIELDS`` name to load.

    Returns
    -------
    dict
        {experiment: xarray.DataArray} of global timeseries, including OM2 where
        it has a matching variable. Empty if no reference has ``var``.
    """
    datastores, om2cat = _om3_timeseries_datastores()
    d = _load_om3_timeseries_var(datastores, var)
    if not d:
        return {}
    om2_var = OM3_TIMESERIES_FIELDS[var][0]
    if om2_var:
        # Match OM2's frequency to OM3's, otherwise the search finds two datasets
        freq = next(iter(d.values())).attrs["intake_esm_attrs:frequency"]
        om2 = (
            om2cat.search(variable=om2_var, frequency=freq)
            .to_dask()
            .rename({om2_var: var})
        )
        d = {OM3_TIMESERIES_OM2_EXPT: om2} | d
    if OM3_TIMESERIES_IAF:
        d = {
            n: ds.convert_calendar("proleptic_gregorian", use_cftime=True)
            for n, ds in d.items()
        }
    return {
        n: global_mean(ds, var, "time", _om3_timeseries_reduction(var))
        for n, ds in d.items()
    }


def _om3_timeseries(ds, variable, name, dim, avg_window):
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
    avg_window : int
        Rolling-mean window in days.

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The timeseries and its plot kwargs.
    """
    require_coords(ds, variable, [dim], "time-varying")
    label = OM3_TIMESERIES_FIELDS[name][1]
    data = global_mean(ds, variable, dim, _om3_timeseries_reduction(name))
    window = _rolling_window_size(data[dim], avg_window)
    # Each reference is smoothed over the same number of days at its own timestep
    references = {
        expt: (ref, _rolling_window_size(ref["time"], avg_window))
        for expt, ref in _load_om3_timeseries_reference(name).items()
    }

    plot_kwargs = {
        "figsize": (11, 4),
        "title": f"{name}: {label}",
        "alpha": 0.6,
        "label": "User data",
        "customise": [
            lambda ax, data: plot_customisations.add_rolling_mean(
                ax, data, window, dim
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

    nino34_ds = extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = calc_anomalies(nino34_ds, x_dim, y_dim, var)

    # Rolling needs the whole time axis in one chunk
    anomalies = anomalies.chunk({"time": -1})
    window = _rolling_window_size(anomalies["time"])
    rolling_mean = anomalies.rolling(time=window, center=True).mean()
    index_plot = (rolling_mean / anomalies.std()).compute()

    plot_kwargs = {
        "title": "Niño 3.4 Index",
        "color": "black",
        "linewidth": 1.5,  # overrides the 1D default of 2 to match plain ax.plot
        "ax_kwargs": {"xlabel": "Year", "ylabel": "Niño 3.4 SST Anomaly"},
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

    data = ds[variable]
    # Surface fields have no depth to select
    if lvl_dim is not None and lvl_dim in data.dims:
        data = data.sel({lvl_dim: depth}, method="nearest")

    data = extract_region(data, region, lon_dim=lon_dim, lat_dim=lat_dim)
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

    plot_kwargs = {
        "title": f"{timeseries.name} (~{depth:g} m)",
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
    avg_window: Annotated[
        int,
        {
            "kind": "int",
            "name": "Select window for rolling average",
            "description": "Window for the rolling average to be taken over",
            "units": "Days",
        },
    ] = 365,
):
    """
    OM3 timeseries suite (OM3 variable names)

    For ACCESS-OM3 output that uses OM3 variable names (e.g. soga, thetaoga). Automatically plots every variable in ``OM3_TIMESERIES_FIELDS`` found in the dataset, overlaid with select reference runs not currently available in the intake catalogue. Gridded datasets can also be plotted but takes significantly longer as global mean must be calculated. Part of the suite of analysis based on the timeseries plots generated for access-om3-paper-1-figures (https://access-om3-paper-1.readthedocs.io/). Analysis adapted from analysis created by Andrew Kiss, Christopher Bull, ezhilsabareesh8.

    Parameters
    ----------
    ds : xarray.Dataset
        Model output with OM3 variable names.
    dim : str, default "time"
        Time dimension; every other dimension is averaged over.
    avg_window : int, default 365
        Rolling-mean window in days.

    Returns
    -------
    list of tuple of (xarray.DataArray, dict)
        One timeseries and its plot kwargs per OM3 variable found.

    Raises
    ------
    ValueError
        If the dataset has none of the OM3 variable names.
    """
    names = [name for name in OM3_TIMESERIES_FIELDS if name in ds]
    if not names:
        raise ValueError(
            "No OM3 variable names (e.g. soga, thetaoga) found in this dataset; "
            "use 'OM3 timeseries suite (custom variable mapping)' to choose them"
        )
    return [_om3_timeseries(ds, name, name, dim, avg_window) for name in names]


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
    avg_window: Annotated[
        int,
        {
            "kind": "int",
            "name": "Select window for rolling average",
            "description": "Window for the rolling average to be taken over",
            "units": "Days",
        },
    ] = 365,
):
    """
    OM3 timeseries suite (custom variable mapping)

    For ACCESS ocean output of any grid, choosing which variable stands in for each OM3 name. Empty variable dropdowns will not be plotted. OM3 timeseries suite overlaid with select reference runs not currently available in the intake catalogue. Gridded datasets can also be plotted but takes significantly longer as global mean must be calculated. Part of the suite of analysis based on the timeseries plots generated for access-om3-paper-1-figures (https://access-om3-paper-1.readthedocs.io/).

    Parameters
    ----------
    ds : xarray.Dataset
        Model output to plot.
    masso_var, soga_var, ..., total_net_massin_var : str or None, default None
        Variable in ``ds`` standing in for each ``OM3_TIMESERIES_FIELDS`` name
        (the parameter name minus ``_var``). None skips that plot.
    dim : str, default "time"
        Time dimension; every other dimension is averaged over.
    avg_window : int, default 365
        Rolling-mean window in days.

    Returns
    -------
    list of tuple of (xarray.DataArray, dict)
        One timeseries and its plot kwargs per chosen variable.
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
    return [
        _om3_timeseries(ds, variable, name, dim, avg_window)
        for name, variable in chosen.items()
        if variable
    ]
