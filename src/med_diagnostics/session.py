# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""Session class functions for med-diagnostics live diagnostics"""

import os

from distributed import Client

from med_diagnostics import controller, data, ui


class CreateModelDiagnosticsSession:
    """
    Primary class for starting a model diagnostics session
    """

    def __init__(self):
        """
        Initialisae a CreateModelDiagnosticsSession instance to start a model diagnostics session, with no arguments/
        """
        self.ui = ui.UserInterface()
        self.ui.start_session_button.on_click(self._session_start_button_click)
        self.ui.refresh_catalog_button.on_click(self._refresh_catalog)

        self.ui._start_session_ui()

    def _start_session(self, model_type, model_path):
        """
        Initialise a CreateModelDiagnosticsSession instance to start a model diagnostics session.

        Parameters
        ----------
        model_type : str
            Type of ACCESS model, case-insensitive (e.g. CM2, OM2).
        model_path : str
            Path to model output directory/files on Gadi.

        """

        # Set local variables
        self.model_type = str(model_type).lower()
        self.model_path = str(model_path)

        # Start dask client
        self.client = Client(threads_per_worker=1)

        print()
        print(
            "----------------------- Live diagnostics session started -----------------------"
        )
        print()
        print("Model type:", str(model_type))
        print("Model data path:", self.model_path)
        print()
        print("Started dask client:", self.client.dashboard_link)
        print()
        print(
            "--------------------------------------------------------------------------------"
        )
        print()

        # Start UserUI instance and display initial status text
        self.ui._initialise_widgets()

        # Get initial model data
        self._get_data()

    def end_session(self):
        """
        Close the dask client and clear the UI to end the current CreateModelDiagnosticsSession instance.
        """

        self.client.close()

        self.ui.user_widget_container.clear()
        self.ui.ref_widget_container.clear()
        self.ui.multiplot_widget_container.clear()
        self.ui.analysis_widget_container.clear()

        print(
            "------------------------ Live diagnostics session ended ------------------------"
        )

    def _get_data(self):
        """
        Check nominated model data path for new data. Private.
        """
        self._build_model_catalog()

        # Load access_nri catalog for model comparison filtered by model type
        self.access_nri_cat = data._load_access_nri_catalog(self.model_type)

        self.ui._enable_widgets_after_catalog_load(self.model_cat, self.access_nri_cat)
        # Generate UI
        self.ui._display_dataset_selection_ui()

    def _build_model_catalog(self):
        """
        Build and load the user model catalog. Private.
        """
        data._build_new_catalog(self.model_path, self.model_type)

        # Update status text
        controller.update_textbox_text(
            self.ui.status_textbox, "User model status >> Model data catalog built"
        )
        controller.update_textbox_text(
            self.ui.last_data_load_textbox,
            "Last model data catalog build >> " + controller.get_current_time(),
        )

        # Load new catalog
        self.model_cat = data._load_new_catalog()

    def _refresh_catalog(self, event):
        """
        Rebuild the user model catalog when the refresh button is clicked. Private.

        The ACCESS-NRI catalog is not reloaded.
        """
        self.ui._refresh_catalog()
        try:
            self._build_model_catalog()
            self.ui._update_widgets_after_catalog_refresh(self.model_cat)
        finally:
            self.ui.refresh_catalog_button.disabled = False

    def return_model_data_catalog(self):
        """
        Convenience function to return currently loaded model data catalog.

        Returns
        ----------
        Intake-ESM datastore object
            Intake catalog of user model data.
        """

        return self.model_cat

    def return_loaded_dataset(self):
        """
        Convenience function to return currently loaded dataset.

        Returns
        ----------
        xr.Dataset
        """

        return self.ui.dataset

    def _session_start_button_click(self, event):
        """
        Event wrapper for the session start button click.

        Errors are shown in the UI, as Panel does not show errors raised in callbacks.
        """
        # Disable straight away so a double click can't start two sessions
        self.ui.start_session_button.disabled = True
        controller.update_textbox_text(self.ui.session_warning_textbox, "")

        model_path = os.path.expanduser(self.ui.live_model_path.value.strip())
        warning = controller.validate_model_path(model_path)
        if warning:
            controller.update_textbox_text(self.ui.session_warning_textbox, warning)
            self.ui.start_session_button.disabled = False
            return

        controller.update_textbox_text(
            self.ui.session_status_textbox,
            "User model status >> Starting session and building model data catalog. This can take a few minutes...",
        )
        try:
            self._start_session(self.ui.model_type_dropdown.value, model_path)
        except Exception as e:  # noqa: BLE001
            if getattr(self, "client", None):
                self.client.close()
                self.client = None
            self.ui._reset_session_ui()
            controller.update_textbox_text(self.ui.session_status_textbox, "")
            controller.update_textbox_text(
                self.ui.session_warning_textbox,
                f"Warning >> Session failed to start: {e}",
            )
            self.ui.start_session_button.disabled = False
            return

        controller.update_textbox_text(
            self.ui.session_status_textbox, "User model status >> Session started"
        )
