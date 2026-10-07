import inspect
from typing import Annotated, Literal
from unittest.mock import MagicMock

import numpy as np
import pytest
import xarray as xr

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


@pytest.mark.parametrize(
    "lon_start", [0.5, -179.5, -279.5], ids=["0-360", "-180-180", "mom5"]
)
@pytest.mark.parametrize("region", list(recipes.PREDEFINED_REGIONS))
def test_every_region_selects_cells(region, lon_start):
    """Test that every predefined region selects cells on common grids.

    Full-width regions (e.g. "tropics") used to select no longitudes, giving an
    all-NaN mean that only surfaced later as a confusing error in add_trend.
    """
    subset = recipes.extract_region(_global_one_degree_grid(lon_start), region)

    assert subset.sizes["lat"] > 0
    assert subset.sizes["lon"] > 0
    if region == "global":
        assert subset.sizes["lon"] == 360


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
    ],
    ids=["monthly", "15-daily", "single-timestep"],
)
def test_rolling_window_size(freq, periods, target_days, expected_steps):
    """Test that a window length in days is converted to timesteps.

    A single timestep can't be smoothed, so it always gives a window of 1.
    """
    time = xr.date_range("2000-01-01", periods=periods, freq=freq, use_cftime=True)

    assert (
        recipes._rolling_window_size(xr.DataArray(time), target_days) == expected_steps
    )


def test_calc_anomalies_removes_monthly_climatology():
    """Test that anomalies are taken from each calendar month's mean.

    Two years share a seasonal cycle, but the second is 1 warmer, so each
    month's anomaly is -0.5 in the first year and +0.5 in the second.
    """
    seasonal_cycle = np.sin(2 * np.pi * np.arange(12) / 12)
    temp = np.concatenate([seasonal_cycle, seasonal_cycle + 1])
    ds = xr.Dataset(
        {
            "temp": (
                ("time", "lat", "lon"),
                np.broadcast_to(temp[:, None, None], (24, 2, 2)),
            )
        },
        coords={"time": _monthly_time(24), "lat": [0, 1], "lon": [0, 1]},
    )

    anomalies = recipes.calc_anomalies(ds, "lon", "lat", "temp")

    np.testing.assert_allclose(anomalies, np.repeat([-0.5, 0.5], 12))


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


@pytest.mark.parametrize(
    "attrs, axis, expected",
    [
        pytest.param({"cartesian_axis": "Y"}, "Y", "dim", id="mom5"),
        pytest.param({"axis": "Z"}, "Z", "dim", id="cf"),
        pytest.param({"axis": "x"}, "X", "dim", id="case-insensitive"),
        pytest.param({"standard_name": "latitude"}, "Y", "dim", id="standard-name-lat"),
        pytest.param({"units": "degrees_north"}, "Y", "dim", id="units"),
        pytest.param({"positive": "down"}, "Z", "dim", id="positive"),
        pytest.param({"standard_name": "depth"}, "Z", "dim", id="standard-name-depth"),
        pytest.param({"axis": "Y"}, "Z", None, id="wrong-axis"),
        pytest.param({}, "Y", None, id="no-attributes"),
    ],
)
def test_find_axis_dim(attrs, axis, expected):
    """Test that each attribute convention identifies the right axis."""
    ds = xr.Dataset(
        {"var": (("time", "dim"), np.ones((2, 3)))},
        coords={"time": [0, 1], "dim": ("dim", [0.0, 1.0, 2.0], attrs)},
    )

    assert recipes._find_axis_dim(ds, ds["var"], axis, skip="time") == expected


def test_find_axis_dim_skips_kept_dim_and_dims_without_coords():
    """Test that the skipped dim and dims with no coordinate are never returned."""
    ds = xr.Dataset(
        {"var": (("time", "nocoord"), np.ones((2, 3)))},
        coords={"time": ("time", [0, 1], {"axis": "Y"})},
    )

    assert recipes._find_axis_dim(ds, ds["var"], "Y", skip="time") is None
    assert recipes._find_axis_dim(ds, ds["var"], "Z", skip="time") is None


# Global means

# Layers in _mom5_style_dataset are 10, 10 and 160 m thick
MOM5_GLOBAL_MEAN_TEMP = (20 * 10 + 2 * 170) / 180
MOM5_GLOBAL_MEAN_SALT = (34 * 20 + 35 * 160) / 180


def _mom5_style_dataset():
    """Small MOM5-style dataset: Kelvin temp, land NaNs and ``st_edges_ocean``."""
    temp = np.full((24, 3, 2, 2), 273.15 + 2.0)
    temp[:, 0] = 273.15 + 20.0  # thin, warm surface layer
    salt = np.full((24, 3, 2, 2), 34.0)
    salt[:, 2] = 35.0  # thick, salty deep layer
    salt[:, :, 1, :] = np.nan  # some land
    dims = ("time", "st_ocean", "yt_ocean", "xt_ocean")
    return xr.Dataset(
        {
            "temp": (dims, temp, {"units": "K"}),
            "salt": (dims, salt, {"units": "psu"}),
            "sst": (dims[:1] + dims[2:], temp[:, 0], {"units": "K"}),
        },
        coords={
            "time": _monthly_time(24),
            "st_ocean": (
                "st_ocean",
                [5.0, 15.0, 100.0],
                {"cartesian_axis": "Z", "edges": "st_edges_ocean", "positive": "down"},
            ),
            "st_edges_ocean": ("st_edges_ocean", [0.0, 10.0, 20.0, 180.0]),
            "yt_ocean": ("yt_ocean", [0.0, 60.0], {"cartesian_axis": "Y"}),
            "xt_ocean": ("xt_ocean", [0.0, 1.0], {"cartesian_axis": "X"}),
        },
    )


def test_layer_thickness_from_edges():
    """Test that thickness comes from the edges variable when there is one."""
    ds = _mom5_style_dataset()

    np.testing.assert_allclose(
        recipes._layer_thickness(ds, "st_ocean"), [10.0, 10.0, 160.0]
    )


def test_layer_thickness_from_level_midpoints():
    """Test that missing edges fall back to boundaries halfway between levels."""
    ds = _mom5_style_dataset().drop_vars("st_edges_ocean")

    np.testing.assert_allclose(
        recipes._layer_thickness(ds, "st_ocean"), [10.0, 47.5, 85.0]
    )


def test_global_mean_weights_by_layer_thickness_and_converts_kelvin():
    """Test that an unweighted mean would be wrong.

    A plain mean counts the thin surface layer as much as the thick deep one,
    and leaves temperature in Kelvin, so OM2/ESM output can't be compared with
    the OM3 references.
    """
    ds = _mom5_style_dataset()
    temp = recipes.global_mean(ds, "temp", "time")
    salt = recipes.global_mean(ds, "salt", "time")

    np.testing.assert_allclose(temp, MOM5_GLOBAL_MEAN_TEMP)
    np.testing.assert_allclose(salt, MOM5_GLOBAL_MEAN_SALT)
    assert temp.attrs["units"] == "degC"


def test_global_mean_uses_cf_bounds_and_cell_measures():
    """Test the MOM6/CF route: ``bounds`` on depth and ``cell_measures`` for area."""
    mom5 = _mom5_style_dataset()
    ds = xr.Dataset(
        {
            "so": (
                ("time", "zl", "yh", "xh"),
                mom5["salt"].values,
                {"cell_measures": "area: areacello"},
            ),
            "areacello": (("yh", "xh"), np.ones((2, 2))),
            "zl_bnds": (("zl", "nv"), [[0.0, 10.0], [10.0, 20.0], [20.0, 180.0]]),
        },
        coords={
            "time": mom5["time"],
            "zl": ("zl", [5.0, 15.0, 100.0], {"axis": "Z", "bounds": "zl_bnds"}),
            "yh": ("yh", [0.0, 60.0], {"axis": "Y"}),
            "xh": ("xh", [0.0, 1.0], {"axis": "X"}),
        },
    )

    np.testing.assert_allclose(
        recipes.global_mean(ds, "so", "time"), MOM5_GLOBAL_MEAN_SALT
    )


def test_global_mean_max():
    """Test that ``how="max"`` takes the global maximum instead of the mean."""
    np.testing.assert_allclose(
        recipes.global_mean(_mom5_style_dataset(), "sst", "time", "max"), 20.0
    )


def test_global_mean_passes_scalar_timeseries_through():
    """Test that data with only a time dimension is returned unchanged."""
    ds = xr.Dataset({"soga": ("time", [34.7, 34.71])}, coords={"time": [0, 1]})

    np.testing.assert_allclose(recipes.global_mean(ds, "soga", "time"), [34.7, 34.71])


@pytest.mark.parametrize("name, how", [("tos_max", "max"), ("soga", "mean")])
def test_om3_timeseries_reduction(name, how):
    """Test that ``*_max`` fields are reduced by max and everything else by mean."""
    assert recipes._om3_timeseries_reduction(name) == how


# OM3 timeseries recipes


@pytest.fixture
def fake_om3_references(monkeypatch):
    """Replace the /g/data reference loader with a flat 34.7 timeseries.

    Returns the list of variables the recipe asked references for.
    """
    loaded = []

    def fake(var):
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

    reference = recipes._load_om3_timeseries_reference("soga")

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

    assert list(recipes._load_om3_timeseries_reference("masso")) == ["refA"]
    om2cat.search.assert_not_called()


def test_load_om3_timeseries_reference_found_nowhere(fake_reference_sources):
    """Test that nothing found in the OM3 runs gives nothing to overlay."""
    _, load_var = fake_reference_sources
    load_var.return_value = {}

    assert recipes._load_om3_timeseries_reference("soga") == {}


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


def test_load_om3_timeseries_var_reports_when_every_search_fails(capsys):
    """Test that a datastore with no usable search is reported and skipped."""
    ref = MagicMock()
    ref.search.side_effect = ValueError("ambiguous")

    assert recipes._load_om3_timeseries_var({"ref": ref}, "soga") == {}
    assert ref.search.call_count == len(recipes.OM3_TIMESERIES_REF_SEARCHES)
    assert "soga failed" in capsys.readouterr().out


# Niño 3.4


def test_recipe_sst_anomaly_nino34():
    """Test the Niño 3.4 index on SST with a known anomaly.

    SST in the region is a seasonal cycle plus a yearly anomaly of 0, +1, -1
    and 0, with 100 outside the region so any leak shows. The anomalies have
    a standard deviation of sqrt(0.5), so mid-year the index is 0 or ±sqrt(2).
    The ~5-month centred rolling mean leaves two NaN months at each end.
    """
    seasonal_cycle = 26 + 2 * np.sin(2 * np.pi * np.arange(48) / 12)
    yearly_anomaly = np.repeat([0.0, 1.0, -1.0, 0.0], 12)
    lon = np.arange(-279.5, 80)
    lat = np.arange(-9.5, 10)
    in_region = (np.abs(lat) < 5)[:, None] & ((lon > -170) & (lon < -120))[None, :]
    tos = np.where(in_region, (seasonal_cycle + yearly_anomaly)[:, None, None], 100.0)
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
    july_each_year = [6, 18, 30, 42]
    np.testing.assert_allclose(
        index.isel(time=july_each_year), [0, np.sqrt(2), -np.sqrt(2), 0], atol=1e-10
    )
    assert plot_kwargs["title"] == "Niño 3.4 Index"
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
        _mom5_regional_dataset()
    )

    np.testing.assert_allclose(timeseries, SURFACE_MEAN)
    assert timeseries.name == "Tasmania mean temp"
    assert plot_kwargs["title"] == "Tasmania mean temp (~0 m)"
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
