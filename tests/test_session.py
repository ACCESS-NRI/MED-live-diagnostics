import pytest
from unittest.mock import MagicMock

# Adjust this import path if your file is named something else (e.g., main.py)
from med_diagnostics.session import CreateModelDiagnosticsSession


@pytest.fixture
def mock_session_deps(monkeypatch):
    """Fixture to mock out Dask, UI, Data, and Controller dependencies."""

    # Mock Dask Client
    mock_client_class = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.dashboard_link = "http://mock-dask:8787"
    mock_client_class.return_value = mock_client_instance

    # Mock UI
    mock_ui_class = MagicMock()
    mock_ui_instance = MagicMock()
    mock_ui_instance.status_textbox = "mock_status_box"
    mock_ui_instance.last_data_load_textbox = "mock_load_box"
    mock_ui_class.return_value = mock_ui_instance

    # Mock Data module
    mock_data = MagicMock()
    mock_data._load_new_catalog.return_value = "mock_model_cat"
    mock_data._load_access_nri_catalog.return_value = "mock_access_cat"

    # Mock Controller module
    mock_controller = MagicMock()
    mock_controller.get_current_time.return_value = "12:00:00"

    # Patch the modules directly where they are imported in your session file
    # (Update "med_diagnostics.session" if your file is named differently)
    monkeypatch.setattr("med_diagnostics.session.Client", mock_client_class)
    monkeypatch.setattr("med_diagnostics.session.ui.UserInterface", mock_ui_class)
    monkeypatch.setattr("med_diagnostics.session.data", mock_data)
    monkeypatch.setattr("med_diagnostics.session.controller", mock_controller)

    return mock_client_instance, mock_ui_instance, mock_data, mock_controller


@pytest.mark.parametrize(
    "timezone, expected_tz",
    [
        (None, "Australia/Canberra"),
        ("Australia/Hobart", "Australia/Hobart"),
    ],
)
def test_init_and_get_data(mock_session_deps, timezone, expected_tz):
    """Tests session initialisation and the automatic _get_data execution."""
    mock_client, mock_ui, mock_data, mock_controller = mock_session_deps

    # Initialise the session
    session = CreateModelDiagnosticsSession(model_type="CM2", model_path="/mock/path", timezone=timezone)

    # Verify __init__ assignments
    assert session.model_type == "cm2"
    assert session.model_path == "/mock/path"
    assert session.timezone == expected_tz
    assert session.data_update is False

    # Verify UI was initialised and status text was displayed
    mock_ui._display_status_text.assert_called_once()

    # Verify _get_data ran correctly
    mock_data._build_new_catalog.assert_called_once_with("/mock/path", "cm2")
    mock_data._load_new_catalog.assert_called_once()
    mock_data._load_access_nri_catalog.assert_called_once_with("cm2")

    assert mock_controller.update_textbox_text.call_count == 2
    mock_ui._display_dataset_selection_ui.assert_called_once_with("mock_model_cat", "mock_access_cat")


def test_end_session(mock_session_deps):
    """Tests the termination of the Dask client and clearing of the UI."""
    mock_client, mock_ui, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession("CM2", "/mock/path")

    session.end_session()

    mock_client.close.assert_called_once()
    mock_ui.widget_container.clear.assert_called_once()


def test_return_model_data_catalog(mock_session_deps):
    """Tests the getter function for the model catalog."""
    _, _, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession("CM2", "/mock/path")

    catalog = session.return_model_data_catalog()

    assert catalog == "mock_model_cat"
