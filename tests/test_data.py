import os
from unittest.mock import MagicMock

import pandas as pd
import pytest
from access_nri_intake.aliases import AliasedESMCatalog
from access_nri_intake.source.builders import (
    AccessCm2Builder,
    AccessCm3Builder,
    AccessEsm15Builder,
    AccessEsm16Builder,
    AccessOm2Builder,
    AccessOm3Builder,
    Mom6Builder,
)

# Import the module and the specific builder classes to test matching logic
from med_diagnostics import data


@pytest.mark.parametrize(
    "model_type, expected_builder, expected_kwargs",
    [
        ("cm2", AccessCm2Builder, {"ensemble": False}),
        ("om2", AccessOm2Builder, {}),
        ("cm3", AccessCm3Builder, {"ensemble": False}),
        ("om3", AccessOm3Builder, {}),
        ("esm15", AccessEsm15Builder, {"ensemble": False}),
        ("esm16", AccessEsm16Builder, {"ensemble": False}),
        ("mom6", Mom6Builder, {}),
    ],
)
def test_build_new_catalog_valid_models(
    monkeypatch, model_type, expected_builder, expected_kwargs
):
    """Test that all valid model types map to the correct builders and kwargs."""
    mock_use_datastore = MagicMock(return_value="mock_datastore")
    monkeypatch.setattr(data, "use_datastore", mock_use_datastore)
    monkeypatch.setattr(os, "getcwd", lambda: "/mock/working/dir")

    result = data._build_new_catalog("/mock/model/path", model_type)

    assert result == "mock_datastore"
    mock_use_datastore.assert_called_once_with(
        experiment_dir="/mock/model/path",
        catalog_dir="/mock/working/dir",
        builder=expected_builder,
        datastore_name="live_diagnostics_tmp_catalog",
        description="Temporary catalog for live diagnostics",
        builder_kwargs=expected_kwargs,
    )


def test_build_new_catalog_invalid_model():
    """Test that an invalid model type correctly raises a ValueError."""
    with pytest.raises(ValueError, match="Unsupported model_type: 'invalid'"):
        data._build_new_catalog("/mock/model/path", "invalid")


def test_load_new_catalog(monkeypatch):
    """Test loading the temporary ESM datastore from the current working directory."""
    mock_open_esm = MagicMock(return_value="mock_catalog")
    monkeypatch.setattr(data.intake, "open_esm_datastore", mock_open_esm)
    monkeypatch.setattr(os, "getcwd", lambda: "/mock/working/dir")

    result = data._load_new_catalog()

    assert result == "mock_catalog"
    mock_open_esm.assert_called_once_with(
        "/mock/working/dir/live_diagnostics_tmp_catalog.json",
        columns_with_iterables=["variable"],
    )


@pytest.mark.parametrize("is_aliased", [True, False])
def test_build_data_object(monkeypatch, is_aliased):
    """Test converting standard and aliased ESM datastores into xarray objects."""

    # Setup nested mocks for: model_cat[key](kwargs).to_dask()
    mock_dataset = "mock_xarray_dataset"
    mock_to_dask = MagicMock(return_value=mock_dataset)

    # The callable object returned by dictionary indexing
    mock_callable = MagicMock()
    mock_callable.to_dask = mock_to_dask

    # The dictionary indexing result
    mock_model_cat_dict = MagicMock(return_value=mock_callable)

    # Setup the parent catalog mock
    mock_model_cat = MagicMock()
    mock_model_cat.__getitem__.return_value = mock_model_cat_dict

    # Handle the AliasedESMCatalog unwrap branch
    mock_unwrapped_cat = MagicMock()
    mock_unwrapped_cat.__getitem__.return_value = mock_model_cat_dict
    mock_model_cat.unwrap.return_value = mock_unwrapped_cat

    # Intercept isinstance to simulate whether it's an AliasedESMCatalog
    original_isinstance = isinstance

    def custom_isinstance(obj, classinfo):
        if classinfo is AliasedESMCatalog:
            return is_aliased
        return original_isinstance(obj, classinfo)

    monkeypatch.setattr("builtins.isinstance", custom_isinstance)

    # Execute the function
    result = data._build_data_object(mock_model_cat, "test_key")

    # Assertions
    if is_aliased:
        mock_model_cat.unwrap.assert_called_once()
        mock_unwrapped_cat.__getitem__.assert_called_once_with("test_key")
    else:
        mock_model_cat.unwrap.assert_not_called()
        mock_model_cat.__getitem__.assert_called_once_with("test_key")

    mock_model_cat_dict.assert_called_once_with(
        xarray_open_kwargs={"use_cftime": True, "chunks": {}},
        xarray_combine_by_coords_kwargs={
            "compat": "override",
            "data_vars": "minimal",
            "coords": "minimal",
        },
    )
    mock_callable.to_dask.assert_called_once()
    assert result == mock_dataset


@pytest.mark.parametrize(
    "filter_arg, expected_regex, model_type",
    [
        (False, None, None),
        (True, ".*CM2.*", "CM2"),
        (True, ".*ESM16.*", "ESM16"),
        (True, ".*ESM15.*", "ESM15"),
        (True, ".*CM3.*", "CM3"),
        (True, ".*OM2.*", "OM2"),
        (True, ".*OM3.*", "OM3"),
    ],
)
def test_load_access_nri_catalog(monkeypatch, filter_arg, expected_regex, model_type):
    """Test loading and filtering the ACCESS-NRI intake catalog."""
    mock_access_nri_cat = MagicMock()
    mock_access_nri_cat.search.return_value = "filtered_catalog"

    # Mock intake.cat.access_nri
    mock_cat = MagicMock()
    mock_cat.access_nri = mock_access_nri_cat
    monkeypatch.setattr(data.intake, "cat", mock_cat)

    result = data._load_access_nri_catalog(model_type, filter=filter_arg)

    if filter_arg:
        mock_access_nri_cat.search.assert_called_once_with(model=expected_regex)
        assert result == "filtered_catalog"
    else:
        mock_access_nri_cat.search.assert_not_called()
        assert result == mock_access_nri_cat


def _monthly_df(start_year, n_years):
    """Catalog rows for one file per month, dated like access-nri-intake's builders."""
    dates = [
        f"{year:04d}-{month:02d}-01, 00:00:00"
        for year in range(start_year, start_year + n_years)
        for month in range(1, 13)
    ]
    return pd.DataFrame({"path": range(len(dates)), "start_date": dates})


@pytest.mark.parametrize(
    "years, from_start, expected_years",
    [
        pytest.param(2, False, [2003, 2004], id="most-recent"),
        pytest.param(2, True, [2000, 2001], id="first"),
        pytest.param(50, False, [2000, 2001, 2002, 2003, 2004], id="more-than-run"),
        pytest.param(None, False, [2000, 2001, 2002, 2003, 2004], id="all-years"),
    ],
)
def test_select_year_files(years, from_start, expected_years):
    """Test that only the files starting in the chosen years are kept.

    Loading is slow because every file is opened, so the filter must drop
    whole files by their start year rather than trimming after loading.
    """
    selected = data._select_year_files(_monthly_df(2000, 5), years, from_start)

    selected_years = sorted({int(date[:4]) for date in selected["start_date"]})
    assert selected_years == expected_years
    assert len(selected) == 12 * len(expected_years)


def test_select_year_files_keeps_undated_files():
    """Test that files without a time axis are kept, and all-undated data is unchanged.

    access-nri-intake dates static files (e.g. grid data) as "none", so they
    have no year to filter on and must not be silently dropped.
    """
    df = pd.concat(
        [_monthly_df(2000, 3), pd.DataFrame({"path": [99], "start_date": ["none"]})]
    )

    selected = data._select_year_files(df, 1)

    assert "none" in list(selected["start_date"])
    assert len(selected) == 13
    static = pd.DataFrame({"path": [1, 2], "start_date": ["none", "none"]})
    assert data._select_year_files(static, 1).equals(static)


class _FakeDatastore:
    """Minimal intake-esm datastore holding one dataset made of ``df``'s files.

    Like the real one, it can be rebuilt from ``{"esmcat", "df"}`` (how a
    search makes a subset), and opening it returns the rows it would load.
    """

    def __init__(self, spec):
        self.df = spec["df"]
        self.esmcat = MagicMock()

    def __getitem__(self, key):
        source = MagicMock(df=self.df)
        source.return_value.to_dask.return_value = self.df
        return source


@pytest.mark.parametrize(
    "years, from_start, expected_years",
    [
        (None, False, [2000, 2001, 2002, 2003, 2004]),
        (2, True, [2000, 2001]),
        (2, False, [2003, 2004]),
    ],
    ids=["all-years", "first-2", "last-2"],
)
def test_build_data_object_years(years, from_start, expected_years):
    """Test that only the files in the chosen years are opened.

    Opening files is the slow part of a load, so the catalog must be cut down
    to the chosen years before ``to_dask`` rather than trimmed afterwards.
    """
    catalog = _FakeDatastore({"df": _monthly_df(2000, 5)})

    opened = data._build_data_object(catalog, "key", years, from_start)

    opened_years = sorted({int(date[:4]) for date in opened["start_date"]})
    assert opened_years == expected_years
