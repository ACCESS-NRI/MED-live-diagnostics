from typing import Annotated
from unittest.mock import MagicMock

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from med_diagnostics import analysis


@pytest.fixture(autouse=True)
def empty_uploads(monkeypatch):
    """Give each test its own empty upload registry."""
    monkeypatch.setattr(analysis, "REGISTERED_ANALYSES", {})


def my_mean(
    ds,
    variable: Annotated[
        str, {"kind": "data variable", "description": "Variable to average"}
    ] = "o2",
):
    """
    Mean of a variable.

    A description
    """
    return ds[variable].mean()


def recipe_summary_test_recipe(
    ds,
    variable: Annotated[
        str, {"kind": "data variable", "description": "Variable to average"}
    ] = "o2",
):
    """
    Mean of a variable.

    Parameters as the first word of the second paragraph of the docstring.
    """
    return ds[variable].mean()


def test_register_analysis_registers_by_name():
    """Test that an uploaded function is stored by name and listed for the UI.

    Returning the function unchanged lets ``register_analysis`` also be used as
    a decorator without replacing the user's function with None.
    """
    assert analysis.register_analysis(my_mean) is my_mean
    assert {"my_mean": my_mean} == analysis.REGISTERED_ANALYSES
    assert analysis._list_recipes()["Custom: Mean of a variable."] is my_mean


def test_reuploading_replaces_the_old_version():
    """Test that editing and re-uploading a function doesn't duplicate it.

    The notebook workflow is edit, re-run the cell, re-upload, so the
    registry must hold only the latest version under each name.
    """
    analysis.register_analysis(my_mean)

    def edited(ds):
        """New version."""

    edited.__name__ = "my_mean"  # as if the notebook cell were edited and re-run
    analysis.register_analysis(edited)
    assert {"my_mean": edited} == analysis.REGISTERED_ANALYSES
    labels = analysis._list_recipes()
    assert "Custom: New version." in labels
    assert not any(label.startswith("Custom: Mean of a variable.") for label in labels)


def test_recipes_with_the_same_summary_get_distinct_labels():
    """Test that two different recipes with the same summary both appear in the dropdown."""

    def other_mean(ds):
        """Mean of a variable."""

    analysis.register_analysis(my_mean)
    analysis.register_analysis(other_mean)
    labels = analysis._list_recipes()
    assert labels["Custom: Mean of a variable."] is my_mean
    assert labels["Custom: Mean of a variable. (other_mean)"] is other_mean


@pytest.mark.parametrize(
    "bad_func, error",
    [
        pytest.param("not a function", TypeError, id="not-callable"),
        pytest.param(lambda: None, TypeError, id="no-dataset-argument"),
    ],
)
def test_register_analysis_rejects_bad_functions(bad_func, error):
    """Test that unusable functions fail at upload, not later in the UI.

    A function that can't take the dataset would otherwise only fail once the
    user picks it in the UI.
    """
    with pytest.raises(error):
        analysis.register_analysis(bad_func)
    assert analysis.REGISTERED_ANALYSES == {}


def test_register_analysis_raises_error_bad_annotation():
    """Test that metadata that isn't a dict fails at upload, saying what's wrong."""

    def bad_annotation(ds, depth: Annotated[str, "data variable"] = "st_depth"):
        """A title."""

    with pytest.raises(TypeError, match="parameter 'depth'.*must be a dict"):
        analysis.register_analysis(bad_annotation)
    assert analysis.REGISTERED_ANALYSES == {}


def test_register_analysis_rejects_misspelt_metadata_keys():
    """Test that a misspelt metadata key fails at upload and suggests the fix.

    Otherwise the key is silently ignored, e.g. a misspelt ``kind`` gives a
    text box instead of a dropdown.
    """

    def misspelt(ds, var: Annotated[str, {"knid": "data variable"}] = "temp"):
        """A title."""

    with pytest.raises(
        ValueError, match="unknown metadata key 'knid'. Did you mean 'kind'"
    ):
        analysis.register_analysis(misspelt)
    assert analysis.REGISTERED_ANALYSES == {}


def test_register_analysis_accepts_unannotated_parameters():
    """Test that parameters without ``Annotated`` metadata don't block an upload.

    Kind validation was dropped on purpose: an unannotated parameter becomes
    a text box in the UI, and whether that suits the recipe is on the user.
    """

    def plain(ds, depth=0):
        """Plain recipe."""

    assert analysis.register_analysis(plain) is plain
    assert {"plain": plain} == analysis.REGISTERED_ANALYSES


def test_get_recipe_summary_regular():
    """Test that the recipe summary is extracted from the docstring."""

    summary, details = analysis._get_recipe_summary(my_mean)
    assert summary == "Mean of a variable."
    assert details == "A description"


def test_get_recipe_summary_parameters():
    """Test that the recipe summary is extracted from the docstring, test that parameters are not included if in the second paragraph of the docstring."""

    summary, details = analysis._get_recipe_summary(recipe_summary_test_recipe)

    assert summary == "Mean of a variable."
    assert details == ""


def random_plot_customisation(ax, data):
    """A mock plot customisation function for testing."""
    ax.set_title("Customised Plot")


def another_random_plot_customisation(ax, data):
    """A mock plot customisation function for testing."""
    ax.set_title("Another Customisation")


def test_plot_result():
    """Test that the plot result is customised by the provided functions."""
    time = np.arange(10)
    da = xr.DataArray(np.random.rand(10), dims="time", coords={"time": time}, name="o2")

    fig = analysis._plot_result(
        (
            da,
            {
                "customise": [
                    random_plot_customisation,
                    another_random_plot_customisation,
                ]
            },
        )
    )

    assert fig.axes[0].get_title() == "Another Customisation"
    plt.close(fig)

    fig = analysis._plot_result((da, {"customise": random_plot_customisation}))
    assert fig.axes[0].get_title() == "Customised Plot"
    plt.close(fig)


@pytest.mark.parametrize(
    "catalog", [None, "user_catalog"], ids=["no-catalog", "catalog"]
)
def test_analyse_and_plot_adds_missing_cell_areas_from_catalog(monkeypatch, catalog):
    """Test that the recipe gets the dataset with missing cell areas added, only when a catalog is given.

    Recipes only receive the dataset, so they can't fetch ``areacello`` themselves.
    """
    loaded = xr.Dataset({"zos": ("time", [0.0, 1.0])})
    with_area = loaded.assign_coords(areacello=1.0)
    add_areas = MagicMock(return_value=with_area)
    monkeypatch.setattr(analysis, "_add_cell_area", add_areas)
    seen = []

    analysis._analyse_and_plot(
        loaded, lambda ds: seen.append(ds) or ds["zos"], catalog=catalog
    )

    if catalog is None:
        add_areas.assert_not_called()
        assert seen[0] is loaded
    else:
        assert add_areas.call_args.args[0] == catalog
        assert seen[0] is with_area
    plt.close("all")


AREA = [[1.0, 3.0], [2.0, 2.0]]


def _grid_catalog(tmp_path, name="areacello", dims=("yh", "xh")):
    """Mock catalog whose search finds one grid file holding ``name``, with MOM6's size-1 time dim."""
    path = tmp_path / "grid.nc"
    xr.Dataset({name: (("time", *dims), [AREA])}).to_netcdf(path)
    catalog = MagicMock()
    catalog.search.return_value.df = pd.DataFrame({"path": [str(path)]})
    return catalog


def _gridded(cell_measures="area: areacello", dims=("time", "yh", "xh")):
    """2D monthly field naming its area in ``cell_measures`` without including it."""
    return xr.Dataset(
        {"zos": (dims, np.zeros((3, 2, 2)), {"cell_measures": cell_measures})}
    )


@pytest.mark.parametrize(
    "name, grid_file, dims",
    [
        pytest.param("areacello", ".*mom6.static.nc", ("yh", "xh"), id="mom6"),
        pytest.param("area_t", ".*ocean_grid.nc", ("yt_ocean", "xt_ocean"), id="mom5"),
    ],
)
def test_add_cell_area_loads_area_from_grid_file(tmp_path, name, grid_file, dims):
    """Test that the area named in ``cell_measures`` is loaded from the model's grid file, as a coordinate.

    As a coordinate it doesn't show up as a variable to plot.
    """
    catalog = _grid_catalog(tmp_path, name, dims)
    ds = _gridded(f"area: {name}", ("time", *dims))

    ds = analysis._add_cell_area(catalog, ds)

    np.testing.assert_allclose(ds[name], AREA)
    assert name not in ds.data_vars
    catalog.search.assert_called_once_with(filename=grid_file)


@pytest.mark.parametrize(
    "cell_measures",
    [pytest.param("", id="none-named"), pytest.param("area: zos", id="present")],
)
def test_add_cell_area_only_searches_for_missing_areas(tmp_path, cell_measures):
    """Test that no grid file is searched for unless the data names an area it lacks, e.g. scalar data."""
    catalog = _grid_catalog(tmp_path)

    analysis._add_cell_area(catalog, _gridded(cell_measures))

    catalog.search.assert_not_called()


def test_add_cell_area_skips_area_on_another_grid(tmp_path):
    """Test that an area that doesn't fit the dataset's grid isn't added."""
    catalog = _grid_catalog(tmp_path, dims=("yq", "xq"))

    ds = analysis._add_cell_area(catalog, _gridded())

    assert "areacello" not in ds


def test_add_cell_area_without_grid_file_leaves_dataset():
    """Test that a catalog with no grid file leaves the dataset as is, so the recipe can warn."""
    catalog = MagicMock()
    catalog.search.return_value.df = pd.DataFrame({"path": []})

    ds = analysis._add_cell_area(catalog, _gridded())

    assert "areacello" not in ds
