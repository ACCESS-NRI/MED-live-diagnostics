# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""API functions for med-diagnostics live diagnostics"""

import os

from med_diagnostics import analysis, controller, data
from med_diagnostics.types import Heatmap, Line

__all__ = [
    "add_reference",
    "build_catalog",
    "list_datasets",
    "list_recipes",
    "load_dataset",
    "load_reference_catalog",
    "plot_data",
    "plot_overlay",
    "recipe_options",
    "reference_metadata",
    "register_analysis",
    "run_recipe",
]

# Re-exported so custom recipes can be added through the API
register_analysis = analysis.register_analysis


def build_catalog(model_path: str, model_type: str):
    """
    Build an intake-ESM datastore of the model output in model_path.

    The catalog is saved under ``~/.med_diagnostics/catalogs`` and reused on later
    calls if the output hasn't changed. Start a Dask client first for faster builds.

    Parameters
    ----------
    model_path : str
        Path to model output directory/files on Gadi.
    model_type : str
        Type of ACCESS model, case-insensitive (e.g. CM2, OM2).

    Returns
    -------
    intake_esm.esm_datastore
        Intake catalog of user model data.

    Raises
    ------
    ValueError
        If model_path doesn't exist or can't be read, or model_type is unsupported.
    """
    model_path = os.path.expanduser(model_path)
    warning = controller.validate_model_path(model_path)
    if warning:
        raise ValueError(warning.removeprefix("Warning >> "))

    print(
        "Building user data catalog for model type: "
        + model_type
        + " and model_path: "
        + model_path
        + "\nThis can take a few minutes."
    )

    return data._build_new_catalog(model_path, model_type.lower())


def load_reference_catalog(model_type, filter=True):
    """
    Load the ACCESS-NRI reference model catalog, optionally filtered to a model type.

    Parameters
    ----------
    model_type : str
        Type of ACCESS model, case-insensitive (e.g. CM2, OM2).
    filter : bool, optional
        Only include models matching model_type. Default True.

    Returns
    -------
    intake.Catalog
        ACCESS-NRI catalog of reference models, keyed by model name.
    """
    return data._load_access_nri_catalog(model_type=model_type, filter=filter)


def list_datasets(model_catalog):
    """
    List the keys in a catalog.

    Parameters
    ----------
    model_catalog : intake_esm.esm_datastore, AliasedESMCatalog or intake.Catalog
        A user or reference model catalog, whose keys are datasets, or the
        ACCESS-NRI catalog, whose keys are reference models.

    Returns
    -------
    list of str
        The catalog's keys.
    """
    return list(model_catalog.keys())


def load_dataset(model_catalog, key, years=None, from_start=False):
    """
    Load a dataset from a user or reference model catalog.

    Parameters
    ----------
    model_catalog : intake_esm.esm_datastore or AliasedESMCatalog
        Catalog of user model data, or of one reference model (e.g. ``ref_cat[model]``).
    key : str
        Dataset key in model_catalog, from ``list_datasets``.
    years : int, optional
        Only load the files for this many years. None loads every year.
    from_start : bool, optional
        Load the first years of the run instead of the most recent.

    Returns
    -------
    xarray.Dataset
        Dask-backed dataset. ``attrs["med_missing_files"]`` counts catalogued files
        that were skipped because they no longer exist on disk.

    Raises
    ------
    FileNotFoundError
        If none of the catalogued files exist on disk.
    ValueError
        If ``years`` is less than 1.
    """

    return data._build_data_object(
        model_catalog, key, years=years, from_start=from_start
    )


def _fill_slices(dataset, variable, slices, keep):
    """
    Add the first value of each unsliced dimension of variable to slices. Private.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset holding variable.
    variable : str
        Variable being plotted.
    slices : dict or None
        Slices chosen by the user, as {dimension: value}.
    keep : set of str
        Dimensions to leave unsliced, e.g. the plot axes.

    Returns
    -------
    dict
        A new dict of slices covering every dimension not in keep.
    """
    slices = dict(slices or {})
    for dim in dataset[variable].dims:
        if dim not in keep and dim not in slices:
            slices[dim] = dataset[dim].values[0]
    return slices


def plot_data(
    dataset,
    variable,
    x_axis,
    y_axis=None,
    animate_over=None,
    slices=None,
    dataset_name="",
    model_name=None,
):
    """
    Plot a variable as a line plot, heatmap or animation.

    Only ``x_axis`` gives a line plot, adding ``y_axis`` gives a heatmap, and adding
    ``animate_over`` as well gives an animated heatmap.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset to plot, e.g. from ``load_dataset``.
    variable : str
        Name of the variable to plot.
    x_axis : str
        Dimension to plot along the x-axis.
    y_axis : str, optional
        Dimension to plot along the y-axis.
    animate_over : str, optional
        Dimension to animate over, e.g. "time". Needs ``y_axis``.
    slices : dict, optional
        Dimension names mapped to the values to plot, e.g. ``{"st_ocean": 100}``.
        Nearest values are used. Other dimensions not plotted use their first value.
    dataset_name : str, optional
        Name of the dataset, shown in the caption.
    model_name : str, optional
        Reference model name. If given, the plot is captioned as a reference model.

    Returns
    -------
    matplotlib.figure.Figure or panel.Column
        The formatted figure, or a Panel layout for animations.
    """
    if animate_over and not y_axis:
        raise ValueError("Animations need a y_axis as well as an x_axis")

    # Line plots draw one line per ensemble member, so leave member unsliced
    keep = {x_axis, y_axis, animate_over} | (set() if y_axis else {"member"})
    slices = _fill_slices(dataset, variable, slices, keep)

    is_ref = model_name is not None
    if animate_over:
        return controller.plot_animation(
            dataset,
            dataset_name,
            variable,
            slices,
            x_axis,
            y_axis,
            animate_over,
            is_ref=is_ref,
        )
    return controller.plot_dataset(
        dataset,
        dataset_name,
        variable,
        x_axis,
        slices,
        is_ref,
        model_name=model_name or "User",
        plot_type=Heatmap() if y_axis else Line(),
        y_axis=y_axis,
    )


def reference_metadata(ref_catalog, model_key):
    """
    Return the metadata of a reference model.

    Parameters
    ----------
    ref_catalog : intake.Catalog
        ACCESS-NRI catalog, from ``load_reference_catalog``.
    model_key : str
        Reference model name, from ``list_datasets(ref_catalog)``.

    Returns
    -------
    dict
        The model's metadata from the ACCESS-NRI catalog.
    """

    return ref_catalog[model_key].metadata


def add_reference(name, ref_catalog, key, user_dataset, references=None):
    """
    Load a reference dataset for overlay plots, converted to the user dataset's calendar.

    Converting the calendar lets the two be plotted together (e.g. 360-day against
    standard calendars).

    Parameters
    ----------
    name : str
        Name to store the reference under, shown in the plot legend.
    ref_catalog : intake_esm.esm_datastore or AliasedESMCatalog
        Catalog of one reference model, e.g. ``ref_cat[model]``.
    key : str
        Dataset key in ref_catalog, from ``list_datasets``.
    user_dataset : xarray.Dataset
        User dataset whose calendar the reference is converted to.
    references : dict, optional
        Existing references to add to, which is updated in place. None starts a new dict.

    Returns
    -------
    dict
        Reference datasets keyed by name, including the new one.
    """
    return controller.add_to_dataset_dict(
        {} if references is None else references, name, ref_catalog, key, user_dataset
    )


def plot_overlay(
    dataset,
    variable,
    references,
    x_axis,
    y_axis=None,
    slices=None,
    difference=False,
    constrain_to_user=False,
):
    """
    Plot the user dataset against reference datasets.

    Only ``x_axis`` overlays lines on one plot, adding ``y_axis`` gives a grid of
    heatmaps on a shared colour scale.

    Parameters
    ----------
    dataset : xarray.Dataset
        User dataset, e.g. from ``load_dataset``.
    variable : str
        Name of the variable to plot.
    references : dict
        Reference datasets keyed by name, from ``add_reference``.
    x_axis : str
        Dimension to plot along the x-axis.
    y_axis : str, optional
        Dimension to plot along the y-axis.
    slices : dict, optional
        Dimension names mapped to the values to plot, e.g. ``{"st_ocean": 100}``.
        Nearest values are used. Other dimensions not plotted use their first value.
    difference : bool, optional
        Plot each reference minus the user data. Default False.
    constrain_to_user : bool, optional
        Limit a line plot's x-axis to the user data's range, instead of spanning
        every dataset. Default False.

    Returns
    -------
    matplotlib.figure.Figure
        The formatted figure.
    """
    if difference and not references:
        raise ValueError("Difference plots need at least one reference")

    slices = _fill_slices(dataset, variable, slices, {x_axis, y_axis, "member"})

    if y_axis:
        return controller.plot_multiplot_heatmap_dataset(
            dataset, variable, references, slices, x_axis, y_axis, plot_diff=difference
        )

    _, global_min, global_max, user_min, user_max = controller.check_bounds(
        dataset, x_axis, references
    )
    x_min, x_max = (
        (user_min, user_max) if constrain_to_user else (global_min, global_max)
    )
    return controller.plot_multiplot_dataset(
        dataset,
        variable,
        references,
        slices,
        x_axis,
        x_min,
        x_max,
        plot_diff=difference,
    )


def list_recipes():
    """
    List the prebuilt and registered analysis recipes.

    Returns
    -------
    dict
        Recipes keyed by label, as ``{label: function}``. Custom recipes added with
        ``register_analysis`` are labelled ``"Custom: <summary>"``.
    """
    return analysis._list_recipes()


def _get_recipe(recipe):
    """
    Return a recipe function from either the function or its label. Private.

    Parameters
    ----------
    recipe : callable or str
        A recipe function, or its label from ``list_recipes``.

    Returns
    -------
    callable
        The recipe function.

    Raises
    ------
    ValueError
        If recipe is a label that doesn't match any recipe.
    """
    if callable(recipe):
        return recipe
    recipes = analysis._list_recipes()
    if recipe not in recipes:
        raise ValueError(f"No recipe labelled {recipe!r}. Recipes: {list(recipes)}")
    return recipes[recipe]


def recipe_options(recipe, dataset=None):
    """
    Describe the arguments a recipe takes.

    Parameters
    ----------
    recipe : callable or str
        A recipe function, or its label from ``list_recipes``.
    dataset : xarray.Dataset, optional
        If given, fills the choices for variable and dimension arguments from it.

    Returns
    -------
    list of dict
        One dict per argument with keys ``name``, ``label``, ``kind``, ``required``,
        ``default``, ``choices``, ``units`` and ``description``.
    """
    return analysis._get_recipe_kwarg_options(_get_recipe(recipe), dataset)


def run_recipe(dataset, recipe, **kwargs):
    """
    Run an analysis recipe on a dataset and plot each result.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset to analyse, e.g. from ``load_dataset``.
    recipe : callable or str
        A recipe function, or its label from ``list_recipes``.
    **kwargs
        Arguments for the recipe, listed by ``recipe_options``.

    Returns
    -------
    list of matplotlib.figure.Figure
        One figure per recipe result.
    """
    return analysis._analyse_and_plot(dataset, _get_recipe(recipe), **kwargs)
