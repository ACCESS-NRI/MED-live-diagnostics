# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

from access_nri_intake import data

from med_diagnostics.ui import UserInterface
import med_diagnostics.data as med_data
import pytest
import xarray as xr
import numpy as np
import panel as pn
import matplotlib.pyplot as plt
import cftime
from unittest.mock import MagicMock, patch

@pytest.fixture(scope="session")
def ui():
    """Return a session-scoped UserInterface instance for testing""" 

    ui = UserInterface()
    # Initialise the user interface widget container to prepare it for test execution
    ui.widget_container = pn.Column() 
    return ui


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
def test_round_slice_val(ui, input_value, expected_output):
    """Test the _round_slice_val method across various input types and formats""" 

    # Verify that the returned string representation matches the expected format
    assert ui._round_slice_val(input_value) == expected_output


def run_validity_check(ui, is_ref, x_value, y_value, z_value, plot_type, var, ds):
    """Check the validity of reference or user plots based on current UI selections"""

    # Assign to correct UI attributes based on whether it is the reference data functions or user data
    if is_ref:
        ui.ref_dataset = ds
        ui.ref_x_axis_dropdown.value = x_value
        ui.ref_y_axis_dropdown.value = y_value
        ui.ref_animation_axis_dropdown.value = z_value
        ui.ref_plot_type_dropdown.value = plot_type
        ui.ref_plot_variable_dropdown.value = var
        return ui._ref_check_plot_validity()
    else:
        ui.dataset = ds
        ui.x_axis_dropdown.value = x_value
        ui.y_axis_dropdown.value = y_value
        ui.animation_axis_dropdown.value = z_value
        ui.plot_type_dropdown.value = plot_type
        ui.plot_variable_dropdown.value = var
        return ui._check_plot_validity()


@pytest.mark.parametrize("is_ref", [False, True])
@pytest.mark.parametrize(
    "x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output",
    [
        ("x", "", "", "line", "data", True, False, False, False),
        ("x", "", "", "Heatmap", "data", False, False, True, False),
        ("x", "", "", "Animation", "data", False, False, True, False),
        ("x", "y", "", "line", "data", True, False, False, False),
        ("x", "y", "z", "line", "data", True, False, False, False),
        ("x", "x", "z", "line", "data", True, False, False, False),
        ("", "", "", "line", "data", False, False, False, False),
    ],
)
def test_check_plot_validity_1d(
    ui,
    is_ref,
    x_value,
    y_value,
    z_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    invalid_heatmap_output,
    same_axes_output,
):
    """Test plot validity and configuration flags for 1D datasets across various axes and plot types""" 

    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})

    results = run_validity_check(
        ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds
    )
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (
        plot_valid_output,
        requires_slice_output,
        invalid_heatmap_output,
        same_axes_output,
    )


@pytest.mark.parametrize("is_ref", [False, True])
@pytest.mark.parametrize(
    "x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output",
    [
        ("x", "", "", "line", "data", False, True, False, False),
        ("x", "", "", "Heatmap", "data", False, True, True, False),
        ("x", "", "", "Animation", "data", False, True, True, False),
        ("x", "y", "", "Heatmap", "data", True, False, False, False),
        ("x", "y", "z", "Heatmap", "data", True, False, False, False),
        ("x", "y", "", "line", "data", False, True, False, False),
        ("x", "y", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "Heatmap", "data", False, True, False, True),
        ("", "", "", "line", "data", False, False, False, False),
    ],
)
def test_check_plot_validity_2d(
    ui,
    is_ref,
    x_value,
    y_value,
    z_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    invalid_heatmap_output,
    same_axes_output,
):
    """Test plot validity and configuration flags for 2D datasets across various axes and plot types""" 

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})

    results = run_validity_check(
        ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds
    )
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (
        plot_valid_output,
        requires_slice_output,
        invalid_heatmap_output,
        same_axes_output,
    )


@pytest.mark.parametrize("is_ref", [False, True])
@pytest.mark.parametrize(
    "x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output",
    [
        ("x", "", "", "line", "data", False, True, False, False),
        ("x", "", "", "Heatmap", "data", False, True, True, False),
        ("x", "", "", "Animation", "data", False, True, True, False),
        ("x", "y", "", "Animation", "data", False, True, True, False),
        ("x", "x", "x", "Animation", "data", False, True, False, True),
        ("x", "z", "z", "Animation", "data", False, True, False, True),
        ("x", "x", "z", "Animation", "data", False, True, False, True),
        ("x", "y", "z", "Animation", "data", True, False, False, False),
        ("x", "y", "", "Heatmap", "data", False, True, False, False),
        ("x", "y", "z", "Heatmap", "data", False, True, False, False),
        ("x", "y", "", "line", "data", False, True, False, False),
        ("x", "y", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "Heatmap", "data", False, True, False, True),
        ("", "", "", "line", "data", False, False, False, False),
    ],
)
def test_check_plot_validity_3d(
    ui,
    is_ref,
    x_value,
    y_value,
    z_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    invalid_heatmap_output,
    same_axes_output,
):
    """Test plot validity and configuration flags for 3D datasets across various axes and plot types""" 

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    
    results = run_validity_check(
        ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds
    )
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (
        plot_valid_output,
        requires_slice_output,
        invalid_heatmap_output,
        same_axes_output,
    )


@pytest.mark.parametrize("is_ref", [False, True])
@pytest.mark.parametrize(
    "x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output",
    [
        ("x", "", "", "line", "data", False, True, False, False),
        ("x", "", "", "Heatmap", "data", False, True, True, False),
        ("x", "", "", "Animation", "data", False, True, True, False),
        ("x", "y", "", "Animation", "data", False, True, True, False),
        ("x", "x", "x", "Animation", "data", False, True, False, True),
        ("x", "z", "z", "Animation", "data", False, True, False, True),
        ("x", "x", "z", "Animation", "data", False, True, False, True),
        ("x", "y", "z", "Animation", "data", False, True, False, False),
        ("x", "y", "", "Heatmap", "data", False, True, False, False),
        ("x", "y", "z", "Heatmap", "data", False, True, False, False),
        ("x", "y", "", "line", "data", False, True, False, False),
        ("x", "y", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "line", "data", False, True, False, False),
        ("x", "x", "z", "Heatmap", "data", False, True, False, True),
        ("", "", "", "line", "data", False, False, False, False),
    ],
)
def test_check_plot_validity_4d(
    ui,
    is_ref,
    x_value,
    y_value,
    z_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    invalid_heatmap_output,
    same_axes_output,
):
    """Test plot validity and configuration flags for 4D datasets across various axes and plot types"""

    # Create a 4D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10, 10),
        dims=["x", "y", "z", "w"],
        coords={
            "x": np.arange(10),
            "y": np.arange(10),
            "z": np.arange(10),
            "w": np.arange(10),
        },
    )
    
    if requires_slice_output:
        if is_ref:
            ui.ref_slice_widgets = {"widget": pn.pane.Markdown("a widget")}
            ui.ref_slice_ui_row = pn.Row(name="ref slice ui row")
            ui.widget_container.append(ui.ref_slice_ui_row)
        else:
            ui.slice_widgets = {"widget": pn.pane.Markdown("a widget")}
            ui.slice_ui_row = pn.Row(name="slice ui row")
            ui.widget_container.append(ui.slice_ui_row)

    ds = xr.Dataset({"data": data})

    results = run_validity_check(
        ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds
    )

    # Verify that the validity check returns the expected configuration flags
    assert results == (
        plot_valid_output,
        requires_slice_output,
        invalid_heatmap_output,
        same_axes_output,
    )
    if requires_slice_output:
        # Determine which attributes we should be checking
        row_attr = "ref_slice_ui_row" if is_ref else "slice_ui_row"
        widget_attr = "ref_slice_widgets" if is_ref else "slice_widgets"

        # If the function exits early due to no x_axis, the cleanup never happens
        if not x_value:
            assert hasattr(ui, row_attr)
            assert getattr(ui, row_attr) in ui.widget_container
        else:
            # Otherwise, the cleanup runs because the slice widgets don't match remaining dims
            assert not hasattr(ui, row_attr)
            assert not hasattr(ui, widget_attr)

@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", True, False, False),
        ("x", "y", "Line", "data", True, False, False),
    ],
)
def test_multiplot_check_plot_validity_1d(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
):
    """Test multiplot validity and configuration flags for 1D datasets""" 

    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})

    # assign dataset and multiplot reference state on the UI instance
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)


@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", False, False, True),
        ("x", "y", "Line", "data", False, False, True),
    ],
)
def test_multiplot_check_plot_validity_1d_bounds(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
):
    """Test multiplot validity and coordinate/bounds mismatch flags for 1D datasets""" 

    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds

    # Introduce mismatched coordinates and values across datasets to trigger bounds checking
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)


@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output, invalid_dataset_test",
    [
        ("x", "", "Line", "data", False, True, False, False),
        ("x", "y", "Line", "data", False, True, False, False),
        ("x", "y", "Heatmap (grid)", "data", True, False, False, False),
        ("x", "x", "Heatmap (grid)", "data", False, False, False, False),
        ("x", "y", "Heatmap (grid)", "data", True, False, False, True),
    ],
)
def test_multiplot_check_plot_validity_2d(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
    invalid_dataset_test,
):
    """Test multiplot validity and configuration flags for 2D datasets""" 

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    
    # Introduce mismatched variables across datasets to test invalid dataset handling
    if invalid_dataset_test:
        ds2 = xr.Dataset({"different_name": data})
    else:
        ds2 = ds
        
    # Assign dataset and multiplot reference state on the UI instance
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds2}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)

    # Verify that the appropriate warning is displayed when a dataset is removed
    if invalid_dataset_test:
        assert (
            "The following models were removed as they do not contain the selected variable"
            in ui.multiplot_warning_textbox.value
        )

@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", False, True, False),
        ("x", "y", "Line", "data", False, True, False),
        ("x", "y", "Heatmap (grid)", "data", False, False, True),
        ("x", "x", "Heatmap (grid)", "data", False, False, False),
    ],
)
def test_multiplot_check_plot_validity_2d_bounds(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
):
    """Test multiplot validity and coordinate/bounds mismatch flags for 2D datasets""" 

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    
    # Introduce mismatched coordinates and values across datasets to trigger bounds checking
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)

@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", False, True, False),
        ("x", "y", "Line", "data", False, True, False),
        ("x", "y", "Heatmap (grid)", "data", False, True, False),
        ("x", "x", "Heatmap (grid)", "data", False, False, False),
    ],
)
def test_multiplot_check_plot_validity_3d(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
):
    """Test multiplot validity and configuration flags for 3D datasets""" 

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    
    # Assign dataset and multiplot reference state on the UI instance
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    if requires_slice_output:
        ui.multiplot_slice_widgets = {"widget": pn.pane.Markdown("a widget")}
        ui.multiplot_slice_ui_row = pn.Row(name="multiplot slice ui row")
        ui.widget_container.append(ui.multiplot_slice_ui_row)
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)
    if requires_slice_output:
        # If the function exits early due to no x_axis, the cleanup never happens
        if not x_value:
            assert hasattr(ui, "multiplot_slice_ui_row")
            assert getattr(ui, "multiplot_slice_widgets") in ui.widget_container
        else:
            # Otherwise, the cleanup runs because the slice widgets don't match remaining dims
            assert not hasattr(ui, "multiplot_slice_ui_row")
            assert not hasattr(ui, "multiplot_slice_widgets")


@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", False, True, False),
        ("x", "y", "Line", "data", False, True, False),
        ("x", "y", "Heatmap (grid)", "data", False, True, False),
        ("x", "x", "Heatmap (grid)", "data", False, False, False),
    ],
)
def test_multiplot_check_plot_validity_3d_bounds(
    ui,
    x_value,
    y_value,
    plot_type,
    variable_value,
    plot_valid_output,
    requires_slice_output,
    check_bounds_output,
):
    """Test multiplot validity and coordinate/bounds mismatch flags for 3D datasets""" 

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    
    # Introduce mismatched coordinates and values across datasets to trigger bounds checking
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    
    results = ui._check_multiplot_plot_validity()
    
    # Verify that the validity check returns the expected configuration flags
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)

@pytest.mark.parametrize(
    "variable_name_short, variable_name_long, is_long",
    [
        ("var1", "Variable 1", False),
        ("var2", "Variable 2", True),
    ],
)
def test_get_selected_variable(ui, variable_name_short, variable_name_long, is_long):
    """Test retrieving the short variable name based on the UI variable toggle state""" 

    # Configure the UI toggle state and set the appropriate variable name in the dropdown
    ui.variable_toggle.value = is_long
    if is_long:
        ui.plot_variable_dropdown.value = variable_name_long
    else:
        ui.plot_variable_dropdown.value = variable_name_short
    ui.long_names = {variable_name_long: variable_name_short}

    # Verify that the correct short variable name is returned regardless of the toggle state
    assert ui._get_selected_variable() == variable_name_short


@pytest.mark.parametrize(
    "variable_name_short, variable_name_long, is_long",
    [
        ("var1", "Variable 1", False),
        ("var2", "Variable 2", True),
    ],
)
def test_ref_get_selected_variable(
    ui, variable_name_short, variable_name_long, is_long
):
    """Test retrieving the short reference variable name based on the reference UI variable toggle state""" 

    # Configure the reference UI toggle state and set the appropriate variable name in the dropdown
    ui.ref_variable_toggle.value = is_long
    if is_long:
        ui.ref_plot_variable_dropdown.value = variable_name_long
    else:
        ui.ref_plot_variable_dropdown.value = variable_name_short
    ui.ref_long_names = {variable_name_long: variable_name_short}

    # Verify that the correct short reference variable name is returned regardless of the toggle state
    assert ui._ref_get_selected_variable() == variable_name_short


@pytest.mark.parametrize(
    "variable_name_short, variable_name_long, is_long",
    [
        ("var1", "Variable 1", False),
        ("var2", "Variable 2", True),
    ],
)
def test_multiplot_get_selected_variable(
    ui, variable_name_short, variable_name_long, is_long
):
    """Test retrieving the short multiplot variable name based on the multiplot UI variable toggle state""" 

    # Configure the multiplot UI toggle state and set the appropriate variable name in the dropdown
    ui.multiplot_variable_toggle.value = is_long
    if is_long:
        ui.multiplot_plot_variable_dropdown.value = variable_name_long
    else:
        ui.multiplot_plot_variable_dropdown.value = variable_name_short
    ui.multiplot_long_names = {variable_name_long: variable_name_short}

    # Verify that the correct short multiplot variable name is returned regardless of the toggle state
    assert ui._multiplot_get_selected_variable() == variable_name_short


@pytest.mark.parametrize(
    "meta, cat, ds",
    [
        ("metadata", "catalog", "dataset"),
        ("metadata", "catalog", True),
        ("", None, None),
    ],
)
def test_ref_clear_data_click(ui, meta, cat, ds):
    """Test clearing reference data and resetting UI state attributes""" 

    # Set the reference model metadata value, not sure if there is a better way I should do this?
    ui.ref_model_metadata.value = meta

    # Conditionally assign a mock dataset or raw catalog values based on parametrisation
    if ds:
        ui.ref_dataset = xr.DataArray(
            np.random.rand(10, 10, 10),
            dims=["x", "y", "z"],
            coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
        )
    else:
        ui.ref_model_cat = cat
        ui.ref_dataset = ds

    # Trigger the clear data callback
    ui._ref_clear_data_click()
    
    # Verify that metadata is cleared and dataset/catalog attributes are removed from the UI instance
    assert ui.ref_model_metadata.value == ""
    assert hasattr(ui, "ref_model_cat") == False
    assert hasattr(ui, "ref_dataset") == False


@pytest.mark.parametrize(
    "n_dims, x_value, y_value, z_value, plot_choices_exists, remaining_dims, expected_n_slices",
    [
        (1, "x", None, None, False, [], 0),
        (2, "x", None, None, False, ["y"], 1),
        (3, "x", None, None, False, ["y", "z"], 2),
        (4, "x", None, None, False, ["y", "z", "dim3"], 3),
        (2, "x", "y", None, False, [], 0),
        (3, "x", "y", None, False, ["z"], 1),
        (4, "x", "y", None, False, ["z", "dim3"], 2),
        (3, "x", "y", "z", False, [], 0),
        (4, "x", "y", "z", False, ["dim3"], 1),
        (3, "x", "y", None, True, ["z"], 1),
        
    ],
)
def test_check_slice(
    ui,
    n_dims,
    x_value,
    y_value,
    z_value,
    plot_choices_exists,
    remaining_dims,
    expected_n_slices,
):
    """Test the generation and placement of slice UI widgets based on dataset dimensions and axis selections""" 

    # Create an xarray dataset with the specified number of dimensions
    target_names = ["x", "y", "z"]
    dims = [target_names[i] if i < 3 else f"dim{i}" for i in range(n_dims)]
    ui.remaining_dims = remaining_dims  # Set remaining_dims for the UI
    coords = {dim: np.arange(10) for dim in dims}
    data_array = xr.DataArray(
            np.random.rand(*([10] * n_dims)), dims=dims, coords=coords
        )
    ds = xr.Dataset({"data": data_array})

    # Assign dataset and axis selections to the UI instance
    ui.dataset = ds
    
    # Conditionally append a plot choices row to the widget container to test slice UI placement
    if plot_choices_exists:
        ui.plot_choices_row = pn.Row(pn.pane.Markdown("something"), name="old")
        ui.widget_container.append(ui.plot_choices_row)
    elif hasattr(ui, "plot_choices_row"):
        del ui.plot_choices_row

    ui.plot_variable_dropdown.value = "data"
    ui.x_axis_dropdown.value = x_value
    ui.y_axis_dropdown.value = y_value
    ui.animation_axis_dropdown.value = z_value

    # Trigger the slice check
    ui._check_slice()
    
    # Verify that the correct number of slice widgets are generated
    assert len(ui.slice_ui_row) == expected_n_slices

    # Verify that the slice UI row is positioned immediately after the plot choices row
    if plot_choices_exists:
        assert (
            ui.widget_container.index(ui.slice_ui_row)
            == ui.widget_container.index(ui.plot_choices_row) + 1
        )


@pytest.mark.parametrize(
    "n_dims, x_value, y_value, z_value, plot_choices_exists, remaining_dims, expected_n_slices",
    [
        (1, "x", None, None, False, [], 0),
        (2, "x", None, None, False, ["y"], 1),
        (3, "x", None, None, False, ["y", "z"], 2),
        (4, "x", None, None, False, ["y", "z", "dim3"], 3),
        (2, "x", "y", None, False, [], 0),
        (3, "x", "y", None, False, ["z"], 1),
        (4, "x", "y", None, False, ["z", "dim3"], 2),
        (3, "x", "y", "z", False, [], 0),
        (4, "x", "y", "z", False, ["dim3"], 1),
        (3, "x", "y", None, True, ["z"], 1),
    ],
)
def test_ref_check_slice(
    ui,
    n_dims,
    x_value,
    y_value,
    z_value,
    plot_choices_exists, remaining_dims,
    expected_n_slices,
):
    """Test the generation and placement of reference slice UI widgets based on dataset dimensions and axis selections"""

    # Create an xarray dataset with the specified number of dimensions
    target_names = ["x", "y", "z"]
    dims = [target_names[i] if i < 3 else f"dim{i}" for i in range(n_dims)]
    ui.ref_remaining_dims = remaining_dims  # Set remaining_dims for the UI
    coords = {dim: np.arange(10) for dim in dims}
    data_array = xr.DataArray(
        np.random.rand(*([10] * n_dims)), dims=dims, coords=coords
    )
    ds = xr.Dataset({"data": data_array})

    # Conditionally append a reference plot choices row to the widget container to test slice UI placement
    if plot_choices_exists:
        ui.ref_plot_choices_row = pn.Row(pn.pane.Markdown("something"), name="old")
        ui.widget_container.append(ui.ref_plot_choices_row)
    elif hasattr(ui, "ref_plot_choices_row"):
        del ui.ref_plot_choices_row

    # Assign reference dataset and axis selections to the UI instance
    ui.ref_dataset = ds
    ui.ref_plot_variable_dropdown.value = "data"
    ui.ref_x_axis_dropdown.value = x_value
    ui.ref_y_axis_dropdown.value = y_value
    ui.ref_animation_axis_dropdown.value = z_value

    # Trigger the reference slice check
    ui._ref_check_slice()

    # Verify that the correct number of reference slice widgets are generated
    assert len(ui.ref_slice_ui_row) == expected_n_slices

    # Verify that the reference slice UI row is positioned immediately after the reference plot choices row
    if plot_choices_exists:
        assert (
            ui.widget_container.index(ui.ref_slice_ui_row)
            == ui.widget_container.index(ui.ref_plot_choices_row) + 1
        )


@pytest.mark.parametrize(
    "n_dims, x_value, y_value, z_value, plot_choices_exists, remaining_dims, expected_n_slices",
    [
        (1, "x", None, None, False, [], 0),
        (2, "x", None, None, False, ["y"], 1),
        (3, "x", None, None, False, ["y", "z"], 2),
        (4, "x", None, None, False, ["y", "z", "dim3"], 3),
        (2, "x", "y", None, False, [], 0),
        (3, "x", "y", None, False, ["z"], 1),
        (4, "x", "y", None, False, ["z", "dim3"], 2),
        (3, "x", "y", "z", False, ["z"], 1),
        (4, "x", "y", "z", False, ["z", "dim3"], 2),
        (3, "x", "y", None, True, ["z"], 1),
    ],
)
def test_multiplot_check_slice(
    ui, n_dims, x_value, y_value, z_value, plot_choices_exists, remaining_dims, expected_n_slices
):
    """Test the generation and placement of multiplot slice UI widgets based on dataset dimensions and axis selections"""

    # Create an xarray dataset with the specified number of dimensions
    target_names = ["x", "y", "z"]
    dims = [target_names[i] if i < 3 else f"dim{i}" for i in range(n_dims)]
    ui.multiplot_remaining_dims = remaining_dims  # Set remaining_dims for the UI
    coords = {dim: np.arange(10) for dim in dims}
    data_array = xr.DataArray(
        np.random.rand(*([10] * n_dims)), dims=dims, coords=coords
    )
    ds = xr.Dataset({"data": data_array})

    # Conditionally append a multiplot choices row to the widget container to test slice UI placement
    if plot_choices_exists:
        ui.multiplot_plot_choices_row = pn.Row(
            pn.pane.Markdown("something"), name="old"
        )
        ui.widget_container.append(ui.multiplot_plot_choices_row)
    elif hasattr(ui, "ref_plot_choices_row"):
        del ui.ref_plot_choices_row

    # Assign multiplot dataset and axis selections to the UI instance
    ui.dataset = ds
    ui.multiplot_plot_variable_dropdown.value = "data"
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value

    # Trigger the multiplot slice check
    ui._multiplot_check_slice()

    # Verify that the correct number of multiplot slice widgets are generated
    assert len(ui.multiplot_slice_ui_row) == expected_n_slices

    # Verify that the multiplot slice UI row is positioned immediately after the multiplot choices row
    if plot_choices_exists:
        assert (
            ui.widget_container.index(ui.multiplot_slice_ui_row)
            == ui.widget_container.index(ui.multiplot_plot_choices_row) + 1
        )


def test_plot_dataset(ui):
    """Test the generation of 1D line plots and 2D heatmaps from a provided dataset""" 

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.chosen_slices = {"z": 1}
    ui.plot_variable_dropdown.value = "data"
    ui.keys_dropdown.value = "data"

    # Assign the mock dataset to the UI instance
    ui.dataset = ds

    # Generate a 1D plot and verify a valid matplotlib Figure is returned with content
    plot_result = ui._plot_dataset("data", "x")
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0

    # Generate a 2D heatmap and verify a valid matplotlib Figure is returned with content
    plot_result = ui._plot_heatmap("data", "x", "y")
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0


def test_plot_ref_dataset(ui):
    """Test the generation of 1D line plots and 2D heatmaps from a provided reference dataset""" 

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.ref_chosen_slices = {"z" : 1}
    ui.ref_keys_dropdown.value = "data"
    ui.ref_data_keys_dropdown.value = "data"
    
    # Assign the mock dataset to the reference UI instance
    ui.ref_dataset = ds
    
    # Generate a 1D reference plot and verify a valid matplotlib Figure is returned with content
    plot_result = ui._plot_ref_dataset("data", "x")
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0

    # Generate a 2D reference heatmap and verify a valid matplotlib Figure is returned with content
    plot_result = ui._plot_ref_heatmap("data", "x", "y")
    ax = plot_result.axes[0]
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 2
    assert len(ax.lines) > 0 or len(ax.collections) > 0 or len(ax.images) > 0


def test_plot_multiplot_dataset(ui, monkeypatch):
    """Test the generation of 1D line multiplots and 2D heatmaps across multiple datasets"""

    # Create a 3D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.multiplot_chosen_slices = {}

    # Assign datasets and multiplot state to the UI instance, and mock the bounds checking method
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_chosen_slices = {"z": 1}
    mock_multiplot_check_bounds = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_check_bounds", mock_multiplot_check_bounds)

    # Generate a 1D multiplot and verify a valid matplotlib Figure is returned with subplots and a legend
    plot_result = ui._plot_multiplot_dataset("data", "x")
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 4  # axes for each subplot and 1 legend

    # Apply user-defined bounds constraints and verify that the bounds checking method is triggered
    ui.prompt_bounds_dropdown.value = "Constrain to user dataset bounds"
    ui.dataset_min = 0
    ui.dataset_max = 1000
    plot_result = ui._plot_multiplot_dataset("data", "x")
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 4  # axes for each subplot and 1 legend
    mock_multiplot_check_bounds.assert_any_call()

    # Generate a 2D multiplot heatmap and verify a valid matplotlib Figure is returned with appropriate axes
    plot_result = ui._plot_multiplot_heatmap_dataset("data", "x", "y")
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 6  # 2 axes for each subplot


def test_clear_multiplot_data(ui):
    """Test clearing multiplot data and resetting UI state attributes"""

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})

    # Assign the mock dataset to the multiplot reference dictionary and set metadata
    ui.multiplot_ref_dataset_dict = {"key": ds}

    # Trigger the multiplot clear data callback
    ui._clear_multiplot_data()

    # Verify that metadata is cleared and catalog/dataset attributes are removed from the UI instance
    assert ui.multiplot_ref_dataset_dict == {}


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
def test_multiplot_check_bounds_numeric(
    ui, ref_min_val, ref_max_val, expected_triggered
):
    """Test numeric coordinate bounds checking across primary and reference datasets in multiplots""" 

    # Create a primary dataset with fixed coordinate bounds from 0 to 10
    ds_primary = xr.Dataset({"data": (["x"], [1, 2])}, coords={"x": [0, 10]})

    # Create a reference dataset with coordinate bounds based on parameters and assign both to the UI
    ds_ref = xr.Dataset(
        {"data": (["x"], [3, 4])}, coords={"x": [ref_min_val, ref_max_val]}
    )
    ui.multiplot_x_axis_dropdown.value = "x"
    ui.dataset = ds_primary
    ui.multiplot_ref_dataset_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result = ui._multiplot_check_bounds()

    assert result == expected_triggered

    expected_global_min = min(0, ref_min_val)
    expected_global_max = max(10, ref_max_val)

    # Verify that the global minimum and maximum bounds are calculated correctly across datasets
    assert ui.multiplot_min == expected_global_min
    assert ui.multiplot_max == expected_global_max


@pytest.mark.parametrize(
    "ref_start, ref_end, expected_triggered",
    [
        ((2000, 2, 1), (2000, 11, 30), False),
        ((1999, 12, 1), (2000, 11, 30), True),
        ((2000, 2, 1), (2001, 1, 1), True),
    ],
)
def test_multiplot_check_bounds_calendar(ui, ref_start, ref_end, expected_triggered):
    """Test calendar coordinate bounds checking across primary and reference datasets in multiplots""" 

    # Create a primary dataset using NoLeap calendar bounds from Jan 1 2000 to Dec 31 2000
    primary_times = [
        cftime.DatetimeNoLeap(2000, 1, 1),
        cftime.DatetimeNoLeap(2000, 12, 31),
    ]
    ds_primary = xr.Dataset(
        {"data": (["time"], [1, 2])}, coords={"time": primary_times}
    )

    # Create a reference dataset using Gregorian calendar bounds based on parameters
    ref_times = [
        cftime.DatetimeGregorian(*ref_start),
        cftime.DatetimeGregorian(*ref_end),
    ]
    ds_ref = xr.Dataset({"data": (["time"], [3, 4])}, coords={"time": ref_times})

    # Assign primary and reference datasets to the UI instance and set the x-axis to time
    ui.multiplot_x_axis_dropdown.value = "time"
    ui.dataset = ds_primary
    ui.multiplot_ref_dataset_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result = ui._multiplot_check_bounds()
    assert result == expected_triggered

@pytest.mark.parametrize(
    "constrain_bounds",
    [
        True, 
        False
    ],
)
def test_plot_multiplot_difference_dataset(ui, constrain_bounds):
    """Test the generation of 1D line and 2D heatmap difference plots across multiple datasets""" 

    # Create a 2D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10),
        dims=["x", "y", "z"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    ui.multiplot_chosen_slices = {"z": 1}
    
    # Assign datasets and multiplot state to the UI instance
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = "x"
    ui.multiplot_y_axis_dropdown.value = "y"
    ui.dataset_min = 0
    ui.dataset_max = 1000
    ui.multiplot_min = -1
    ui.multiplot_max = 1001

    if constrain_bounds:
        ui.prompt_bounds_dropdown.value = "Constrain to user dataset bounds"
    else:
        ui.prompt_bounds_dropdown.value = ""

    # Generate a 2D multiplot difference heatmap and verify a valid matplotlib Figure is returned
    plot_result = ui._plot_multiplot_difference_heatmap("data", "x", "y")
    ax = plot_result.axes[0]
    xmin, xmax = ax.get_xlim()
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 4  # axes for each difference plotted
    assert any("Sliced by: " in t.get_text() for t in plot_result.texts)

    # Generate a 1D multiplot difference plot and verify a valid matplotlib Figure is returned
    plot_result = ui._plot_multiplot_difference_dataset("data", "x")
    ax = plot_result.axes[0]
    xmin, xmax = ax.get_xlim()
    assert isinstance(plot_result, plt.Figure)
    assert len(plot_result.axes) == 3  # axes for each difference plotted + legend
    assert any("Sliced by: " in t.get_text() for t in plot_result.texts)


def test_display_status_text(ui):
    """Test the initialization and default values of the UI status display widgets""" 

    # Trigger the status text display mechanism to initialize UI components
    ui._display_status_text()

    # Verify that all expected status components and dividers are successfully attached to the UI instance
    assert hasattr(ui, "last_data_load_textbox")
    assert hasattr(ui, "status_textbox")
    assert hasattr(ui, "warning_textbox")
    assert hasattr(ui, "div_1")
    assert hasattr(ui, "keys_selection_row")
    assert hasattr(ui, "div_2")

    # Verify that the status textbox displays the expected initial loading message
    assert (
        ui.status_textbox.value
        == "User model status >> Waiting for initial model data catalog to be built. This can take a few minutes."
    )


def test_update_status_text(ui):
    """Test updating the primary UI status textbox"""

    # Define a mock status string and trigger the update method
    text = "Test update text"
    ui._update_status_text(text)

    # Verify that the status textbox value matches the updated text
    assert ui.status_textbox.value == text


def test_update_ref_status_text(ui):
    """Test updating the reference UI status textbox"""

    # Define a mock status string and trigger the reference update method
    text = "Test update text"
    ui._update_ref_status_text(text)

    # Verify that the reference status textbox value matches the updated text
    assert ui.ref_status_textbox.value == text


def test_update_multiplot_status_text(ui):
    """Test updating the multiplot UI status textbox"""

    # Define a mock status string and trigger the multiplot update method
    text = "Test update text"
    ui._update_multiplot_status_text(text)

    # Verify that the multiplot status textbox value matches the updated text
    assert ui.multiplot_status_textbox.value == text


def test_update_warning_text(ui):
    """Test updating the primary UI warning textbox"""

    # Define a mock warning string and trigger the update method
    text = "Test update text"
    ui._update_warning_text(text)

    # Verify that the warning textbox value matches the updated text
    assert ui.warning_textbox.value == text


def test_update_ref_warning_text(ui):
    """Test updating the reference UI warning textbox"""

    # Define a mock warning string and trigger the reference update method
    text = "Test update text"
    ui._update_ref_warning_text(text)

    # Verify that the reference warning textbox value matches the updated text
    assert ui.ref_warning_textbox.value == text


def test_update_multiplot_warning_text(ui):
    """Test updating the multiplot UI warning textbox"""

    # Define a mock warning string and trigger the multiplot update method
    text = "Test update text"
    ui._update_multiplot_warning_text(text)

    # Verify that the multiplot warning textbox value matches the updated text
    assert ui.multiplot_warning_textbox.value == text


def test_update_last_data_load_text(ui):
    """Test updating the last data load textbox"""

    # Define a mock load text string and trigger the update method
    text = "Test update text"
    ui._update_last_data_load_text(text)

    # Verify that the last data load textbox value matches the updated text
    assert ui.last_data_load_textbox.value == text


def test_variable_toggle_change(ui):
    """Test updating the variable dropdown options based on the variable toggle state""" 

    # Create a 2D xarray dataset with a long_name attribute
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
        attrs={"long_name": "long name"},
    )
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    
    # Set toggle to True and verify the dropdown options display the long name
    ui.variable_toggle.value = True
    ui._variable_toggle_change()
    assert ui.plot_variable_dropdown.options == ["long name"]

    # Set toggle to False and verify the dropdown options revert to the short variable name
    ui.variable_toggle.value = False
    ui._variable_toggle_change()
    assert ui.plot_variable_dropdown.options == ["data"]


def test_ref_variable_toggle_change(ui):
    """Test updating the reference variable dropdown options based on the reference variable toggle state""" 

    # Create a 2D xarray dataset with a long_name attribute and assign it to the reference UI instance
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
        attrs={"long_name": "long name"},
    )
    ds = xr.Dataset({"data": data})
    ui.ref_dataset = ds
    
    # Set the reference toggle to True and verify the dropdown options display the long name
    ui.ref_variable_toggle.value = True
    ui._ref_variable_toggle_change()
    assert ui.ref_plot_variable_dropdown.options == ["long name"]

    # Set the reference toggle to False and verify the dropdown options revert to the short variable name
    ui.ref_variable_toggle.value = False
    ui._ref_variable_toggle_change()
    assert ui.ref_plot_variable_dropdown.options == ["data"]


def test_multiplot_variable_toggle_change(ui):
    """Test updating the multiplot variable dropdown options based on the multiplot variable toggle state""" 

    # Create a 2D xarray dataset with a long_name attribute and assign it to the UI instance
    data = xr.DataArray(
        np.random.rand(10, 10),
        dims=["x", "y"],
        coords={"x": np.arange(10), "y": np.arange(10)},
        attrs={"long_name": "long name"},
    )
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    
    # Set the multiplot toggle to True and verify the dropdown options display the long name
    ui.multiplot_variable_toggle.value = True
    ui._multiplot_variable_toggle_change()
    assert ui.multiplot_plot_variable_dropdown.options == ["long name"]

    # Set the multiplot toggle to False and verify the dropdown options revert to the short variable name
    ui.multiplot_variable_toggle.value = False
    ui._multiplot_variable_toggle_change()
    assert ui.multiplot_plot_variable_dropdown.options == ["data"]


def test_display_dataset_selection_ui(ui):
    """Test the initialization and visibility of the dataset selection UI components""" 

    # Define a mock model catalog and trigger the dataset selection UI display
    model_cat = {"ds1": None, "ds2": None}
    ui._display_dataset_selection_ui(model_cat, "access_nri_cat")

    # Verify that catalog attributes are correctly assigned to the UI instance
    assert ui.model_cat == model_cat
    assert ui.access_nri_cat == "access_nri_cat"
    
    # Verify that the relevant dividers and selection rows are made visible
    assert ui.div_1.visible == True
    assert ui.keys_selection_row.visible == True
    assert ui.div_2.visible == True
    
    # Verify that the dropdown options match the sorted catalog keys and button properties are set
    assert ui.keys_dropdown.options == sorted(list(model_cat.keys()))
    assert ui.keys_button.name == "Load dataset"
    assert ui.keys_button.button_type == "primary"


def test_display_reference_model_selection_ui(ui):
    """Test the initialization and layout of the reference model selection UI components""" 

    # Assign a mock model catalog and trigger the reference model selection UI display
    ui.access_nri_cat = {"key": None, "key2": None}
    ui._display_reference_model_selection_ui()

    # Verify that the reference status and warning textboxes are correctly initialized
    assert (
        ui.ref_status_textbox.value
        == "Reference Model Status >> Select a model to load and plot data"
    )
    assert hasattr(ui, "ref_status_textbox")
    assert hasattr(ui, "ref_warning_textbox")
    
    # Verify that the dropdown options match the catalog and button properties are correctly configured
    assert ui.ref_keys_dropdown.name == "2. Select reference model (optional):"
    assert ui.ref_keys_dropdown.options == sorted(list(ui.access_nri_cat.keys()))
    assert ui.ref_keys_button.name == "Load reference model"
    assert ui.ref_keys_button.button_type == "success"

    assert ui.clear_ref_model_data_button.name == "Clear reference model"
    assert ui.clear_ref_model_data_button.button_type == "danger"

    assert ui.ref_model_info_button.name == "Reference model information"
    assert ui.ref_model_info_button.button_type == "primary"
    
    # Verify that all expected reference model UI components are attached to the UI instance
    assert hasattr(ui, "ref_keys_dropdown")
    assert hasattr(ui, "ref_model_info_button")
    assert hasattr(ui, "ref_keys_button")
    assert hasattr(ui, "clear_ref_model_data_button")
    assert hasattr(ui, "ref_keys_selection_row")
    assert hasattr(ui, "ref_model_metadata")


@pytest.mark.parametrize(
    "ref_model_metadata, ref_keys_selection_row",
    [
        (False, True),
        (True, False),
        (False, False),
    ],
)
def test_display_reference_dataset_selection_ui(
    ui, ref_model_metadata, ref_keys_selection_row
):
    """Test the initialization and layout of the reference dataset selection UI components""" 

    # Assign a mock reference model catalog and clear the widget container
    ui.ref_model_cat = {"key1": None, "key2": None}
    ui.widget_container.clear()
    
    # Conditionally append reference UI rows to test the layout positioning of the dataset selection row
    if ref_model_metadata:
        ui.ref_model_metadata = pn.pane.Markdown("something")
        ui.widget_container.append(ui.ref_model_metadata)
        ui._display_reference_dataset_selection_ui()
        assert (
            ui.widget_container.index(ui.ref_data_keys_selection_row)
            == ui.widget_container.index(ui.ref_model_metadata) + 1
        )
    elif ref_keys_selection_row:
        ui.ref_keys_selection_row = pn.pane.Markdown("something")
        ui.widget_container.append(ui.ref_keys_selection_row)
        ui._display_reference_dataset_selection_ui()
        assert (
            ui.widget_container.index(ui.ref_data_keys_selection_row)
            == ui.widget_container.index(ui.ref_keys_selection_row) + 1
        )
    else:
        ui._display_reference_dataset_selection_ui()

    # Verify that the reference dataset dropdown and button properties are correctly configured
    assert ui.ref_data_keys_dropdown.name == "2.1. Select reference dataset (optional):"
    assert ui.ref_data_keys_dropdown.options == sorted(list(ui.ref_model_cat.keys()))
    assert ui.ref_data_keys_button.name == "Load reference dataset"
    assert ui.ref_data_keys_button.button_type == "success"
    assert hasattr(ui, "ref_data_keys_dropdown")
    assert hasattr(ui, "ref_data_keys_button")


def test_display_multiplot_user_data_selection_ui(ui):
    """Test the initialization and configuration of the multiplot user data selection UI components"""

    # Assign a mock catalog and configure dropdown options on the UI instance
    ui.access_nri_cat = {"key1": None, "key2": None}
    ui.keys_dropdown.options = ["option2", "option23", "option1"]
    ui.keys_dropdown.value = "option1"
    ui.plot_variable_dropdown.options = ["option2", "option23", "option1"]
    ui.plot_variable_dropdown.value = "option1"

    # Trigger the multiplot user data selection UI display
    ui._display_multiplot_user_data_selection_ui()

    # Verify that the multiplot status and warning textboxes are correctly initialized
    assert hasattr(ui, "multiplot_status_textbox")
    assert hasattr(ui, "multiplot_warning_textbox")
    assert (
        ui.multiplot_status_textbox.value
        == "Overlay Plot >> Choose reference variables to compare with the current plot."
    )

    # Verify that the reference keys dropdown and buttons are correctly configured
    assert (
        ui.multiplot_ref_keys_dropdown.name
        == "Select one or more reference models to overlay (optional):"
    )

    assert ui.multiplot_ref_keys_dropdown.options == sorted(
        list(ui.access_nri_cat.keys())
    )
    assert ui.multiplot_ref_keys_button.name == "Add reference model"
    assert ui.clear_multiplot_data_button.name == "Clear loaded data"
    assert ui.multiplot_select_variable_button.name == "Select variable and plot type"

    # Verify that the multiplot user dataset and variable dropdowns match the primary UI selections
    assert ui.multiplot_keys_dropdown.name == "Select user dataset"
    assert ui.multiplot_keys_dropdown.options == sorted(list(ui.keys_dropdown.options))
    assert ui.multiplot_keys_dropdown.value == ui.keys_dropdown.value
    assert ui.multiplot_keys_update_button.name == "Update loaded dataset"
    assert ui.multiplot_plot_variable_dropdown.name == "Variable selection"
    assert ui.multiplot_plot_variable_dropdown.options == sorted(
        list(ui.plot_variable_dropdown.options)
    )
    assert ui.multiplot_plot_variable_dropdown.value == "option1"

    # Verify the plot type dropdown options
    assert ui.multiplot_plot_type_dropdown.name == "Select plot type"
    assert ui.multiplot_plot_type_dropdown.options == ["Line", "Heatmap (grid)"]

    # Verify that all expected multiplot UI selection rows are attached to the UI instance
    assert hasattr(ui, "multiplot_user_dataset_keys_selection_row")
    assert hasattr(ui, "multiplot_ref_keys_selection_row")
    assert hasattr(ui, "multiplot_type_selection_row")


@pytest.mark.parametrize(
    "plot_type, slice_dict",
    [
        ("Heatmap", {"time": pn.widgets.DiscreteSlider(options=[0, 1], value=0)}),
        ("Line", {}),
        ("Animation", {}),
    ],
)
@patch("med_diagnostics.ui.UserInterface._plot_heatmap")
@patch("med_diagnostics.ui.UserInterface._plot_dataset")
@patch("med_diagnostics.ui.UserInterface._plot_animation")
@patch("panel.pane.Matplotlib")
def test_plot_data_button_click(
    mock_matplotlib,
    mock_plot_animation,
    mock_plot_dataset,
    mock_plot_heatmap,
    ui,
    plot_type,
    slice_dict,
):
    """Test the plot data button callback for generating heatmaps, line plots, and animations""" 

    # Configure UI dropdown selections for the target plot type and variables
    ui.plot_type_dropdown.value = plot_type
    ui.x_axis_dropdown.value = "x"
    ui.y_axis_dropdown.value = "y"
    ui.plot_variable_dropdown.value = "data"

    # Configure slice widgets and establish expected slice values
    if slice_dict is None:
        if hasattr(ui, "slice_widgets"):
            del ui.slice_widgets
        if hasattr(ui, "slice_ui_row"):
            del ui.slice_ui_row
        expected_slices = {}
    else:
        ui.slice_widgets = slice_dict
        expected_slices = {dim: widget.value for dim, widget in slice_dict.items()}
        ui.slice_ui_row = pn.Row(name="slices")
        ui.widget_container.append(ui.slice_ui_row)

    # Append UI rows to the widget container to verify cleanup during plot generation
    ui.plot_choices_row = pn.Row(name="choices")
    ui.slice_ui_row = pn.Row(name="slices")
    ui.widget_container.append(ui.plot_choices_row)
    ui.widget_container.append(ui.slice_ui_row)

    # Trigger the plot generation callback
    ui._plot_data_button_click()

    # Verify that UI buttons and status text labels are updated appropriately
    assert ui.plot_button.name == "Add Plot"
    assert (
        ui.select_variable_button.name
        == "Add new plot with different variable/ plot type"
    )
    assert ui.x_axis_dropdown.name == "Select X-Axis"
    assert ui.y_axis_dropdown.name == "Select Y-Axis"
    assert ui.status_textbox.value == "User model status >> Plot created"

    assert ui.chosen_slices == expected_slices

    # Verify that the correct internal plot generation method is called based on the selected plot type
    if plot_type == "Heatmap":
        mock_plot_heatmap.assert_called_once_with("data", "x", "y")
    elif plot_type == "Line":
        mock_plot_dataset.assert_called_once_with("data", "x")
    elif plot_type == "Animation":
        mock_plot_animation.assert_called_once_with("data")

    # Verify that plot choices and slice UI components are removed from the widget container
    assert ui.plot_choices_row not in ui.widget_container
    assert not hasattr(ui.widget_container, "slice_ui_row")
    assert not hasattr(ui.widget_container, "slice_widgets")

@pytest.mark.parametrize(
    "plot_type, slice_dict",
    [
        ("Heatmap", {"time": pn.widgets.DiscreteSlider(options=[0, 1], value=0)}),
        ("Line", {}),
        ("Animation", {}),
    ],
)
@patch("med_diagnostics.ui.UserInterface._plot_ref_heatmap")
@patch("med_diagnostics.ui.UserInterface._plot_ref_dataset")
@patch("med_diagnostics.ui.UserInterface._plot_ref_animation")
@patch("panel.pane.Matplotlib")
def test_plot_ref_data_button_click(
    mock_matplotlib,
    mock_plot_ref_animation,
    mock_plot_ref_dataset,
    mock_plot_ref_heatmap,
    ui,
    plot_type,
    slice_dict,
):
    """Test the reference plot data button callback for generating heatmaps, line plots, and animations""" 

    # Configure reference UI dropdown selections for the target plot type and variables
    ui.ref_plot_type_dropdown.value = plot_type
    ui.ref_x_axis_dropdown.value = "x"
    ui.ref_y_axis_dropdown.value = "y"
    ui.ref_plot_variable_dropdown.value = "data"

    # Configure reference slice widgets and establish expected slice values
    if slice_dict is None:
        if hasattr(ui, "slice_widgets"):
            del ui.ref_slice_widgets
        if hasattr(ui, "slice_ui_row"):
            del ui.ref_slice_ui_row
        expected_slices = {}
    else:
        ui.ref_slice_widgets = slice_dict
        expected_slices = {dim: widget.value for dim, widget in slice_dict.items()}
        ui.ref_slice_ui_row = pn.Row(name="slices")
        ui.widget_container.append(ui.ref_slice_ui_row)

    # Append reference UI rows to the widget container to verify cleanup during plot generation
    ui.ref_plot_choices_row = pn.Row(name="choices")
    ui.ref_slice_ui_row = pn.Row(name="slices")
    ui.widget_container.append(ui.ref_plot_choices_row)
    ui.widget_container.append(ui.ref_slice_ui_row)

    # Trigger the reference plot generation callback
    ui._ref_plot_data_button_click()

    # Verify that reference UI buttons and status text labels are updated appropriately
    assert ui.ref_plot_button.name == "Add Plot"
    assert (
        ui.ref_select_variable_button.name
        == "Add new plot with different variable/ plot type"
    )
    assert ui.ref_x_axis_dropdown.name == "Select X-Axis"
    assert ui.ref_y_axis_dropdown.name == "Select Y-Axis"
    assert ui.ref_status_textbox.value == "Reference model status >> Plot created"

    assert ui.ref_chosen_slices == expected_slices

    # Verify that the correct internal reference plot generation method is called based on the selected plot type
    if plot_type == "Heatmap":
        mock_plot_ref_heatmap.assert_called_once_with("data", "x", "y")
    elif plot_type == "Line":
        mock_plot_ref_dataset.assert_called_once_with("data", "x")
    elif plot_type == "Animation":
        mock_plot_ref_animation.assert_called_once_with()

    # Verify that reference plot choices and slice UI components are removed from the widget container
    assert ui.ref_plot_choices_row not in ui.widget_container
    assert not hasattr(ui.widget_container, "ref_slice_ui_row")
    assert not hasattr(ui.widget_container, "ref_slice_widgets")


@pytest.mark.parametrize(
    "plot_type, analysis_type, slice_dict",
    [
        (
            "Heatmap (grid)",
            "None (plot all loaded data)",
            {"time": pn.widgets.DiscreteSlider(options=[0, 1], value=0)},
        ),
        ("Heatmap (grid)", "Plot Difference (Ref. - User data)", {}),
        ("Heatmap (grid)", "Plot All Data & Difference", {}),
        ("Line", "None (plot all loaded data)", {}),
        (
            "Line",
            "Plot Difference (Ref. - User data)",
            {"time": pn.widgets.DiscreteSlider(options=[0, 1], value=0)},
        ),
        (
            "Line",
            "Plot All Data & Difference",
            {"time": pn.widgets.DiscreteSlider(options=[0, 1], value=0)},
        ),
    ],
)
@patch("med_diagnostics.ui.UserInterface._plot_multiplot_heatmap_dataset")
@patch("med_diagnostics.ui.UserInterface._plot_multiplot_difference_heatmap")
@patch("med_diagnostics.ui.UserInterface._plot_multiplot_dataset")
@patch("med_diagnostics.ui.UserInterface._plot_multiplot_difference_dataset")
@patch("panel.pane.Matplotlib")
def test_plot_multiplot_data_button_click(
    mock_matplotlib,
    mock_plot_multiplot_difference_dataset,
    mock_plot_multiplot_dataset,
    mock_plot_multiplot_difference_heatmap,
    mock_plot_multiplot_heatmap_dataset,
    ui,
    plot_type,
    analysis_type,
    slice_dict,
):
    """Test the multiplot data button callback for generating heatmaps, line plots, and difference plots across multiple datasets"""

    # Configure multiplot UI dropdown selections for plot type, axes, variables, and analysis type
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_x_axis_dropdown.value = "x"
    ui.multiplot_y_axis_dropdown.value = "y"
    ui.multiplot_plot_variable_dropdown.value = "data"
    ui.multiplot_analysis_choice_dropdown.value = analysis_type

    # Configure multiplot slice widgets and establish expected slice values
    if slice_dict is None:
        if hasattr(ui, "slice_widgets"):
            del ui.multiplot_slice_widgets
        if hasattr(ui, "slice_ui_row"):
            del ui.multiplot_slice_ui_row
        expected_slices = {}
    else:
        ui.multiplot_slice_widgets = slice_dict
        expected_slices = {dim: widget.value for dim, widget in slice_dict.items()}
        ui.multiplot_slice_ui_row = pn.Row(name="slices")
        ui.widget_container.append(ui.multiplot_slice_ui_row)

    # Append multiplot UI rows to the widget container to verify cleanup during plot generation
    ui.multiplot_plot_choices_row = pn.Row(name="choices")
    ui.multiplot_slice_ui_row = pn.Row(name="slices")
    ui.widget_container.append(ui.multiplot_plot_choices_row)
    ui.widget_container.append(ui.multiplot_slice_ui_row)

    # Trigger the multiplot plot generation callback
    ui._multiplot_plot_data_button_click()

    # Verify that multiplot UI dropdown names and status text labels are updated appropriately
    assert ui.multiplot_x_axis_dropdown.name == "Select X-Axis"
    assert ui.multiplot_y_axis_dropdown.name == "Select Y-Axis"
    assert ui.multiplot_status_textbox.value == "Overlay plot status >> Plot created"

    assert ui.multiplot_chosen_slices == expected_slices

    # Verify that the correct internal multiplot generation methods are called based on the selected plot and analysis type
    if plot_type == "Heatmap (grid)" and analysis_type == "None (plot all loaded data)":
        mock_plot_multiplot_heatmap_dataset.assert_called_once_with("data", "x", "y")
    elif (
        plot_type == "Heatmap (grid)"
        and analysis_type == "Plot Difference (Ref. - User data)"
    ):
        mock_plot_multiplot_difference_heatmap.assert_called_once_with("data", "x", "y")
    elif (
        plot_type == "Heatmap (grid)" and analysis_type == "Plot All Data & Difference"
    ):
        mock_plot_multiplot_heatmap_dataset.assert_called_once_with("data", "x", "y")
        mock_plot_multiplot_difference_heatmap.assert_called_once_with("data", "x", "y")
    elif plot_type == "Line" and analysis_type == "None (plot all loaded data)":
        mock_plot_multiplot_dataset.assert_called_once_with("data", "x")
    elif plot_type == "Line" and analysis_type == "Plot Difference (Ref. - User data)":
        mock_plot_multiplot_difference_dataset.assert_called_once_with("data", "x")
    elif plot_type == "Line" and analysis_type == "Plot All Data & Difference":
        mock_plot_multiplot_dataset.assert_called_once_with("data", "x")
        mock_plot_multiplot_difference_dataset.assert_called_once_with("data", "x")

    # Verify that multiplot choices and slice UI components are removed from the widget container
    assert ui.ref_plot_choices_row not in ui.widget_container
    assert not hasattr(ui.widget_container, "multiplot_slice_ui_row")
    assert not hasattr(ui.widget_container, "multiplot_slice_widgets")


def test_display_dataset_plot_ui(ui):
    """Test the initialization and layout of the primary dataset plotting UI components"""

    # Assign a mock dataset to the UI instance
    dataset = {"key2": None, "Key1": None}
    ui.dataset = dataset

    # Trigger the dataset plot UI display
    ui._display_dataset_plot_ui()

    # Verify that the plot variable and type dropdowns, toggle, and buttons are correctly initialized
    assert ui.plot_variable_dropdown.name == "Available variables"
    assert ui.plot_variable_dropdown.options == sorted(list(dataset.keys()))
    assert ui.plot_type_dropdown.name == "Select plot type"
    assert ui.plot_type_dropdown.options == ["Line", "Heatmap", "Animation"]
    assert ui.variable_toggle.value == False
    assert ui.select_variable_button.name == "Select variable and plot type"

    # Verify that the plot UI selection row is attached to the UI instance
    assert hasattr(ui, "plot_ui_row")


@pytest.mark.parametrize(
    "datakeysexists",
    [
        ((False), (True)),
    ],
)
def test_ref_display_dataset_plot_ui(ui, datakeysexists):
    """Test the initialization and layout of the reference dataset plotting UI components""" 

    # Assign a mock dataset and conditionally configure the reference data keys selection row
    dataset = {"key2": None, "Key1": None}

    if datakeysexists:
        ui.ref_data_keys_selection_row = pn.Row()
        ui.widget_container.append(ui.ref_data_keys_selection_row)
    else:
        del ui.ref_data_keys_selection_row

    # Assign the mock dataset to the reference UI instance and trigger the plot UI display
    ui.ref_dataset = dataset
    ui._ref_display_dataset_plot_ui()

    # Verify that the reference plot variable and type dropdowns, toggle, and buttons are correctly initialized
    assert ui.ref_plot_variable_dropdown.name == "Available variables"
    assert ui.ref_plot_variable_dropdown.options == sorted(list(dataset.keys()))
    assert ui.ref_plot_type_dropdown.name == "Select plot type"
    assert ui.ref_plot_type_dropdown.options == ["Line", "Heatmap", "Animation"]
    assert ui.ref_variable_toggle.value == False
    assert ui.ref_select_variable_button.name == "Select variable and plot type"
    assert hasattr(ui, "ref_plot_ui_row")

    # Verify that the reference plot UI row is positioned correctly within the widget container based on prior UI state
    if datakeysexists:
        assert (
            ui.widget_container.index(ui.ref_plot_ui_row)
            == ui.widget_container.index(ui.ref_data_keys_selection_row) + 1
        )
    else:
        assert ui.widget_container.index(ui.ref_plot_ui_row) == len(ui.widget_container)


@pytest.mark.parametrize(
    "plot_type, dim_dict, has_existing_row, has_plot_ui, expected_outcome",
    [
        ("Heatmap", {"time": 10, "lat": 10}, True, False, "success_heatmap"),
        ("Heatmap", {"time": 10, "nv": 5, "scalar": 1}, False, False, "fail_dim_check"),
        ("Line", {"time": 10, "lat": 10}, False, True, "success_line"),
        ("Line", {"time": 10}, False, False, "auto_plot_line"),
        ("Animation", {"time": 10}, False, False, "fail_dim_check_animation"),
        ("Animation", {"time": 10, "lat": 10}, False, False, "success_animation"),
    ],
)
def test_display_plot_choices_ui(
    ui, monkeypatch, plot_type, dim_dict, has_existing_row, has_plot_ui, expected_outcome
):
    """Test the configuration and layout of primary dataset plot choices UI across different plot types and dimension constraints""" 

    # Create an xarray dataset with specified dimensions, sizes, and coordinate values
    coords = {dim: np.arange(size) for dim, size in dim_dict.items()}
    size = tuple(dim_dict.values())
    data_array = xr.DataArray(
        np.random.rand(*size), dims=list(dim_dict.keys()), coords=coords
    )
    ui.dataset = xr.Dataset({"data": data_array})

    ui.plot_variable_dropdown.value = "data"

    # Mock the plot button click handler to prevent automated callback execution during testing
    mock_plot_data_button_click = MagicMock()
    monkeypatch.setattr(ui, "_plot_data_button_click", mock_plot_data_button_click)

    ui.plot_type_dropdown.value = plot_type
    ui.widget_container.clear()

    # Conditionally configure existing rows and plot UI elements in the widget container
    if has_existing_row:
        ui.plot_choices_row = pn.Row(name="old_row")
        ui.widget_container.append(ui.plot_choices_row)
    elif hasattr(ui, "plot_choices_row"):
        del ui.plot_choices_row

    if has_plot_ui:
        ui.plot_ui_row = pn.Row()
        ui.widget_container.append(ui.plot_ui_row)
    elif hasattr(ui, "plot_ui_row"):
        del ui.plot_ui_row

    # Trigger the plot choices UI display method
    ui._display_plot_choices_ui()

    # Verify that the X-axis dropdown and plot button names are correctly set
    assert ui.x_axis_dropdown.name == "Select X-Axis dimension"
    assert ui.plot_button.name == "Plot data"

    # Verify that previous plot choice rows are successfully cleaned up from the container
    if has_existing_row:
        for item in ui.widget_container:
            if hasattr(item, "name"):
                assert item.name != "old_row"

    # Verify expected outcomes for dimension check failures, automatic plotting, or successful UI layout generation
    if expected_outcome == "fail_dim_check":
        assert ui.plot_type_dropdown.value == "Line"
        assert (
            ui.warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot a Heatmap."
        )
        assert not hasattr(ui, "plot_choices_row")
    elif expected_outcome == "auto_plot_line":
        assert (
            ui.warning_textbox.value
            == "Only one valid x-axis dimension, plotting automatically."
        )
        assert ui.x_axis_dropdown.value == "time"
        mock_plot_data_button_click.assert_called_once()
        assert not hasattr(ui, "plot_choices_row")

    elif expected_outcome == "fail_dim_check_animation":
        assert (
            ui.warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot an animation."
        )
        assert ui.plot_type_dropdown.value == "Line"
        assert not hasattr(ui, "plot_choices_row")

    else:
        assert ui.plot_choices_row in ui.widget_container

        if has_plot_ui:
            assert (
                ui.widget_container.index(ui.plot_choices_row)
                == ui.widget_container.index(ui.plot_ui_row) + 1
            )

        if expected_outcome == "success_heatmap":
            assert ui.y_axis_dropdown.name == "Select Y-Axis dimension"
            assert len(ui.plot_choices_row) == 3  # x, y, button
        elif expected_outcome == "success_line":
            assert len(ui.plot_choices_row) == 2  # x, button
        elif expected_outcome == "success_animation":
            assert ui.y_axis_dropdown.name == "Select Y-Axis dimension"
            assert ui.animation_axis_dropdown.name == "Select Z-Axis dimension"
            assert len(ui.plot_choices_row) == 4  # x, y, z, button


@pytest.mark.parametrize(
    "plot_type, dim_dict, has_existing_row, has_plot_ui, expected_outcome",
    [
        ("Heatmap", {"time": 10, "lat": 10}, True, False, "success_heatmap"),
        ("Heatmap", {"time": 10, "nv": 5, "scalar": 1}, False, False, "fail_dim_check"),
        ("Line", {"time": 10, "lat": 10}, False, True, "success_line"),
        ("Line", {"time": 10}, False, False, "auto_plot_line"),
        ("Animation", {"time": 10}, False, False, "fail_dim_check_animation"),
        ("Animation", {"time": 10, "lat": 10}, False, False, "success_animation"),
    ],
)
def test_ref_display_plot_choices_ui(
    ui, monkeypatch, plot_type, dim_dict, has_existing_row, has_plot_ui, expected_outcome
):
    """Test the configuration and layout of reference dataset plot choices UI across different plot types and dimension constraints"""

    # Create a reference dataset with specified dimensions, sizes, and coordinate values
    coords = {dim: np.arange(size) for dim, size in dim_dict.items()}
    size = tuple(dim_dict.values())
    data_array = xr.DataArray(
        np.random.rand(*size), dims=list(dim_dict.keys()), coords=coords
    )
    ui.ref_dataset = xr.Dataset({"data": data_array})

    ui.ref_plot_variable_dropdown.value = "data"

    # Mock the reference plot button click handler to prevent automated callback execution during testing
    mock_ref_plot_data_button_click = MagicMock()
    monkeypatch.setattr(
        ui, "_ref_plot_data_button_click", mock_ref_plot_data_button_click
    )

    ui.ref_plot_type_dropdown.value = plot_type
    ui.widget_container.clear()

    # Conditionally configure existing rows and reference plot UI elements in the widget container
    if has_existing_row:
        ui.ref_plot_choices_row = pn.Row(name="old_row")
        ui.widget_container.append(ui.ref_plot_choices_row)
    elif hasattr(ui, "ref_plot_choices_row"):
        del ui.ref_plot_choices_row

    if has_plot_ui:
        ui.ref_plot_ui_row = pn.Row()
        ui.widget_container.append(ui.ref_plot_ui_row)
    elif hasattr(ui, "ref_plot_ui_row"):
        del ui.ref_plot_ui_row

    # Trigger the reference plot choices UI display method
    ui._ref_display_plot_choices_ui()

    # Verify that the reference X-axis dropdown and plot button names are correctly set
    assert ui.ref_x_axis_dropdown.name == "Select X-Axis dimension"
    assert ui.ref_plot_button.name == "Plot data"

    # Verify that previous reference plot choice rows are successfully cleaned up from the container
    if has_existing_row:
        for item in ui.widget_container:
            if hasattr(item, "name"):
                assert item.name != "old_row"

    # Verify expected outcomes for dimension check failures, automatic plotting, or successful UI layout generation
    if expected_outcome == "fail_dim_check":
        assert ui.ref_plot_type_dropdown.value == "Line"
        assert (
            ui.ref_warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot a Heatmap."
        )
        assert (
            not hasattr(ui, "ref_plot_choices_row")
            or ui.ref_plot_choices_row not in ui.widget_container
        )

    elif expected_outcome == "auto_plot_line":
        assert (
            ui.ref_warning_textbox.value
            == "Only one valid x-axis dimension, plotting automatically."
        )
        assert ui.ref_x_axis_dropdown.value == "time"
        mock_ref_plot_data_button_click.assert_called_once()
        assert not hasattr(ui, "ref_plot_choices_row")

    elif expected_outcome == "fail_dim_check_animation":
        assert (
            ui.ref_warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot an animation."
        )
        assert ui.ref_plot_type_dropdown.value == "Line"
        assert not hasattr(ui, "ref_plot_choices_row")

    else:
        assert ui.ref_plot_choices_row in ui.widget_container

        if has_plot_ui:
            assert (
                ui.widget_container.index(ui.ref_plot_choices_row)
                == ui.widget_container.index(ui.ref_plot_ui_row) + 1
            )

        if expected_outcome == "success_heatmap":
            assert ui.ref_y_axis_dropdown.name == "Select Y-Axis dimension"
            assert len(ui.ref_plot_choices_row) == 3  # x, y, button
        elif expected_outcome == "success_line":
            assert len(ui.ref_plot_choices_row) == 2  # x, button
        elif expected_outcome == "success_animation":
            assert ui.ref_y_axis_dropdown.name == "Select Y-Axis dimension"
            assert ui.ref_animation_axis_dropdown.name == "Select Z-Axis dimension"
            assert len(ui.ref_plot_choices_row) == 4  # x, y, z, button


@pytest.mark.parametrize(
    "plot_type, dim_dict, has_selection_row, bounds, expected_outcome",
    [
        ("Heatmap (grid)", {"time": 10, "lat": 10}, False, False, "success_heatmap"),
        (
            "Heatmap (grid)",
            {"time": 10, "nv": 5, "scalar": 1},
            False,
            False,
            "fail_dim_check",
        ),
        ("Line", {"time": 10, "lat": 10}, True, False, "success_line"),
        ("Line", {"time": 10}, False, False, "auto_plot_line"),
        ("Line", {"time": 10}, False, True, "one_dim_bounds_line"),
    ],
)
def test_display_multiplot_plot_choices_ui(
    ui, monkeypatch, plot_type, dim_dict, has_selection_row, bounds, expected_outcome
):
    """Test the configuration and layout of multiplot choices UI across different plot types, dimensions, and bounds check states"""

    # Create a dataset with specified dimensions, sizes, and coordinate values for multiplot evaluation
    coords = {dim: np.arange(size) for dim, size in dim_dict.items()}
    size = tuple(dim_dict.values())
    data_array = xr.DataArray(
        np.random.rand(*size), dims=list(dim_dict.keys()), coords=coords
    )
    ui.dataset = xr.Dataset({"data": data_array})
    ui._multiplot_check_bounds = MagicMock(return_value=bounds)

    # Mock the bounds UI prompt handler to prevent interactive display during testing
    mock_prompt_bounds_ui = MagicMock()
    monkeypatch.setattr(ui, "_prompt_bounds_ui", mock_prompt_bounds_ui)

    ui.multiplot_plot_variable_dropdown.value = "data"

    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.widget_container.clear()

    # Conditionally configure the type selection row in the widget container to verify relative layout placement
    if has_selection_row:
        ui.multiplot_type_selection_row = pn.Row(
            pn.pane.Markdown("Dummy"), name="selection_row"
        )
        ui.widget_container.append(ui.multiplot_type_selection_row)
    elif hasattr(ui, "multiplot_type_selection_row"):
        del ui.multiplot_type_selection_row

    # Trigger the multiplot plot choices UI display method
    ui._display_multiplot_plot_choices_ui()

    # Verify that multiplot X-axis, analysis dropdown, and plot button names and options are correctly set
    assert ui.multiplot_x_axis_dropdown.name == "Select X-Axis dimension"
    assert ui.multiplot_analysis_choice_dropdown.name == "Select analysis type"
    assert ui.multiplot_analysis_choice_dropdown.options == [
        "None (plot all loaded data)",
        "Plot Difference (Ref. - User data)",
        "Plot All Data & Difference",
    ]
    assert ui.multiplot_plot_button.name == "Plot data"

    # Verify expected outcomes for dimension check failures, automatic line plotting, bounds prompts, or successful multiplot UI layouts
    if expected_outcome == "fail_dim_check":
        assert ui.multiplot_plot_type_dropdown.value == "Line"
        assert (
            ui.multiplot_warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot a Heatmap."
        )

    elif expected_outcome == "auto_plot_line":
        ui._multiplot_check_bounds.assert_called_once()
        assert ui.multiplot_warning_textbox.value == "Only one valid x-axis dimension."

    elif expected_outcome == "one_dim_bounds_line":
        mock_prompt_bounds_ui.assert_called_once()

    elif expected_outcome == "fail_dim_check_animation":
        assert (
            ui.multiplot_warning_textbox.value
            == "Warning >> Not enough dimensions available for this variable to plot an animation."
        )
        assert ui.multiplot_plot_type_dropdown.value == "Line"
        assert not hasattr(ui, "multiplot_plot_choices_row")

    else:
        assert ui.multiplot_plot_choices_row in ui.widget_container
        if has_selection_row:
            assert (
                ui.widget_container.index(ui.multiplot_plot_choices_row)
                == ui.widget_container.index(ui.multiplot_type_selection_row) + 1
            )

        if expected_outcome == "success_heatmap":
            assert ui.multiplot_y_axis_dropdown.name == "Select Y-Axis dimension"
            assert len(ui.multiplot_plot_choices_row) == 4  # x, y, analysis, button
        elif expected_outcome == "success_line":
            ui._multiplot_check_bounds.assert_called_once()
            assert len(ui.multiplot_plot_choices_row) == 3  # x, analysis, button
        elif expected_outcome == "success_animation":
            assert ui.multiplot_y_axis_dropdown.name == "Select Y-Axis dimension"
            assert (
                ui.multiplot_animation_axis_dropdown.name == "Select Z-Axis dimension"
            )
            assert len(ui.multiplot_plot_choices_row) == 5  # x, y, z, analysis, button

def test_update_dataset_plot_ui(ui):
    """Test updating the dataset plot UI variables and multiplot dropdown options when a new dataset is loaded""" 

    # Mock matplotlib close to verify figure cleanup during dataset updates
    plt.close = MagicMock()
    ui.multiplot_ref_keys_selection_row = pn.Row(pn.pane.Markdown("row"))

    # Trigger the dataset plot UI update method
    ui._update_dataset_plot_ui()

    # Verify that plot variable dropdown options match the dataset keys for both primary and multiplot selectors
    assert ui.plot_variable_dropdown.options == sorted(list(ui.dataset.keys()))
    assert ui.multiplot_plot_variable_dropdown.options == sorted(
            list(ui.dataset.keys())
        )

    # Verify that the multiplot user dataset dropdown value synchronizes with the primary keys dropdown
    assert ui.multiplot_keys_dropdown.value == ui.keys_dropdown.value

    # Verify that matplotlib figures are closed to clean up memory
    plt.close.assert_called_once()

    plt.close.reset_mock()


def test_update_ref_dataset_keys_plot_ui(ui, monkeypatch):
    """Test updating reference dataset key options and triggering reference dataset plot updates"""

    # Mock matplotlib close and the reference dataset plot update method
    plt.close = MagicMock()
    mock_update_ref_dataset_plot_ui = MagicMock()
    monkeypatch.setattr(
        ui, "_update_ref_dataset_plot_ui", mock_update_ref_dataset_plot_ui
    )

    # Trigger the reference dataset keys plot UI update method
    ui._update_ref_dataset_keys_plot_ui()

    # Verify that reference data keys dropdown options are updated and cleanup handlers are called
    assert ui.ref_data_keys_dropdown.options == sorted(list(ui.ref_dataset.keys()))
    plt.close.assert_called_once()
    mock_update_ref_dataset_plot_ui.assert_called_once()


def test_update_ref_dataset_plot_ui(ui):
    """Test updating reference dataset plot variables and clearing existing reference figure panes"""

    # Mock matplotlib close and assign a mock reference figure and dataset
    plt.close = MagicMock()
    ui.ref_fig = "Figure"
    ui.ref_dataset = {"key1": None, "key4": None}

    # Trigger the reference dataset plot UI update method
    ui._update_ref_dataset_plot_ui()

    # Verify that reference variable dropdown options match the dataset keys and the plot pane object is cleared
    assert ui.ref_plot_variable_dropdown.options == sorted(list(ui.ref_dataset.keys()))
    assert not ui.ref_plot_pane.object
    plt.close.assert_called_once()


@pytest.mark.parametrize(
    "ui_row",
    [
        "multiplot_slice_ui_row", 
        "multiplot_plot_choices_row", 
        "multiplot_type_selection_row", 
        "multiplot_ref_keys_selection_row", 
        ""
    ],
)
def test_prompt_bounds_ui(ui, ui_row):
    """Test the configuration and relative layout positioning of the multiplot bounds prompting UI components""" 

    # Clear the widget container and conditionally append mock multiplot UI rows based on parameters
    ui.widget_container.clear()
    if ui_row == "multiplot_slice_ui_row":
        ui.multiplot_slice_ui_row = pn.Row(pn.pane.Markdown("something"))
        ui.widget_container.append(ui.multiplot_slice_ui_row)
    elif ui_row == "multiplot_plot_choices_row":
        ui.multiplot_plot_choices_row = pn.Row(pn.pane.Markdown("something"))
        ui.widget_container.append(ui.multiplot_plot_choices_row)
    elif ui_row == "multiplot_type_selection_row":
        ui.multiplot_type_selection_row = pn.Row(pn.pane.Markdown("something"))
        ui.widget_container.append(ui.multiplot_type_selection_row)
    elif ui_row == "multiplot_ref_keys_selection_row":
        ui.multiplot_ref_keys_selection_row = pn.Row(pn.pane.Markdown("something"))
        ui.widget_container.append(ui.multiplot_ref_keys_selection_row)

    # Trigger the prompt bounds UI generation method
    ui._prompt_bounds_ui()

    # Verify that the bounds dropdown name, options, and container row are correctly configured
    assert ui.prompt_bounds_dropdown.name == "Choose how to constrain the x-axis bounds"
    assert ui.prompt_bounds_dropdown.options == [
            "Constrain to user dataset bounds",
            "Constrain to min-max reference dataset bounds",
        ]
    assert hasattr(ui, "prompt_bounds_row")

    # Verify that the bounds prompt row is positioned immediately after the corresponding multiplot row in the container
    if ui_row == "multiplot_slice_ui_row":
        assert ui.widget_container.index(ui.prompt_bounds_row) == ui.widget_container.index(ui.multiplot_slice_ui_row) + 1
    elif ui_row == "multiplot_plot_choices_row":
        assert ui.widget_container.index(ui.prompt_bounds_row) == ui.widget_container.index(ui.multiplot_plot_choices_row) + 1
    elif ui_row == "multiplot_type_selection_row":
        assert ui.widget_container.index(ui.prompt_bounds_row) == ui.widget_container.index(ui.multiplot_type_selection_row) + 1
    elif ui_row == "multiplot_ref_keys_selection_row":
        assert ui.widget_container.index(ui.prompt_bounds_row) == ui.widget_container.index(ui.multiplot_ref_keys_selection_row) + 1

def test_plot_animation(ui, monkeypatch):
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

    # Configure UI values for dataset selection, axes, and chosen slices
    ui.keys_dropdown.value = "my_dataset"
    ui.x_axis_dropdown.value = "x"
    ui.y_axis_dropdown.value = "y"
    ui.animation_axis_dropdown.value = "time"
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ui.chosen_slices = {"z" : 1}
    
    # Execute the animation plotting method
    panel_returned = ui._plot_animation("data")

    # Verify that quadmesh is called on hvplot and a panel Column container is returned
    mock_hvplot.quadmesh.assert_called_once()
    assert isinstance(panel_returned, pn.Column)

def test_plot_ref_animation(ui, monkeypatch):
    """Test generating an animated quadmesh plot for reference datasets using hvplot with sliced dimensions"""

    # Mock hvplot on the xarray DataArray to intercept reference plotting calls during testing
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

    # Configure reference UI values for dataset selection, axes, and chosen slices
    ui.ref_keys_dropdown.value = "my_dataset"
    ui.ref_x_axis_dropdown.value = "x"
    ui.ref_y_axis_dropdown.value = "y"
    ui.ref_animation_axis_dropdown.value = "time"
    ds = xr.Dataset({"data": data})
    ui.ref_dataset = ds
    ui.ref_chosen_slices = {"z": 1}

    # Execute the reference animation plotting method
    panel_returned = ui._plot_ref_animation()

    # Verify that quadmesh is called on hvplot and a panel Column container is returned
    mock_hvplot.quadmesh.assert_called_once()
    assert isinstance(panel_returned, pn.Column)


@pytest.mark.parametrize(
    "fig_exists",
    [
        True,
        False
    ],
)
def test_keys_dropdown_click(ui, monkeypatch, fig_exists):
    """Test the dataset loading callback triggered when selecting a model from the keys dropdown""" 

    # Mock the data object builder and patch UI display/update methods based on figure existence
    mock_build_data_object = MagicMock()
    monkeypatch.setattr(med_data, "_build_data_object", mock_build_data_object)
    ui.figure_exists = fig_exists

    if fig_exists:
        mock_update_dataset_plot_ui = MagicMock()
        monkeypatch.setattr(ui, '_update_dataset_plot_ui', mock_update_dataset_plot_ui)
    else:
        mock_display_dataset_plot_ui = MagicMock()
        monkeypatch.setattr(ui, '_display_dataset_plot_ui', mock_display_dataset_plot_ui)

    # Configure mock catalog and dropdown selection on the UI instance
    ui.model_cat = {"fake": None, "catalog": None}
    ui.keys_dropdown.value = "an option"

    # Trigger the keys dropdown selection click handler
    ui._keys_dropdown_click()

    # Verify that the dataset builder is called with correct arguments
    mock_build_data_object.assert_called_once_with(ui.model_cat, ui.keys_dropdown.value)

    # Verify that loaded dataset tracking, status message, and button properties are updated correctly
    assert ui.loaded_dataset_key == ui.keys_dropdown.value
    assert ui.status_textbox.value == "User model status >> Data successfully loaded."
    assert ui.keys_button.name == "Load different dataset"

    # Verify that either the dataset plot UI update or initial display method is called appropriately
    if fig_exists:
        mock_update_dataset_plot_ui.assert_called_once_with()
    else:
        mock_display_dataset_plot_ui.assert_called_once_with()


def test_update_multiplot_dataset(ui, monkeypatch):
    """Test updating the multiplot user dataset, refreshing associated dropdowns, and clearing stale multiplot data""" 

    # Configure mock model catalog and multiplot dropdown selection
    ui.model_cat = {"fake": None, "catalog": None}
    ui.multiplot_keys_dropdown.value = "an option"

    # Mock the data object builder and multiplot data clearing method
    mock_build_data_object = MagicMock()
    monkeypatch.setattr(med_data, "_build_data_object", mock_build_data_object)

    mock_clear_multiplot_data = MagicMock()
    monkeypatch.setattr(ui, "_clear_multiplot_data", mock_clear_multiplot_data)

    # Trigger the multiplot dataset update method
    ui._update_multiplot_dataset()

    # Verify that the dataset builder is called with the correct multiplot catalog and key
    mock_build_data_object.assert_called_once_with(ui.model_cat, ui.multiplot_keys_dropdown.value)

    # Verify that dataset tracking keys, variable dropdown options, primary dropdown synchronization, and status messages are correctly updated
    assert ui.loaded_dataset_key == ui.multiplot_keys_dropdown.value
    assert ui.multiplot_plot_variable_dropdown.options == sorted(list(ui.dataset.keys()))
    assert ui.keys_dropdown.value == ui.loaded_dataset_key
    assert ui.plot_variable_dropdown.options == sorted(list(ui.dataset.keys()))
    assert ui.multiplot_status_textbox.value == "Overlay Plot Status >> New user dataset loaded, clearing loaded user models"
    
    # Verify that old multiplot data is cleared out
    mock_clear_multiplot_data.assert_called_once()


@pytest.mark.parametrize(
    "selection_row_exists",
    [True, False],
)
def test_ref_keys_dropdown_click(ui, monkeypatch, selection_row_exists):
    """Test the reference model dropdown selection callback for loading catalogs and initializing reference dataset UI components""" 

    # Mock the catalog search response and patch the reference dataset selection UI display method
    mock_cat = MagicMock()
    mock_cat.search.return_value.to_source.return_value = {"fake_catalog": None}
    monkeypatch.setattr(ui, "access_nri_cat", mock_cat)

    mock_display_reference_dataset_selection_ui = MagicMock()
    monkeypatch.setattr(ui, "_display_reference_dataset_selection_ui", mock_display_reference_dataset_selection_ui)

    # Conditionally configure the reference data keys selection row in the widget container
    if selection_row_exists:
        ui.ref_data_keys_selection_row = pn.Row()
        ui.widget_container.append(ui.ref_data_keys_selection_row)
    else:
        ui.widget_container.clear()

    # Trigger the reference keys dropdown click handler
    ui._ref_keys_dropdown_click()

    # Verify that the reference status message is successfully updated and catalog search is executed
    assert (
        ui.ref_status_textbox.value
        == "Reference model status >> Data catalog successfully loaded."
    )

    mock_cat.search.assert_called_once()

    # Verify that either reference options are updated in place or the UI display method is called depending on container state
    if selection_row_exists:
        assert ui.ref_data_keys_dropdown.options == sorted(list(ui.ref_model_cat.keys()))
    else:
        mock_display_reference_dataset_selection_ui.assert_called_once()


@pytest.mark.parametrize(
    "has_dict, matching_catalog, already_loaded, user_selection_changed",
    [
        (True, False, False, False),
    (False, True, False, False),
    (True, True, False, False),
    (True, True, True, False),
    (True, True, False, True),
    ],
)
def test_multiplot_ref_keys_dropdown_click(ui, monkeypatch, has_dict, matching_catalog, already_loaded, user_selection_changed):
    """Test the multiplot reference keys dropdown selection callback for loading reference models, validating datasets, and handling duplicate or mismatched selections""" 

    # Mock the catalog search response and the data object builder for reference datasets
    mock_cat = MagicMock()
    mock_cat.search.return_value.to_source.return_value = {"fake_catalog": None}
    monkeypatch.setattr(ui, "access_nri_cat", mock_cat)

    mock_ref_dataset = MagicMock()
    mock_ref_dataset.coords = {"time": None}
    mock_ref_dataset.indexes.get.return_value = MagicMock()

    mock_build_data_object = MagicMock(return_value=mock_ref_dataset)
    monkeypatch.setattr(med_data, "_build_data_object", mock_build_data_object)

    mock_clear_multiplot_data = MagicMock()
    monkeypatch.setattr(ui, "_clear_multiplot_data", mock_clear_multiplot_data)

    # Configure mock user dataset with time coordinates
    ui.dataset = MagicMock()
    ui.dataset.coords = {"time": None}
    ui.dataset.indexes.get.return_value = MagicMock()

    ui.multiplot_ref_keys_dropdown.value = "my_ref_model"

    # Set up matching or mismatching catalog options based on parameters
    if matching_catalog:
        ui.multiplot_keys_dropdown.value = "fake_catalog"
    else:
        ui.multiplot_keys_dropdown.value = "something_else"

    # Configure existing multiplot reference dataset dictionary states
    if already_loaded: 
            ui.multiplot_ref_dataset_dict = {"Key1": None, "my_ref_model": None}
    else:
        if has_dict:
            ui.multiplot_ref_dataset_dict = {"Key1": None, "Key2": None}
        else:
            if hasattr(ui, "multiplot_ref_dataset_dict"):
                del ui.multiplot_ref_dataset_dict

    # Configure user selection change state
    if user_selection_changed:
        ui.loaded_dataset_key = "a_previous_selection"
    else:
        ui.loaded_dataset_key = ui.multiplot_keys_dropdown.value

    # Trigger the multiplot reference keys dropdown click handler
    ui._multiplot_ref_keys_dropdown_click()

    # Verify that the catalog search is executed
    mock_cat.search.assert_called_once()

    # Verify expected build counts, duplicate warnings, and mismatch warnings based on catalog matching and load states
    if matching_catalog and not already_loaded:
        expected_build_calls = 2 if user_selection_changed else 1
        assert mock_build_data_object.call_count == expected_build_calls
        mock_ref_dataset.convert_calendar.assert_not_called()
    elif matching_catalog and already_loaded:
        assert (
            ui.multiplot_warning_textbox.value
            == "Warning >> Model has already been added, skipping duplicate"
        )
    elif not matching_catalog:
        assert (
            ui.multiplot_warning_textbox.value
            == "Overlay Plot Status >> There is no dataset matching the user dataset in this model, please select another"
        )

    # Verify that state cleanup and status updates occur correctly when user selection changes
    if user_selection_changed:
        assert (
            ui.multiplot_status_textbox.value
            == "Overlay Plot Status >> New user dataset loaded, clearing loaded user models"
        )
        assert ui.loaded_dataset_key == ui.multiplot_keys_dropdown.value
        assert ui.multiplot_plot_variable_dropdown.options == sorted(list(ui.dataset.keys()))
        mock_clear_multiplot_data.assert_called_once()

@pytest.mark.parametrize(
    "fig_exists",
    [True, False],
)
def test_ref_dataset_dropdown_click(ui, monkeypatch, fig_exists):
    """Test the reference dataset dropdown selection callback for loading reference data objects and updating reference UI components"""

    # Mock the data object builder and patch reference dataset plot display and update methods
    mock_build_data_object = MagicMock()
    monkeypatch.setattr(med_data, "_build_data_object", mock_build_data_object)

    mock_ref_display_dataset_plot_ui = MagicMock()
    monkeypatch.setattr(
        ui, "_ref_display_dataset_plot_ui", mock_ref_display_dataset_plot_ui
    )

    mock_update_ref_dataset_plot_ui = MagicMock()
    monkeypatch.setattr(
        ui, "_update_ref_dataset_plot_ui", mock_update_ref_dataset_plot_ui
    )

    # Configure reference figure existence state based on parameters
    if fig_exists:
        ui.ref_figure_exists = True
    else:
        ui.ref_figure_exists = False

    # Trigger the reference dataset dropdown click handler
    ui._ref_dataset_dropdown_click()

    # Verify that the dataset builder is invoked and reference status message is updated
    mock_build_data_object.assert_called_once()
    assert (
        ui.ref_status_textbox.value
        == "Reference model status >> Reference dataset successfully loaded."
    )

    # Verify that either the reference dataset plot UI update or initial display method is called based on figure existence
    if fig_exists:
        mock_update_ref_dataset_plot_ui.assert_called_once()
    else:
        mock_ref_display_dataset_plot_ui.assert_called_once()


def test_ref_model_info_click(ui, monkeypatch):
    """Test the reference model info button callback for fetching catalog metadata and rendering HTML details in the UI""" 

    # Mock the catalog access and metadata dictionary to return fake info items
    mock_cat = MagicMock()
    mock_metadata = MagicMock()
    mock_metadata.__getitem__.return_value = "fake_info"
    mock_cat.__getitem__.return_value.metadata = mock_metadata
    monkeypatch.setattr(ui, "access_nri_cat", mock_cat)

    ui.ref_keys_dropdown.value = "selection"

    # Trigger the reference model info button click handler
    ui._ref_model_info_click()
    
    # Verify that the catalog access count and key lookup match expected behavior, and status textbox is reset
    assert mock_cat.__getitem__.call_count == 7
    mock_cat.__getitem__.assert_called_with("selection")
    assert ui.ref_status_textbox.value == ""

    # Verify that the generated HTML metadata output contains the expected model and email information strings
    html_output = ui.ref_model_metadata.value
    assert "<b>Model:   </b>fake_info<br>" in html_output
    assert "<b>Email:   </b>fake_info<br>" in html_output


@pytest.mark.parametrize(
    "plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen",
    [
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
        (False, False, False, True)
    ],
)
def test_plot_button_click(ui, monkeypatch, plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen):
    """Test the primary plot button click handler across various validation checks, slicing requirements, and error warning states""" 

    # Mock plot validity checkers, plotting triggers, slice checks, and choice UI display methods
    mock_check_plot_validity = MagicMock(return_value=(plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen))
    monkeypatch.setattr(ui, "_check_plot_validity", mock_check_plot_validity)
    
    mock_plot_data_button_click = MagicMock()
    monkeypatch.setattr(ui, "_plot_data_button_click", mock_plot_data_button_click)
    
    mock_check_slice = MagicMock()
    monkeypatch.setattr(ui, "_check_slice", mock_check_slice)
    
    mock_display_plot_choices_ui = MagicMock()
    monkeypatch.setattr(ui, "_display_plot_choices_ui", mock_display_plot_choices_ui)

    ui.plot_choices_row = pn.Row(name = "plot choices row")
    ui.widget_container.append(ui.plot_choices_row)
    ui.slice_ui_row = pn.Row()
    ui.slice_widgets = {"dim": pn.pane.Markdown("A widget")}
    ui.widget_container.append(ui.slice_ui_row)
    
    # Trigger the plot button click handler with a dummy event argument
    ui._plot_button_click(None)

    # Verify that the correct action or warning is executed based on the plot validity and error flags
    if plot_valid:
        mock_plot_data_button_click.assert_called()
        
    elif requires_slice:
        mock_check_slice.assert_called_once()
    elif invalid_heatmap_data:
        assert ui.warning_textbox.value == "Warning >> The dataset only has one plottable dimension. Defaulting to line plot."
        assert ui.plot_type_dropdown.value == "Line"
        mock_plot_data_button_click.assert_called()
    elif same_axes_chosen:
        assert ui.warning_textbox.value == "Warning >> Please ensure different values are selected for each axis."
        mock_display_plot_choices_ui.assert_called_once()
        assert ui.plot_choices_row not in ui.widget_container
        assert not hasattr(ui, "slice_ui_row")



@pytest.mark.parametrize(
    "plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen",
    [
        (True, False, False, False),
        (False, True, False, False),
        (False, False, True, False),
        (False, False, False, True),
    ],
)
def test_ref_plot_button_click(
    ui, monkeypatch, plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen
):
    """Test the reference plot button click handler across various validation checks, slicing requirements, and error warning states"""

    # Mock reference plot validity checkers, plotting triggers, slice checks, and choice UI display methods
    mock_check_plot_validity = MagicMock(
        return_value=(
            plot_valid,
            requires_slice,
            invalid_heatmap_data,
            same_axes_chosen,
        )
    )
    monkeypatch.setattr(ui, "_ref_check_plot_validity", mock_check_plot_validity)

    mock_plot_data_button_click = MagicMock()
    monkeypatch.setattr(ui, "_ref_plot_data_button_click", mock_plot_data_button_click)

    mock_check_slice = MagicMock()
    monkeypatch.setattr(ui, "_ref_check_slice", mock_check_slice)

    mock_display_plot_choices_ui = MagicMock()
    monkeypatch.setattr(
        ui, "_ref_display_plot_choices_ui", mock_display_plot_choices_ui
    )

    ui.ref_plot_choices_row = pn.Row(name = "plot choices row")
    ui.widget_container.append(ui.ref_plot_choices_row)
    ui.ref_slice_ui_row = pn.Row()
    ui.ref_slice_widgets = {"dim": pn.pane.Markdown("A widget")}
    ui.widget_container.append(ui.ref_slice_ui_row)

    # Trigger the reference plot button click handler with a dummy event argument
    ui._ref_plot_button_click(None)

    # Verify that the correct reference action or warning is executed based on the plot validity and error flags
    if plot_valid:
        mock_plot_data_button_click.assert_called()
    elif requires_slice:
        mock_check_slice.assert_called_once()
    elif invalid_heatmap_data:
        assert (
            ui.ref_warning_textbox.value
            == "Warning >> The dataset only has one plottable dimension. Defaulting to line plot."
        )
        assert ui.ref_plot_type_dropdown.value == "Line"
        mock_plot_data_button_click.assert_called()
    elif same_axes_chosen:
        assert (
            ui.ref_warning_textbox.value
            == "Warning >> Please ensure different values are selected for each axis."
        )
        mock_display_plot_choices_ui.assert_called_once()
        assert ui.ref_plot_choices_row not in ui.widget_container
        assert not hasattr(ui, "ref_slice_ui_row")

@pytest.mark.parametrize(
    "plot_valid, requires_slice, prompt_bounds",
    [
        (True, False, False),
        (False, True, False),
        (False, False, True)
    ],
)
def test_multiplot_plot_button_click(ui, monkeypatch, plot_valid, requires_slice, prompt_bounds):
    """Test the multiplot data button click handler across validation checks, slicing requirements, and bounds prompting states""" 

    # Mock multiplot plot validity checkers, plotting triggers, slice checks, and bounds prompt UI methods
    mock_check_plot_validity = MagicMock(
            return_value=(
                plot_valid,
                requires_slice,
                prompt_bounds
            )
        )
    monkeypatch.setattr(ui, "_check_multiplot_plot_validity", mock_check_plot_validity)

    mock_plot_data_button_click = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_plot_data_button_click", mock_plot_data_button_click)
    
    mock_check_slice = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_check_slice", mock_check_slice)
    
    mock_prompt_bounds_ui = MagicMock()
    monkeypatch.setattr(ui, "_prompt_bounds_ui", mock_prompt_bounds_ui)

    # Trigger the multiplot plot button click handler with a dummy event argument
    ui._multiplot_plot_button_click(None)

    # Verify that the correct multiplot action or UI prompt is executed based on validity and flag states
    if plot_valid:
        mock_plot_data_button_click.assert_called_once()
    elif requires_slice:
        mock_check_slice.assert_called_once()
    elif prompt_bounds:
        mock_prompt_bounds_ui.assert_called_once()


def test_keys_button_click(ui, monkeypatch):
    """Test that pressing the keys button triggers the correct internal method."""
    
    mock_keys_dropdown_click = MagicMock()
    monkeypatch.setattr(ui, "_keys_dropdown_click", mock_keys_dropdown_click)

    # Simulate clicking the button
    ui.keys_button.clicks += 1
    
    # Verify the bound function was executed
    mock_keys_dropdown_click.assert_called_once()

def test_ref_keys_button_click(ui, monkeypatch):
    """Test that pressing the ref keys button triggers the correct internal method."""
    
    mock_keys_dropdown_click = MagicMock()
    monkeypatch.setattr(ui, "_ref_keys_dropdown_click", mock_keys_dropdown_click)

    # Simulate clicking the button
    ui.ref_keys_button.clicks += 1
    
    # Verify the bound function was executed
    mock_keys_dropdown_click.assert_called_once()

def test_ref_data_keys_button_click(ui, monkeypatch):
    """Test that pressing the ref data keys button triggers the correct internal method."""
    
    mock_ref_data_keys_button_click = MagicMock()
    monkeypatch.setattr(ui, "_ref_dataset_dropdown_click", mock_ref_data_keys_button_click)

    # Simulate clicking the button
    ui.ref_data_keys_button.clicks += 1
    
    # Verify the bound function was executed
    mock_ref_data_keys_button_click.assert_called_once()

def test_ref_model_info_button_click(ui, monkeypatch):
    """Test that pressing the ref model info button triggers the correct internal method."""
    
    mock_ref_model_info_click = MagicMock()
    monkeypatch.setattr(ui, "_ref_model_info_click", mock_ref_model_info_click)

    # Simulate clicking the button
    ui.ref_model_info_button.clicks += 1
    
    # Verify the bound function was executed
    mock_ref_model_info_click.assert_called_once()

def test_ref_clear_data_button_click(ui, monkeypatch):
    """Test that pressing the ref clear data button triggers the correct internal method."""
    
    mock_ref_clear_data_click = MagicMock()
    monkeypatch.setattr(ui, "_ref_clear_data_click", mock_ref_clear_data_click)

    # Simulate clicking the button
    ui.clear_ref_model_data_button.clicks += 1
    
    # Verify the bound function was executed
    mock_ref_clear_data_click.assert_called_once()

def test_select_variable_button_click(ui, monkeypatch):
    """Test that pressing the select variabel button triggers the correct internal method."""
    
    mock_display_plot_choices_ui = MagicMock()
    monkeypatch.setattr(ui, "_display_plot_choices_ui", mock_display_plot_choices_ui)

    # Simulate clicking the button
    ui.select_variable_button.clicks += 1
    
    # Verify the bound function was executed
    mock_display_plot_choices_ui.assert_called_once()

def test_ref_select_variable_button_click(ui, monkeypatch):
    """Test that pressing the ref select variabel button triggers the correct internal method."""
    
    mock_display_plot_choices_ui = MagicMock()
    monkeypatch.setattr(ui, "_ref_display_plot_choices_ui", mock_display_plot_choices_ui)

    # Simulate clicking the button
    ui.ref_select_variable_button.clicks += 1
    
    # Verify the bound function was executed
    mock_display_plot_choices_ui.assert_called_once()

def test_multiplot_select_variable_button_click(ui, monkeypatch):
    """Test that pressing the multiplot_ref_keys_button triggers the correct internal method."""
    
    mock_multiplot_ref_keys_dropdown_click = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_ref_keys_dropdown_click", mock_multiplot_ref_keys_dropdown_click)

    # Simulate clicking the button
    ui.multiplot_ref_keys_button.clicks += 1
    
    # Verify the bound function was executed
    mock_multiplot_ref_keys_dropdown_click.assert_called_once()

def test_clear_multiplot_data_button_click(ui, monkeypatch):
    """Test that pressing the clear_multiplot_data_button triggers the correct internal method."""
    
    mock_clear_multiplot_data = MagicMock()
    monkeypatch.setattr(ui, "_clear_multiplot_data", mock_clear_multiplot_data)

    # Simulate clicking the button
    ui.clear_multiplot_data_button.clicks += 1
    
    # Verify the bound function was executed
    mock_clear_multiplot_data.assert_called_once()

def test_multiplot_keys_update_button_click(ui, monkeypatch):
    """Test that pressing the multiplot_keys_update_button triggers the correct internal method."""
    
    mock_update_multiplot_dataset = MagicMock()
    monkeypatch.setattr(ui, "_update_multiplot_dataset", mock_update_multiplot_dataset)

    # Simulate clicking the button
    ui.multiplot_keys_update_button.clicks += 1
    
    # Verify the bound function was executed
    mock_update_multiplot_dataset.assert_called_once()


def test_multiplot_select_variable_button_click(ui, monkeypatch):
    """Test that pressing the multiplot_select_variable_button triggers the correct internal method."""
    
    mock_display_multiplot_plot_choices_ui = MagicMock()
    monkeypatch.setattr(ui, "_display_multiplot_plot_choices_ui", mock_display_multiplot_plot_choices_ui)

    # Simulate clicking the button
    ui.multiplot_select_variable_button.clicks += 1
    
    # Verify the bound function was executed
    mock_display_multiplot_plot_choices_ui.assert_called_once()

def test_multiplot_ref_keys_button_click(ui, monkeypatch):
    """Test that pressing the multiplot_ref_keys_button triggers the correct internal method."""
    
    mock_display_multiplot_plot_choices_ui  = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_ref_keys_dropdown_click", mock_display_multiplot_plot_choices_ui)

    # Simulate clicking the button
    ui.multiplot_ref_keys_button.clicks += 1
    
    # Verify the bound function was executed
    mock_display_multiplot_plot_choices_ui.assert_called_once()

def test_prompt_bounds_button_click(ui, monkeypatch):
    """Test that pressing the prompt_bounds_button triggers the correct internal method."""
    
    mock_multiplot_plot_data_button_click  = MagicMock()
    monkeypatch.setattr(ui, "_multiplot_plot_data_button_click", mock_multiplot_plot_data_button_click)

    # Simulate clicking the button
    ui.prompt_bounds_button.clicks += 1
    
    # Verify the bound function was executed
    mock_multiplot_plot_data_button_click.assert_called_once()