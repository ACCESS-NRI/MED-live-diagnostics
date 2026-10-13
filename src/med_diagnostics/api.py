# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""API functions for med-diagnostics live diagnostics"""

from med_diagnostics import controller, data
from med_diagnostics.types import Heatmap, Line


def build_catalog(model_path: str, model_type: str):
    """
    Build new intake ESM datastore from user model data found in model_path.
    Uses intake datastore builder for the specified model_type.
    Saves new catalog file to the current working directory.

    Parameters
    ----------
    model_path : str
        Path to model output directory/files on Gadi.
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).
    Returns
    ----------
    Intake-ESM datastore object or None
        Intake catalog of user model data, if valid.
    """
    warning = controller.validate_model_path(model_path) if model_path else None
    if warning:
        raise ValueError(warning)

    print(
        "Building user data catalog for model type: "
        + model_type
        + " and model_path: "
        + model_path
        + "\nThis can take a few minutes."
    )

    return data._build_new_catalog(model_path, model_type.lower())


def load_accessnri_catalog(model_type, filter=True):
    """
    Load the ACCESS-NRI reference model catalog, optionally filtering for your model type.

    Parameters
    ----------
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).
    filter : bool
        Whether to filter the models for the selected model type (True), or return the whole catalog (False)

    """
    return data._load_access_nri_catalog(model_type=model_type, filter=filter)


def list_datasets(model_catalog):
    """
    List the datasets within a given model catalog.

    Returns
    ---------
    List
        List of model catalog keys, if valid.
    """
    return list(model_catalog.keys())


def load_dataset(model_catalog, key, years=None, from_start=False):
    """
    Convert model_cat ESM datastore to xarray object.

    Parameters
    ----------
    model_cat : Intake-ESM datastore object or AliasedESMCatalog object
        Intake catalog of user or reference model data.
    key : str
        model_cat dictionary key
    years : int, optional
        Only load the files for this many years. None loads every year.
    from_start : bool, optional
        Load the first years of the run instead of the most recent.

    Returns
    ----------
    dataset : xarray object
        Dask xarray object. ``attrs["med_missing_files"]`` counts catalogued files
        that were skipped because they no longer exist on disk.

    Raises
    ------
    FileNotFoundError
        If none of the catalogued files exist on disk.
    """

    return data._build_data_object(
        model_catalog, key, years=years, from_start=from_start
    )


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

    slices = dict(slices or {})
    plotted = {x_axis, y_axis, animate_over}
    for dim in dataset[variable].dims:
        # Line plots draw one line per ensemble member, so leave member unsliced
        if dim in plotted or dim in slices or (dim == "member" and not y_axis):
            continue
        slices[dim] = dataset[dim].values[0]

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


def get_metadata(ref_catalog, model_key):
    """
    Return a dictionary with the model metadata

    Parameters
    ---------
    ref_catalog: Intake-ESM datastore object or AliasedESMCatalog object
        Intake catalog of user or reference model data.
    model_key: str
        model_cat dictionary key
    """

    return ref_catalog[model_key].metadata
