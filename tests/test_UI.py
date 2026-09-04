# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for tests"""

from med_diagnostics.ui import UserInterface
import pytest
import xarray as xr
import numpy as np


@pytest.fixture(scope="session")
def ui():
    return UserInterface()


def run_validity_check(ui, is_ref, dimensions, x, y, z, ptype, var):
    """Helper to dynamically generate datasets, populate the UI, and return validity results."""
    # 1. Generate dataset with the requested number of dimensions
    dim_names = ["x", "y", "z", "w"][:dimensions]
    shape = tuple([10] * dimensions)
    coords = {d: np.arange(10) for d in dim_names}
    ds = xr.Dataset({"data": xr.DataArray(np.random.rand(*shape), dims=dim_names, coords=coords)})

    # 2. Assign to correct UI attributes and execute the check
    if is_ref:
        ui.ref_dataset = ds
        ui.ref_x_axis_dropdown.value = x
        ui.ref_y_axis_dropdown.value = y
        ui.ref_animation_axis_dropdown.value = z
        ui.ref_plot_type_dropdown.value = ptype
        ui.ref_plot_variable_dropdown.value = var
        return ui._ref_check_plot_validity()
    else:
        ui.dataset = ds
        ui.x_axis_dropdown.value = x
        ui.y_axis_dropdown.value = y
        ui.animation_axis_dropdown.value = z
        ui.plot_type_dropdown.value = ptype
        ui.plot_variable_dropdown.value = var
        return ui._check_plot_validity()


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
    assert ui._round_slice_val(input_value) == expected_output


# @pytest.mark.parametrize("is_ref", [False, True])
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
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ui.dataset = xr.Dataset({"data": data})
    ui.x_axis_dropdown.value = x_value
    ui.y_axis_dropdown.value = y_value
    ui.animation_axis_dropdown.value = z_value
    ui.plot_type_dropdown.value = plot_type
    ui.plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 2D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10), dims=["x", "y"], coords={"x": np.arange(10), "y": np.arange(10)})
    ui.dataset = xr.Dataset({"data": data})
    ui.x_axis_dropdown.value = x_value
    ui.y_axis_dropdown.value = y_value
    ui.animation_axis_dropdown.value = z_value
    ui.plot_type_dropdown.value = plot_type
    ui.plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 3D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10, 10), dims=["x", "y", "z"], coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)})
    ui.dataset = xr.Dataset({"data": data})
    ui.x_axis_dropdown.value = x_value
    ui.y_axis_dropdown.value = y_value
    ui.animation_axis_dropdown.value = z_value
    ui.plot_type_dropdown.value = plot_type
    ui.plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 4D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10, 10),
        dims=["x", "y", "z", "w"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10), "w": np.arange(10)},
    )
    ui.dataset = xr.Dataset({"data": data})
    ui.x_axis_dropdown.value = x_value
    ui.y_axis_dropdown.value = y_value
    ui.animation_axis_dropdown.value = z_value
    ui.plot_type_dropdown.value = plot_type
    ui.plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
def test_ref_check_plot_validity_1d(
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ui.ref_dataset = xr.Dataset({"data": data})
    ui.ref_x_axis_dropdown.value = x_value
    ui.ref_y_axis_dropdown.value = y_value
    ui.ref_animation_axis_dropdown.value = z_value
    ui.ref_plot_type_dropdown.value = plot_type
    ui.ref_plot_variable_dropdown.value = variable_value
    # Now perform tests for the reference datasets as well
    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._ref_check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
def test_ref_check_plot_validity_2d(
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 2D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10), dims=["x", "y"], coords={"x": np.arange(10), "y": np.arange(10)})
    ui.ref_dataset = xr.Dataset({"data": data})
    ui.ref_x_axis_dropdown.value = x_value
    ui.ref_y_axis_dropdown.value = y_value
    ui.ref_animation_axis_dropdown.value = z_value
    ui.ref_plot_type_dropdown.value = plot_type
    ui.ref_plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._ref_check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
def test_ref_check_plot_validity_3d(
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 3D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10, 10), dims=["x", "y", "z"], coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)})
    ui.ref_dataset = xr.Dataset({"data": data})
    ui.ref_x_axis_dropdown.value = x_value
    ui.ref_y_axis_dropdown.value = y_value
    ui.ref_animation_axis_dropdown.value = z_value
    ui.ref_plot_type_dropdown.value = plot_type
    ui.ref_plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._ref_check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output


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
def test_ref_check_plot_validity_4d(
    ui, x_value, y_value, z_value, plot_type, variable_value, plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output
):
    # Create a 4D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10, 10),
        dims=["x", "y", "z", "w"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10), "w": np.arange(10)},
    )
    ui.ref_dataset = xr.Dataset({"data": data})
    ui.ref_x_axis_dropdown.value = x_value
    ui.ref_y_axis_dropdown.value = y_value
    ui.ref_animation_axis_dropdown.value = z_value
    ui.ref_plot_type_dropdown.value = plot_type
    ui.ref_plot_variable_dropdown.value = variable_value

    plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = ui._check_plot_validity()
    assert plot_valid is plot_valid_output
    assert requires_slice is requires_slice_output
    assert invalid_heatmap_data is invalid_heatmap_output
    assert same_axes_chosen is same_axes_output
