# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Data IO functions"""

import os

import intake
import pandas as pd
from access_nri_intake.aliases import AliasedESMCatalog
from access_nri_intake.experiment import use_datastore
from access_nri_intake.source.builders import (
    AccessCm2Builder,
    AccessCm3Builder,
    AccessEsm15Builder,
    AccessEsm16Builder,
    AccessOm2Builder,
    AccessOm3Builder,
    Mom6Builder,
)


def _build_new_catalog(model_path, model_type):
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
    """

    # Match the model type to the correct type of builder
    match model_type:
        case "cm2":
            model_type_builder = AccessCm2Builder
        case "om2":
            model_type_builder = AccessOm2Builder
        case "cm3":
            model_type_builder = AccessCm3Builder
        case "om3":
            model_type_builder = AccessOm3Builder
        case "esm15":
            model_type_builder = AccessEsm15Builder
        case "esm16":
            model_type_builder = AccessEsm16Builder
        case "mom6":
            model_type_builder = Mom6Builder
        case _:
            raise ValueError(f"Unsupported model_type: {model_type!r}")
    # Set builder kwargs based on model type, if model_type is one of the builders that requires the ensemble argument, set it to False, otherwise set it to an empty dictionary.
    if model_type_builder in [
        AccessEsm15Builder,
        AccessEsm16Builder,
        AccessCm2Builder,
        AccessCm3Builder,
    ]:
        builder_kwargs_set = {"ensemble": False}
    else:
        builder_kwargs_set = {}

    # Use the matched builder to build the new catalog in the users working directory.
    return use_datastore(
        experiment_dir=model_path,
        catalog_dir=os.getcwd(),
        builder=model_type_builder,
        datastore_name="live_diagnostics_tmp_catalog",
        description="Temporary catalog for live diagnostics",
        builder_kwargs=builder_kwargs_set,
    )


def _load_new_catalog():
    """
    Load saved ESM datastore catalog file from the current working directory. Private.

    Returns
    ----------
    model_cat : Intake-ESM datastore object
        Intake catalog of user model data.
    """

    return intake.open_esm_datastore(
        os.path.join(os.getcwd(), "live_diagnostics_tmp_catalog.json"),
        columns_with_iterables=["variable"],
    )


def _select_year_files(df, years=None, from_start=False):
    """
    Keep the catalog rows for the first or most recent ``years`` years. Private.

    Parameters
    ----------
    df : pandas.DataFrame
        Catalog rows for one dataset, with a ``start_date`` column.
    years : int, optional
        Number of years to keep. None keeps every row.
    from_start : bool, optional
        Keep the first years of the run instead of the most recent.

    Returns
    ----------
    pandas.DataFrame
        The rows to load.
    """

    if years is None or "start_date" not in df:
        return df

    # Dates are "%Y-%m-%d, %H:%M:%S" strings, or "none" for files without a
    # time axis, which become NaN. end_date isn't used because a December
    # file ends on 1 January of the next year, so it would count one extra year
    start_years = pd.to_numeric(df["start_date"].astype(str).str[:4], errors="coerce")
    if start_years.isna().all():
        return df

    if from_start:
        in_range = start_years <= start_years.min() + years - 1
    else:
        in_range = start_years >= start_years.max() - years + 1
    # Undated files (e.g. static grid data) are kept whatever the range
    return df[in_range | start_years.isna()]


def _summarise_year_selection(model_cat, key, years=None, from_start=False):
    """
    Count the files and years a year selection would load, without opening any files.

    Parameters
    ----------
    model_cat : Intake-ESM datastore object
        Intake catalog of user model data.
    key : str
        model_cat dictionary key.
    years : int, optional
        Number of years to load. None loads every year.
    from_start : bool, optional
        Load the first years of the run instead of the most recent.

    Returns
    ----------
    dict or None
        ``n_files``, ``total_files``, ``first_year`` and ``last_year``, or None
        if the catalog entry has no file table.
    """

    df = getattr(model_cat[key], "df", None)
    if df is None:
        return None

    selected = _select_year_files(df, years, from_start)
    start_years = pd.to_numeric(
        selected["start_date"].astype(str).str[:4], errors="coerce"
    ).dropna()
    return {
        "n_files": len(selected),
        "total_files": len(df),
        "first_year": int(start_years.min()) if len(start_years) else None,
        "last_year": int(start_years.max()) if len(start_years) else None,
    }


def _build_data_object(model_cat, key, years=None, from_start=False):
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
        Dask xarray object.
    """

    # If the model_cat is an AliasedESMCatalog, unwrap it to get the raw esm_datastore (intake_esm.core.esm_datastore) object. Reference models are stored as AliasedESMCatalog objects, so this is necessary for loading reference model data.
    if isinstance(model_cat, AliasedESMCatalog):
        model_cat = model_cat.unwrap()

    # Opening each file is the slow part of a load, so drop the files outside
    # the chosen years before opening anything
    if years is not None:
        df = model_cat[key].df
        selected = _select_year_files(df, years, from_start)
        if len(selected) < len(df):
            # The same subset-catalog construction intake-esm's search uses,
            # so the key still refers to this dataset
            model_cat = model_cat.__class__(
                {"esmcat": model_cat.esmcat.model_dump(), "df": selected}
            )

    open_kwargs = {"use_cftime": True, "chunks": {}}
    combine_kwargs = {"compat": "override", "data_vars": "minimal", "coords": "minimal"}
    # Standard Intake catalog approach for getting dataset
    return model_cat[key](
        xarray_open_kwargs=open_kwargs, xarray_combine_by_coords_kwargs=combine_kwargs
    ).to_dask()


def _load_access_nri_catalog(model_type, filter=True):
    """
    Load ACCESS-NRI data catalog. Private.

    Parameters
    ----------
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).

    Returns
    ----------
    ACCESS-NRI intake catalog
    """

    catalog = intake.cat.access_nri

    if not filter:
        return catalog

    # Filter catalog by model type
    return catalog.search(model=f".*{model_type.upper()}.*")
