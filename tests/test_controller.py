from access_nri_intake import data


from med_diagnostics.ui import UserInterface
import med_diagnostics.controller as controller
import med_diagnostics.data as med_data
import pytest
import xarray as xr
import numpy as np
import panel as pn
import matplotlib.pyplot as plt
import cftime
from unittest.mock import MagicMock, patch
import datetime

@pytest.fixture(scope="function")
def ui():
    """Return a session-scoped UserInterface instance for testing"""

    ui = UserInterface()
    # Initialise the user interface widget container to prepare it for test execution
    ui.widget_container = pn.Column()
    return ui


@pytest.mark.parametrize(
    "input_text",
    [ "A word", 1, 1.0, True
    ],
)
def test_update_textbox_text(input_text):
    """Test updating any textbox with an entered value"""

    widget = pn.widgets.StaticText(value="something")
    controller.update_textbox_text(widget, input_text)

    # Verify that the status textbox value matches the updated text
    assert widget.value == str(input_text)


@patch("med_diagnostics.controller.datetime")
def test_get_current_time(mock_datetime):
    # Create a static datetime object
    frozen_time = datetime.datetime(2026, 9, 9, 14, 47, 14)

    # tell the mock to return our frozen time whenever .now() is called
    mock_datetime.datetime.now.return_value = frozen_time

    # Call the function (it will use the mocked .now())
    result = controller.get_current_time()

    # Assert against the exact string we expect
    assert result == "2026-09-09 14:47:14"
