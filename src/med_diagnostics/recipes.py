import inspect
import re
import sys

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
        A recipe with a numpy-format docstring. Each ``Parameters`` type line
        reads ``kind[, units <u>][, {choices}][, default <x> | optional]``, where
        kind is ``data variable``, ``dimension``, a Python type, or omitted for a
        bare ``{choices}`` set.
    ds : xarray.Dataset, optional
        If given, fills ``choices`` for ``data variable`` and ``dimension``
        parameters from this dataset.

    Returns
    -------
    list of dict
        One dict per parameter with keys ``name``, ``kind``, ``required``,
        ``default``, ``choices``, ``units`` and ``description``, matching
        ``diagnostics.get_indicator_kwarg_options``.

    Raises
    ------
    ValueError
        If the docstring doesn't describe the recipe's parameters correctly.
    """
    signature = inspect.signature(recipe)
    documented = _parse_parameters_section(inspect.getdoc(recipe) or "")
    _validate_recipe_docs(recipe.__name__, signature, documented)

    kwarg_options = []
    # The first argument is always the dataset, which the UI supplies itself
    for name, param in list(signature.parameters.items())[1:]:
        doc = documented.get(name, {})
        has_default = param.default is not inspect.Parameter.empty
        choices = doc.get("choices")
        if ds is not None and doc.get("kind") in ("data variable", "dimension"):
            choices = _dataset_choices(ds, doc["kind"])
            # Optional dims (e.g. no vertical level for surface fields) need
            # a "none" entry
            if has_default and param.default is None:
                choices = [None, *choices]
        kwarg_options.append(
            {
                "name": name,
                "kind": doc.get("kind"),
                "required": not has_default,
                # The signature, not the docstring, is the source of truth
                "default": param.default if has_default else None,
                "choices": choices,
                "units": doc.get("units"),
                "description": doc.get("description"),
            }
        )
    return kwarg_options


def _validate_recipe_docs(recipe_name, signature, documented):
    """Raise if a recipe's docstring would give the UI an incomplete form."""
    # A free-text docstring has no checking of its own, so a typo (e.g.
    # "data varible") would otherwise quietly become a text box in the UI
    user_params = list(signature.parameters.values())[1:]
    problems = []
    for param in user_params:
        doc = documented.get(param.name)
        if doc is None:
            problems.append(f"'{param.name}' is not documented")
        elif doc["kind"] not in RECIPE_KINDS:
            problems.append(
                f"'{param.name}' has unknown kind {doc['kind']!r} "
                f"(expected one of {sorted(RECIPE_KINDS)})"
            )
        elif (
            doc["choices"]
            and param.default is not inspect.Parameter.empty
            and param.default is not None
            and str(param.default) not in doc["choices"]
        ):
            problems.append(
                f"'{param.name}' defaults to {param.default!r}, which isn't one "
                f"of its choices {doc['choices']}"
            )
    # Docs for a parameter that no longer exists are stale
    all_params = set(signature.parameters)
    for name in sorted(documented.keys() - all_params):
        problems.append(f"'{name}' is documented but not a parameter")

    if problems:
        raise ValueError(
            f"Recipe '{recipe_name}' has an invalid docstring: " + "; ".join(problems)
        )


def _dataset_choices(ds, kind):
    """List the variables or coordinates of ``ds`` a parameter can take."""
    if kind == "data variable":
        return list(ds.data_vars)
    # Coords rather than dims alone, so 2D lat/lon (e.g. geolon_t) are
    # offered; dims without a coordinate variable are included too
    return list(dict.fromkeys([*ds.coords, *ds.dims]))


def _parse_parameters_section(docstring):
    """Parse a numpy ``Parameters`` section into ``{name: fields}``."""
    lines = docstring.splitlines()
    try:
        start = lines.index("Parameters") + 2  # skip the "----------" underline
    except ValueError:
        return {}

    params: dict[str, dict] = {}
    current = None
    for line in lines[start:]:
        if line and not line.startswith(" "):
            if " : " not in line:
                break  # the next section header, e.g. "Returns"
            name, type_line = line.split(" : ", 1)
            current = {"description": None, **_parse_type_line(type_line)}
            params[name.strip()] = current
        elif line.strip() and current is not None:
            desc = current["description"]
            current["description"] = f"{desc} {line.strip()}" if desc else line.strip()
    return params


def _parse_type_line(type_line):
    """Split ``kind, units m, {"a", "b"}, default 0`` into its fields."""
    fields = {"kind": None, "units": None, "choices": None}
    # Commas inside {choices} aren't separators, so pull the set out first
    choices = re.search(r"\{(.*?)\}", type_line)
    if choices:
        fields["choices"] = [
            c.strip().strip("\"'") for c in choices.group(1).split(",")
        ]
        type_line = type_line.replace(choices.group(0), "")

    for part in (p.strip() for p in type_line.split(",")):
        if part.startswith("units "):
            fields["units"] = part.removeprefix("units ").strip()
        elif part and not part.startswith("default") and part != "optional":
            fields["kind"] = part
    # A bare {choices} set, e.g. ``{"mean", "max"}, default "mean"``
    if fields["kind"] is None and fields["choices"]:
        fields["kind"] = "choice"
    return fields


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
    variable: str = "o2",
    lon_dim: str = "xt_ocean",
    lat_dim: str = "yt_ocean",
    lvl_dim: str = "st_ocean",
    depth: float = 0,
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
    variable: str = "tas",
    lon_dim: str = "lon",
    lat_dim: str = "lat",
    lvl_dim: str | None = None,
    level: float = 0,
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


def recipe_sst_anomaly_nino34(dataset, x_dim="xt_ocean", y_dim="yt_ocean", var="tos"):
    """
    Niño 3.4 index for sea surface temperature

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
        "figsize": (12, 6),
        "title": "Niño 3.4 Index",
        "color": "black",
        "linewidth": 1.5,  # overrides the 1D default of 2 to match plain ax.plot
        "ax_kwargs": {"xlabel": "Year", "ylabel": "Niño 3.4 SST Anomoly (°C)"},
        "customise": [
            plot_customisations._nino_fills,
            plot_customisations._nino_reference_lines,
        ],
    }

    return index_plot, plot_kwargs
