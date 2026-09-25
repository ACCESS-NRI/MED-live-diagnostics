import pytest

from med_diagnostics import analysis, recipes


@pytest.fixture(autouse=True)
def empty_uploads(monkeypatch):
    """Give each test its own empty upload registry."""
    monkeypatch.setattr(analysis, "UPLOADED_ANALYSES", {})


def my_mean(ds, variable="o2"):
    """
    Mean of a variable.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset.
    variable : data variable, default "o2"
        Variable to average.
    """
    return ds[variable].mean()


def test_upload_analysis_registers_by_name():
    """Test that an uploaded function is stored by name and listed for the UI.

    Returning the function unchanged lets ``upload_analysis`` also be used as
    a decorator without replacing the user's function with None.
    """
    assert analysis.upload_analysis(my_mean) is my_mean
    assert analysis.UPLOADED_ANALYSES == {"my_mean": my_mean}
    assert recipes.list_recipes()["Custom: Mean of a variable."] is my_mean


def test_reuploading_replaces_the_old_version():
    """Test that editing and re-uploading a function doesn't duplicate it.

    The notebook workflow is edit, re-run the cell, re-upload, so the
    registry must hold only the latest version under each name.
    """
    analysis.upload_analysis(my_mean)

    def edited(ds):
        """New version."""

    edited.__name__ = "my_mean"  # as if the notebook cell were edited and re-run
    analysis.upload_analysis(edited)
    assert analysis.UPLOADED_ANALYSES == {"my_mean": edited}
    assert list(recipes.list_recipes()).count("Custom: New version.") == 1


@pytest.mark.parametrize(
    "bad_func, error",
    [
        pytest.param("not a function", TypeError, id="not-callable"),
        pytest.param(lambda: None, TypeError, id="no-dataset-argument"),
        pytest.param(lambda ds, depth=0: None, ValueError, id="undocumented-parameter"),
    ],
)
def test_upload_analysis_rejects_bad_functions(bad_func, error):
    """Test that unusable functions fail at upload, not later in the UI.

    A function that can't take the dataset, or whose docstring can't build a
    form, would otherwise only fail once the user picks it in the UI.
    """
    with pytest.raises(error):
        analysis.upload_analysis(bad_func)
    assert analysis.UPLOADED_ANALYSES == {}
