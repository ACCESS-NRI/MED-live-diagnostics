import re
from unittest.mock import MagicMock

import intake
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
    monkeypatch.setattr(data, "_catalog_dir", lambda path: "/mock/catalog/dir")

    result = data._build_new_catalog("/mock/model/path", model_type)

    assert result == "mock_datastore"
    mock_use_datastore.assert_called_once_with(
        experiment_dir="/mock/model/path",
        catalog_dir="/mock/catalog/dir",
        builder=expected_builder,
        datastore_name="live_diagnostics_tmp_catalog",
        description="Temporary catalog for live diagnostics",
        builder_kwargs=expected_kwargs,
    )


def test_build_new_catalog_invalid_model():
    """Test that an invalid model type correctly raises a ValueError."""
    with pytest.raises(ValueError, match="Unsupported model_type: 'invalid'"):
        data._build_new_catalog("/mock/model/path", "invalid")


def test_load_new_catalog(monkeypatch, tmp_path):
    """Test loading the temporary ESM datastore from the experiment's catalog folder."""
    mock_open_esm = MagicMock(return_value="mock_catalog")
    monkeypatch.setattr(data.intake, "open_esm_datastore", mock_open_esm)
    monkeypatch.setattr(data, "_catalog_dir", lambda path: tmp_path)

    result = data._load_new_catalog("/mock/model/path")

    assert result == "mock_catalog"
    mock_open_esm.assert_called_once_with(
        tmp_path / "live_diagnostics_tmp_catalog.json",
        columns_with_iterables=["variable"],
    )


def test_catalog_dir(monkeypatch, tmp_path):
    """Test each experiment gets its own catalog folder, even with the same folder name."""
    monkeypatch.setattr(data, "CATALOG_ROOT", tmp_path)

    run_a = data._catalog_dir("/g/data/a/output")
    run_b = data._catalog_dir("/g/data/b/output")

    assert run_a.is_dir() and run_b.is_dir()
    assert run_a.parent == tmp_path
    assert run_a.name.startswith("output_")
    assert run_a != run_b
    assert data._catalog_dir("/g/data/a/output") == run_a


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
    # Indexed twice: once for the file table, once to open the dataset
    if is_aliased:
        mock_model_cat.unwrap.assert_called_once()
        mock_unwrapped_cat.__getitem__.assert_called_with("test_key")
    else:
        mock_model_cat.unwrap.assert_not_called()
        mock_model_cat.__getitem__.assert_called_with("test_key")

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


# Real ACCESS-NRI model names (2026-10-08), including non-ACCESS ones
CATALOG_MODELS = [
    "ACCESS-CM2",
    "ACCESS-ESM1-5",
    "ACCESS-ESM1.6",
    "ACCESS-OM2",
    "ACCESS-OM2-01",
    "ACCESS-OM2-025",
    "ACCESS1-3",
    "CMCC-CM2-SR5",
    "GFDL-CM2p1",
    "GFDL-CM3",
    "HadCM3",
    "MOM6",
    "MRI-CGCM3",
    "TaiESM1-TIMCOM2",
]


class _FakeAccessNriCatalog:
    """Stands in for intake.cat.access_nri, matching search patterns as regexes."""

    def __init__(self, models):
        self.models = models

    def search(self, model):
        return [name for name in self.models if re.search(model, name)]

    def __len__(self):
        return len(self.models)


@pytest.mark.parametrize(
    "model_type, expected_models",
    [
        ("CM2", ["ACCESS-CM2"]),
        ("CM3", ["ACCESS-CM2", "MOM6"]),
        ("ESM15", ["ACCESS-ESM1-5"]),
        ("ESM16", ["ACCESS-ESM1.6"]),
        ("MOM6", ["MOM6"]),
        ("OM2", ["ACCESS-OM2", "ACCESS-OM2-01", "ACCESS-OM2-025"]),
        ("OM3", ["ACCESS-OM2", "ACCESS-OM2-01", "ACCESS-OM2-025", "MOM6"]),
    ],
)
def test_load_access_nri_catalog_finds_only_its_models(
    monkeypatch, model_type, expected_models
):
    """Each model type finds exactly its own ACCESS models in the catalog.

    Guards against substring matches, which missed ESM1-5/ESM1.6 and picked up
    CMCC-CM2-SR5, GFDL-CM3 and TaiESM1-TIMCOM2.
    """
    monkeypatch.setattr(
        data.intake, "cat", MagicMock(access_nri=_FakeAccessNriCatalog(CATALOG_MODELS))
    )

    assert data._load_access_nri_catalog(model_type) == expected_models


def test_every_model_type_has_catalog_names():
    """Every model type that can build a user catalog can also filter the reference catalog."""
    for model_type in ["cm2", "cm3", "esm15", "esm16", "mom6", "om2", "om3"]:
        assert model_type in data.CATALOG_MODEL_NAMES


def test_load_access_nri_catalog_unfiltered(monkeypatch):
    """With filter=False the whole catalog is returned without searching."""
    mock_access_nri_cat = MagicMock()
    monkeypatch.setattr(data.intake, "cat", MagicMock(access_nri=mock_access_nri_cat))

    assert data._load_access_nri_catalog("cm2", filter=False) is mock_access_nri_cat
    mock_access_nri_cat.search.assert_not_called()


def test_load_access_nri_catalog_off_gadi(monkeypatch):
    """Off Gadi the empty placeholder catalog is returned instead of failing to search."""
    placeholder = intake.catalog.Catalog()
    monkeypatch.setattr(data.intake, "cat", MagicMock(access_nri=placeholder))

    assert data._load_access_nri_catalog("om2") is placeholder


def _monthly_df(start_year, n_years):
    """Catalog rows for one file per month, dated like access-nri-intake's builders."""
    dates = [
        f"{year:04d}-{month:02d}-01, 00:00:00"
        for year in range(start_year, start_year + n_years)
        for month in range(1, 13)
    ]
    return pd.DataFrame({"path": range(len(dates)), "start_date": dates})


@pytest.mark.parametrize(
    "start_year, years, from_start, expected_years",
    [
        pytest.param(2000, 2, False, [2003, 2004], id="most-recent"),
        pytest.param(2000, 2, True, [2000, 2001], id="first"),
        pytest.param(101, 2, True, [101, 102], id="first-early-years"),
        pytest.param(1, 200, True, [1, 2, 3, 4, 5], id="from-year-1-more-than-run"),
        pytest.param(
            2000, 50, False, [2000, 2001, 2002, 2003, 2004], id="more-than-run"
        ),
        pytest.param(2000, None, False, [2000, 2001, 2002, 2003, 2004], id="all-years"),
    ],
)
def test_select_year_files(start_year, years, from_start, expected_years):
    """Test that only the files starting in the chosen years are kept.

    Loading is slow because every file is opened, so the filter must drop
    whole files by their start year rather than trimming after loading.
    Runs often start at year 1 or 101, so early years are checked too.
    """
    selected = data._select_year_files(_monthly_df(start_year, 5), years, from_start)

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


@pytest.mark.parametrize("years", [0, -1])
def test_select_year_files_rejects_non_positive_years(years):
    """Test that fewer than 1 year raises a clear error.

    Otherwise nothing is selected and loading fails later with an IndexError.
    """
    with pytest.raises(ValueError, match="at least 1"):
        data._select_year_files(_monthly_df(2000, 5), years)


def test_summarise_year_selection_without_start_date():
    """Test that a catalog with no start_date column still gives file counts.

    Some catalogs have no dates, so the summary must not crash; the UI then
    shows the file count without a year range.
    """
    model_cat = {"ocean.1mon": MagicMock(df=pd.DataFrame({"path": [1, 2, 3]}))}

    summary = data._summarise_year_selection(model_cat, "ocean.1mon", years=2)

    assert summary == {
        "n_files": 3,
        "total_files": 3,
        "first_year": None,
        "last_year": None,
    }


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
def test_build_data_object_years(monkeypatch, years, from_start, expected_years):
    """Test that only the files in the chosen years are opened.

    Opening files is the slow part of a load, so the catalog must be cut down
    to the chosen years before ``to_dask`` rather than trimmed afterwards.
    """
    monkeypatch.setattr(data.os.path, "exists", lambda path: True)
    catalog = _FakeDatastore({"df": _monthly_df(2000, 5)})

    opened = data._build_data_object(catalog, "key", years, from_start)

    opened_years = sorted({int(date[:4]) for date in opened["start_date"]})
    assert opened_years == expected_years


def test_build_data_object_skips_missing_files(tmp_path):
    """Test that catalogued files missing on disk are skipped and counted.

    The ACCESS-NRI catalog can list files that have since been moved or deleted
    (e.g. ESM1.6 piControl), which would otherwise fail the whole load.
    """
    paths = [tmp_path / f"file_{i}.nc" for i in range(4)]
    for path in paths[:3]:
        path.touch()
    df = pd.DataFrame({"path": [str(p) for p in paths], "start_date": ["none"] * 4})

    opened = data._build_data_object(_FakeDatastore({"df": df}), "key")

    assert list(opened["path"]) == [str(p) for p in paths[:3]]
    assert opened.attrs["med_missing_files"] == 1


def test_build_data_object_all_files_missing(tmp_path):
    """Test that a clear error is raised when none of the catalogued files exist."""
    df = pd.DataFrame({"path": [str(tmp_path / "gone.nc")], "start_date": ["none"]})

    with pytest.raises(FileNotFoundError, match="None of the 1 files"):
        data._build_data_object(_FakeDatastore({"df": df}), "key")
