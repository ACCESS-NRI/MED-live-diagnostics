# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for tests"""

import sys
import med_diagnostics
import med_diagnostics.ui as UserInterface
from med_diagnostics.data import _build_new_catalog
import pytest
from unittest.mock import MagicMock

# This intercepts the import before Pytest even looks at your src/ folder
sys.modules["access_nri_intake"] = MagicMock()
sys.modules["access_nri_intake.aliases"] = MagicMock()


# Just trying out testing one of the functions
def test_round_slice_val():
    """Test the round_slice_val function"""
    # 1. Instantiate the UI class to access its methods
    ui = UserInterface()

    # 2. Assert against strings, as that is what your function returns
    # Test with a float value
    assert ui._round_slice_val(3.14159) == "3.14"

    # Test with an integer value
    assert ui._round_slice_val(42) == "42"

    # Test with a string that can be converted to a float
    assert ui._round_slice_val("2.71828") == "2.72"

    # Test with a string that cannot be converted to a float
    assert ui._round_slice_val("not a number") == "not a number"
