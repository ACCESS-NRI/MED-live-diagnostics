# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" This is a placeholder for tests """
import sys
from pathlib import Path
src_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(src_dir))
import med_diagnostics
from med_diagnostics.data import _build_new_catalog


# Testing the _build_new_catalog function with a non-existent directory and a model type of "OM2"
#_build_new_catalog("blah not a directory", "ESM15")

session = med_diagnostics.session.CreateModelDiagnosticsSession(model_type='CM2', model_path='path/to/your/live/model/data/output', period=20)