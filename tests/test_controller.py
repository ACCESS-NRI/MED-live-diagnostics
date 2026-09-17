import datetime
from unittest.mock import MagicMock, call, patch

import cftime
import matplotlib.pyplot as plt
import numpy as np
import panel as pn
import pytest
import xarray as xr

import med_diagnostics.data as med_data
from med_diagnostics import controller
from med_diagnostics.types import Animation, Heatmap, Line
from med_diagnostics.ui import UserInterface


@pytest.fixture(scope="function")
def ui():
    """Return a session-scoped UserInterface instance for testing"""

    ui = UserInterface()
    return ui


@pytest.mark.parametrize(
    "input_text",
    ["A word", 1, 1.0, True],
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
    frozen_time = datetime.datetime(
        2026, 9, 9, 14, 47, 14, tzinfo=datetime.timezone.utc
    )

    # tell the mock to return our frozen time whenever .now() is called
    mock_datetime.datetime.now.return_value = frozen_time

    # Call the function (it will use the mocked .now())
    result = controller.get_current_time()

    # Assert against the exact string we expect
    expected_str = frozen_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    assert result == expected_str


@pytest.mark.parametrize(
    "has_member, plot_type, is_ref, attrs, expected_caption",
    [
        # Case 1: Member dims exist, Line plot, Is Reference
        (
            True,
            Line(),
            True,
            {"long_name": "Test Var"},
            "Model: TestModel\nDataset: TestData",
        ),
        # Case 2: Heatmap plot (bypasses member loop), Not Reference
        (True, Heatmap(), False, {}, "User model \nDataset: TestData"),
        # Case 3: No member dims, Line plot, Not Reference
        (False, Line(), False, {}, "User model \nDataset: TestData"),
    ],
)
def test_plot_dataset(
    monkeypatch, has_member, plot_type, is_ref, attrs, expected_caption
):
    """Test plotting dataset routing across member loops, heatmaps, lines, and reference captions."""

    # Mock plt.subplots
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    mock_subplots = MagicMock(return_value=(mock_fig, mock_ax))
    monkeypatch.setattr("matplotlib.pyplot.subplots", mock_subplots)

    # Mock formatting and slice rounding dependencies
    mock_apply_formatting = MagicMock(return_value=mock_fig)
    monkeypatch.setattr(
        controller, "apply_standard_plot_formatting", mock_apply_formatting
    )
    monkeypatch.setattr(controller, "round_slice_val", lambda x: str(x), raising=False)

    # Configure dataset and sliced_data
    dataset = MagicMock()
    sliced_data = MagicMock()
    dataset.sel.return_value = sliced_data

    if has_member:
        sliced_data.dims = {"lon": 10, "member": 2}
        sliced_data.member.values = ["mem1", "mem2"]
    else:
        sliced_data.dims = {"lon": 10}

    mock_da = MagicMock()
    mock_da.attrs = attrs  # Standard dict allows .get() to work natively
    sliced_data.__getitem__.return_value = mock_da

    mock_mem_da = MagicMock()
    mock_da.sel.return_value = mock_mem_da

    chosen_slices = {"lat": -35.0}
    variable = "temp"
    x_axis = "lon"
    y_axis = "lat"

    result = controller.plot_dataset(
        dataset=dataset,
        dataset_name="TestData",
        variable=variable,
        x_axis=x_axis,
        chosen_slices=chosen_slices,
        is_ref=is_ref,
        model_name="TestModel",
        plot_type=plot_type,
        y_axis=y_axis,
    )

    # Assertions
    dataset.sel.assert_called_once_with(**chosen_slices, method="nearest")

    # Verify the correct plot method was called based on the branch
    if has_member and not isinstance(plot_type, Heatmap):
        assert mock_da.sel.call_count == 2
        mock_mem_da.plot.assert_has_calls(
            [
                call(label="mem1", x=x_axis, ax=mock_ax),
                call(label="mem2", x=x_axis, ax=mock_ax),
            ]
        )
    elif isinstance(plot_type, Heatmap):
        mock_da.plot.assert_called_once_with(x=x_axis, y=y_axis, ax=mock_ax)
    else:
        mock_da.plot.assert_called_once_with(x=x_axis, ax=mock_ax)

    # Verify formatting application
    expected_title = attrs.get("long_name", variable)
    mock_apply_formatting.assert_called_once_with(
        fig=mock_fig,
        ax=mock_ax,
        title_text=expected_title,
        chosen_slices=chosen_slices,
        caption_text=expected_caption,
    )

    assert result == mock_fig


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
    toggle_widget = pn.widgets.Toggle(value=toggle_value)
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
        (False, {}),
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

    result = controller.get_selected_variable(
        toggle_widget, variable_dropdown_widget, long_names
    )

    if toggle_value and long_names:
        assert result == long_names[variable_dropdown_widget.value]
    else:
        assert result == variable_dropdown_widget.value


@pytest.mark.parametrize(
    "has_time, user_is_cftime, ref_is_cftime, user_cal, ref_cal, expect_convert",
    [
        (False, False, False, None, None, False),
        (True, True, True, "noleap", "noleap", False),
        (True, True, True, "noleap", "standard", True),
        (True, False, True, "standard", "noleap", True),
    ],
)
def test_add_to_dataset_dict(
    monkeypatch,
    has_time,
    user_is_cftime,
    ref_is_cftime,
    user_cal,
    ref_cal,
    expect_convert,
):
    # Mock data._build_data_object
    mock_dataset = MagicMock()
    monkeypatch.setattr(
        med_data, "_build_data_object", MagicMock(return_value=mock_dataset)
    )

    # Configure coords
    mock_dataset.coords = ["time"] if has_time else []

    mock_user_data = MagicMock()
    mock_user_data.coords = ["time"] if has_time else []

    # Configure indexes and calendars
    mock_user_index = MagicMock()
    mock_user_index.calendar = user_cal

    mock_ref_index = MagicMock()
    mock_ref_index.calendar = ref_cal

    mock_user_data.indexes.get.return_value = mock_user_index
    mock_dataset.indexes.get.return_value = mock_ref_index

    # Mock isinstance to selectively return True for CFTimeIndex checks
    original_isinstance = isinstance

    def custom_isinstance(obj, classinfo):
        if classinfo is xr.CFTimeIndex:
            if obj == mock_user_index:
                return user_is_cftime
            if obj == mock_ref_index:
                return ref_is_cftime
            return False
        return original_isinstance(obj, classinfo)

    monkeypatch.setattr("builtins.isinstance", custom_isinstance)

    dataset_dict = {}
    result = controller.add_to_dataset_dict(
        dataset_dict=dataset_dict,
        model="TestModel",
        catalog=MagicMock(),
        data_to_load={},
        user_data=mock_user_data,
    )

    # Assertions
    assert "TestModel" in result
    if expect_convert:
        mock_dataset.convert_calendar.assert_called_once_with(
            user_cal if user_is_cftime else "standard"
        )
    else:
        mock_dataset.convert_calendar.assert_not_called()


def test_get_metadata():
    dummy_meta = {
        "model": "ACCESS-CM2",
        "description": "Short desc",
        "nominal_resolution": "1 deg",
        "parent_experiment": "piControl",
        "long_description": "Long desc",
        "contact": "John Doe",
        "email": "john@example.com",
    }

    result = controller.get_metadata(dummy_meta)

    assert "<b>Model:   </b>ACCESS-CM2<br>" in result
    assert "<b>Contact:   </b>John Doe<br>" in result
    assert "<b>Email:   </b>john@example.com<br>" in result
    assert result.startswith('<div style="color: var(--jp-ui-font-color1);">')


@pytest.mark.parametrize(
    "plot_type, x, y, z, has_slice, dim_sizes, expected",
    [
        # (plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, remaining_dims)
        (
            Line(),
            None,
            None,
            None,
            False,
            {"time": 10},
            (False, False, False, False, []),
        ),
        (
            Line(),
            "time",
            None,
            None,
            False,
            {"time": 10},
            (True, False, False, False, []),
        ),
        (
            Line(),
            "time",
            None,
            None,
            False,
            {"time": 10, "lat": 10},
            (False, True, False, False, ["lat"]),
        ),
        (
            Heatmap(),
            "time",
            "lat",
            None,
            True,
            {"time": 10, "lat": 10},
            (True, False, False, False, []),
        ),
        (
            Heatmap(),
            "time",
            "lat",
            None,
            True,
            {"time": 10},
            (False, False, True, False, []),
        ),
        (
            Heatmap(),
            "time",
            None,
            None,
            True,
            {"time": 10, "lat": 10},
            (False, False, True, False, ["lat"]),
        ),
        (
            Heatmap(),
            "time",
            "time",
            None,
            True,
            {"time": 10, "lat": 10},
            (False, False, False, True, ["lat"]),
        ),
        (
            Animation(),
            "time",
            "lat",
            "lon",
            True,
            {"time": 10, "lat": 10, "lon": 10},
            (True, False, False, False, []),
        ),
        (
            Animation(),
            "time",
            "lat",
            "lon",
            True,
            {"time": 10, "lat": 10},
            (False, False, True, False, []),
        ),
        (
            Animation(),
            "time",
            "lat",
            None,
            True,
            {"time": 10, "lat": 10, "lon": 10},
            (False, False, True, False, ["lon"]),
        ),
    ],
)
def test_check_plot_validity(plot_type, x, y, z, has_slice, dim_sizes, expected):
    mock_dataset = MagicMock()
    mock_dataset.__getitem__.return_value.sizes = dim_sizes
    exp_valid, exp_req_slice, exp_inv_heat, exp_same_axes, exp_rem_dims = expected

    validity, remaining_dims = controller.check_plot_validity(
        dataset=mock_dataset,
        variable="temp",
        plot_type=plot_type,
        x=x,
        y=y,
        z=z,
        has_slice_widgets=has_slice,
    )

    assert validity.plot_valid == exp_valid
    assert validity.requires_slice == exp_req_slice
    assert validity.invalid_heatmap_data == exp_inv_heat
    assert validity.same_axes_chosen == exp_same_axes
    assert validity.prompt_bounds is False

    assert remaining_dims == exp_rem_dims


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
    ds_ref = xr.Dataset(
        {"data": (["x"], [3, 4])}, coords={"x": [ref_min_val, ref_max_val]}
    )
    ref_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result, global_min, global_max, _dataset_min, _dataset_max = (
        controller.check_bounds(ds_primary, "x", ref_dict)
    )

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
    ds_primary = xr.Dataset(
        {"data": (["time"], [1, 2])}, coords={"time": primary_times}
    )

    # Create a reference dataset using Gregorian calendar bounds based on parameters
    ref_times = [
        cftime.DatetimeGregorian(*ref_start),
        cftime.DatetimeGregorian(*ref_end),
    ]
    ds_ref = xr.Dataset({"data": (["time"], [3, 4])}, coords={"time": ref_times})
    ref_dict = {"ref1": ds_ref}

    # Execute the bounds check and verify if a bounds mismatch is triggered
    result, _global_min, _global_max, _dataset_min, _dataset_max = (
        controller.check_bounds(ds_primary, "time", ref_dict)
    )

    assert result == expected_triggered


def test_multiplot_check_bounds_mismatched_types():
    """Test that check_bounds safely ignores reference datasets with incompatible axis types."""
    import cftime
    import xarray as xr

    from med_diagnostics import controller  # Update import if needed

    # Primary dataset is numeric
    ds_primary = xr.Dataset({"data": (["x"], [1, 2])}, coords={"x": [0, 10]})

    # Reference dataset is calendar time (incompatible with numeric!)
    ref_times = [
        cftime.DatetimeGregorian(2000, 1, 1),
        cftime.DatetimeGregorian(2000, 12, 31),
    ]
    ds_ref = xr.Dataset({"data": (["x"], [3, 4])}, coords={"x": ref_times})
    ref_dict = {"ref1": ds_ref}

    # Execute the bounds check
    result, global_min, global_max, _dataset_min, _dataset_max = (
        controller.check_bounds(ds_primary, "x", ref_dict)
    )

    # Because they are incompatible, bounds should NOT be widened,
    # and the global bounds should remain equal to the primary numeric bounds.
    assert result is False
    assert global_min == 0
    assert global_max == 10


@pytest.fixture
def multiplot_datasets():
    """Create a primary dataset and a reference dictionary for plotting tests."""
    ds_user = xr.Dataset(
        {"data": (["time", "lat"], np.random.rand(5, 5))},
        coords={"time": [1, 2, 3, 4, 5], "lat": [10, 20, 30, 40, 50]},
    )
    ds_user.data.attrs["long_name"] = "Temperature"

    # Reference 1: Standard
    ds_ref1 = ds_user * 1.5

    # Reference 2: With members
    ds_ref2 = xr.Dataset(
        {"data": (["member", "time", "lat"], np.random.rand(2, 5, 5))},
        coords={"member": [0, 1], "time": [1, 2, 3, 4, 5], "lat": [10, 20, 30, 40, 50]},
    )

    return ds_user, {"Model A": ds_ref1, "Model B": ds_ref2}


@pytest.mark.parametrize("plot_diff", [True, False])
def test_plot_multiplot_dataset(multiplot_datasets, monkeypatch, plot_diff):
    """Test line plotting logic and difference calculation."""
    ds_user, ref_dict = multiplot_datasets

    # Mock standard formatter to just return the figure so we can verify the ax
    monkeypatch.setattr(
        controller, "apply_standard_plot_formatting", lambda fig, **kwargs: fig
    )

    fig = controller.plot_multiplot_dataset(
        dataset=ds_user,
        variable="data",
        ref_dict=ref_dict,
        chosen_slices={"lat": 30},
        x_axis="time",
        x_min=1,
        x_max=5,
        plot_diff=plot_diff,
    )

    assert isinstance(fig, plt.Figure)
    ax = fig.axes[0]

    # Check x limits were applied
    assert ax.get_xlim() == (1, 5)

    # Verify number of lines plotted
    # No-diff: 1 (User) + 1 (Model A) + 2 (Model B mems) = 4 lines
    # Diff: 1 (Model A diff) + 2 (Model B mems diff) + 1 (hline) = 4 lines
    assert len(ax.lines) == 4


def _make_mock_da():
    mock_da = MagicMock()
    mock_da.min.return_value = 0.0
    mock_da.max.return_value = 10.0
    return mock_da


def _no_refs_case():
    """total_plots == 0 -> returns fig with 'No reference models selected' text."""
    return {"dataset": MagicMock(), "ref_dict": {}, "chosen_slices": {}}


def _no_refs_diff_case():
    """total_plots == 0 -> returns fig with 'No reference models selected' text."""
    return {
        "dataset": MagicMock(),
        "ref_dict": {},
        "chosen_slices": {},
        "plot_diff": True,
    }


def _delaxes_and_slices_case():
    """Odd total_plots (triggers fig.delaxes) and non-empty chosen_slices (triggers bottom=0.15 adjust)."""
    # 3 reference models forces a 2x2 grid, leaving 1 empty subplot
    mock_da = _make_mock_da()

    ref_ds = MagicMock(spec=xr.Dataset)
    ref_ds.dims = {"lon": 10, "lat": 10}
    ref_ds.sel.return_value = ref_ds
    ref_ds.__getitem__.return_value = mock_da

    user_ds = MagicMock()
    user_ds.sel.return_value = user_ds
    user_ds.__getitem__.return_value = mock_da

    return {
        "dataset": user_ds,
        "ref_dict": {"model1": ref_ds, "model2": ref_ds, "model3": ref_ds},
        "chosen_slices": {"lev": 5},  # non-empty to trigger slice_str and bottom=0.15
    }


def _member_dims_case():
    """'member' in sliced_user_data.dims and 'member' in sliced_first_ref.dims."""
    mock_da = _make_mock_da()

    # Configure mock for sliced reference dataset after isel
    sliced_ref_mock = MagicMock()
    sliced_ref_mock.dims = {"lon": 10, "lat": 10}
    sliced_ref_mock.__getitem__.return_value = mock_da
    sliced_ref_mock.__sub__.return_value = (
        sliced_ref_mock  # subtraction for plot_diff=True
    )

    # Not spec'd, so dynamic attributes like .member are allowed
    ref_ds = MagicMock()
    ref_ds.dims = {"lon": 10, "lat": 10, "member": 3}
    ref_ds.member.values = [1]
    ref_ds.sel.return_value = ref_ds
    ref_ds.isel.return_value = sliced_ref_mock

    # Configure mock for sliced user dataset after isel
    sliced_user_mock = MagicMock()
    sliced_user_mock.dims = {"lon": 10, "lat": 10}
    sliced_user_mock.__getitem__.return_value = mock_da

    user_ds = MagicMock()
    user_ds.dims = {"lon": 10, "lat": 10, "member": 3}
    user_ds.sel.return_value = user_ds
    user_ds.isel.return_value = sliced_user_mock

    return {
        "dataset": user_ds,
        "ref_dict": {"model1": ref_ds},
        "chosen_slices": {},
        "plot_diff": True,
    }


@pytest.mark.parametrize(
    "build_kwargs",
    [_no_refs_case, _delaxes_and_slices_case, _member_dims_case, _no_refs_diff_case],
    ids=["no_refs", "delaxes_and_slices", "member_dims", "no_ref_diff"],
)
def test_plot_multiplot_heatmap_dataset(build_kwargs):
    fig = controller.plot_multiplot_heatmap_dataset(
        variable="temp", x_axis="lon", y_axis="lat", **build_kwargs()
    )
    assert fig is not None


@pytest.mark.parametrize(
    "chosen_slices, x_min, x_max, multiplot_legend, expected_caption, expected_xlim_called",
    [
        # Case 1: Empty slices, no limits, multiplot_legend=False
        ({}, None, None, False, "Base Caption", False),
        # Case 2: Populated slices, valid limits, multiplot_legend=True
        ({"lat": -35.5}, 0.0, 100.0, True, "Base Caption\nSliced by: lat: -35.5", True),
    ],
)
def test_apply_standard_plot_formatting(
    monkeypatch,
    chosen_slices,
    x_min,
    x_max,
    multiplot_legend,
    expected_caption,
    expected_xlim_called,
):
    """Test standard plot formatting applied correctly across all layout and legend combinations."""

    # Mock the figure and axis
    fig = MagicMock()
    ax = MagicMock()
    title_text = "Test Title"
    caption_text = "Base Caption"

    # Mock round_slice_val to just return the value as a string to avoid complex logic
    monkeypatch.setattr(controller, "round_slice_val", lambda x: str(x), raising=False)

    # Call the function
    result = controller.apply_standard_plot_formatting(
        fig=fig,
        ax=ax,
        title_text=title_text,
        chosen_slices=chosen_slices,
        caption_text=caption_text,
        x_min=x_min,
        x_max=x_max,
        multiplot_legend=multiplot_legend,
    )

    # Core Assertions
    assert result == fig
    fig.tight_layout.assert_called_once()
    ax.set_title.assert_called_once_with(title_text, fontsize=14)
    ax.grid.assert_called_once()

    # Caption Assertion
    fig.text.assert_called_once_with(
        0.1, 0.01, expected_caption, wrap=True, horizontalalignment="left", fontsize=10
    )

    # X-Limits Assertion
    if expected_xlim_called:
        ax.set_xlim.assert_called_once_with(x_min, x_max)
    else:
        ax.set_xlim.assert_not_called()

    # Legend and Subplots Adjust Assertion
    if multiplot_legend:
        fig.subplots_adjust.assert_called_once_with(bottom=0.15, right=0.7)
        ax.legend.assert_called_once_with(loc="center left", bbox_to_anchor=(1.05, 0.5))
    else:
        fig.subplots_adjust.assert_called_once_with(bottom=0.3)
        ax.legend.assert_called_once_with()


@pytest.mark.parametrize(
    "missing_x, missing_y, chosen_slices, expected_slice_text",
    [
        (True, True, {}, False),
        (False, False, {"lat": -35.0}, True),
    ],
)
def test_plot_animation(
    monkeypatch, missing_x, missing_y, chosen_slices, expected_slice_text
):
    # Mock dependencies
    monkeypatch.setattr(
        controller, "round_slice_val", lambda val: str(val), raising=False
    )

    mock_dataset = MagicMock()
    mock_sliced_data = MagicMock()
    mock_plot_dataset = MagicMock()

    mock_dataset.sel.return_value = mock_sliced_data
    mock_sliced_data.__getitem__.return_value = mock_plot_dataset
    mock_plot_dataset.load.return_value = mock_plot_dataset

    # Configure min/max
    mock_plot_dataset.min.return_value = 0.0
    mock_plot_dataset.max.return_value = 100.0

    # Configure coords
    mock_plot_dataset.coords = []
    if not missing_x:
        mock_plot_dataset.coords.append("lon")
    if not missing_y:
        mock_plot_dataset.coords.append("lat")

    mock_plot_dataset.sizes = {"lon": 10, "lat": 10}
    mock_plot_dataset.assign_coords.return_value = mock_plot_dataset

    # Configure attrs and hvplot
    mock_plot_dataset.attrs = {"long_name": "Temperature"}
    mock_hvplot_obj = "hvplot_quadmesh_mock"
    mock_plot_dataset.hvplot.quadmesh.return_value = mock_hvplot_obj

    result = controller.plot_animation(
        dataset=mock_dataset,
        dataset_name="TestDataset",
        variable="temp",
        chosen_slices=chosen_slices,
        x_axis="lon",
        y_axis="lat",
        z_axis="time",
    )

    # Assertions
    mock_dataset.sel.assert_called_once_with(**chosen_slices, method="nearest")

    if missing_x or missing_y:
        assert mock_plot_dataset.assign_coords.call_count > 0
    else:
        mock_plot_dataset.assign_coords.assert_not_called()

    mock_plot_dataset.hvplot.quadmesh.assert_called_once()

    # Check returned panel column structure
    assert isinstance(result, pn.Column)
    assert len(result) == 2

    # Verify caption HTML injection
    caption_pane = result[1]
    assert isinstance(caption_pane, pn.pane.HTML)
    assert "Variable: Temperature" in caption_pane.object
    if expected_slice_text:
        assert "Sliced by: lat: -35.0" in caption_pane.object


@pytest.mark.parametrize(
    "variable, ref_dict, expected_invalid, expected_valid",
    [
        ("temp", None, {}, {}),
        ("temp", {}, {}, {}),
        (
            "temp",
            {"model_A": {"temp": [1, 2], "salt": [3, 4]}, "model_B": {"temp": [5, 6]}},
            {},
            {"model_A": {"temp": [1, 2], "salt": [3, 4]}, "model_B": {"temp": [5, 6]}},
        ),
        (
            "temp",
            {
                "model_A": {"temp": [1, 2]},
                "model_B": {"salt": [3, 4]},
                "model_C": {"temp": [5, 6]},
            },
            {"model_B": {"salt": [3, 4]}},
            {"model_A": {"temp": [1, 2]}, "model_C": {"temp": [5, 6]}},
        ),
        (
            "temp",
            {"model_A": {"salt": [1, 2]}, "model_B": {"salt": [3, 4]}},
            {"model_A": {"salt": [1, 2]}, "model_B": {"salt": [3, 4]}},
            {},
        ),
    ],
)
def test_check_dict_validity(variable, ref_dict, expected_invalid, expected_valid):
    """Test the filtering of reference datasets missing the target variable."""
    invalid, valid = controller.check_dict_validity(variable, ref_dict)

    assert invalid == expected_invalid
    assert valid == expected_valid
