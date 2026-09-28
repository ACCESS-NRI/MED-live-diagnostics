import inspect
import sys
from typing import Annotated, Literal, get_args, get_type_hints

import numpy as np
import xarray as xr

from med_diagnostics import analysis, plot_customisations

# --------------------------------------------------------------------------
# Docstring parsing for the UI
# --------------------------------------------------------------------------

# Parameter kinds the UI knows how to build a widget for
RECIPE_KINDS = {"data variable", "dimension", "choice", "float", "int", "str", "bool"}


def list_recipes():
    """
    Return every prebuilt and uploaded recipe, keyed by a label for the UI.

    Returns
    -------
    dict
        ``{label: recipe}``: each ``recipe_*`` function in this module under its
        docstring summary, then each ``analysis.upload_analysis`` recipe as
        ``"Custom: <summary>"``.
    """
    found = {}

    def add(label, name, func):
        # Dropdown labels must be unique, so fall back to the function name
        found[label if label not in found else f"{label} ({name})"] = func

    for name, func in inspect.getmembers(sys.modules[__name__], inspect.isfunction):
        if name.startswith("recipe_"):
            add(get_recipe_summary(func)[0], name, func)
    for name, func in analysis.UPLOADED_ANALYSES.items():
        add(f"Custom: {get_recipe_summary(func)[0]}", name, func)
    return found


def get_recipe_summary(recipe):
    """
    Return a recipe's docstring summary line and the paragraph after it.

    Parameters
    ----------
    recipe : callable
        A recipe with a numpy-format docstring.

    Returns
    -------
    tuple of (str, str)
        The summary, e.g. what it computes, and details, e.g. the grid it targets.
    """
    paragraphs = (inspect.getdoc(recipe) or "").split("\n\n")
    summary = paragraphs[0].strip() or recipe.__name__
    # The second paragraph is the grid line, unless it's the Parameters section
    details = paragraphs[1].strip() if len(paragraphs) > 1 else ""
    if details.startswith("Parameters"):
        details = ""
    return summary, details


def get_recipe_kwarg_options(recipe, ds=None):
    """
    Describe every user-facing parameter of a recipe, e.g. for a UI form.

    Parameters
    ----------
    recipe : callable
        A recipe where parameters are typed using ``typing.Annotated``.
        Metadata should be a dictionary with keys like ``kind``, ``units``,
        or ``description``. e.g., ``Annotated[str, {"kind": "data variable"}]``
    ds : xarray.Dataset, optional
        If given, fills ``choices`` for ``data variable`` and ``dimension``
        parameters from this dataset.

    Returns
    -------
    list of dict
        One dict per parameter with keys ``name``, ``label``, ``kind``,
        ``required``, ``default``, ``choices``, ``units`` and ``description``.
    """

    hints = get_type_hints(recipe, include_extras=True)
    signature = inspect.signature(recipe)

    kwarg_options = []
    # The first argument is always the dataset, which the UI supplies itself, loop over everything after the first argument
    for name, param in list(signature.parameters.items())[1:]:
        hint = hints.get(name)
        metadata = {}
        base_type = hint

        # Extract metadata if Annotated is used
        if hasattr(hint, "__metadata__"):
            metadata = (
                hint.__metadata__[0]
                if isinstance(hint.__metadata__, tuple) and hint.__metadata__
                else {}
            )
            # Fallback for base type across Python versions
            base_type = getattr(hint, "__origin__", hint)

        has_default = param.default is not inspect.Parameter.empty
        choices = metadata.get("choices")

        # Handle Literal types for implicit choices (e.g. Literal["mean", "sum"])
        if getattr(base_type, "__origin__", base_type) is Literal:
            choices = list(get_args(base_type) or getattr(base_type, "__args__", []))

        # Dynamically populate choices from the xarray dataset
        if ds is not None and metadata.get("kind") in ("data variable", "dimension"):
            choices = _dataset_choices(ds, metadata["kind"])
            # Optional dims need a "none" entry
            if has_default and param.default is None:
                choices = [None, *choices]

        kwarg_options.append(
            {
                "name": name,
                # Display label for the UI; the value is still passed as ``name``
                "label": metadata.get("name") or name,
                "kind": metadata.get("kind"),
                "required": not has_default,
                "default": param.default if has_default else None,
                "choices": choices,
                "units": metadata.get("units"),
                "description": metadata.get("description"),
            }
        )

    return kwarg_options


def _dataset_choices(ds, kind):
    """List the variables or coordinates of ``ds`` a parameter can take."""
    if kind == "data variable":
        return list(ds.data_vars)
    # Coords rather than dims alone, so 2D lat/lon (e.g. geolon_t) are
    # offered; dims without a coordinate variable are included too
    return [
        dim
        for dim in dict.fromkeys([*ds.coords, *ds.dims])
        if ds.sizes.get(dim, 1) > 1 and dim not in ("nv", "st_edges_ocean")
    ]


# General helpers - reusable in custom recipes for any grid


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


# --------------------------------------------------------------------------
# Recipes
# --------------------------------------------------------------------------


def recipe_nino34_timeseries_mom5(
    ds: xr.Dataset,
    variable: Annotated[
        str, {"name": "Select Variable", "kind": "data variable"}
    ] = "no3",
    lon_dim: Annotated[
        str, {"name": "Select Longitude Dim", "kind": "dimension"}
    ] = "xt_ocean",
    lat_dim: Annotated[
        str, {"name": "Select Latitude Dim", "kind": "dimension"}
    ] = "yt_ocean",
    lvl_dim: Annotated[
        str, {"name": "Select Depth Dim", "kind": "dimension"}
    ] = "st_ocean",
    depth: Annotated[
        float,
        {
            "name": "Select Depth Slice",
            "kind": "float",
            "units": "m",
            "description": "Level for the analysis to be sliced at, default 0m",
        },
    ] = 0,
):
    """
    Niño 3.4 area-weighted mean timeseries of an ocean variable.

    For MOM5 output (ACCESS-OM2, ACCESS-ESM1.6).

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset to analyse, supplied by the UI.
    variable : data variable, default "o2"
        Variable to average over the region, e.g. o2 or temp.
    lon_dim : dimension, default "xt_ocean"
        Longitude coordinate.
    lat_dim : dimension, default "yt_ocean"
        Latitude coordinate.
    lvl_dim : dimension, default "st_ocean"
        Depth coordinate; ignored if the variable has no depth.
    depth : float, units m, default 0
        Depth to plot; the nearest model level is used.

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The timeseries and its plot kwargs.
    """
    require_coords(ds, variable, [lat_dim, lon_dim], "MOM5")
    data = ds[variable]
    if lvl_dim in data.dims:
        data = data.sel({lvl_dim: depth}, method="nearest")

    # MOM5 cell areas, if the static fields were loaded; cos(lat) otherwise
    timeseries = nino34_timeseries(data, lat_dim, lon_dim, ds.get("area_t"))
    timeseries.name = f"Niño 3.4 {variable}"
    if lvl_dim in data.coords:
        timeseries.name += f" (~{float(data[lvl_dim]):.0f}m)"

    return timeseries, plot_customisations.timeseries_plot_kwargs(
        timeseries, variable, data.attrs.get("units", "")
    )


def recipe_nino34_timeseries_um(
    ds: xr.Dataset,
    variable: Annotated[
        str,
        {
            "name": "Select Variable",
            "kind": "data variable",
            "description": "Variable from your dataset you want to analyse",
        },
    ] = "tas",
    lon_dim: Annotated[
        str, {"name": "Select Longitude Dim", "kind": "dimension"}
    ] = "lon",
    lat_dim: Annotated[
        str, {"name": "Select Latitude Dim", "kind": "dimension"}
    ] = "lat",
    lvl_dim: Annotated[
        str | None, {"name": "Select Depth Dim", "kind": "dimension"}
    ] = None,
    level: Annotated[
        float,
        {
            "name": "Select Level Slice",
            "kind": "float",
            "units": "m",
            "description": "Level for the analysis to be sliced at, default 0m",
        },
    ] = 0,
):
    """
    Niño 3.4 area-weighted mean timeseries of an atmosphere variable.

    For UM output on a regular lat/lon grid.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset to analyse, supplied by the UI.
    variable : data variable, default "tas"
        Variable to average over the region, e.g. tas or pr.
    lon_dim : dimension, default "lon"
        Longitude coordinate.
    lat_dim : dimension, default "lat"
        Latitude coordinate.
    lvl_dim : dimension, optional
        Vertical coordinate, e.g. pressure; leave unset for surface fields.
    level : float, default 0
        Level to plot, in lvl_dim's units; the nearest level is used.

    Returns
    -------
    tuple of (xarray.DataArray, dict)
        The timeseries and its plot kwargs.
    """
    require_coords(ds, variable, [lat_dim, lon_dim], "UM")
    data = ds[variable]
    # Surface fields (e.g. tas) have no vertical dim to select
    if lvl_dim is not None and lvl_dim in data.dims:
        data = data.sel({lvl_dim: level}, method="nearest")

    # Regular lat/lon grid, so cos(lat) weighting is exact
    timeseries = nino34_timeseries(data, lat_dim, lon_dim)
    timeseries.name = f"Niño 3.4 {variable}"
    if lvl_dim is not None and lvl_dim in data.coords:
        timeseries.name += f" ({lvl_dim}={float(data[lvl_dim]):g})"

    return timeseries, plot_customisations.timeseries_plot_kwargs(
        timeseries, variable, data.attrs.get("units", "")
    )


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

    nino34_ds = analysis.extract_region(dataset, "nino34", x_dim, y_dim)
    anomalies = analysis.calc_anomolies(nino34_ds, x_dim, y_dim, var)

    # Rolling needs the whole time axis in one chunk
    anomalies = anomalies.chunk({"time": -1})
    window = analysis.rolling_window_size(anomalies["time"])
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
