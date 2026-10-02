import inspect
from typing import Annotated, Literal

import numpy as np
import pytest
import xarray as xr

from med_diagnostics import analysis, recipes

RECIPES = [
    func
    for name, func in inspect.getmembers(recipes, inspect.isfunction)
    if name.startswith("recipe_")
]


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r.__name__)
def test_every_recipe_annotation_parses_for_the_ui(recipe):
    """Test that each prebuilt recipe's annotations give the UI a complete form.

    Unknown kinds silently become text boxes, so a typo in a prebuilt recipe
    would only show up as a wrong widget at runtime. Every parameter must get
    a known kind and a description for its tooltip.
    """
    options = analysis._get_recipe_kwarg_options(recipe)
    names = [p for p in inspect.signature(recipe).parameters][1:]
    assert [o["name"] for o in options] == names
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
    """
    options = {o["name"]: o for o in analysis._get_recipe_kwarg_options(recipe_example)}

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
    # Literal fills choices, but the kind still comes from the metadata
    assert options["stat"]["kind"] == "choice"
    assert options["stat"]["choices"] == ["mean", "max"]
    assert options["region"]["choices"] == ["a", "b"]
    assert options["depth"]["units"] == "m"
    assert options["depth"]["label"] == "depth"
    assert options["required"]["required"] is True
    assert options["depth"]["required"] is False


def test_dataset_fills_variable_and_dimension_choices():
    """Test that choices come from the dataset, with None for optional dims.

    Single-valued dims and bounds dims (``nv``) aren't useful analysis axes,
    so they're left out of the dropdown.
    """
    ds = xr.Dataset(
        {"temp": (("time", "lat", "nv"), [[[0.0, 1.0]] * 2] * 3)},
        coords={"time": [0, 1, 2], "lat": [0, 1], "st_ocean": ("st_ocean", [5.0])},
    )
    options = {
        o["name"]: o for o in analysis._get_recipe_kwarg_options(recipe_example, ds)
    }

    assert options["variable"]["choices"] == ["temp"]
    assert options["lvl_dim"]["choices"] == [None, "time", "lat"]


def test_unannotated_parameters_are_accepted():
    """Test that parameters without annotations still get an option.

    Kind validation was dropped on purpose: an unknown or missing kind becomes
    a text box in the UI rather than an error.
    """

    def recipe_plain(ds, depth=0, method: Annotated[str, {"kind": "mispelt"}] = "x"):
        """Plain recipe."""

    options = {o["name"]: o for o in analysis._get_recipe_kwarg_options(recipe_plain)}
    assert options["depth"]["kind"] is None
    assert options["depth"]["default"] == 0
    assert options["method"]["kind"] == "mispelt"


@pytest.mark.parametrize(
    "lon_start", [0.5, -179.5, -279.5], ids=["0-360", "-180-180", "mom5"]
)
@pytest.mark.parametrize("region", list(recipes.PREDEFINED_REGIONS))
def test_every_region_selects_cells(region, lon_start):
    """Test that every predefined region selects cells on common grids.

    Full-width regions (e.g. "tropics") used to select no longitudes, giving an
    all-NaN mean that only surfaced later as a confusing error in add_trend.
    """
    ds = xr.Dataset(
        {"temp": (("lat", "lon"), np.ones((180, 360)))},
        coords={
            "lat": np.arange(-89.5, 90),
            "lon": np.arange(lon_start, lon_start + 360),
        },
    )
    subset = recipes.extract_region(ds, region)
    assert subset.sizes["lat"] > 0
    assert subset.sizes["lon"] > 0
    if region == "global":
        assert subset.sizes["lon"] == 360


def _mom5_style_dataset():
    """Small MOM5-style dataset: Kelvin temp, land NaNs and ``st_edges_ocean``."""
    time = xr.date_range("2000-01-01", periods=24, freq="MS", use_cftime=True)
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
            "time": time,
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


def test_global_mean_weights_by_layer_thickness_and_converts_kelvin():
    """Test that an unweighted mean would be wrong.

    A plain mean counts the thin surface layer as much as the thick deep one,
    and leaves temperature in Kelvin, so OM2/ESM output can't be compared with
    the OM3 references.
    """
    ds = _mom5_style_dataset()
    temp = recipes.global_mean(ds, "temp", "time")
    salt = recipes.global_mean(ds, "salt", "time")

    # Layers are 10, 10 and 160 m thick
    np.testing.assert_allclose(temp, (20 * 10 + 2 * 170) / 180)
    np.testing.assert_allclose(salt, (34 * 20 + 35 * 160) / 180)
    assert temp.attrs["units"] == "degC"


def test_global_mean_uses_cf_bounds_and_cell_measures():
    """Test the MOM6/CF route: ``bounds`` on depth and ``cell_measures`` for area."""
    ds = _mom5_style_dataset()
    salt = ds["salt"].values
    ds = xr.Dataset(
        {
            "so": (
                ("time", "zl", "yh", "xh"),
                salt,
                {"cell_measures": "area: areacello"},
            ),
            "areacello": (("yh", "xh"), np.ones((2, 2))),
            "zl_bnds": (("zl", "nv"), [[0.0, 10.0], [10.0, 20.0], [20.0, 180.0]]),
        },
        coords={
            "time": ds["time"],
            "zl": ("zl", [5.0, 15.0, 100.0], {"axis": "Z", "bounds": "zl_bnds"}),
            "yh": ("yh", [0.0, 60.0], {"axis": "Y"}),
            "xh": ("xh", [0.0, 1.0], {"axis": "X"}),
        },
    )
    np.testing.assert_allclose(
        recipes.global_mean(ds, "so", "time"), (34 * 20 + 35 * 160) / 180
    )


def test_global_mean_max_and_scalar_passthrough():
    """Test that ``*_max`` fields take the global maximum, and scalars pass through."""
    ds = _mom5_style_dataset()
    np.testing.assert_allclose(recipes.global_mean(ds, "sst", "time", "max"), 20.0)
    assert recipes._om3_timeseries_reduction("tos_max") == "max"
    assert recipes._om3_timeseries_reduction("soga") == "mean"

    scalar = xr.Dataset({"soga": ("time", [34.7, 34.71])}, coords={"time": [0, 1]})
    np.testing.assert_allclose(
        recipes.global_mean(scalar, "soga", "time"), [34.7, 34.71]
    )


@pytest.fixture
def fake_om3_references(monkeypatch):
    """Replace the /g/data reference loader with a flat 34.7 timeseries."""
    time = xr.date_range("2000-01-01", periods=24, freq="MS", use_cftime=True)
    loaded = []

    def fake(var):
        loaded.append(var)
        return {"refA": xr.DataArray(np.full(24, 34.7), coords={"time": time})}

    monkeypatch.setattr(recipes, "_load_om3_timeseries_reference", fake)
    return loaded


def test_om3_timeseries_plots_each_found_variable(fake_om3_references):
    """Test that the OM3-names recipe plots every known variable, with references."""
    ds = xr.Dataset(
        {"soga": ("time", np.full(24, 34.6)), "other": ("time", np.zeros(24))},
        coords={
            "time": xr.date_range("2000-01-01", periods=24, freq="MS", use_cftime=True)
        },
    )
    figs = analysis._analyse_and_plot(ds, recipes.recipe_om3_timeseries)

    assert [f.axes[0].get_title() for f in figs] == ["soga: Global Mean Ocean Salinity"]
    labels = [line.get_label() for line in figs[0].axes[0].get_lines()]
    assert "User data" in labels and "refA" in labels
    # Only the plotted variable's references are loaded
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
    np.testing.assert_allclose(user_line.get_ydata(), (34 * 20 + 35 * 160) / 180)
    assert fake_om3_references == ["soga"]
