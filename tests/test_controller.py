from access_nri_intake import data


from med_diagnostics.ui import UserInterface
import med_diagnostics.controller as controller
import med_diagnostics.data as med_data
import pytest
import xarray as xr
import numpy as np
import panel as pn
import matplotlib.pyplot as plt
import cftime
from unittest.mock import MagicMock, patch
import datetime

@pytest.fixture(scope="function")
def ui():
    """Return a session-scoped UserInterface instance for testing"""

    ui = UserInterface()
    # Initialise the user interface widget container to prepare it for test execution
    ui.widget_container = pn.Column()
    return ui


@pytest.mark.parametrize(
    "input_text",
    [ "A word", 1, 1.0, True
    ],
)
def test_update_textbox_text(input_text):
    """Test updating any textbox with an entered value"""

    widget = pn.widgets.StaticText(value="something")
    controller.update_textbox_text(widget, input_text)

    # Verify that the status textbox value matches the updated text
    assert widget.value == str(input_text)

@pytest.mark.parametrize(
    "input_value, expected_output",
    [
        (3.14159, "3.14"),
        (42, "42.0"),
        ("2.71828", "2.72"),
        ("not a number", "not a number"),
        ([1, 2], "[1, 2]"),
    ],
)
def test_round_slice_val(input_value, expected_output):
    """Test the _round_slice_val method across various input types and formats"""

    # Verify that the returned string representation matches the expected format
    assert controller.round_slice_val(input_value) == expected_output


@patch("med_diagnostics.controller.datetime")
def test_get_current_time(mock_datetime):
    # Create a static datetime object
    frozen_time = datetime.datetime(2026, 9, 9, 14, 47, 14)

    # tell the mock to return our frozen time whenever .now() is called
    mock_datetime.datetime.now.return_value = frozen_time

    # Call the function (it will use the mocked .now())
    result = controller.get_current_time()

    # Assert against the exact string we expect
    assert result == "2026-09-09 14:47:14"


@pytest.mark.parametrize(
    "is_ref",
    [
        True,
        False
    ],
)
def test_plot_dataset(is_ref):
    """Test the generation of 1D line plots and 2D heatmaps from a provided dataset"""

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    chosen_slices = {"z": 1}

    # Generate a 1D plot and verify a valid matplotlib Figure is returned with content
    plot_result = controller.plot_dataset(
        ds,
        "dataset_name",
        "data",
        "x",
        chosen_slices,
        is_ref
    )
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0

    """
    # Generate a 2D heatmap and verify a valid matplotlib Figure is returned with content
    plot_result = ui._plot_heatmap("data", "x", "y")
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0
    """


@pytest.mark.parametrize(
    "toggle_value",
    [True, False],
)
def test_variable_toggle_change(toggle_value):
    """Test updating the multiplot variable dropdown options based on the multiplot variable toggle state"""

    # Create a 2D xarray dataset with a long_name attribute and assign it to the UI instance
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
        attrs={"long_name": "long name"},
    )
    ds = xr.Dataset({"data": data})
    toggle_widget = pn.widgets.Toggle(value = toggle_value)
    variable_dropdown_widget = pn.widgets.Select()
    if toggle_value:
        variable_dropdown_widget.options = ["data"]
    else:  
        variable_dropdown_widget.options = ["long name"]

    controller.variable_toggle_change(toggle_widget, variable_dropdown_widget, ds)
    if toggle_value:
        assert variable_dropdown_widget.options == ["long name"]
        assert toggle_widget.label == "Display Variable Short Names"
    else:  
        assert variable_dropdown_widget.options == ["data"]
        assert toggle_widget.label == "Display Variable Long Names"


@pytest.mark.parametrize(
    "toggle_value, long_names",
    [
        (True, {"long name": "data"}), 
        (False, {"long name": "data"}), 
        (True, {}), 
        (False, {})
     ],
)
def test_get_selected_variable(toggle_value, long_names):

    toggle_widget = pn.widgets.Toggle(value=toggle_value)
    variable_dropdown_widget = pn.widgets.Select()
    if toggle_value:
        variable_dropdown_widget.options = ["long name"]
        variable_dropdown_widget.value = "long name"
    else:
        variable_dropdown_widget.options = ["data"]
        variable_dropdown_widget.value = "data"

    result = controller.get_selected_variable(toggle_widget, variable_dropdown_widget, long_names)

    if toggle_value and long_names:
        assert result == long_names[variable_dropdown_widget.value]
    else:
        assert result == variable_dropdown_widget.value


@pytest.mark.parametrize(
    "is_ref",
    [True, False],
)
def test_plot_animation(monkeypatch, is_ref):
    """Test generating an animated quadmesh plot using hvplot with sliced dimensions"""

    # Mock hvplot on the xarray DataArray to intercept plotting calls during testing
    mock_hvplot = MagicMock()
    monkeypatch.setattr(xr.DataArray, "hvplot", property(lambda self: mock_hvplot))

    # Create a 4D xarray DataArray with spatial, vertical, and temporal dimensions
    data = xr.DataArray(
        np.random.rand(10, 10, 10, 10),
        dims=["x", "y", "z", "time"],
        coords={
            "x": np.arange(10),
            "y": np.arange(10),
            "z": np.arange(10),
            "time": np.arange(10),
        },
    )

    ds = xr.Dataset({"data": data})
    chosen_slices = {"z": 1}

    # Execute the animation plotting method
    panel_returned = controller.plot_animation(ds, "dataset_name", "data", chosen_slices, "x", "y", "z", is_ref = is_ref)

    # Verify that quadmesh is called on hvplot and a panel Column container is returned
    mock_hvplot.quadmesh.assert_called_once()
    assert isinstance(panel_returned, pn.Column)


@pytest.mark.parametrize(
    "ref_min_val, ref_max_val, expected_triggered",
    [
        (2, 8, False),
        (0, 10, False),
        (-5, 8, True),
        (2, 15, True),
        (-2, 12, True),
    ],
)
def test_multiplot_check_bounds_numeric(ref_min_val, ref_max_val, expected_triggered):
    """Test numeric coordinate bounds checking across primary and reference datasets in multiplots"""

    # Create a primary dataset with fixed coordinate bounds from 0 to 10
    ds_primary = xr.Dataset({"data": (["x"], [1, 2])}, coords={"x": [0, 10]})

    # Create a reference dataset with coordinate bounds based on parameters
    ds_ref = xr.Dataset({"data": (["x"], [3, 4])}, coords={"x": [ref_min_val, ref_max_val]})
    ref_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result, global_min, global_max, dataset_min, dataset_max = controller.check_bounds(ds_primary, "x", ref_dict)

    assert result == expected_triggered

    expected_global_min = min(0, ref_min_val)
    expected_global_max = max(10, ref_max_val)

    # Verify that the global minimum and maximum bounds are calculated correctly across datasets
    assert global_min == expected_global_min
    assert global_max == expected_global_max


@pytest.mark.parametrize(
    "ref_start, ref_end, expected_triggered",
    [
        ((2000, 2, 1), (2000, 11, 30), False),
        ((1999, 12, 1), (2000, 11, 30), True),
        ((2000, 2, 1), (2001, 1, 1), True),
    ],
)
def test_multiplot_check_bounds_calendar(ref_start, ref_end, expected_triggered):
    """Test calendar coordinate bounds checking across primary and reference datasets in multiplots"""

    # Create a primary dataset using NoLeap calendar bounds from Jan 1 2000 to Dec 31 2000
    primary_times = [
        cftime.DatetimeNoLeap(2000, 1, 1),
        cftime.DatetimeNoLeap(2000, 12, 31),
    ]
    ds_primary = xr.Dataset({"data": (["time"], [1, 2])}, coords={"time": primary_times})

    # Create a reference dataset using Gregorian calendar bounds based on parameters
    ref_times = [
        cftime.DatetimeGregorian(*ref_start),
        cftime.DatetimeGregorian(*ref_end),
    ]
    ds_ref = xr.Dataset({"data": (["time"], [3, 4])}, coords={"time": ref_times})
    ref_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result, global_min, global_max, dataset_min, dataset_max = controller.check_bounds(ds_primary, "time", ref_dict)

    assert result == expected_triggered
