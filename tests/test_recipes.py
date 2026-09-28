import inspect
from typing import Annotated, Literal

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
    options = analysis.get_recipe_kwarg_options(recipe)
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
    options = {o["name"]: o for o in analysis.get_recipe_kwarg_options(recipe_example)}

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
        o["name"]: o for o in analysis.get_recipe_kwarg_options(recipe_example, ds)
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

    options = {o["name"]: o for o in analysis.get_recipe_kwarg_options(recipe_plain)}
    assert options["depth"]["kind"] is None
    assert options["depth"]["default"] == 0
    assert options["method"]["kind"] == "mispelt"
