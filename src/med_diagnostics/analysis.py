import inspect
from collections.abc import Callable
from typing import Any, Literal, get_args, get_type_hints

import matplotlib.pyplot as plt
import xarray as xr

from med_diagnostics import recipes

# Default `DataArray.plot` kwargs by result dimensionality: 1D is a timeseries,
# 2D a Hovmöller diagram or zonal mean over latitude.
DEFAULT_PLOT_KWARGS: dict[int, dict[str, Any]] = {
    1: {"linewidth": 2},
    2: {"cmap": "viridis"},
    3: {"figsize": (6, 4)},
}

# Custom recipes uploaded from a notebook with `upload_analysis`, by function name
UPLOADED_ANALYSES: dict[str, Callable] = {}


# --------------------------------------------------------------------------
# Reading recipes for the UI
# --------------------------------------------------------------------------

# Parameter kinds the UI knows how to build a widget for
RECIPE_KINDS = {"data variable", "dimension", "choice", "float", "int", "str", "bool"}


def _list_recipes():
    """
    Return every prebuilt and uploaded recipe, keyed by a label for the UI.

    Returns
    -------
    dict
        ``{label: recipe}``: each ``recipe_*`` function in ``recipes`` under its
        docstring summary, then each ``upload_analysis`` recipe as
        ``"Custom: <summary>"``.
    """
    found = {}

    def add(label, name, func):
        # Dropdown labels must be unique, so fall back to the function name
        found[label if label not in found else f"{label} ({name})"] = func

    for name, func in inspect.getmembers(recipes, inspect.isfunction):
        if name.startswith("recipe_"):
            add(_get_recipe_summary(func)[0], name, func)
    for name, func in UPLOADED_ANALYSES.items():
        add(f"Custom: {_get_recipe_summary(func)[0]}", name, func)
    return found


def _get_recipe_summary(recipe):
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


def _get_recipe_kwarg_options(recipe, ds=None):
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


# --------------------------------------------------------------------------
# Running and registering recipes
# --------------------------------------------------------------------------


def _analyse_and_plot(dataset: xr.Dataset, recipe_func, **recipe_kwargs) -> plt.Figure:
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
    # Execute the chosen recipe function, unpacking any extra arguments
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
    figsize = plot_kwargs.pop("figsize", (6, 4))
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
        with its arguments declared using ``typing.Annotated`` like the recipes in
        ``med_diagnostics.recipes``.

    Returns
    -------
    callable
        ``recipe_func`` unchanged, so this also works as a decorator.

    Raises
    ------
    TypeError
        If ``recipe_func`` can't take the dataset as its first argument.
    """
    # Check that the passed in function is actually a function, and takes arguments.
    if not callable(recipe_func) or not inspect.signature(recipe_func).parameters:
        raise TypeError(
            "An analysis must be a function taking the dataset as its first argument."
        )

    # Read the annotations now, so mistakes show at upload rather than in the UI
    _get_recipe_kwarg_options(recipe_func)

    # Keyed by name, so re-uploading an edited function replaces the old one
    UPLOADED_ANALYSES[recipe_func.__name__] = recipe_func
    return recipe_func
