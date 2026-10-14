from typing import Annotated
from unittest.mock import MagicMock

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from med_diagnostics import analysis, api
from med_diagnostics.types import Heatmap, Line


@pytest.fixture(autouse=True)
def empty_uploads(monkeypatch):
    """Give each test its own empty recipe registry."""
    monkeypatch.setattr(analysis, "REGISTERED_ANALYSES", {})


@pytest.fixture(autouse=True)
def close_figures():
    """Close figures each test makes."""
    yield
    plt.close("all")


def make_dataset(start="2000-01-01", periods=4, member=False):
    """Small ocean-like dataset with time, depth, lat and lon."""
    dims = ["time", "st_ocean", "yt_ocean", "xt_ocean"]
    coords = {
        "time": pd.date_range(start, periods=periods, freq="MS"),
        "st_ocean": [5.0, 50.0],
        "yt_ocean": [-10.0, 0.0, 10.0],
        "xt_ocean": [100.0, 150.0, 200.0],
    }
    if member:
        dims.insert(0, "member")
        coords["member"] = ["r1", "r2"]
    shape = [len(coords[d]) for d in dims]
    temp = xr.DataArray(
        np.arange(np.prod(shape), dtype=float).reshape(shape), dims=dims
    )
    return xr.Dataset({"temp": temp}, coords=coords)


# Catalogs


def test_build_catalog(monkeypatch, tmp_path):
    """Test the path is expanded and the model type lowercased."""
    mock_build = MagicMock(return_value="mock_cat")
    monkeypatch.setattr(api.data, "_build_new_catalog", mock_build)
    monkeypatch.setenv("HOME", str(tmp_path))

    assert api.build_catalog("~", "OM2") == "mock_cat"
    mock_build.assert_called_once_with(str(tmp_path), "om2")


@pytest.mark.parametrize("model_path", ["", "/no/such/path"])
def test_build_catalog_bad_path(monkeypatch, model_path):
    """Test bad paths raise a ValueError without the UI prefix, and nothing is built."""
    mock_build = MagicMock()
    monkeypatch.setattr(api.data, "_build_new_catalog", mock_build)

    with pytest.raises(ValueError) as err:
        api.build_catalog(model_path, "om2")

    assert not str(err.value).startswith("Warning >>")
    mock_build.assert_not_called()


def test_load_reference_catalog(monkeypatch):
    """Test the model type and filter are passed through."""
    mock_load = MagicMock(return_value="mock_ref_cat")
    monkeypatch.setattr(api.data, "_load_access_nri_catalog", mock_load)

    assert api.load_reference_catalog("OM2", filter=False) == "mock_ref_cat"
    mock_load.assert_called_once_with(model_type="OM2", filter=False)


def test_list_datasets():
    """Test catalog keys are returned as a list."""
    assert api.list_datasets({"a": 1, "b": 2}) == ["a", "b"]


def test_load_dataset(monkeypatch):
    """Test the year selection is passed through."""
    mock_build = MagicMock(return_value="mock_ds")
    monkeypatch.setattr(api.data, "_build_data_object", mock_build)

    assert api.load_dataset("cat", "key", years=3, from_start=True) == "mock_ds"
    mock_build.assert_called_once_with("cat", "key", years=3, from_start=True)


def test_reference_metadata():
    """Test the model's metadata is returned."""
    ref_cat = {"model": MagicMock(metadata={"description": "A model"})}

    assert api.reference_metadata(ref_cat, "model") == {"description": "A model"}


# Single-dataset plots


def test_plot_data_line_fills_slices(monkeypatch):
    """Test a line plot slices every other dimension at its first value."""
    mock_plot = MagicMock(return_value="fig")
    monkeypatch.setattr(api.controller, "plot_dataset", mock_plot)
    ds = make_dataset()
    slices = {"st_ocean": 50.0}
    assert api.plot_data(ds, "temp", "time", slices=slices) == "fig"

    args, kwargs = mock_plot.call_args
    assert args[4] == {"st_ocean": 50.0, "yt_ocean": -10.0, "xt_ocean": 100.0}
    assert args[5] is False
    assert kwargs["model_name"] == "User"
    assert isinstance(kwargs["plot_type"], Line)
    assert slices == {"st_ocean": 50.0}


def test_plot_data_heatmap_reference(monkeypatch):
    """Test a heatmap is chosen by y_axis, and model_name marks it as a reference."""
    mock_plot = MagicMock()
    monkeypatch.setattr(api.controller, "plot_dataset", mock_plot)

    api.plot_data(
        make_dataset(), "temp", "xt_ocean", y_axis="yt_ocean", model_name="OM2"
    )

    args, kwargs = mock_plot.call_args
    assert set(args[4]) == {"time", "st_ocean"}
    assert args[5] is True
    assert kwargs["model_name"] == "OM2"
    assert isinstance(kwargs["plot_type"], Heatmap)
    assert kwargs["y_axis"] == "yt_ocean"


@pytest.mark.parametrize("y_axis, member_sliced", [(None, False), ("yt_ocean", True)])
def test_plot_data_member(monkeypatch, y_axis, member_sliced):
    """Test member is left for line plots, which draw each one, but sliced for heatmaps."""
    mock_plot = MagicMock()
    monkeypatch.setattr(api.controller, "plot_dataset", mock_plot)

    api.plot_data(make_dataset(member=True), "temp", "xt_ocean", y_axis=y_axis)

    assert ("member" in mock_plot.call_args.args[4]) is member_sliced


def test_plot_data_animation(monkeypatch):
    """Test animate_over gives an animation over that dimension."""
    mock_animate = MagicMock(return_value="anim")
    monkeypatch.setattr(api.controller, "plot_animation", mock_animate)

    result = api.plot_data(
        make_dataset(), "temp", "xt_ocean", y_axis="yt_ocean", animate_over="time"
    )

    assert result == "anim"
    args, kwargs = mock_animate.call_args
    assert args[3] == {"st_ocean": 5.0}
    assert args[4:] == ("xt_ocean", "yt_ocean", "time")
    assert kwargs["is_ref"] is False


def test_plot_data_animation_needs_y_axis():
    """Test an animation without a y_axis raises a ValueError."""
    with pytest.raises(ValueError, match="y_axis"):
        api.plot_data(make_dataset(), "temp", "xt_ocean", animate_over="time")


@pytest.mark.parametrize("y_axis", [None, "yt_ocean"])
def test_plot_data_returns_figure(y_axis):
    """Test real line plots and heatmaps are drawn."""
    x_axis = "xt_ocean" if y_axis else "time"

    fig = api.plot_data(make_dataset(), "temp", x_axis, y_axis=y_axis)

    assert isinstance(fig, plt.Figure)


# Overlays


@pytest.fixture
def mock_build_data_object(monkeypatch):
    """Load a fixed reference dataset in place of reading a catalog."""
    mock_build = MagicMock(return_value=make_dataset())
    monkeypatch.setattr(api.controller.data, "_build_data_object", mock_build)
    return mock_build


def test_add_reference_new_dict(mock_build_data_object):
    """Test leaving out references starts a new dict."""
    refs = api.add_reference("OM2", "ref_cat", "key", make_dataset())

    assert list(refs) == ["OM2"]
    mock_build_data_object.assert_called_once_with("ref_cat", "key")


def test_add_reference_existing_dict(mock_build_data_object):
    """Test a new reference is added to the dict passed in."""
    refs = {"first": make_dataset()}

    result = api.add_reference("second", "ref_cat", "key", make_dataset(), refs)

    assert result is refs
    assert list(refs) == ["first", "second"]


def test_add_reference_default_not_shared(mock_build_data_object):
    """Test separate calls without references don't share a dict."""
    first = api.add_reference("a", "ref_cat", "key", make_dataset())
    second = api.add_reference("b", "ref_cat", "key", make_dataset())

    assert list(first) == ["a"]
    assert list(second) == ["b"]


@pytest.mark.parametrize(
    "constrain_to_user, expected",
    [(False, ("1999-01-01", "2000-04-01")), (True, ("2000-01-01", "2000-04-01"))],
)
def test_plot_overlay_line_bounds(monkeypatch, constrain_to_user, expected):
    """Test the x-axis spans every dataset, or only the user data if constrained."""
    mock_plot = MagicMock(return_value="fig")
    monkeypatch.setattr(api.controller, "plot_multiplot_dataset", mock_plot)
    refs = {"ref": make_dataset(start="1999-01-01")}

    result = api.plot_overlay(
        make_dataset(), "temp", refs, "time", constrain_to_user=constrain_to_user
    )

    assert result == "fig"
    args, kwargs = mock_plot.call_args
    assert args[3] == {"st_ocean": 5.0, "yt_ocean": -10.0, "xt_ocean": 100.0}
    assert (args[5], args[6]) == tuple(np.datetime64(d) for d in expected)
    assert kwargs["plot_diff"] is False


def test_plot_overlay_heatmap(monkeypatch):
    """Test y_axis gives the heatmap grid, leaving member for it to handle."""
    mock_plot = MagicMock(return_value="fig")
    monkeypatch.setattr(api.controller, "plot_multiplot_heatmap_dataset", mock_plot)
    refs = {"ref": make_dataset()}

    api.plot_overlay(
        make_dataset(member=True),
        "temp",
        refs,
        "xt_ocean",
        y_axis="yt_ocean",
        difference=True,
    )

    args, kwargs = mock_plot.call_args
    assert set(args[3]) == {"time", "st_ocean"}
    assert args[4:] == ("xt_ocean", "yt_ocean")
    assert kwargs["plot_diff"] is True


def test_plot_overlay_difference_needs_reference():
    """Test a difference plot with no references raises a ValueError."""
    with pytest.raises(ValueError, match="reference"):
        api.plot_overlay(make_dataset(), "temp", {}, "time", difference=True)


@pytest.mark.parametrize("y_axis", [None, "yt_ocean"])
def test_plot_overlay_returns_figure(y_axis):
    """Test real overlay line plots and heatmaps are drawn."""
    x_axis = "xt_ocean" if y_axis else "time"
    refs = {"ref": make_dataset()}

    fig = api.plot_overlay(make_dataset(), "temp", refs, x_axis, y_axis=y_axis)

    assert isinstance(fig, plt.Figure)


# Analysis


def recipe_api_mean(
    ds,
    variable: Annotated[
        str, {"kind": "data variable", "description": "Variable to average"}
    ] = "temp",
):
    """API test mean."""
    da = ds[variable]
    return da.mean([d for d in da.dims if d != "time"])


def test_register_analysis_is_reexported():
    """Test register_analysis is the analysis module's function."""
    assert api.register_analysis is analysis.register_analysis


def test_list_recipes_includes_registered():
    """Test registered recipes are listed with a Custom label."""
    api.register_analysis(recipe_api_mean)

    assert api.list_recipes()["Custom: API test mean."] is recipe_api_mean


@pytest.mark.parametrize("recipe", [recipe_api_mean, "Custom: API test mean."])
def test_recipe_options(recipe):
    """Test options are found from the function or its label."""
    api.register_analysis(recipe_api_mean)

    (option,) = api.recipe_options(recipe, make_dataset())

    assert option["name"] == "variable"
    assert option["choices"] == ["temp"]


@pytest.mark.parametrize("recipe", [recipe_api_mean, "Custom: API test mean."])
def test_run_recipe(recipe):
    """Test a recipe runs from the function or its label, giving one figure."""
    api.register_analysis(recipe_api_mean)

    figs = api.run_recipe(make_dataset(), recipe, variable="temp")

    assert len(figs) == 1
    assert isinstance(figs[0], plt.Figure)


def test_run_recipe_unknown_label():
    """Test an unknown label raises a ValueError listing the recipes."""
    with pytest.raises(ValueError, match="No recipe labelled 'nope'"):
        api.run_recipe(make_dataset(), "nope")
