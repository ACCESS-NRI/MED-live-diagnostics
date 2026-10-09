from unittest.mock import MagicMock

import pytest

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

    # Patch the modules directly where they are imported in session.py
    monkeypatch.setattr("med_diagnostics.session.Client", mock_client_class)
    monkeypatch.setattr("med_diagnostics.session.LocalCluster", MagicMock())
    monkeypatch.setattr("med_diagnostics.session.ui.UserInterface", mock_ui_class)
    monkeypatch.setattr("med_diagnostics.session.data", mock_data)
    monkeypatch.setattr("med_diagnostics.session.controller", mock_controller)

    return mock_client_instance, mock_ui_instance, mock_data, mock_controller


def test_init_and_get_data(mock_session_deps):
    """Tests session initialisation and the automatic _get_data execution."""
    _mock_client, mock_ui, mock_data, mock_controller = mock_session_deps

    # Initialise the session
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")
    # Verify __init__ assignments
    assert session.model_type == "cm2"
    assert session.model_path == "/mock/path"

    # Verify UI was initialised and status text was displayed
    mock_ui._initialise_widgets.assert_called_once()

    # Verify _get_data ran correctly
    mock_data._build_new_catalog.assert_called_once_with("/mock/path", "cm2")
    mock_data._load_new_catalog.assert_called_once()
    mock_data._load_access_nri_catalog.assert_called_once_with("cm2")

    assert mock_controller.update_textbox_text.call_count == 2
    mock_ui._enable_widgets_after_catalog_load.assert_called_once_with(
        "mock_model_cat", "mock_access_cat"
    )
    mock_ui._display_dataset_selection_ui.assert_called_once_with()


def test_end_session(mock_session_deps):
    """Tests the termination of the Dask client and clearing of the UI."""
    mock_client, mock_ui, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")

    mock_cluster = session.cluster

    session.end_session()

    mock_client.close.assert_called_once()
    mock_cluster.close.assert_called_once()
    assert session.client is None
    assert session.cluster is None
    mock_ui._reset_session_ui.assert_called_once()
    assert mock_ui.end_session_button.disabled is True
    assert mock_ui.start_session_button.disabled is False


def test_end_session_twice(mock_session_deps):
    """Tests ending an already ended session doesn't crash."""
    mock_client, _, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")

    mock_cluster = session.cluster

    session.end_session()
    session.end_session()

    mock_client.close.assert_called_once()
    mock_cluster.close.assert_called_once()


def test_session_end_button_click(mock_session_deps, monkeypatch):
    """Tests the end session button calls end_session."""
    _, mock_ui, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession()
    mock_end_session = MagicMock()
    monkeypatch.setattr(session, "end_session", mock_end_session)

    mock_ui.end_session_button.on_click.assert_called_once_with(
        session._session_end_button_click
    )
    session._session_end_button_click(None)

    mock_end_session.assert_called_once_with()


def test_return_model_data_catalog(mock_session_deps):
    """Tests the getter function for the model catalog."""
    _, _, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")

    catalog = session.return_model_data_catalog()

    assert catalog == "mock_model_cat"


def test_refresh_catalog(mock_session_deps, monkeypatch):
    """Tests the refresh catalog functionality."""
    _, mock_ui, _, _ = mock_session_deps
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")

    mock_refresh_catalog = MagicMock()
    monkeypatch.setattr(mock_ui, "_refresh_catalog", mock_refresh_catalog)

    mock_build_model_catalog = MagicMock()
    monkeypatch.setattr(session, "_build_model_catalog", mock_build_model_catalog)

    mock_update_widgets_after_catalog_refresh = MagicMock()
    monkeypatch.setattr(
        mock_ui,
        "_update_widgets_after_catalog_refresh",
        mock_update_widgets_after_catalog_refresh,
    )

    # Call the refresh catalog method
    session._refresh_catalog(None)

    mock_refresh_catalog.assert_called_once()
    # Verify that the model catalog was rebuilt and loaded
    mock_build_model_catalog.assert_called_once()
    mock_update_widgets_after_catalog_refresh.assert_called_once()

    assert mock_ui.refresh_catalog_button.disabled is False


def test_return_loaded_dataset(mock_session_deps):
    """Tests the getter function for the loaded dataset."""
    _, mock_ui, _, _ = mock_session_deps
    mock_ui.dataset = dataset = {"some": "data"}  # Mock dataset
    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")
    dataset_return = session.return_loaded_dataset()

    assert dataset_return == dataset


def _click_start(mock_ui, model_path, model_type="CM2"):
    """Set the start session inputs and click the button."""
    mock_ui.live_model_path.value = model_path
    mock_ui.model_type_dropdown.value = model_type
    session = CreateModelDiagnosticsSession()
    session._session_start_button_click(None)
    return session


def test_session_start_click_starts_session(mock_session_deps):
    """Tests a valid path is tidied and starts the session."""
    _, mock_ui, mock_data, mock_controller = mock_session_deps
    mock_controller.validate_model_path.return_value = None

    _click_start(mock_ui, "  /mock/path\n")

    mock_controller.validate_model_path.assert_called_once_with("/mock/path")
    mock_data._build_new_catalog.assert_called_once_with("/mock/path", "cm2")
    mock_ui._reset_session_ui.assert_not_called()
    assert mock_ui.start_session_button.disabled is True
    assert mock_ui.end_session_button.disabled is False


def test_session_start_click_invalid_path(mock_session_deps):
    """Tests an invalid path shows a warning without starting dask."""
    _, mock_ui, mock_data, mock_controller = mock_session_deps
    mock_controller.validate_model_path.return_value = "Warning >> Path not found"

    session = _click_start(mock_ui, "/bad/path")

    assert not hasattr(session, "client")
    mock_data._build_new_catalog.assert_not_called()
    mock_controller.update_textbox_text.assert_called_with(
        mock_ui.session_warning_textbox, "Warning >> Path not found"
    )
    assert mock_ui.start_session_button.disabled is False


def test_session_start_click_failure_cleans_up(mock_session_deps):
    """Tests a failed catalog build closes dask and resets the UI for a retry."""
    mock_client, mock_ui, mock_data, mock_controller = mock_session_deps
    mock_controller.validate_model_path.return_value = None
    mock_data._build_new_catalog.side_effect = OSError("no assets found")
    # Disabled until a session starts, so a failed start must leave it disabled
    mock_ui.end_session_button.disabled = True

    session = _click_start(mock_ui, "/mock/path")

    mock_client.close.assert_called_once()
    assert session.client is None
    assert session.cluster is None
    mock_ui._reset_session_ui.assert_called_once()
    assert mock_ui.end_session_button.disabled is True
    mock_controller.update_textbox_text.assert_called_with(
        mock_ui.session_warning_textbox,
        "Warning >> Session failed to start: no assets found",
    )
    assert mock_ui.start_session_button.disabled is False


def test_start_session_creates_dask_cluster(mock_session_deps, monkeypatch):
    """Tests the session owns a single-threaded cluster so its workers can be shut down."""
    mock_cluster_class = MagicMock()
    mock_client_class = MagicMock()
    monkeypatch.setattr("med_diagnostics.session.LocalCluster", mock_cluster_class)
    monkeypatch.setattr("med_diagnostics.session.Client", mock_client_class)

    session = CreateModelDiagnosticsSession()
    session._start_session(model_type="CM2", model_path="/mock/path")

    mock_cluster_class.assert_called_once_with(threads_per_worker=1)
    mock_client_class.assert_called_once_with(mock_cluster_class.return_value)
    assert session.cluster is mock_cluster_class.return_value
    assert session.client is mock_client_class.return_value


def test_init_wires_session_buttons(mock_session_deps):
    """Tests the no-arg constructor wires the buttons and shows the start UI."""
    _, mock_ui, _, _ = mock_session_deps

    session = CreateModelDiagnosticsSession()

    mock_ui.start_session_button.on_click.assert_called_once_with(
        session._session_start_button_click
    )
    mock_ui.end_session_button.on_click.assert_called_once_with(
        session._session_end_button_click
    )
    mock_ui.refresh_catalog_button.on_click.assert_called_once_with(
        session._refresh_catalog
    )
    mock_ui._start_session_ui.assert_called_once_with()
