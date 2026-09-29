from typing import Annotated

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


def calc_anomolies(dataset, lon_dim, lat_dim, var):
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


def _require_coords(ds, variable, coords, grid):
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

    For analysis of sea surface temperature anomoly in the Niño 3.4 region.

    Parameters
    ----------
    dataset : xarray.Dataset
        Model output containing ``var``.
    x_dim : str, dimension
        Native longitude name (e.g. "lon"/"lat" or "xt_ocean"/"yt_ocean"). Default "xt_ocean".
    y_dim : str, dimension
        Native latitude name (e.g. "lon"/"lat" or "xt_ocean"/"yt_ocean"). Default "yt_ocean".
    var : str, data variable
        Sea surface temperature variable to use, default "tos".

    Returns
    -------
    matplotlib.figure.Figure
        The Niño 3.4 index plot.
    """
    # Trim before any computation so spinup doesn't skew the climatology,
    # anomaly or normalisation - not just the plotted window

    nino34_ds = extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = calc_anomolies(nino34_ds, x_dim, y_dim, var)

    # Rolling needs the whole time axis in one chunk
    anomalies = anomalies.chunk({"time": -1})
    window = _rolling_window_size(anomalies["time"])
    rolling_mean = anomalies.rolling(time=window, center=True).mean()
    index_plot = (rolling_mean / anomalies.std()).compute()

    plot_kwargs = {
        "title": "Niño 3.4 Index",
        "color": "black",
        "linewidth": 1.5,  # overrides the 1D default of 2 to match plain ax.plot
        "ax_kwargs": {"xlabel": "Year", "ylabel": "Niño 3.4 SST Anomoly (°C)"},
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
    """
    # Fail with a readable message if this isn't the grid we expect
    _require_coords(ds, variable, [lat_dim, lon_dim], "MOM5")

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
