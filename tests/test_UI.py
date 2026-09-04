# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""This is a placeholder for tests"""

import sys
import med_diagnostics
from med_diagnostics.ui import UserInterface

# from med_diagnostics.data import _build_new_catalog
import pytest


# Just trying out testing one of the functions
def test_round_slice_val():
    ui = UserInterface()
    assert ui._round_slice_val(3.14159) == "3.14"
    assert ui._round_slice_val(42) == "42.0"
    assert ui._round_slice_val("2.71828") == "2.72"
    assert ui._round_slice_val("not a number") == "not a number"
