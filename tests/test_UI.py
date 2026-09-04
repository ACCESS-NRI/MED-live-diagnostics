# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for tests"""

from med_diagnostics.ui import UserInterface

# from med_diagnostics.data import _build_new_catalog
import pytest


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
    ui = UserInterface()
    assert ui._round_slice_val(input_value) == expected_output


# make xarray dataset, one for each that it tests, 1d, 2d, 3d.
# run the test

# eeach in a seperate function, checkplotvalidity3d e.g.

if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
