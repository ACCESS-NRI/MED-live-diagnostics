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

    print("Started Dask cluster, 1 thread per worker")

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
    data._load_access_nri_catalog(model_type=model_type, filter=filter)


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
        model_cat dictionary key - in this case the selected dropdown value.
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
    dataset_name,
    variable,
    x_axis,
    chosen_slices,
    is_ref,
    plot_type,
    model_name="User",
    y_axis=None,
):
    """
    Plot a variable from a loaded dataset as a line plot or heatmap.

    Parameters
    ----------
    dataset : xarray.Dataset
        Dataset to plot, e.g. from ``load_dataset``.
    dataset_name : str
        Name of the dataset, shown in the plot caption.
    variable : str
        Name of the variable to plot.
    x_axis : str
        Dimension to plot along the x-axis.
    chosen_slices : dict
        Dimension names mapped to values to select, e.g. ``{"time": "2000-01"}``.
        Nearest values are used.
    is_ref : bool
        Whether the dataset is a reference model, which changes the caption.
    plot_type : {"Line", "Heatmap"}
        Type of plot to draw.
    model_name : str, optional
        Model name shown in the caption of reference plots. Default "User".
    y_axis : str, optional
        Dimension to plot along the y-axis. Required for heatmaps.

    Returns
    -------
    matplotlib.figure.Figure
        The formatted figure.
    """
    plot_types = {Line.value: Line(), Heatmap.value: Heatmap()}
    if plot_type not in plot_types:
        raise ValueError(
            f"plot_type must be one of {list(plot_types)}, got {plot_type!r}"
        )

    return controller.plot_dataset(
        dataset,
        dataset_name,
        variable,
        x_axis,
        chosen_slices,
        is_ref,
        model_name=model_name,
        plot_type=plot_types[plot_type],
        y_axis=y_axis,
    )
