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
