import inspect
from typing import Annotated, Literal
from unittest.mock import MagicMock

import numpy as np
import pytest
import xarray as xr
from intake_esm.source import ESMDataSourceError

from med_diagnostics import analysis, recipes

RECIPES = [
    func
    for name, func in inspect.getmembers(recipes, inspect.isfunction)
    if name.startswith("recipe_")
]


def _monthly_time(periods, **kwargs):
    """Monthly time axis starting in 2000, cftime unless told otherwise."""
    kwargs.setdefault("use_cftime", True)
    return xr.date_range("2000-01-01", periods=periods, freq="MS", **kwargs)


def _user_warnings(recwarn):
    """Messages of the plain UserWarnings a test raised, which the UI shows, joined."""
    return "\n".join(str(w.message) for w in recwarn if w.category is UserWarning)


def _options_by_name(recipe, ds=None):
    """The UI options for ``recipe``, keyed by parameter name."""
    return {o["name"]: o for o in analysis._get_recipe_kwarg_options(recipe, ds)}


# Recipe annotations


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r.__name__)
def test_every_recipe_annotation_parses_for_the_ui(recipe):
    """Test that each prebuilt recipe's annotations give the UI a complete form.

    Unknown kinds silently become text boxes, so a typo in a prebuilt recipe
    would only show up as a wrong widget at runtime. Every parameter must get
    a known kind and a description for its tooltip.
    """
    options = analysis._get_recipe_kwarg_options(recipe)
    parameters_after_dataset = list(inspect.signature(recipe).parameters)[1:]

    assert [o["name"] for o in options] == parameters_after_dataset
    for option in options:
        assert option["kind"] in analysis.RECIPE_KINDS
        assert option["description"]


def test_recipes_are_found():
    """Guard against the parametrised test above silently running on nothing."""
    assert RECIPES


def recipe_example(
    ds,
    variable: Annotated[
        str,
        {"name": "Select Variable", "kind": "data variable", "description": "Var."},
    ] = "temp",
    stat: Annotated[Literal["mean", "max"], {"kind": "choice"}] = "mean",
    region: Annotated[str, {"kind": "choice", "choices": ["a", "b"]}] = "a",
    depth: Annotated[float, {"kind": "float", "units": "m"}] = 0,
    lvl_dim: Annotated[str | None, {"kind": "dimension"}] = None,
    *,
    required: Annotated[int, {"kind": "int"}],
):
    """Example recipe."""


def test_annotations_parse_every_field():
    """Test that each part of the ``Annotated`` convention reaches the UI dict.

    The metadata ``name`` is only the display label: the option's ``name``
    must stay the parameter name, because the UI passes values back by it.
    ``Literal`` fills the choices, but the kind still comes from the metadata.
    """
    options = _options_by_name(recipe_example)

    assert list(options) == [
        "variable",
        "stat",
        "region",
        "depth",
        "lvl_dim",
        "required",
    ]

    assert options["variable"]["label"] == "Select Variable"
    assert options["variable"]["kind"] == "data variable"
    assert options["variable"]["default"] == "temp"
    assert options["variable"]["description"] == "Var."

    assert options["stat"]["kind"] == "choice"
    assert options["stat"]["choices"] == ["mean", "max"]
    assert options["region"]["choices"] == ["a", "b"]

    assert options["depth"]["label"] == "depth"
    assert options["depth"]["units"] == "m"
    assert options["depth"]["required"] is False
    assert options["required"]["required"] is True


def test_dataset_fills_variable_and_dimension_choices():
    """Test that choices come from the dataset, with None for optional dims.

    Single-valued dims (``st_ocean``) and bounds dims (``nv``) aren't useful
    analysis axes, so they're left out of the dropdown.
    """
    ds = xr.Dataset(
        {"temp": (("time", "lat", "nv"), [[[0.0, 1.0]] * 2] * 3)},
        coords={"time": [0, 1, 2], "lat": [0, 1], "st_ocean": ("st_ocean", [5.0])},
    )
    options = _options_by_name(recipe_example, ds)

    assert options["variable"]["choices"] == ["temp"]
    assert options["lvl_dim"]["choices"] == [None, "time", "lat"]


def test_unannotated_parameters_are_accepted():
    """Test that parameters without annotations still get an option.

    Kind validation was dropped on purpose: an unknown or missing kind becomes
    a text box in the UI rather than an error.
    """

    def recipe_plain(ds, depth=0, method: Annotated[str, {"kind": "mispelt"}] = "x"):
        """Plain recipe."""

    options = _options_by_name(recipe_plain)

    assert options["depth"]["kind"] is None
    assert options["depth"]["default"] == 0
    assert options["method"]["kind"] == "mispelt"


# Regions


def _global_one_degree_grid(lon_start=0.5):
    """Global 1° lat/lon dataset of ones, with longitudes from ``lon_start``."""
    return xr.Dataset(
        {"temp": (("lat", "lon"), np.ones((180, 360)))},
        coords={
            "lat": np.arange(-89.5, 90),
            "lon": np.arange(lon_start, lon_start + 360),
        },
    )


# Number of 1° latitude and longitude cells inside each predefined region
REGION_SIZES = {
    "nino12": (10, 10),
    "nino3": (10, 60),
    "nino34": (10, 50),
    "nino4": (10, 50),
    "iod_west": (20, 20),
    "iod_east": (10, 20),
    "tna": (20, 40),
    "tsa": (20, 40),
    "global": (180, 360),
    "nh": (90, 360),
    "sh": (90, 360),
    "tropics": (40, 360),
    "tasmania": (5, 6),
    "australia": (34, 42),
    "maritime_continent": (20, 60),
    "southern_ocean": (40, 360),
    "arctic": (24, 360),
    "antarctic": (24, 360),
}


def test_region_sizes_cover_every_region():
    """Test that a new region can't be added without an expected size."""
    assert set(REGION_SIZES) == set(recipes.PREDEFINED_REGIONS)


@pytest.mark.parametrize(
    "lon_start", [0.5, -179.5, -279.5], ids=["0-360", "-180-180", "mom5"]
)
@pytest.mark.parametrize("region", list(recipes.PREDEFINED_REGIONS))
def test_every_region_selects_the_right_cells(region, lon_start):
    """Test that every predefined region selects the same cells on every longitude convention.

    A region wrapped the wrong way around the globe would select the cells
    outside it instead, and full-width regions used to select nothing.
    """
    subset = recipes.extract_region(_global_one_degree_grid(lon_start), region)
    n_lat, n_lon = REGION_SIZES[region]
    lat_south, _ = recipes.PREDEFINED_REGIONS[region]["lat"]
    lon_west, _ = recipes.PREDEFINED_REGIONS[region]["lon"]

    # Compare cell centres with each grid's longitudes converted to 0-360
    expected_lats = np.ceil(lat_south - 0.5) + 0.5 + np.arange(n_lat)
    expected_lons = np.sort((lon_west + 0.5 + np.arange(n_lon)) % 360)
    np.testing.assert_allclose(subset["lat"], expected_lats)
    np.testing.assert_allclose(np.sort(subset["lon"] % 360), expected_lons)


def test_extract_region_by_name():
    """Test that a predefined region is looked up by name."""
    tropics = recipes.extract_region(_global_one_degree_grid(), "tropics")

    assert tropics.sizes["lat"] == 40
    assert tropics.sizes["lon"] == 360


def test_extract_region_by_bounds():
    """Test that a dict of lat/lon bounds selects a custom box."""
    box = recipes.extract_region(
        _global_one_degree_grid(), {"lat": (-10, 10), "lon": (100, 200)}
    )

    assert box.sizes["lat"] == 20
    assert box.sizes["lon"] == 100


def test_extract_region_on_curvilinear_grid():
    """Test that 2D lat/lon are masked rather than indexed.

    With 10° cell centres, the box keeps lat -5 and 5, and lon 105 to 195.
    """
    lon_2d, lat_2d = np.meshgrid(np.arange(5, 360, 10), np.arange(-85, 90, 10))
    ds = xr.Dataset(
        {"temp": (("y", "x"), np.ones((18, 36)))},
        coords={"lat": (("y", "x"), lat_2d), "lon": (("y", "x"), lon_2d)},
    )
    box = recipes.extract_region(ds, {"lat": (-10, 10), "lon": (100, 200)})

    assert box.sizes["y"] == 2
    assert box.sizes["x"] == 10


def test_extract_region_on_curvilinear_grid_masks_cells_outside_region():
    """Test that cells outside the region don't leak into a regional mean.

    On a tilted grid the region isn't a rectangle of rows and columns, so the
    kept rectangle includes cells outside it. They must be NaN, so the mean
    only sees the in-region cells (10), never the outside ones (1000).
    """
    # Latitude tilts across each row, so only the diagonal is within ±5°
    lat_2d = np.array([[0, 10, 20], [-10, 0, 10], [-20, -10, 0]])
    lon_2d = np.array([[0, 10, 20]] * 3)
    temp = np.where(np.eye(3, dtype=bool), 10.0, 1000.0)
    ds = xr.Dataset(
        {"temp": (("y", "x"), temp)},
        coords={"lat": (("y", "x"), lat_2d), "lon": (("y", "x"), lon_2d)},
    )

    box = recipes.extract_region(ds, {"lat": (-5, 5), "lon": (0, 25)})

    # Every row and column holds an in-region cell, so the whole grid is kept
    assert box["temp"].shape == (3, 3)
    assert np.isnan(box["temp"].values[~np.eye(3, dtype=bool)]).all()
    weights = np.cos(np.deg2rad(box["lat"]))
    assert float(box["temp"].weighted(weights).mean()) == 10.0


def test_extract_region_rejects_unknown_regions():
    """Test that an unknown name or a dict without lat/lon bounds raises."""
    ds = _global_one_degree_grid()

    with pytest.raises(ValueError, match="not defined region"):
        recipes.extract_region(ds, "not defined region")
    with pytest.raises(TypeError):
        recipes.extract_region(ds, {"not": "a region", "raise": "an error"})


# Time helpers


@pytest.mark.parametrize(
    "freq, expected_days",
    [
        # 2000 is a leap year, so the gaps are 31, 29, 31 and 30 days
        ("MS", 30.5),
        ("15D", 15.0),
    ],
)
def test_median_timestep_days(freq, expected_days):
    """Test the median gap between timesteps on a cftime axis."""
    time = xr.date_range("2000-01-01", periods=5, freq=freq, use_cftime=True)

    assert recipes.median_timestep_days(xr.DataArray(time)) == expected_days


@pytest.mark.parametrize(
    "freq, periods, target_days, expected_steps",
    [
        ("MS", 5, 61, 2),
        ("15D", 5, 30, 2),
        ("15D", 1, 30, 1),
        ("MS", 5, 365, 5),
    ],
    ids=["monthly", "15-daily", "single-timestep", "window-longer-than-series"],
)
def test_rolling_window_size(freq, periods, target_days, expected_steps):
    """Test that a window length in days is converted to timesteps.

    A single timestep can't be smoothed, so it always gives a window of 1. A
    window longer than the series is cut to its length, otherwise the rolling
    mean is all NaN and its line silently vanishes.
    """
    time = xr.date_range("2000-01-01", periods=periods, freq=freq, use_cftime=True)

    assert (
        recipes._rolling_window_size(xr.DataArray(time), target_days) == expected_steps
    )


def test_calc_anomalies_removes_monthly_climatology():
    """Test that anomalies are the difference from the usual value for that month, area weighted.

    The anomaly is bigger at 60° than at the equator, but boxes there have half
    the area, so the equator counts double.
    """
    seasonal_cycle = np.sin(2 * np.pi * np.arange(12) / 12)
    second_year_warming = np.array([1.0, 4.0])  # at 0° and 60°
    temp = np.concatenate(
        [
            np.broadcast_to(seasonal_cycle[:, None], (12, 2)),
            seasonal_cycle[:, None] + second_year_warming[None, :],
        ]
    )
    ds = xr.Dataset(
        {
            "temp": (
                ("time", "lat", "lon"),
                np.broadcast_to(temp[:, :, None], (24, 2, 2)),
            )
        },
        coords={"time": _monthly_time(24), "lat": [0.0, 60.0], "lon": [0, 1]},
    )

    anomalies = recipes.calc_anomalies(ds, "lon", "lat", "temp")

    np.testing.assert_allclose(anomalies, np.repeat([-1.0, 1.0], 12))


# Grid checks


@pytest.fixture
def lat_lon_dataset():
    """Dataset whose ``temp`` has time, lat and lon coordinates."""
    return xr.Dataset(
        {"temp": (("time", "lat", "lon"), np.ones((5, 2, 2)))},
        coords={"time": _monthly_time(5), "lat": [0, 1], "lon": [0, 1]},
    )


def test_require_coords_accepts_matching_grid(lat_lon_dataset):
    """Test that nothing is raised when every coordinate is present."""
    recipes.require_coords(lat_lon_dataset, "temp", ["time", "lat", "lon"], "MOM5")


def test_require_coords_names_missing_coords(lat_lon_dataset):
    """Test that a missing coordinate gives a readable error naming it."""
    with pytest.raises(ValueError, match=r"missing \['depth'\]"):
        recipes.require_coords(
            lat_lon_dataset, "temp", ["time", "lat", "depth"], "MOM5"
        )


def test_require_coords_rejects_missing_variable(lat_lon_dataset):
    """Test that a variable not in the dataset raises a KeyError."""
    with pytest.raises(KeyError):
        recipes.require_coords(lat_lon_dataset, "missing", ["time"], "MOM5")


# Global means

# Each layer's mean counts the equator double, then every layer counts equally
MOM5_GLOBAL_MEAN_TEMP = (18 + 2 * (8 / 3)) / 3
MOM5_UNWEIGHTED_MEAN_TEMP = (20 + 14 + 2 + 4 + 2 + 4) / 6
MOM5_GLOBAL_MEAN_SALT = (34 + 34 + 35) / 3
MOM5_UNWEIGHTED_MEAN_SST = (20 + 14) / 2


def _mom5_style_dataset():
    """Small MOM5-style dataset: temp varying with latitude, land NaNs and an ``area_t`` cell measure."""
    temp = np.full((24, 3, 2, 2), 2.0)
    temp[:, 0] = 20.0  # thin, warm surface layer
    temp[:, 0, 1, :] = 14.0  # cooler surface at 60°
    temp[:, 1:, 1, :] = 4.0  # warmer below at 60°
    salt = np.full((24, 3, 2, 2), 34.0)
    salt[:, 2] = 35.0  # thick, salty deep layer
    salt[:, :, 1, :] = np.nan  # some land
    dims = ("time", "st_ocean", "yt_ocean", "xt_ocean")
    return xr.Dataset(
        {
            "temp": (dims, temp, {"units": "degC", "cell_measures": "area: area_t"}),
            "salt": (dims, salt, {"units": "psu", "cell_measures": "area: area_t"}),
            "sst": (dims[:1] + dims[2:], temp[:, 0], {"units": "degC"}),
            "area_t": (dims[2:], [[2.0, 2.0], [1.0, 1.0]]),
        },
        coords={
            "time": _monthly_time(24),
            "st_ocean": [5.0, 15.0, 100.0],
            "yt_ocean": [0.0, 60.0],
            "xt_ocean": [0.0, 1.0],
        },
    )


def test_global_mean_weights_by_cell_area():
    """Test that the mean is weighted by the ``cell_measures`` area.

    A plain mean would count the small 60° boxes as much as the equator. Like the
    paper's ``grid.average``, every depth layer counts equally.
    """
    ds = _mom5_style_dataset()
    temp = recipes.global_mean(ds, "temp", "time")
    salt = recipes.global_mean(ds, "salt", "time")

    np.testing.assert_allclose(temp, MOM5_GLOBAL_MEAN_TEMP)
    np.testing.assert_allclose(salt, MOM5_GLOBAL_MEAN_SALT)


def test_global_mean_keeps_kelvin():
    """Test that Kelvin data stays in Kelvin, as in the paper, which plots each run in its own units."""
    ds = _mom5_style_dataset()
    ds["temp"] = (ds["temp"] + 273.15).assign_attrs(ds["temp"].attrs, units="K")

    temp = recipes.global_mean(ds, "temp", "time")

    np.testing.assert_allclose(temp, MOM5_GLOBAL_MEAN_TEMP + 273.15)


def _mom6_style_dataset():
    """Small MOM6/CF-style dataset: ``so`` varying across boxes, with uneven ``areacello``."""
    layer = np.array([[34.0, 35.0], [36.0, 38.0]])
    so = layer[None, None] + np.array([0.0, 0.0, 1.0])[None, :, None, None]
    volcello = np.ones((3, 2, 2))
    volcello[2, 1, 1] = 9.0
    return xr.Dataset(
        {
            "so": (("time", "zl", "yh", "xh"), np.broadcast_to(so, (24, 3, 2, 2))),
            "areacello": (("yh", "xh"), [[1.0, 3.0], [2.0, 2.0]]),
            "volcello": (("zl", "yh", "xh"), volcello),
        },
        coords={
            "time": _monthly_time(24),
            "zl": [5.0, 15.0, 100.0],
            "yh": [0.0, 60.0],
            "xh": [0.0, 1.0],
        },
    )


@pytest.mark.parametrize(
    "cell_measures",
    [
        pytest.param(None, id="areacello-without-cell-measures"),
        pytest.param("area: areacello", id="cell-measures"),
        pytest.param("area: areacello volume: volcello", id="volcello-ignored"),
    ],
)
def test_global_mean_weights_by_areacello(cell_measures):
    """Test that the real box areas in ``areacello`` are used, and never ``volcello``.

    The areas are uneven, so equal weights would give a different answer. One deep
    box has a much bigger volume, so weighting by ``volcello`` would too.
    """
    ds = _mom6_style_dataset()
    if cell_measures:
        ds["so"].attrs["cell_measures"] = cell_measures

    np.testing.assert_allclose(recipes.global_mean(ds, "so", "time"), 35.875 + 1 / 3)


def test_global_mean_without_cell_area_is_unweighted_and_says_so(recwarn):
    """Test that data with no cell area still gets a plain mean, with a message saying so."""
    ds = _mom5_style_dataset().drop_vars("area_t")

    np.testing.assert_allclose(
        recipes.global_mean(ds, "temp", "time"), MOM5_UNWEIGHTED_MEAN_TEMP
    )
    assert "No cell area found for 'temp'" in _user_warnings(recwarn)


@pytest.mark.parametrize("how, expected", [("max", 20.0), ("min", 14.0)])
def test_global_mean_max_and_min(how, expected):
    """Test that ``how="max"``/``"min"`` take the global maximum/minimum instead of the mean."""
    np.testing.assert_allclose(
        recipes.global_mean(_mom5_style_dataset(), "sst", "time", how), expected
    )


def test_global_mean_passes_size_one_dims_through_unweighted_without_warning(
    recwarn,
):
    """Test that MOM's size-1 ``scalar_axis`` is dropped, not treated as a grid with no cell area."""
    ds = xr.Dataset(
        {"soga": (("time", "scalar_axis"), [[34.7], [34.71]])}, coords={"time": [0, 1]}
    )

    result = recipes.global_mean(ds, "soga", "time")

    np.testing.assert_allclose(result, [34.7, 34.71])
    assert result.dims == ("time",)
    assert _user_warnings(recwarn) == ""


def test_global_mean_passes_scalar_timeseries_through():
    """Test that data with only a time dimension is returned unchanged."""
    ds = xr.Dataset({"soga": ("time", [34.7, 34.71])}, coords={"time": [0, 1]})

    np.testing.assert_allclose(recipes.global_mean(ds, "soga", "time"), [34.7, 34.71])


def _gridded_sst(cell_methods=None):
    """Gridded ``sst`` DataArray, with ``cell_methods`` if given."""
    attrs = {} if cell_methods is None else {"cell_methods": cell_methods}
    return xr.DataArray(np.ones((2, 3)), dims=("time", "xh"), name="sst", attrs=attrs)


@pytest.mark.parametrize(
    "name, how", [("tos_max", "max"), ("tos_min", "min"), ("soga", "mean")]
)
def test_om3_timeseries_reduction_without_cell_methods_uses_field_name(name, how):
    """Test that ``*_max``/``*_min`` fields are reduced by max/min and everything else by mean."""
    assert recipes._om3_timeseries_reduction(_gridded_sst(), name, "time") == how


@pytest.mark.parametrize(
    "cell_methods, name, how",
    [
        ("area: mean time: mean", "tos", "mean"),
        ("area: mean time: max", "tos_max", "max"),
        ("time: min", "tos_min", "min"),
    ],
)
def test_om3_timeseries_reduction_follows_cell_methods(
    cell_methods, name, how, recwarn
):
    """Test that the time method in ``cell_methods`` picks the reduction, with no warning when it matches."""
    da = _gridded_sst(cell_methods)

    assert recipes._om3_timeseries_reduction(da, name, "time") == how
    assert _user_warnings(recwarn) == ""


def test_om3_timeseries_reduction_prefers_cell_methods_to_field_name(recwarn):
    """Test that a time-mean variable mapped to a ``*_max`` field is averaged, with a warning.

    The paper goes by ``cell_methods``, and the user may plot whatever they map.
    """
    da = _gridded_sst("time: mean")

    assert recipes._om3_timeseries_reduction(da, "tos_max", "time") == "mean"
    assert "tos_max is a spatial max, but 'sst'" in _user_warnings(recwarn)


def test_om3_timeseries_reduction_without_time_method_falls_back_to_mean(recwarn):
    """Test that gridded data with no time mean, max or min is averaged, with a warning.

    The paper leaves such data as is, which would leave a grid that can't be plotted
    as a timeseries.
    """
    da = _gridded_sst("time: point")

    assert recipes._om3_timeseries_reduction(da, "tos_max", "time") == "mean"
    assert "no time mean, max or min" in _user_warnings(recwarn)


def test_om3_timeseries_reduction_strict_rejects_grid_without_time_method():
    """Test that the automated recipe's strict mode raises instead of plotting a mean."""
    with pytest.raises(ValueError, match="no time mean, max or min"):
        recipes._om3_timeseries_reduction(
            _gridded_sst("time: point"), "tos_max", "time", strict=True
        )


def test_om3_timeseries_reduction_ignores_cell_methods_on_scalars(recwarn):
    """Test that scalars, which aren't reduced, give no warning whatever their ``cell_methods``."""
    da = xr.DataArray(
        np.ones((2, 1)),
        dims=("time", "scalar_axis"),
        name="soga",
        attrs={"cell_methods": "time: point"},
    )

    recipes._om3_timeseries_reduction(da, "tos_max", "time")

    assert _user_warnings(recwarn) == ""


# OM3 timeseries recipes


@pytest.fixture
def fake_om3_references(monkeypatch):
    """Replace the /g/data reference loader with a flat 34.7 timeseries.

    Returns the list of variables the recipe asked references for.
    """
    loaded = []

    def fake(var, start, end):
        loaded.append(var)
        return {
            "refA": xr.DataArray(np.full(24, 34.7), coords={"time": _monthly_time(24)})
        }

    monkeypatch.setattr(recipes, "_load_om3_timeseries_reference", fake)
    return loaded


def test_om3_timeseries_plots_each_found_variable(fake_om3_references):
    """Test that the OM3-names recipe plots every known variable, with references.

    Only the plotted variable's references should be loaded, since each load
    reads from /g/data.
    """
    ds = xr.Dataset(
        {"soga": ("time", np.full(24, 34.6)), "other": ("time", np.zeros(24))},
        coords={"time": _monthly_time(24)},
    )

    figs = analysis._analyse_and_plot(ds, recipes.recipe_om3_timeseries)

    assert [f.axes[0].get_title() for f in figs] == ["soga: Global Mean Ocean Salinity"]
    labels = [line.get_label() for line in figs[0].axes[0].get_lines()]
    assert "User data" in labels
    assert "refA" in labels
    assert fake_om3_references == ["soga"]


def test_om3_timeseries_without_om3_names_points_to_mapped_recipe():
    """Test the readable error on a dataset with none of the OM3 names."""
    with pytest.raises(ValueError, match="custom variable mapping"):
        recipes.recipe_om3_timeseries(_mom5_style_dataset())


def test_om3_timeseries_mapped_reduces_gridded_data(fake_om3_references):
    """Test that a mapped gridded variable is plotted as its global mean."""
    figs = analysis._analyse_and_plot(
        _mom5_style_dataset(), recipes.recipe_om3_timeseries_mapped, soga_var="salt"
    )

    user_line = figs[0].axes[0].get_lines()[0]
    np.testing.assert_allclose(user_line.get_ydata(), MOM5_GLOBAL_MEAN_SALT)
    assert fake_om3_references == ["soga"]


def _om3_dataset_with_unplottable_grid():
    """OM3-named dataset: a plottable ``soga`` and a gridded ``tos_max`` with no time method."""
    return xr.Dataset(
        {
            "soga": ("time", np.full(24, 34.6)),
            "tos_max": (
                ("time", "xh"),
                np.ones((24, 3)),
                {"cell_methods": "time: point"},
            ),
        },
        coords={"time": _monthly_time(24)},
    )


def test_om3_timeseries_skips_grid_without_time_method(fake_om3_references, recwarn):
    """Test that the automated recipe skips only that plot, with a warning pointing to the mapped recipe."""
    results = recipes.recipe_om3_timeseries(_om3_dataset_with_unplottable_grid())

    assert [plot_kwargs["title"] for _, plot_kwargs in results] == [
        "soga: Global Mean Ocean Salinity"
    ]
    warning = _user_warnings(recwarn)
    assert "tos_max skipped" in warning
    assert "custom variable mapping" in warning


def test_om3_timeseries_raises_when_every_plot_is_skipped(fake_om3_references):
    """Test that a suite with nothing left to plot fails, rather than reporting no plots as a success."""
    ds = _om3_dataset_with_unplottable_grid().drop_vars("soga")

    with pytest.raises(ValueError, match="could be plotted"):
        recipes.recipe_om3_timeseries(ds)


def test_om3_timeseries_mapped_plots_grid_without_time_method_with_warning(
    fake_om3_references, recwarn
):
    """Test that the mapped recipe plots the spatial mean of such data, with a warning."""
    ds = _mom5_style_dataset()
    ds["sst"].attrs["cell_methods"] = "time: point"

    figs = analysis._analyse_and_plot(
        ds, recipes.recipe_om3_timeseries_mapped, tos_max_var="sst"
    )

    user_line = figs[0].axes[0].get_lines()[0]
    np.testing.assert_allclose(user_line.get_ydata(), MOM5_UNWEIGHTED_MEAN_SST)
    assert "no time mean, max or min" in _user_warnings(recwarn)


def test_om3_timeseries_mapped_plots_mismatched_variable_with_warning(
    fake_om3_references, recwarn
):
    """Test that mapping a time-mean SST to ``tos_max`` still plots, as its mean, with a warning."""
    ds = _mom5_style_dataset()
    ds["sst"].attrs["cell_methods"] = "time: mean"

    figs = analysis._analyse_and_plot(
        ds, recipes.recipe_om3_timeseries_mapped, tos_max_var="sst"
    )

    user_line = figs[0].axes[0].get_lines()[0]
    np.testing.assert_allclose(user_line.get_ydata(), MOM5_UNWEIGHTED_MEAN_SST)
    assert "tos_max is a spatial max, but 'sst'" in _user_warnings(recwarn)


@pytest.mark.parametrize("name", ["masso", "total_wfo"])
def test_om3_timeseries_mapped_rejects_gridded_totals(fake_om3_references, name):
    """Test that a gridded variable can't stand in for a global-total field.

    Averaging a gridded flux and plotting it against reference totals would be
    off by roughly the ocean area. Nothing should be loaded before the error.
    """
    with pytest.raises(ValueError, match=f"{name} is a global total"):
        recipes.recipe_om3_timeseries_mapped(
            _mom5_style_dataset(), soga_var="salt", **{f"{name}_var": "salt"}
        )
    assert fake_om3_references == []


@pytest.mark.parametrize(
    "dims, shape",
    [
        pytest.param(("time",), (24,), id="time-only"),
        pytest.param(("time", "scalar_axis"), (24, 1), id="mom-scalar-axis"),
    ],
)
def test_om3_timeseries_plots_timeseries_totals(fake_om3_references, dims, shape):
    """Test that an already-totalled timeseries plots unchanged as a total field.

    MOM writes its global scalars with a size-1 ``scalar_axis``, which must not
    count as gridded.
    """
    ds = xr.Dataset(
        {"total_wfo": (dims, np.arange(24.0).reshape(shape))},
        coords={"time": _monthly_time(24)},
    )

    [(data, _plot_kwargs)] = recipes.recipe_om3_timeseries(ds)

    np.testing.assert_allclose(data.squeeze(), np.arange(24.0))


def test_om3_timeseries_skips_gridded_totals(fake_om3_references, recwarn):
    """Test that the OM3-names recipe skips a gridded total field, with a warning, and plots the rest.

    Its references shouldn't be loaded either, since each load reads from /g/data.
    """
    ds = xr.Dataset(
        {
            "masso": (("time", "x"), np.ones((24, 2))),
            "soga": ("time", np.full(24, 34.6)),
        },
        coords={"time": _monthly_time(24)},
    )

    results = recipes.recipe_om3_timeseries(ds)

    assert [plot_kwargs["title"] for _, plot_kwargs in results] == [
        "soga: Global Mean Ocean Salinity"
    ]
    assert "masso skipped: masso is a global total" in _user_warnings(recwarn)
    assert fake_om3_references == ["soga"]


# OM3 reference loading


def test_om3_timeseries_datastores(monkeypatch):
    """Test that each reference catalog is opened and keyed by experiment folder.

    The catalogs' ``variable`` column holds lists, so intake-esm must be told
    to parse it as an iterable or searches by variable find nothing.
    """
    monkeypatch.setattr(
        recipes,
        "OM3_TIMESERIES_REF_CATALOGS",
        ["/g/data/refA/datastore.json", "/g/data/refB/datastore.json"],
    )
    open_datastore = MagicMock(side_effect=lambda path, **kwargs: path)
    monkeypatch.setattr(recipes.intake, "open_esm_datastore", open_datastore)
    access_nri_catalog = MagicMock()
    access_nri_catalog.access_nri = {recipes.OM3_TIMESERIES_OM2_EXPT: "om2 catalog"}
    monkeypatch.setattr(recipes.intake, "cat", access_nri_catalog)

    recipes._om3_timeseries_datastores.cache_clear()
    datastores, om2cat = recipes._om3_timeseries_datastores()
    # A second call reuses the opened catalogs
    recipes._om3_timeseries_datastores()
    recipes._om3_timeseries_datastores.cache_clear()

    assert datastores == {
        "refA": "/g/data/refA/datastore.json",
        "refB": "/g/data/refB/datastore.json",
    }
    assert om2cat == "om2 catalog"
    assert open_datastore.call_count == 2
    open_datastore.assert_any_call(
        "/g/data/refA/datastore.json", columns_with_iterables=["variable"]
    )


def _mock_search_result(ds):
    """Mock an intake-esm search result that finds ``ds``, or nothing if None."""
    result = MagicMock()
    result.__len__.return_value = 0 if ds is None else 1
    result.to_dask.return_value = ds
    return result


def _mock_datastore(*search_results):
    """Mock a datastore whose successive searches return or raise ``search_results``."""
    datastore = MagicMock()
    datastore.search.side_effect = list(search_results)
    return datastore


def _om3_scalar_timeseries(name, values, calendar="noleap"):
    """Monthly scalar timeseries like the OM3 reference ``*ga`` fields."""
    return xr.Dataset(
        {name: ("time", values)},
        coords={"time": _monthly_time(len(values), calendar=calendar)},
        attrs={"intake_esm_attrs:frequency": "1mon"},
    )


# (year, month) range covering the fake references below
YEAR_2000 = ((2000, 1), (2000, 12))


@pytest.fixture
def fake_reference_sources(monkeypatch):
    """Replace the reference catalogs with an OM2 catalog and one OM3 run.

    Returns ``(om2cat, load_var)``: the mock OM2 catalog, and the mock
    per-datastore loader, which finds ``soga`` in run "refA".
    """
    om2cat = MagicMock()
    om2cat.search.return_value.to_dask.return_value = _om3_scalar_timeseries(
        "salt_global_ave", [34.60, 34.61, 34.62]
    )
    monkeypatch.setattr(
        recipes, "_om3_timeseries_datastores", MagicMock(return_value=({}, om2cat))
    )
    load_var = MagicMock(
        return_value={"refA": _om3_scalar_timeseries("soga", [34.70, 34.71, 34.72])}
    )
    monkeypatch.setattr(recipes, "_load_om3_timeseries_var", load_var)
    return om2cat, load_var


def test_load_om3_timeseries_reference_adds_om2(fake_reference_sources):
    """Test that OM2 is found under its own name and drawn beneath the OM3 runs.

    OM2's field is searched at OM3's frequency and renamed to the OM3 name, and
    every run is put on one calendar so the IAF runs share an x-axis.
    """
    om2cat, _ = fake_reference_sources

    reference = recipes._load_om3_timeseries_reference("soga", *YEAR_2000)

    assert list(reference) == [recipes.OM3_TIMESERIES_OM2_EXPT, "refA"]
    om2cat.search.assert_called_once_with(variable="salt_global_ave", frequency="1mon")
    np.testing.assert_allclose(
        reference[recipes.OM3_TIMESERIES_OM2_EXPT], [34.60, 34.61, 34.62]
    )
    np.testing.assert_allclose(reference["refA"], [34.70, 34.71, 34.72])
    assert all(
        da.time.dt.calendar == "proleptic_gregorian" for da in reference.values()
    )


def test_load_om3_timeseries_reference_without_om2_equivalent(fake_reference_sources):
    """Test that fields with no OM2 equivalent skip the OM2 search."""
    om2cat, load_var = fake_reference_sources
    load_var.return_value = {"refA": _om3_scalar_timeseries("masso", [1.0])}

    assert list(recipes._load_om3_timeseries_reference("masso", *YEAR_2000)) == ["refA"]
    om2cat.search.assert_not_called()


def test_load_om3_timeseries_reference_found_nowhere(fake_reference_sources):
    """Test that nothing found in the OM3 runs gives nothing to overlay."""
    _, load_var = fake_reference_sources
    load_var.return_value = {}

    assert recipes._load_om3_timeseries_reference("soga", *YEAR_2000) == {}


def test_load_om3_timeseries_var_keeps_datastores_with_the_variable():
    """Test that each datastore is searched, and only those with matches are kept."""
    ds = _om3_scalar_timeseries("soga", [34.7])
    match = _mock_search_result(ds)
    ref_a = _mock_datastore(match)
    ref_b = _mock_datastore(_mock_search_result(None))

    found = recipes._load_om3_timeseries_var({"refA": ref_a, "refB": ref_b}, "soga")

    assert found == {"refA": ds}
    ref_a.search.assert_called_once_with(variable="soga")
    match.to_dask.assert_called_once_with(
        xarray_combine_by_coords_kwargs=recipes.OM3_TIMESERIES_COMBINE_KWARGS
    )


def test_load_om3_timeseries_var_retries_ambiguous_searches():
    """Test that a search matching several datasets falls back to a narrower one."""
    ds = _om3_scalar_timeseries("soga", [34.7])
    ref = _mock_datastore(ValueError("ambiguous"), _mock_search_result(ds))

    assert recipes._load_om3_timeseries_var({"ref": ref}, "soga") == {"ref": ds}
    ref.search.assert_called_with(
        variable="soga", **recipes.OM3_TIMESERIES_REF_SEARCHES[1]
    )


def test_load_om3_timeseries_var_reports_when_every_search_fails(recwarn):
    """Test that a datastore with no usable search is reported and skipped."""
    ref = MagicMock()
    ref.search.side_effect = ValueError("ambiguous")

    assert recipes._load_om3_timeseries_var({"ref": ref}, "soga") == {}
    assert ref.search.call_count == len(recipes.OM3_TIMESERIES_REF_SEARCHES)
    assert "soga failed" in _user_warnings(recwarn)


def test_om3_timeseries_datastores_skips_catalogs_that_fail(monkeypatch, recwarn):
    """Test that a missing reference catalog is reported and the rest still open.

    The references live on /g/data/ol01, which not every user can read, so one
    failing must not stop the whole suite.
    """
    monkeypatch.setattr(
        recipes,
        "OM3_TIMESERIES_REF_CATALOGS",
        ["/g/data/refA/datastore.json", "/g/data/refB/datastore.json"],
    )

    def open_datastore(path, **kwargs):
        if "refA" in path:
            raise FileNotFoundError(path)
        return path

    monkeypatch.setattr(recipes.intake, "open_esm_datastore", open_datastore)
    access_nri_catalog = MagicMock()
    access_nri_catalog.access_nri = {}
    monkeypatch.setattr(recipes.intake, "cat", access_nri_catalog)

    recipes._om3_timeseries_datastores.cache_clear()
    datastores, om2cat = recipes._om3_timeseries_datastores()
    recipes._om3_timeseries_datastores.cache_clear()

    assert datastores == {"refB": "/g/data/refB/datastore.json"}
    assert om2cat is None
    out = _user_warnings(recwarn)
    assert "refA failed" in out
    assert f"{recipes.OM3_TIMESERIES_OM2_EXPT} failed" in out


def test_load_om3_timeseries_var_skips_datastores_that_fail(recwarn):
    """Test that one unreadable datastore is reported and the others still load."""
    ds = _om3_scalar_timeseries("soga", [34.7])
    broken = _mock_search_result(ds)
    broken.to_dask.side_effect = ESMDataSourceError("corrupt file")
    ref_a = _mock_datastore(broken)
    ref_b = _mock_datastore(_mock_search_result(ds))

    found = recipes._load_om3_timeseries_var({"refA": ref_a, "refB": ref_b}, "soga")

    assert found == {"refB": ds}
    assert "soga failed for refA: corrupt file" in _user_warnings(recwarn)


def test_load_om3_timeseries_var_retries_only_the_ambiguous_datastore():
    """Test that an ambiguous search in one datastore doesn't re-search the others."""
    ds = _om3_scalar_timeseries("soga", [34.7])
    ambiguous = _mock_datastore(ValueError("ambiguous"), _mock_search_result(ds))
    plain = _mock_datastore(_mock_search_result(ds))

    found = recipes._load_om3_timeseries_var({"refA": ambiguous, "refB": plain}, "soga")

    assert found == {"refA": ds, "refB": ds}
    plain.search.assert_called_once_with(variable="soga")


def test_load_om3_timeseries_reference_cuts_to_user_range(fake_reference_sources):
    """Test that references only keep the months the user data covers."""
    reference = recipes._load_om3_timeseries_reference("soga", (2000, 2), (2000, 3))

    np.testing.assert_allclose(reference["refA"], [34.71, 34.72])
    np.testing.assert_allclose(
        reference[recipes.OM3_TIMESERIES_OM2_EXPT], [34.61, 34.62]
    )


def test_load_om3_timeseries_reference_leaves_out_runs_outside_user_range(
    fake_reference_sources, recwarn
):
    """Test that a reference with no data in the user's years is left out, with a warning."""
    reference = recipes._load_om3_timeseries_reference("masso", (1958, 1), (1967, 12))

    assert reference == {}
    assert "masso reference refA has no data" in _user_warnings(recwarn)


def test_load_om3_timeseries_reference_moves_ryf_run_to_user_start(
    fake_reference_sources, monkeypatch
):
    """Test that an RYF run's made-up years are moved to start in the user data's first year.

    Its months stay as they are, and it's cut at the end of the user data.
    """
    _, load_var = fake_reference_sources
    load_var.return_value = {
        "ryf": xr.Dataset(
            {"masso": ("time", [1.0, 2.0, 3.0, 4.0])},
            coords={
                "time": xr.date_range(
                    "1900-01-01",
                    periods=4,
                    freq="MS",
                    calendar="noleap",
                    use_cftime=True,
                )
            },
        )
    }
    monkeypatch.setattr(recipes, "OM3_TIMESERIES_RYF_EXPTS", ["ryf"])

    reference = recipes._load_om3_timeseries_reference("masso", (1958, 1), (1958, 3))

    ryf = reference["ryf"]
    np.testing.assert_allclose(ryf, [1.0, 2.0, 3.0])
    assert [(t.year, t.month) for t in ryf.indexes["time"]] == [
        (1958, 1),
        (1958, 2),
        (1958, 3),
    ]


def test_om3_timeseries_rejects_time_dim_without_dates():
    """Test that a time dimension without dates fails readably, so the suite can skip it."""
    ds = xr.Dataset({"soga": ("step", np.full(5, 34.6))}, coords={"step": np.arange(5)})

    with pytest.raises(ValueError, match="must hold dates"):
        recipes._om3_timeseries(ds, "soga", "soga", "step")


def test_om3_timeseries_asks_for_references_over_user_range(monkeypatch):
    """Test that the user data's first and last (year, month) are passed to the reference loader."""
    asked = []
    monkeypatch.setattr(
        recipes,
        "_load_om3_timeseries_reference",
        lambda var, start, end: asked.append((var, start, end)) or {},
    )
    ds = xr.Dataset(
        {"soga": ("time", np.full(14, 34.6))}, coords={"time": _monthly_time(14)}
    )

    recipes._om3_timeseries(ds, "soga", "soga", "time")

    assert asked == [("soga", (2000, 1), (2001, 2))]


def test_load_om3_timeseries_reference_skips_om2_when_it_fails(
    fake_reference_sources, recwarn
):
    """Test that the OM3 runs are still plotted if the OM2 run can't be loaded."""
    om2cat, _ = fake_reference_sources
    om2cat.search.return_value.to_dask.side_effect = ESMDataSourceError("no access")

    reference = recipes._load_om3_timeseries_reference("soga", *YEAR_2000)

    assert list(reference) == ["refA"]
    assert f"soga failed for {recipes.OM3_TIMESERIES_OM2_EXPT}" in _user_warnings(
        recwarn
    )


# Niño 3.4

# Area-weighted mean of the anomaly scaling used below
NINO34_LATS = np.arange(-4.5, 5)
NINO34_ANOMALY_SCALE = np.average(
    1 + NINO34_LATS**2 / 10, weights=np.cos(np.deg2rad(NINO34_LATS))
)


def test_recipe_sst_anomaly_nino34():
    """Test the Niño 3.4 index on SST with a known anomaly.

    Some years are warmer or cooler than usual, more so away from the equator,
    so the area weighting changes the answer. SST outside the box is very
    high, so any leak shows. Smoothing leaves NaN months at each end.
    """
    seasonal_cycle = 26 + 2 * np.sin(2 * np.pi * np.arange(48) / 12)
    yearly_anomaly = np.repeat([0.0, 1.0, -1.0, 0.0], 12)
    lon = np.arange(-279.5, 80)
    lat = np.arange(-9.5, 10)
    in_region = (np.abs(lat) < 5)[:, None] & ((lon > -170) & (lon < -120))[None, :]
    anomaly = yearly_anomaly[:, None, None] * (1 + lat**2 / 10)[None, :, None]
    tos = np.where(in_region, seasonal_cycle[:, None, None] + anomaly, 100.0)
    ds = xr.Dataset(
        {"tos": (("time", "yt_ocean", "xt_ocean"), tos)},
        coords={
            "time": _monthly_time(48, use_cftime=False),
            "yt_ocean": lat,
            "xt_ocean": lon,
        },
    )

    index, plot_kwargs = recipes.recipe_sst_anomaly_nino34(ds)

    assert index.sizes["time"] == 48
    assert index[:2].isnull().all()
    assert index[-2:].isnull().all()
    expected = [0, NINO34_ANOMALY_SCALE, -NINO34_ANOMALY_SCALE, 0]
    # In July the seasons average out, so April also checks they are removed
    for month in [4, 7]:
        np.testing.assert_allclose(
            index.sel(time=index["time.month"] == month), expected, atol=1e-10
        )
    assert plot_kwargs["title"] == "Niño 3.4 Index"
    assert plot_kwargs["ax_kwargs"]["ylabel"] == "Niño 3.4 SST Anomaly (°C)"
    assert plot_kwargs["customise"] == [
        recipes.plot_customisations.nino_fills,
        recipes.plot_customisations.nino_reference_lines,
    ]


def test_recipe_sst_anomaly_nino34_rejects_wrong_grid():
    """Test that a dataset without the chosen lat/lon dims gives a readable error."""
    ds = xr.Dataset(
        {"tos": (("time", "lat", "lon"), np.zeros((12, 2, 2)))},
        coords={"time": _monthly_time(12), "lat": [0, 1], "lon": [0, 1]},
    )

    with pytest.raises(ValueError, match="write a custom"):
        recipes.recipe_sst_anomaly_nino34(ds)


# Regional mean (MOM5)

# Tasmania's 1° latitude centres, weighted by cos(latitude)
TASMANIA_LATS = np.arange(-43.5, -39)
TASMANIA_MEAN_LAT = np.average(TASMANIA_LATS, weights=np.cos(np.deg2rad(TASMANIA_LATS)))


def _mom5_regional_dataset():
    """MOM5-style ``temp`` that is time + latitude + 100 per depth level in the region.

    Outside the region it is 1000, so any leak shows in the mean. The regional
    mean at the surface is therefore ``time step + TASMANIA_MEAN_LAT``.
    """
    depth = np.array([5.0, 50.0, 500.0])
    lat = np.arange(-49.5, -30)
    # MOM5 longitudes run from -280 to 80, so Tasmania sits at -217 to -211
    lon = np.arange(-279.5, 80)
    in_region = ((lat > -44) & (lat < -39))[:, None] & ((lon > -217) & (lon < -211))[
        None, :
    ]
    values = (
        np.arange(6)[:, None, None, None]
        + 100 * np.arange(3)[None, :, None, None]
        + lat[None, None, :, None]
    )
    temp = np.where(in_region, values, 1000.0)
    return xr.Dataset(
        {
            "temp": (
                ("time", "st_ocean", "yt_ocean", "xt_ocean"),
                temp,
                {"units": "degC"},
            ),
            "sst": (("time", "yt_ocean", "xt_ocean"), temp[:, 0]),
        },
        coords={
            "time": _monthly_time(6, use_cftime=False),
            "st_ocean": depth,
            "yt_ocean": lat,
            "xt_ocean": lon,
        },
    )


SURFACE_MEAN = np.arange(6) + TASMANIA_MEAN_LAT


def test_recipe_regional_mean_mom5_defaults():
    """Test the default: area-weighted surface mean with percentiles and trend."""
    timeseries, plot_kwargs = recipes.recipe_regional_mean_mom5(
        _mom5_regional_dataset(), depth=2
    )

    np.testing.assert_allclose(timeseries, SURFACE_MEAN)
    assert timeseries.name == "Tasmania mean temp"
    assert plot_kwargs["title"] == "Tasmania mean temp (5 m)"
    assert plot_kwargs["ax_kwargs"]["ylabel"] == "temp (degC)"
    assert plot_kwargs["customise"] == [
        recipes.plot_customisations.shade_top_10pct,
        recipes.plot_customisations.shade_bottom_10pct,
        recipes.plot_customisations.add_trend,
    ]


def test_recipe_regional_mean_mom5_depth_and_threshold(monkeypatch):
    """Test that the nearest level is used and only the chosen overlay is drawn.

    The nearest level to 60 m is the second one (50 m), which is 100 warmer.
    """
    add_threshold = MagicMock()
    monkeypatch.setattr(recipes.plot_customisations, "add_threshold", add_threshold)

    timeseries, plot_kwargs = recipes.recipe_regional_mean_mom5(
        _mom5_regional_dataset(),
        depth=60.0,
        show_trend=False,
        show_percentiles=False,
        threshold="15",
    )

    np.testing.assert_allclose(timeseries, SURFACE_MEAN + 100)
    (draw_threshold,) = plot_kwargs["customise"]
    ax = MagicMock()
    draw_threshold(ax, timeseries)
    add_threshold.assert_called_once_with(ax, value=15.0)


def test_recipe_regional_mean_mom5_smoothing():
    """Test that a centred 3-step mean keeps a straight line but loses each end."""
    timeseries, _ = recipes.recipe_regional_mean_mom5(
        _mom5_regional_dataset(), smooth_steps=3
    )

    assert timeseries[[0, -1]].isnull().all()
    np.testing.assert_allclose(timeseries[1:-1], SURFACE_MEAN[1:-1])


def test_recipe_regional_mean_mom5_surface_field():
    """Test that a field with no depth dimension needs no level selected."""
    timeseries, _ = recipes.recipe_regional_mean_mom5(
        _mom5_regional_dataset(), variable="sst"
    )

    np.testing.assert_allclose(timeseries, SURFACE_MEAN)


def test_recipe_regional_mean_mom5_rejects_other_grids():
    """Test that non-MOM5 dimension names fail with a readable message."""
    with pytest.raises(ValueError, match="expects MOM5 output"):
        recipes.recipe_regional_mean_mom5(_mom5_regional_dataset(), lat_dim="yh")


def test_om3_timeseries_smooths_user_and_references_by_calendar_year(monkeypatch):
    """Test that the user data and each reference get calendar-year means, as in the paper.

    The reference is daily and the user data monthly, so a fixed window of
    timesteps would smooth them over different spans.
    """
    days = xr.date_range("2000-01-01", "2002-12-31", freq="D", use_cftime=True)
    reference = xr.DataArray(days.year - 2000.0, coords={"time": days}, dims="time")
    monkeypatch.setattr(
        recipes,
        "_load_om3_timeseries_reference",
        lambda var, start, end: {"refA": reference},
    )
    ds = xr.Dataset(
        {"soga": ("time", np.arange(36.0))}, coords={"time": _monthly_time(36)}
    )

    [fig] = analysis._analyse_and_plot(ds, recipes.recipe_om3_timeseries)

    _, user_yearly, _, ref_yearly = fig.axes[0].get_lines()
    np.testing.assert_allclose(user_yearly.get_ydata(), [5.5, 17.5, 29.5])
    np.testing.assert_allclose(ref_yearly.get_ydata(), [0.0, 1.0, 2.0])


def test_om3_timeseries_matches_paper_styling(fake_om3_references):
    """Test the paper's styling: thin raw lines, thick labelled yearly means, no x label."""
    ds = xr.Dataset(
        {"soga": ("time", np.full(24, 34.6))}, coords={"time": _monthly_time(24)}
    )

    [fig] = analysis._analyse_and_plot(ds, recipes.recipe_om3_timeseries)

    ax = fig.axes[0]
    assert [line.get_linewidth() for line in ax.get_lines()] == [0.7, 2, 0.7, 2]
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["User data", "refA"]
    assert ax.get_xlabel() == ""
    assert tuple(fig.get_size_inches()) == (10, 5)
