# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for tests"""

from access_nri_intake import data

from med_diagnostics.ui import UserInterface
import pytest
import xarray as xr
import numpy as np


@pytest.fixture(scope="session")
def ui():
    return UserInterface()


def run_validity_check(ui, is_ref, x, y, z, ptype, var, ds):
    """Checks validity of both reference and user plots based on selections."""
    # Assign to correct UI attributes and execute the check
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
    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})
    results = run_validity_check(ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds)
    assert results == (plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output)


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
    # Create a 2D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10), dims=["x", "y"], coords={"x": np.arange(10), "y": np.arange(10)})
    ds = xr.Dataset({"data": data})
    results = run_validity_check(ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds)
    assert results == (plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output)


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
    # Create a 3D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10, 10), dims=["x", "y", "z"], coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)})
    ds = xr.Dataset({"data": data})
    results = run_validity_check(ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds)
    assert results == (plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output)


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
    # Create a 4D xarray dataset
    data = xr.DataArray(
        np.random.rand(10, 10, 10, 10),
        dims=["x", "y", "z", "w"],
        coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10), "w": np.arange(10)},
    )
    ds = xr.Dataset({"data": data})
    results = run_validity_check(ui, is_ref, x_value, y_value, z_value, plot_type, variable_value, ds)
    assert results == (plot_valid_output, requires_slice_output, invalid_heatmap_output, same_axes_output)


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
    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
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
    # Create a 1D xarray dataset
    data = xr.DataArray(np.random.rand(10), dims=["x"], coords={"x": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)


@pytest.mark.parametrize(
    "x_value, y_value, plot_type, variable_value, plot_valid_output, requires_slice_output, check_bounds_output",
    [
        ("x", "", "Line", "data", False, True, False),
        ("x", "y", "Line", "data", False, True, False),
        ("x", "y", "Heatmap (grid)", "data", True, False, False),
        ("x", "x", "Heatmap (grid)", "data", False, False, False),
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
):
    # Create a 2D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10), dims=["x", "y"], coords={"x": np.arange(10), "y": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)


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
    # Create a 2D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10), dims=["x", "y"], coords={"x": np.arange(10), "y": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
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
    # Create a 3D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10, 10), dims=["x", "y", "z"], coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ui.multiplot_ref_dataset_dict = {"key": ds, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
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
    # Create a 3D xarray dataset
    data = xr.DataArray(np.random.rand(10, 10, 10), dims=["x", "y", "z"], coords={"x": np.arange(10), "y": np.arange(10), "z": np.arange(10)})
    ds = xr.Dataset({"data": data})
    ui.dataset = ds
    ds_different_bounds = ds.assign_coords(x=ds["x"] * 2)
    ui.multiplot_ref_dataset_dict = {"key": ds_different_bounds * 2, "key2": ds}
    ui.multiplot_x_axis_dropdown.value = x_value
    ui.multiplot_y_axis_dropdown.value = y_value
    ui.multiplot_plot_type_dropdown.value = plot_type
    ui.multiplot_plot_variable_dropdown.value = variable_value
    results = ui._check_multiplot_plot_validity()
    assert results == (plot_valid_output, requires_slice_output, check_bounds_output)
