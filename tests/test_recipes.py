import inspect

import pytest

from med_diagnostics import recipes

RECIPES = [
    func
    for name, func in inspect.getmembers(recipes, inspect.isfunction)
    if name.startswith("recipe_")
]


@pytest.mark.parametrize("recipe", RECIPES, ids=lambda r: r.__name__)
def test_every_recipe_docstring_parses_for_the_ui(recipe):
    """Test that each prebuilt recipe's docstring gives the UI a complete form.

    The UI builds its widgets from these docstrings, so a typo in a kind, an
    undocumented parameter or stale docs would otherwise only show up as a
    wrong widget at runtime. Every parameter must get a known kind.
    """
    options = recipes.get_recipe_kwarg_options(recipe)
    names = [p for p in inspect.signature(recipe).parameters][1:]
    assert [o["name"] for o in options] == names
    for option in options:
        assert option["kind"] in recipes.RECIPE_KINDS
        assert option["description"]


def test_recipes_are_found():
    """Guard against the parametrised test above silently running on nothing."""
    assert RECIPES


def _recipe_with_doc(docstring, **defaults):
    """Build a throwaway recipe with the given docstring and keyword defaults."""

    def recipe_example(ds, **kwargs):
        pass

    params = [inspect.Parameter("ds", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    params += [
        inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY, default=value)
        for name, value in defaults.items()
    ]
    recipe_example.__signature__ = inspect.Signature(params)  # type: ignore[attr-defined]
    recipe_example.__doc__ = docstring
    return recipe_example


VALID_DOC = """
    Example recipe.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset.
    variable : data variable, default "o2"
        Variable to use.
    stat : {"mean", "max"}, default "mean"
        Statistic.
    depth : float, units m, default 0
        Depth.
    """


def test_valid_docstring_parses_every_field():
    """Test that each part of the type-line convention reaches the UI dict.

    Kind, units, choices and description all come from the docstring, while
    the default comes from the signature, so a stale docstring default can't
    mislead the UI.
    """
    recipe = _recipe_with_doc(VALID_DOC, variable="temp", stat="mean", depth=0)
    options = {o["name"]: o for o in recipes.get_recipe_kwarg_options(recipe)}

    assert options["variable"]["kind"] == "data variable"
    assert options["variable"]["default"] == "temp"
    assert options["stat"]["kind"] == "choice"
    assert options["stat"]["choices"] == ["mean", "max"]
    assert options["depth"]["units"] == "m"
    assert options["depth"]["description"] == "Depth."


@pytest.mark.parametrize(
    "docstring, defaults, message",
    [
        pytest.param(
            VALID_DOC.replace("data variable", "data varible"),
            {"variable": "o2", "stat": "mean", "depth": 0},
            "unknown kind 'data varible'",
            id="typo-in-kind",
        ),
        pytest.param(
            VALID_DOC,
            {"variable": "o2", "stat": "mean", "depth": 0, "level": 0},
            "'level' is not documented",
            id="undocumented-parameter",
        ),
        pytest.param(
            VALID_DOC,
            {"variable": "o2", "stat": "mean"},
            "'depth' is documented but not a parameter",
            id="stale-docs",
        ),
        pytest.param(
            VALID_DOC,
            {"variable": "o2", "stat": "min", "depth": 0},
            "defaults to 'min', which isn't one of its choices",
            id="default-not-in-choices",
        ),
    ],
)
def test_invalid_docstring_raises(docstring, defaults, message):
    """Test that docstring mistakes fail loudly instead of reaching the UI.

    Without this, each of these would silently give the UI a wrong or missing
    widget rather than an error the recipe's author can fix.
    """
    recipe = _recipe_with_doc(docstring, **defaults)
    with pytest.raises(ValueError, match=message):
        recipes.get_recipe_kwarg_options(recipe)
