import inspect
from collections.abc import Callable
from typing import Any

import matplotlib.pyplot as plt
import xarray as xr

PREDEFINED_REGIONS = {
    "nino34": {"lat": (-5, 5), "lon": (-170, -120)},
    "nino3": {"lat": (-5, 5), "lon": (-150, -90)},
    "nino4": {"lat": (-5, 5), "lon": (160, -150)},
    "tasmania": {"lat": (-44, -39), "lon": (143, 149)},
}

# Default `DataArray.plot` kwargs by result dimensionality: 1D is a timeseries,
# 2D a Hovmöller diagram or zonal mean over latitude.
DEFAULT_PLOT_KWARGS: dict[int, dict[str, Any]] = {
    1: {"linewidth": 2},
    2: {"cmap": "viridis"},
}

# Custom recipes uploaded from a notebook with `upload_analysis`, by function name
UPLOADED_ANALYSES: dict[str, Callable] = {}


def extract_region(dataset, region, lon_dim="lon", lat_dim="lat"):
    """
    Extract a lat/lon bounding box, on regular or curvilinear grids.

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

    lon_west, lon_east = bounds["lon"]
    lat_lo, lat_hi = sorted(bounds["lat"])

    lon_coord = dataset[lon_dim]
    lat_coord = dataset[lat_dim]

    # 2. Shift the region's longitudes into the grid's own 360° window. This
    # covers 0-360, -180-180 and MOM5's -280-80 grids alike.
    grid_lon_min = float(lon_coord.min())
    lon_west = (lon_west - grid_lon_min) % 360 + grid_lon_min
    lon_east = (lon_east - grid_lon_min) % 360 + grid_lon_min

    # 3. Longitudes run west to east, so west > east means the box wraps past
    # the grid's seam (e.g. Niño 4 across the dateline on a -180-180 grid).
    # Sorting them would select the opposite side of the globe instead.
    if lon_west <= lon_east:
        in_lon = (lon_coord >= lon_west) & (lon_coord <= lon_east)
    else:
        in_lon = (lon_coord >= lon_west) | (lon_coord <= lon_east)
    # Boolean masks, unlike `.sel(slice(...))`, don't care whether latitude
    # is stored ascending or descending (e.g. ERA5 runs 90 to -90).
    in_lat = (lat_coord >= lat_lo) & (lat_coord <= lat_hi)

    # 4a. Curvilinear/tripolar grids (e.g. ACCESS-OM2/CICE TLAT/TLON): `.sel()`
    # can't index by a 2D coordinate, so mask and drop instead.
    if lon_coord.ndim > 1 or lat_coord.ndim > 1:
        # `where(..., drop=True)` refuses a dask-backed boolean mask (the
        # result shape would be unknown). The mask is grid-sized with no time
        # dimension, so computing it eagerly is cheap.
        return dataset.where((in_lon & in_lat).compute(), drop=True)

    # 4b. Regular 1D grids: index each axis by its mask
    return dataset.isel(
        {lat_coord.dims[0]: in_lat.values, lon_coord.dims[0]: in_lon.values}
    )


def analyse_and_plot(dataset: xr.Dataset, recipe_func, **recipe_kwargs) -> plt.Figure:
    """
    Run a recipe on the dataset and plot the result.

    Parameters
    ----------
    dataset : xarray.Dataset
        Data passed to the recipe.
    recipe_func : callable
        ``recipe_func(dataset, **recipe_kwargs)``, returning either a DataArray or
        ``(DataArray, plot_kwargs)`` to customise the plot. ``plot_kwargs`` may
        include ``customise``, a ``func(ax, data)`` or list of them, run in
        order after plotting.
    **recipe_kwargs
        Extra arguments for the recipe (e.g. variable or depth).

    Returns
    -------
    matplotlib.figure.Figure
        The figure holding the plot.
    """
    # 1. Execute the chosen recipe function, unpacking any extra arguments
    result = recipe_func(dataset, **recipe_kwargs)

    # A recipe may return (data, plot_kwargs) to style its own plot
    if isinstance(result, tuple):
        result_data, recipe_plot_kwargs = result
    else:
        result_data, recipe_plot_kwargs = result, {}

    # 2. Plotting logic. The recipe's kwargs override the defaults.
    defaults = DEFAULT_PLOT_KWARGS.get(len(result_data.dims), {})
    plot_kwargs = {**defaults, **(recipe_plot_kwargs or {})}

    # Figure/axes-level keys aren't accepted by `DataArray.plot`, so pop them
    # first. `ax_kwargs` goes to `ax.set` (e.g. xlabel, ylim, yscale), and
    # `customise` funcs `(ax, data)` run last for anything kwargs can't express
    # (fills, reference lines, annotations).
    figsize = plot_kwargs.pop("figsize", (10, 5))
    title = plot_kwargs.pop("title", result_data.name or "Diagnostic Output")
    ax_kwargs = plot_kwargs.pop("ax_kwargs", {})
    customise = plot_kwargs.pop("customise", [])
    # Accept a single function as well as a list of them
    if callable(customise):
        customise = [customise]

    fig, ax = plt.subplots(figsize=figsize)
    # Everything else goes to xarray, then on to matplotlib (e.g. color, vmin)
    result_data.plot(ax=ax, **plot_kwargs)

    ax.set_title(title)
    ax.set(**ax_kwargs)
    for func in customise:
        func(ax, result_data)
    plt.tight_layout()
    return fig


def upload_analysis(recipe_func):
    """
    Register a custom recipe for the UI's analysis section.

    It appears in the recipe dropdown after "Refresh analysis recipes" is clicked.

    Parameters
    ----------
    recipe_func : callable
        ``recipe_func(ds, ...)`` returning a DataArray or ``(DataArray, plot_kwargs)``,
        with a docstring following the recipe convention in ``med_diagnostics.recipes``.

    Returns
    -------
    callable
        ``recipe_func`` unchanged, so this also works as a decorator.

    Raises
    ------
    TypeError
        If ``recipe_func`` can't take the dataset as its first argument.
    ValueError
        If its docstring doesn't describe its parameters correctly.
    """
    # Imported here because recipes imports this module
    from med_diagnostics import recipes

    if not callable(recipe_func) or not inspect.signature(recipe_func).parameters:
        raise TypeError(
            "An analysis must be a function taking the dataset as its first argument."
        )
    # Check the docstring now, so mistakes show at upload rather than in the UI
    recipes.get_recipe_kwarg_options(recipe_func)

    # Keyed by name, so re-uploading an edited function replaces the old one
    UPLOADED_ANALYSES[recipe_func.__name__] = recipe_func
    return recipe_func
