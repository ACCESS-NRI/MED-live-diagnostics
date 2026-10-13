# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""API functions for med-diagnostics live diagnostics"""

from med_diagnostics import data


def build_catalog(model_path: str, model_type: str):
    """
    Build new intake ESM datastore from user model data found in model_path.
    Uses intake datastore builder for the specified model_type.
    Saves new catalog file to the current working directory. Private.

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

    print(
        "Building user data catalog for model type: "
        + model_type
        + " and model_path: "
        + model_path
        + "\n This can take a few minutes."
    )
    return data._build_new_catalog(model_path, model_type.lower())


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
    Convert model_cat ESM datastore to xarray object. Private.

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
