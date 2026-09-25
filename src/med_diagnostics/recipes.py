import numpy as np
import xarray as xr

from med_diagnostics import analysis, plot_customisations

# --------------------------------------------------------------------------
# General helpers - reusable in custom recipes for any grid
# --------------------------------------------------------------------------


def nino34_timeseries(data, lat_dim, lon_dim, area=None):
    """
    Area-weighted mean of ``data`` over the Niño 3.4 region.

    Parameters
    ----------
    data : xarray.DataArray
        Variable with a time dim and lat/lon coords (1D or 2D).
    lat_dim, lon_dim : str
        Latitude/longitude coordinate names.
    area : xarray.DataArray, optional
        Cell areas to weight by. Defaults to cos(lat).

    Returns
    -------
    xarray.DataArray
        The regional mean timeseries.
    """
    data = analysis.extract_region(
        data, region="nino34", lon_dim=lon_dim, lat_dim=lat_dim
    )
    if area is not None:
        # Model cell areas; land cells are NaN and are skipped automatically
        weights = analysis.extract_region(
            area, region="nino34", lon_dim=lon_dim, lat_dim=lat_dim
        ).fillna(0)
    else:
        # cos(lat) is exact on regular lat/lon grids
        weights = np.cos(np.deg2rad(data[lat_dim]))
    # On curvilinear grids lat/lon are 2D coords, so average over their dims
    dims = list(dict.fromkeys(data[lat_dim].dims + data[lon_dim].dims))
    return data.weighted(weights).mean(dim=dims)


def _require_coords(ds, variable, coords, grid):
    """Raise a readable error if ``ds`` isn't the grid this recipe targets."""
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


def recipe_nino34_timeseries_mom5(
    ds: xr.Dataset, variable: str = "o2", depth: float = 0
):
    """Niño 3.4 mean timeseries of a MOM5 ocean variable (ACCESS-OM2, ESM1.6)."""
    _require_coords(ds, variable, ["yt_ocean", "xt_ocean"], "MOM5")
    data = ds[variable]
    if "st_ocean" in data.dims:
        data = data.sel(st_ocean=depth, method="nearest")

    # MOM5 cell areas, if the static fields were loaded; cos(lat) otherwise
    timeseries = nino34_timeseries(data, "yt_ocean", "xt_ocean", ds.get("area_t"))
    timeseries.name = f"Niño 3.4 {variable}"
    if "st_ocean" in data.coords:
        timeseries.name += f" (~{float(data.st_ocean):.0f}m)"

    return timeseries, plot_customisations.timeseries_plot_kwargs(
        timeseries, variable, data.attrs.get("units", "")
    )


def recipe_nino34_timeseries_um(
    ds: xr.Dataset,
    variable: str = "tas",
    level_dim: str | None = None,
    level: float = 0,
):
    """Niño 3.4 mean timeseries of a UM atmosphere variable."""
    _require_coords(ds, variable, ["lat", "lon"], "UM")
    data = ds[variable]
    # Surface fields (e.g. tas) have no vertical dim to select
    if level_dim is not None and level_dim in data.dims:
        data = data.sel({level_dim: level}, method="nearest")

    # Regular lat/lon grid, so cos(lat) weighting is exact
    timeseries = nino34_timeseries(data, "lat", "lon")
    timeseries.name = f"Niño 3.4 {variable}"
    if level_dim is not None and level_dim in data.coords:
        timeseries.name += f" ({level_dim}={float(data[level_dim]):g})"

    return timeseries, plot_customisations.timeseries_plot_kwargs(
        timeseries, variable, data.attrs.get("units", "")
    )
