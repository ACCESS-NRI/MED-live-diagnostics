import os
from unittest.mock import MagicMock

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


def test_start_dask_cluster(monkeypatch):
    """Test that the local Dask cluster starts and returns the dashboard link."""
    # Create mock instances to traverse distributed.Client().dashboard_link
    mock_client_instance = MagicMock()
    mock_client_instance.dashboard_link = "http://mock-dashboard:8787"
    mock_client_class = MagicMock(return_value=mock_client_instance)

    # Patch the Client inside the distributed module, which is imported locally in the function
    monkeypatch.setattr("distributed.Client", mock_client_class)

    result = data._start_dask_cluster()

    assert result == "http://mock-dashboard:8787"
    mock_client_class.assert_called_once_with(threads_per_worker=1)


@pytest.mark.parametrize("is_aliased", [True, False])
def test_build_data_object(monkeypatch, is_aliased):
    """Test converting standard and aliased ESM datastores into xarray objects."""

    # 1. Setup nested mocks for: model_cat[key](kwargs).to_dask()
    mock_dataset = "mock_xarray_dataset"
    mock_to_dask = MagicMock(return_value=mock_dataset)

    # The callable object returned by dictionary indexing
    mock_callable = MagicMock()
    mock_callable.to_dask = mock_to_dask

    # The dictionary indexing result
    mock_model_cat_dict = MagicMock(return_value=mock_callable)

    # 2. Setup the parent catalog mock
    mock_model_cat = MagicMock()
    mock_model_cat.__getitem__.return_value = mock_model_cat_dict

    # 3. Handle the AliasedESMCatalog unwrap branch
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

    # 4. Execute the function
    result = data._build_data_object(mock_model_cat, "test_key")

    # 5. Assertions
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
    "filter_arg, expected_regex",
    [
        (False, None),
        (True, ".*CM2.*"),
    ],
)
def test_load_access_nri_catalog(monkeypatch, filter_arg, expected_regex):
    """Test loading and filtering the ACCESS-NRI intake catalog."""
    mock_access_nri_cat = MagicMock()
    mock_access_nri_cat.search.return_value = "filtered_catalog"

    # Mock intake.cat.access_nri
    mock_cat = MagicMock()
    mock_cat.access_nri = mock_access_nri_cat
    monkeypatch.setattr(data.intake, "cat", mock_cat)

    result = data._load_access_nri_catalog("cm2", filter=filter_arg)

    if filter_arg:
        mock_access_nri_cat.search.assert_called_once_with(model=expected_regex)
        assert result == "filtered_catalog"
    else:
        mock_access_nri_cat.search.assert_not_called()
        assert result == mock_access_nri_cat
