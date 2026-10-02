from typing import Annotated

import pytest

from med_diagnostics import analysis


@pytest.fixture(autouse=True)
def empty_uploads(monkeypatch):
    """Give each test its own empty upload registry."""
    monkeypatch.setattr(analysis, "REGISTERED_ANALYSES", {})


def my_mean(
    ds,
    variable: Annotated[
        str, {"kind": "data variable", "description": "Variable to average"}
    ] = "o2",
):
    """Mean of a variable."""
    return ds[variable].mean()


def test_register_analysis_registers_by_name():
    """Test that an uploaded function is stored by name and listed for the UI.

    Returning the function unchanged lets ``register_analysis`` also be used as
    a decorator without replacing the user's function with None.
    """
    assert analysis.register_analysis(my_mean) is my_mean
    assert analysis.REGISTERED_ANALYSES == {"my_mean": my_mean}
    assert analysis._list_recipes()["Custom: Mean of a variable."] is my_mean


def test_reuploading_replaces_the_old_version():
    """Test that editing and re-uploading a function doesn't duplicate it.

    The notebook workflow is edit, re-run the cell, re-upload, so the
    registry must hold only the latest version under each name.
    """
    analysis.register_analysis(my_mean)

    def edited(ds):
        """New version."""

    edited.__name__ = "my_mean"  # as if the notebook cell were edited and re-run
    analysis.register_analysis(edited)
    assert analysis.REGISTERED_ANALYSES == {"my_mean": edited}
    assert list(analysis._list_recipes()).count("Custom: New version.") == 1


@pytest.mark.parametrize(
    "bad_func, error",
    [
        pytest.param("not a function", TypeError, id="not-callable"),
        pytest.param(lambda: None, TypeError, id="no-dataset-argument"),
    ],
)
def test_register_analysis_rejects_bad_functions(bad_func, error):
    """Test that unusable functions fail at upload, not later in the UI.

    A function that can't take the dataset would otherwise only fail once the
    user picks it in the UI.
    """
    with pytest.raises(error):
        analysis.register_analysis(bad_func)
    assert analysis.REGISTERED_ANALYSES == {}


def test_register_analysis_accepts_unannotated_parameters():
    """Test that parameters without ``Annotated`` metadata don't block an upload.

    Kind validation was dropped on purpose: an unannotated parameter becomes
    a text box in the UI, and whether that suits the recipe is on the user.
    """

    def plain(ds, depth=0):
        """Plain recipe."""

    assert analysis.register_analysis(plain) is plain
    assert analysis.REGISTERED_ANALYSES == {"plain": plain}
