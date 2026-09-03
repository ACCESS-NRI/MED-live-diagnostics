# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""UI class and functions"""

import panel as pn
import matplotlib.pyplot as plt
import datetime

from med_diagnostics import data
from IPython.display import display, HTML
import hvplot.xarray  # type: ignore #For creating interactive plots
import holoviews as hv  # type: ignore
import xarray as xr
import io
import base64


class UserInterface:
    """
    Primary class for user interface (UI) components and deployment
    """

    def __init__(self):
        """
        Initialise a UserInterface instance.
        """

        # Import panel extensions
        pn.extension()

        # Set up styles used for text boxes and buttons
        self.STYLES = {
            "status_text": {
                "styles": {
                    "background": "lightblue",
                    "font-size": "18px",
                    "color": "black",
                    "padding": "5px",
                },
                "margin": (10, 0, 10, 0),
            },
            "last_data_load_text": {
                "styles": {
                    "background": "orange",
                    "font-size": "18px",
                    "color": "black",
                    "padding": "5px",
                },
                "margin": (10, 0, 10, 0),
            },
            "warning_text": {
                "styles": {
                    "background": "darkred",
                    "font-size": "18px",
                    "color": "white",
                    "padding": "5px",
                },
                "margin": (10, 0, 10, 0),
            },
            "primary_button": {
                "styles": {},
                "margin": (23, 0, 0, 0),
                "button_type": "primary",
            },
            "danger_button": {
                "styles": {},
                "margin": (23, 0, 0, 0),
                "button_type": "danger",
            },
            "green_button": {
                "styles": {},
                "margin": (23, 0, 0, 0),
                "button_type": "success",
            },
            "remove_button": {
                "name": "Remove the above plot",
                "button_type": "danger",
                "margin": (23, 0, 0, 10),
            },
            "variable_toggle": {
                "label": "Display Variable Long Names",
                "name": "",
                "color": "primary",
                "value": False,
                "align": "end",
            },
        }

        # Build initial panel text widgets
        self.last_data_load_textbox = pn.widgets.StaticText(**self.STYLES.get("last_data_load_text"))
        self.status_textbox = pn.widgets.StaticText(**self.STYLES.get("status_text"))
        self.warning_textbox = pn.widgets.StaticText(**self.STYLES.get("warning_text"))

        # Build initial user plot buttons and dropdowns
        self.keys_dropdown = pn.widgets.Select()
        self.keys_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.plot_variable_dropdown = pn.widgets.Select()
        self.variable_toggle = pn.widgets.Toggle(**self.STYLES.get("variable_toggle"))
        self.plot_button = pn.widgets.Button(**self.STYLES.get("green_button"))
        self.plot_pane = pn.pane.Matplotlib(tight=True)
        self.plot_type_dropdown = pn.widgets.Select()
        self.x_axis_dropdown, self.y_axis_dropdown, self.animation_axis_dropdown = pn.widgets.Select(), pn.widgets.Select(), pn.widgets.Select()
        self.select_variable_button = pn.widgets.Button(**self.STYLES.get("green_button"))

        # Build reference panel status text
        self.ref_status_textbox = pn.widgets.StaticText(**self.STYLES.get("status_text"))
        self.ref_warning_textbox = pn.widgets.StaticText(**self.STYLES.get("warning_text"))

        # Build reference panel buttons
        self.ref_keys_dropdown = pn.widgets.Select()
        self.ref_keys_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.ref_data_keys_dropdown = pn.widgets.Select()
        self.ref_data_keys_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.ref_plot_variable_dropdown = pn.widgets.Select()
        self.ref_variable_toggle = pn.widgets.Toggle(**self.STYLES.get("variable_toggle"))
        self.clear_ref_model_data_button = pn.widgets.Button(**self.STYLES.get("danger_button"))
        self.ref_model_info_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.ref_model_metadata = pn.widgets.StaticText(styles={"color": "white"})
        self.ref_plot_button = pn.widgets.Button(**self.STYLES.get("green_button"))
        self.ref_plot_pane = pn.pane.Matplotlib(tight=True)
        self.ref_plot_type_dropdown = pn.widgets.Select()
        self.ref_x_axis_dropdown, self.ref_y_axis_dropdown, self.ref_animation_axis_dropdown = (
            pn.widgets.Select(),
            pn.widgets.Select(),
            pn.widgets.Select(),
        )
        self.ref_y_axis_dropdown = pn.widgets.Select()
        self.ref_animation_axis_dropdown = pn.widgets.Select()
        self.ref_select_variable_button = pn.widgets.Button(**self.STYLES.get("green_button"))

        # Build plot overlay status text
        self.multiplot_status_textbox = pn.widgets.StaticText(**self.STYLES.get("status_text"))
        self.multiplot_warning_textbox = pn.widgets.StaticText(**self.STYLES.get("warning_text"))

        # Build plot overlay buttons
        self.multiplot_ref_keys_dropdown = pn.widgets.Select()
        self.multiplot_ref_keys_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.multiplot_plot_button = pn.widgets.Button(**self.STYLES.get("green_button"))
        self.multiplot_plot_pane = pn.pane.Matplotlib(tight=True)
        self.clear_multiplot_data_button = pn.widgets.Button(**self.STYLES.get("danger_button"))

        self.multiplot_keys_dropdown = pn.widgets.Select()
        self.multiplot_keys_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.multiplot_plot_variable_dropdown = pn.widgets.Select()
        self.multiplot_x_axis_dropdown, self.multiplot_y_axis_dropdown = pn.widgets.Select(), pn.widgets.Select()
        self.multiplot_select_variable_button = pn.widgets.Button(**self.STYLES.get("green_button"))
        self.multiplot_keys_update_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.prompt_bounds_dropdown = pn.widgets.Select()
        self.prompt_bounds_button = pn.widgets.Button(**self.STYLES.get("primary_button"))
        self.multiplot_plot_type_dropdown = pn.widgets.Select()
        self.multiplot_analysis_choice_dropdown = pn.widgets.Select()
        self.multiplot_variable_toggle = pn.widgets.Toggle(**self.STYLES.get("variable_toggle"))

        self.figure_exists, self.ref_figure_exists = False, False

        # Initialise button listener functions
        @pn.depends(self.keys_dropdown.param.value)
        def _keys_button_click(event):

            self._keys_dropdown_click()

        @pn.depends(self.ref_keys_dropdown.param.value)
        def _ref_keys_button_click(event):

            self._ref_keys_dropdown_click()

        @pn.depends(self.ref_data_keys_dropdown.param.value)
        def _ref_data_keys_button_click(event):

            self._ref_dataset_dropdown_click()

        @pn.depends(self.ref_keys_dropdown.param.value)
        def _ref_model_info_button_click(event):

            self._ref_model_info_click()

        def _ref_clear_data_button_click(event):

            self._ref_clear_data_click()

        def _plot_button_click(event):

            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = self._check_plot_validity()
            if plot_valid:
                self._plot_data_button_click()
            elif requires_slice:
                self._check_slice()
            elif invalid_heatmap_data:
                self._update_warning_text("Warning >> The dataset only has one plottable dimension. Defaulting to line plot.")
                self.plot_type_dropdown.value = "Line"
                self._plot_data_button_click()
            elif same_axes_chosen:
                self._update_warning_text("Warning >> Please ensure different values are selected for each axis.")

                # Remove preexisting plot choices UI
                if hasattr(self, "plot_choices_row") and self.plot_choices_row in self.widget_container:
                    self.widget_container.remove(self.plot_choices_row)
                if hasattr(self, "slice_ui_row") and self.slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.slice_ui_row)
                    # Delete the attributes so it resets for the next plot
                    del self.slice_ui_row
                    del self.slice_widgets
                    self.chosen_slices = {}
                self._display_plot_choices_ui()

        def _ref_plot_button_click(event):

            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen = self._ref_check_plot_validity()
            if plot_valid:
                self._ref_plot_data_button_click()
            elif requires_slice:
                self._ref_check_slice()
            elif invalid_heatmap_data:
                self._update_ref_warning_text("Warning >> The dataset only has one plottable dimension. Defaulting to line plot.")
                self.ref_plot_type_dropdown.value = "Line"
                self._ref_plot_data_button_click()
            elif same_axes_chosen:
                self._update_ref_warning_text("Warning >> Please ensure different values are selected for each axis.")
                if hasattr(self, "ref_plot_choices_row") and self.ref_plot_choices_row in self.widget_container:
                    self.widget_container.remove(self.ref_plot_choices_row)
                if hasattr(self, "ref_slice_ui_row") and self.ref_slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.ref_slice_ui_row)
                    # Delete the attributes so it resets for the next plot
                    del self.ref_slice_ui_row
                    del self.ref_slice_widgets
                    self.chosen_slices = {}
                self._ref_display_plot_choices_ui()

        def _select_variable_button_click(event):

            self._display_plot_choices_ui()

        def _ref_select_variable_button_click(event):

            self._ref_display_plot_choices_ui()

        def _multiplot_ref_keys_button_click(event):

            self._multiplot_ref_keys_dropdown_click()

        def _multiplot_plot_button_click(event):

            plot_valid, requires_slice, prompt_bounds = self._check_multiplot_plot_validity()
            if plot_valid:
                self._multiplot_plot_data_button_click()
            elif requires_slice:
                self._multiplot_check_slice()
            elif prompt_bounds:
                self._prompt_bounds_ui()

        def _clear_multiplot_data_button_click(event):

            self._clear_multiplot_data()

        def _multiplot_keys_update_button_click(event):

            self._update_multiplot_dataset()

        def _multiplot_select_variable_button_click(event):

            self._display_multiplot_plot_choices_ui()

        def _prompt_bounds_button_click(event):

            self._multiplot_plot_data_button_click()

        def _variable_toggle_click(event):

            self._variable_toggle_change()

        def _ref_variable_toggle_click(event):

            self._ref_variable_toggle_change()

        def _multiplot_variable_toggle_click(event):

            self._multiplot_variable_toggle_change()

        self.plot_button.on_click(_plot_button_click)
        self.ref_plot_button.on_click(_ref_plot_button_click)
        self.keys_button.on_click(_keys_button_click)
        self.ref_keys_button.on_click(_ref_keys_button_click)
        self.ref_data_keys_button.on_click(_ref_data_keys_button_click)
        self.clear_ref_model_data_button.on_click(_ref_clear_data_button_click)
        self.ref_model_info_button.on_click(_ref_model_info_button_click)
        self.select_variable_button.on_click(_select_variable_button_click)
        self.ref_select_variable_button.on_click(_ref_select_variable_button_click)
        self.multiplot_ref_keys_button.on_click(_multiplot_ref_keys_button_click)
        self.multiplot_plot_button.on_click(_multiplot_plot_button_click)
        self.clear_multiplot_data_button.on_click(_clear_multiplot_data_button_click)
        self.multiplot_keys_update_button.on_click(_multiplot_keys_update_button_click)
        self.multiplot_select_variable_button.on_click(_multiplot_select_variable_button_click)
        self.prompt_bounds_button.on_click(_prompt_bounds_button_click)
        self.variable_toggle.param.watch(_variable_toggle_click, "value")
        self.ref_variable_toggle.param.watch(_ref_variable_toggle_click, "value")
        self.multiplot_variable_toggle.param.watch(_multiplot_variable_toggle_click, "value")

    def _display_status_text(self):
        """
        Create widget_container then add status_textbox and last_data_load_textbox widgets. Private.
        """

        # Create panel column
        self.widget_container = pn.Column()

        # Append widget_container with textbox widgets
        self.widget_container.append(self.last_data_load_textbox)
        self.widget_container.append(self.status_textbox)
        self.widget_container.append(self.warning_textbox)

        # pre build but hide the dataset selection UI elements
        self.div_1 = pn.layout.Divider(styles={"color": "white"}, visible=False)
        self.keys_selection_row = pn.Row(self.keys_dropdown, self.keys_button, visible=False)
        self.div_2 = pn.layout.Divider(styles={"color": "white"}, visible=False)

        self.widget_container.append(self.div_1)
        self.widget_container.append(self.keys_selection_row)
        self.widget_container.append(self.div_2)

        self.status_textbox.value = "User model status >> Waiting for initial model data catalog to be built. This can take a few minutes."
        # Display widget_container in notebook
        display(self.widget_container)
        print()

    def _update_status_text(self, text):
        """
        Update text displayed in status_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in status_textbox
        """

        # Update status_textbox with text
        self.status_textbox.value = str(text)

    def _update_ref_status_text(self, text):
        """
        Update text displayed in ref_status_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in ref_status_textbox
        """

        # Update ref_status_textbox with text
        self.ref_status_textbox.value = str(text)

    def _update_multiplot_status_text(self, text):
        """
        Update text displayed in multiplot_status_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in multiplot_status_textbox
        """

        # Update ref_status_textbox with text
        self.multiplot_status_textbox.value = str(text)

    def _update_warning_text(self, text):
        """
        Update text displayed in status_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in status_textbox
        """

        # Update status_textbox with text
        self.warning_textbox.value = str(text)

    def _update_ref_warning_text(self, text):
        """
        Update text displayed in status_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in status_textbox
        """

        # Update status_textbox with text
        self.ref_warning_textbox.value = str(text)

    def _update_multiplot_warning_text(self, text):
        """
        Update text displayed in _multiplot_warning_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in _multiplot_warning_textbox
        """

        # Update ref_status_textbox with text
        self.multiplot_warning_textbox.value = str(text)

    def _update_last_data_load_text(self, text):
        """
        Update text displayed in last_data_load_textbox widget. Private.

        Parameters
        ----------
        text : str
            Text to be displayed in last_data_load_textbox
        """

        # Update last_data_load_textbox with text
        self.last_data_load_textbox.value = str(text)

    def _get_current_time(self):
        """
        Get current time. Private.

        Returns
        ----------
        str
            Current time in "%Y-%m-%d %H:%M:%S" format.
        """

        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _variable_toggle_change(self):
        """Toggles the user variable dropdown options between short names and long name."""

        if self.variable_toggle.value:
            self.long_names = {}
            for var in self.dataset.keys():
                self.long_names[(self.dataset[var].attrs.get("long_name", var))] = var
            self.plot_variable_dropdown.options = list(self.long_names.keys())
            self.variable_toggle.label = "Display Variable Short Names"
            self.multiplot_variable_toggle.label = "Display Variable Short Names"
            self.multiplot_variable_toggle.value = True
        else:
            self.plot_variable_dropdown.options = list(self.dataset.keys())
            self.variable_toggle.label = "Display Variable Long Names"
            self.multiplot_variable_toggle.label = "Display Variable Long Names"
            self.multiplot_variable_toggle.value = False

    def _get_selected_variable(self):
        """Returns the internal dataset variable key regardless of display toggle state."""

        if self.variable_toggle.value:
            return self.long_names[self.plot_variable_dropdown.value]
        return self.plot_variable_dropdown.value

    def _ref_variable_toggle_change(self):
        """Toggles the reference variable dropdown options between short names and long name."""

        if self.ref_variable_toggle.value:
            self.ref_long_names = {}
            for var in self.ref_dataset.keys():
                self.ref_long_names[(self.ref_dataset[var].attrs.get("long_name", var))] = var
            self.ref_plot_variable_dropdown.options = list(self.ref_long_names.keys())
            self.ref_variable_toggle.label = "Display Variable Short Names"
        else:
            self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
            self.ref_variable_toggle.label = "Display Variable Long Names"

    def _ref_get_selected_variable(self):
        """Returns the reference dataset variable key regardless of display toggle state."""

        if self.ref_variable_toggle.value:
            return self.ref_long_names[self.ref_plot_variable_dropdown.value]
        return self.ref_plot_variable_dropdown.value

    def _multiplot_variable_toggle_change(self):
        """Toggles the multiplot variable dropdown options between short names and long name."""

        self.variable_toggle.value = self.multiplot_variable_toggle.value
        if self.multiplot_variable_toggle.value:
            self.multiplot_long_names = {}
            for var in self.dataset.keys():
                self.multiplot_long_names[(self.dataset[var].attrs.get("long_name", var))] = var
            self.multiplot_plot_variable_dropdown.options = list(self.multiplot_long_names.keys())
            self.multiplot_variable_toggle.label = "Display Variable Short Names"
            self.variable_toggle.label = "Display Variable Short Names"
            self.variable_toggle.value = True
        else:
            self.multiplot_plot_variable_dropdown.options = list(self.dataset.keys())
            self.multiplot_variable_toggle.label = "Display Variable Long Names"
            self.variable_toggle.label = "Display Variable Long Names"
            self.variable_toggle.value = False

    def _multiplot_get_selected_variable(self):
        """Returns the multiplot dataset variable key regardless of display toggle state."""

        if self.multiplot_variable_toggle.value:
            return self.multiplot_long_names[self.multiplot_plot_variable_dropdown.value]
        return self.multiplot_plot_variable_dropdown.value

    def _display_dataset_selection_ui(self, model_cat, access_nri_cat):
        """
        Label, populate and append dataset selection-related widgets to widget_container. Private.

        Parameters
        ----------
        model_cat : Intake-ESM datastore object
            Intake catalog of user model data.
        access_nri_cat : Intake-ESM datastore object
            Intake catalog of ACCESS model data.
        """

        # Assign argument to class-accessible variables
        self.model_cat = model_cat
        self.access_nri_cat = access_nri_cat

        # Populate user model widgets
        self.keys_dropdown.name = "1. Please select a dataset to monitor:"
        self.keys_dropdown.options = sorted(list(self.model_cat.keys()))
        self.keys_button.name = "Load dataset"
        self.keys_button.button_type = "primary"

        # Unhide the widgets via property updates rather than structural appends
        self.div_1.visible = True
        self.keys_selection_row.visible = True
        self.div_2.visible = True

    def _display_reference_model_selection_ui(self):
        """
        Label, populate and append ACCESS reference model selection-related widgets to widget_container. Private.
        """

        self._update_ref_status_text("Reference Model Status >> Select a model to load and plot data")
        # Add refrence data status text box
        self.widget_container.append(self.ref_status_textbox)
        self.widget_container.append(self.ref_warning_textbox)

        # Populate reference/comparison model widgets
        self.ref_keys_dropdown.name = "2. Select reference model (optional):"
        self.ref_keys_dropdown.options = sorted(list(self.access_nri_cat.keys()))
        self.ref_keys_button.name = "Load reference model"
        self.ref_keys_button.button_type = "success"

        self.clear_ref_model_data_button.name = "Clear reference model"
        self.clear_ref_model_data_button.button_type = "danger"

        self.ref_model_info_button.name = "Reference model information"
        self.ref_model_info_button.button_type = "primary"

        # Add reference/comparison widgets to ref_keys_selection_row
        self.ref_keys_selection_row = pn.Row()
        self.ref_keys_selection_row.append(self.ref_keys_dropdown)
        self.ref_keys_selection_row.append(self.ref_model_info_button)
        self.ref_keys_selection_row.append(self.ref_keys_button)
        self.ref_keys_selection_row.append(self.clear_ref_model_data_button)

        # Add ref_keys_selection_row to widget_container
        self.widget_container.append(self.ref_keys_selection_row)
        self.widget_container.append(self.ref_model_metadata)

        # Add horizontal line divider to widget_container
        self.widget_container.append(pn.layout.Divider(styles={"color": "white"}))

    def _display_reference_dataset_selection_ui(self):
        """
        Label, populate and append ACCESS reference dataset selection-related widgets to widget_container. Private.

        """
        # Populate reference/comparison dataset widgets
        self.ref_data_keys_dropdown.name = "2.1. Select reference dataset (optional):"
        self.ref_data_keys_dropdown.options = sorted(list(self.ref_model_cat.keys()))
        self.ref_data_keys_button.name = "Load reference dataset"
        self.ref_data_keys_button.button_type = "success"

        # Add reference/comparison widgets to ref_data_keys_selection_row
        self.ref_data_keys_selection_row = pn.Row()
        self.ref_data_keys_selection_row.append(self.ref_data_keys_dropdown)
        self.ref_data_keys_selection_row.append(self.ref_data_keys_button)

        # Insert the UI row under the reference model selection
        if hasattr(self, "ref_model_metadata") and self.ref_model_metadata in self.widget_container:
            insert_index = self.widget_container.index(self.ref_model_metadata) + 1
            self.widget_container.insert(insert_index, self.ref_data_keys_selection_row)
        elif hasattr(self, "ref_keys_selection_row") and self.ref_keys_selection_row in self.widget_container:
            insert_index = self.widget_container.index(self.ref_keys_selection_row) + 1
            self.widget_container.insert(insert_index, self.ref_data_keys_selection_row)
        else:
            self.widget_container.append(self.ref_data_keys_selection_row)

    def _display_multiplot_user_data_selection_ui(self):
        """
        Displays the selection user interface for producing plots that overlay user and reference models. Private
        """

        # Add overlay data status text box
        self.widget_container.append(self.multiplot_status_textbox)
        self.widget_container.append(self.multiplot_warning_textbox)
        self._update_multiplot_status_text("Overlay Plot >> Choose reference variables to compare with the current plot.")

        # Populate reference/comparison model widgets
        self.multiplot_ref_keys_dropdown.name = "Select one or more reference models to overlay (optional):"
        self.multiplot_ref_keys_dropdown.options = sorted(list(self.access_nri_cat.keys()))
        self.multiplot_ref_keys_button.name = "Add reference model"
        self.clear_multiplot_data_button.name = "Clear loaded data"
        self.multiplot_select_variable_button.name = "Select variable and plot type"
        self.multiplot_keys_dropdown.name = "Select user dataset"
        self.multiplot_keys_dropdown.options = sorted(list(self.keys_dropdown.options))
        self.multiplot_keys_dropdown.value = self.keys_dropdown.value
        self.multiplot_keys_update_button.name = "Update loaded dataset"
        self.multiplot_plot_variable_dropdown.name = "Variable selection"
        self.multiplot_plot_variable_dropdown.options = sorted(list(self.plot_variable_dropdown.options))
        self.multiplot_plot_variable_dropdown.value = self._get_selected_variable()
        self.multiplot_plot_type_dropdown.name = "Select plot type"
        self.multiplot_plot_type_dropdown.options = ["Line", "Heatmap (grid)"]

        self.multiplot_user_dataset_keys_selection_row = pn.Row()
        self.multiplot_user_dataset_keys_selection_row.append(self.multiplot_keys_dropdown)
        self.multiplot_user_dataset_keys_selection_row.append(self.multiplot_keys_update_button)

        # Add reference/comparison widgets to ref_keys_selection_row
        self.multiplot_ref_keys_selection_row = pn.Row()
        self.multiplot_ref_keys_selection_row.append(self.multiplot_plot_variable_dropdown)
        self.multiplot_ref_keys_selection_row.append(self.multiplot_ref_keys_dropdown)
        self.multiplot_ref_keys_selection_row.append(self.multiplot_ref_keys_button)
        self.multiplot_ref_keys_selection_row.append(self.clear_multiplot_data_button)
        self.multiplot_ref_keys_selection_row.append(self.multiplot_variable_toggle)

        self.multiplot_type_selection_row = pn.Row()
        self.multiplot_type_selection_row.append(self.multiplot_plot_type_dropdown)
        self.multiplot_type_selection_row.append(self.multiplot_select_variable_button)

        # Add ref_keys_selection_row to widget_container
        self.widget_container.append(self.multiplot_user_dataset_keys_selection_row)
        self.widget_container.append(self.multiplot_ref_keys_selection_row)
        self.widget_container.append(self.multiplot_type_selection_row)

        # Add horizontal line divider to widget_container
        self.widget_container.append(pn.layout.Divider(styles={"color": "white"}))

    def _keys_dropdown_click(self):
        """
        Loads selected model dataset from keys_dropdown and creates new interactive plot. Private.
        """
        # Update text box
        self._update_status_text("User model status >> Loading data.")

        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.keys_dropdown.value)
        self.loaded_dataset_key = self.keys_dropdown.value

        # Update text box
        self._update_status_text("User model status >> Data successfully loaded.")
        self.keys_button.name = "Load different dataset"

        # Check if plot already exists
        if not self.figure_exists:

            self.figure_exists = True
            # Create new plot
            self._display_dataset_plot_ui()

        elif self.figure_exists:

            # Update existing plot
            self._update_dataset_plot_ui()

    def _plot_data_button_click(self):
        """
        Triggers plotting of the user dataset after the plot data button is clicked
        """

        self.plot_button.name = "Add Plot"
        self.select_variable_button.name = "Add new plot with different variable/ plot type"
        self.x_axis_dropdown.name = "Select X-Axis"
        self.y_axis_dropdown.name = "Select Y-Axis"
        self._update_status_text("User model status >> Generating plot...")
        fig_animated = None
        fig = None

        # For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.chosen_slices = {}
        if hasattr(self, "slice_widgets"):
            for dim, widget in self.slice_widgets.items():
                self.chosen_slices[dim] = widget.value

        # Based on plot type change function that is used
        if self.plot_type_dropdown.value == "Heatmap":
            x_axis = self.x_axis_dropdown.value
            y_axis = self.y_axis_dropdown.value
            fig = self._plot_heatmap(self._get_selected_variable(), x_axis, y_axis)
        elif self.plot_type_dropdown.value == "Line":
            x_axis = self.x_axis_dropdown.value
            fig = self._plot_dataset(self._get_selected_variable(), x_axis)
        elif self.plot_type_dropdown.value == "Animation":
            fig_animated = self._plot_animation(self._get_selected_variable())

        if fig_animated:
            new_plot_pane = fig_animated
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(**self.STYLES.get("remove_button"))
        remove_btn.name = "Remove Plot"
        # Group the plot and the button together
        plot_group = pn.Column(new_plot_pane, remove_btn, margin=(0, 0, 25, 0))

        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)

        remove_btn.on_click(_remove_this_plot)

        # remove the plot choices row since the plot has been created
        if hasattr(self, "plot_choices_row") and self.plot_choices_row in self.widget_container:
            self.widget_container.remove(self.plot_choices_row)

        if hasattr(self, "slice_ui_row") and self.slice_ui_row in self.widget_container:
            self.widget_container.remove(self.slice_ui_row)
            # Delete the attributes it resets for the next plot
            del self.slice_ui_row
            del self.slice_widgets

        # Check if the reference UI already exists
        if self.ref_status_textbox in self.widget_container:
            # Find where the reference UI is
            insert_index = self.widget_container.index(self.ref_status_textbox)

            # Insert the new plot just above the reference UI
            self.widget_container.insert(insert_index, plot_group)
        else:
            # First time plotting: append plot to bottom, then generate reference UI below it
            self.widget_container.append(plot_group)
            self._display_reference_model_selection_ui()
            self._display_multiplot_user_data_selection_ui()

        self._update_status_text("User model status >> Plot created")

        self._update_warning_text("")

    def _ref_plot_data_button_click(self):
        """
        Triggers plotting of the reference dataset after the plot data button fis clicked
        """

        self.ref_plot_button.name = "Add Plot"
        self.ref_select_variable_button.name = "Add new plot with different variable/ plot type"
        self._update_ref_status_text("User model status >> Generating plot...")
        self.ref_x_axis_dropdown.name = "Select X-Axis"
        self.ref_y_axis_dropdown.name = "Select Y-Axis"

        # For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.ref_chosen_slices = {}
        if hasattr(self, "ref_slice_widgets"):
            for dim, widget in self.ref_slice_widgets.items():
                self.ref_chosen_slices[dim] = widget.value

        fig = None
        fig_animated = None

        # Based on plot type change function that is used
        if self.ref_plot_type_dropdown.value == "Heatmap":
            x_axis = self.ref_x_axis_dropdown.value
            y_axis = self.ref_y_axis_dropdown.value
            fig = self._plot_ref_heatmap(self._ref_get_selected_variable(), x_axis, y_axis)
        elif self.ref_plot_type_dropdown.value == "Line":
            x_axis = self.ref_x_axis_dropdown.value
            fig = self._plot_ref_dataset(self._ref_get_selected_variable(), x_axis)
        elif self.ref_plot_type_dropdown.value == "Animation":
            fig_animated = self._plot_ref_animation()

        if fig_animated:
            new_plot_pane = fig_animated
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(**self.STYLES.get("remove_button"))
        remove_btn.name = "Remove Plot"
        # Group the plot and the button together
        plot_group = pn.Column(new_plot_pane, remove_btn, margin=(0, 0, 25, 0))

        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)

        remove_btn.on_click(_remove_this_plot)

        # remove the plot choices row since the plot has been created
        if hasattr(self, "ref_plot_choices_row") and self.ref_plot_choices_row in self.widget_container:
            self.widget_container.remove(self.ref_plot_choices_row)

        if hasattr(self, "ref_slice_ui_row") and self.ref_slice_ui_row in self.widget_container:
            self.widget_container.remove(self.ref_slice_ui_row)
            # Delete the attributes it resets for the next plot
            del self.ref_slice_ui_row
            del self.ref_slice_widgets

        # Check if the reference UI already exists
        if self.multiplot_status_textbox in self.widget_container:
            # Find where the reference UI is
            insert_index = self.widget_container.index(self.multiplot_status_textbox)

            # Insert the new plot just above the reference UI
            self.widget_container.insert(insert_index, plot_group)
        else:
            # If the multiplot UI is not present, just append the new plots to the bottom of the widget
            self.widget_container.append(plot_group)

        self._update_ref_status_text("User model status >> Plot created")
        self._update_ref_warning_text("")

    def _multiplot_plot_data_button_click(self):
        """
        Triggers the plotting of the overlay data plot once the multiplot plot data button has been pressed. Private
        """

        self.multiplot_plot_button.name = "Select"
        self._update_multiplot_status_text("Plot Overlay Status >> Generating plot...")
        self.multiplot_x_axis_dropdown.name = "Select X-Axis"
        self.multiplot_y_axis_dropdown.name = "Select Y-Axis"
        fig1 = None

        # remove the plot choices row since the plot has been created
        if hasattr(self, "multiplot_plot_choices_row") and self.multiplot_plot_choices_row in self.widget_container:
            self.widget_container.remove(self.multiplot_plot_choices_row)

        if hasattr(self, "prompt_bounds_row") and self.prompt_bounds_row in self.widget_container:
            self.widget_container.remove(self.prompt_bounds_row)
            # Delete the attributes it resets for the next plot
            del self.prompt_bounds_row

        # For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.multiplot_chosen_slices = {}
        if hasattr(self, "multiplot_slice_widgets"):
            for dim, widget in self.multiplot_slice_widgets.items():
                self.multiplot_chosen_slices[dim] = widget.value
        # Based on plot type change function that is used
        if (
            self.multiplot_plot_type_dropdown.value == "Heatmap (grid)"
            and self.multiplot_analysis_choice_dropdown.value == "None (plot all loaded data)"
        ):
            x_axis = self.multiplot_x_axis_dropdown.value
            y_axis = self.multiplot_y_axis_dropdown.value
            fig = self._plot_multiplot_heatmap_dataset(self._multiplot_get_selected_variable(), x_axis, y_axis)
        elif (
            self.multiplot_plot_type_dropdown.value == "Heatmap (grid)"
            and self.multiplot_analysis_choice_dropdown.value == "Plot Difference (Ref. - User data)"
        ):
            x_axis = self.multiplot_x_axis_dropdown.value
            y_axis = self.multiplot_y_axis_dropdown.value
            fig = self._plot_multiplot_difference_heatmap(self._multiplot_get_selected_variable(), x_axis, y_axis)
        elif (
            self.multiplot_plot_type_dropdown.value == "Heatmap (grid)"
            and self.multiplot_analysis_choice_dropdown.value == "Plot All Data & Difference"
        ):
            x_axis = self.multiplot_x_axis_dropdown.value
            y_axis = self.multiplot_y_axis_dropdown.value
            fig1 = self._plot_multiplot_heatmap_dataset(self._multiplot_get_selected_variable(), x_axis, y_axis)
            fig2 = self._plot_multiplot_difference_heatmap(self._multiplot_get_selected_variable(), x_axis, y_axis)
        elif self.multiplot_plot_type_dropdown.value == "Line" and self.multiplot_analysis_choice_dropdown.value == "None (plot all loaded data)":
            x_axis = self.multiplot_x_axis_dropdown.value
            fig = self._plot_multiplot_dataset(self._multiplot_get_selected_variable(), x_axis)
        elif (
            self.multiplot_plot_type_dropdown.value == "Line"
            and self.multiplot_analysis_choice_dropdown.value == "Plot Difference (Ref. - User data)"
        ):
            x_axis = self.multiplot_x_axis_dropdown.value
            fig = self._plot_multiplot_difference_dataset(self._multiplot_get_selected_variable(), x_axis)
        elif self.multiplot_plot_type_dropdown.value == "Line" and self.multiplot_analysis_choice_dropdown.value == "Plot All Data & Difference":
            x_axis = self.multiplot_x_axis_dropdown.value
            fig1 = self._plot_multiplot_dataset(self._multiplot_get_selected_variable(), x_axis)
            fig2 = self._plot_multiplot_difference_dataset(self._multiplot_get_selected_variable(), x_axis)

        if fig1:
            pane1 = pn.pane.Matplotlib(fig1, tight=True)
            pane2 = pn.pane.Matplotlib(fig2, tight=True)
            new_plot_pane = pn.Column(pane1, pane2)
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(**self.STYLES.get("remove_button"))
        remove_btn.name = "Remove Plot"

        if hasattr(self, "multiplot_slice_ui_row") and self.multiplot_slice_ui_row in self.widget_container:
            self.widget_container.remove(self.multiplot_slice_ui_row)
            # Delete the attributes it resets for the next plot
            del self.multiplot_slice_ui_row
            del self.multiplot_slice_widgets

        # Group the plot and the button together
        plot_group = pn.Column(new_plot_pane, remove_btn, margin=(0, 0, 25, 0))

        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)

        remove_btn.on_click(_remove_this_plot)

        self.widget_container.append(plot_group)

        self._update_multiplot_status_text("User model status >> Plot created")
        self._update_ref_warning_text("")

    def _ref_keys_dropdown_click(self):
        """
        Loads selected reference model from ref_keys_dropdown and display reference model dataset selection. Private.
        """

        # Update text box
        self._update_ref_status_text("Reference model status >> Loading data.")

        # Extract selected model catalog
        self.ref_model_cat = self.access_nri_cat.search(name=self.ref_keys_dropdown.value).to_source()

        # Update text box
        self._update_ref_status_text("Reference model status >> Data catalog successfully loaded.")

        if hasattr(self, "ref_data_keys_selection_row") and self.ref_data_keys_selection_row in self.widget_container:
            # Just update the options in the existing dropdown to match the new model
            self.ref_data_keys_dropdown.options = sorted(list(self.ref_model_cat.keys()))
        else:
            # Build and display the UI for the first time
            self._display_reference_dataset_selection_ui()

    def _multiplot_ref_keys_dropdown_click(self):
        """
        Loads selected reference model, and if it contains the correct dataset, adds it to a dictionary to plot. Private.
        """

        if not hasattr(self, "multiplot_ref_dataset_dict"):
            self.multiplot_ref_dataset_dict = {}

        self._update_multiplot_warning_text("")
        selected_ref_model_cat = self.access_nri_cat.search(name=self.multiplot_ref_keys_dropdown.value).to_source()

        if (
            self.multiplot_keys_dropdown.value in list(selected_ref_model_cat.keys())
            and not self.multiplot_ref_keys_dropdown.value in self.multiplot_ref_dataset_dict
        ):
            model_value = self.multiplot_ref_keys_dropdown.value
            self._update_multiplot_status_text("Overlay Plot Status >> Loading reference dataset...")
            dataset = data._build_data_object(selected_ref_model_cat, self.multiplot_keys_dropdown.value)

            # Align calendars to prevent crashes
            if "time" in self.dataset.coords and "time" in dataset.coords:
                # Extract the target calendar from the user dataset
                user_index = self.dataset.indexes.get("time")
                target_cal = user_index.calendar if isinstance(user_index, xr.CFTimeIndex) else "standard"

                # Extract the calendar from the newly loaded reference dataset
                ref_index = dataset.indexes.get("time")
                ref_cal = ref_index.calendar if isinstance(ref_index, xr.CFTimeIndex) else "standard"

                # Convert the reference dataset calendar if there is a mismatch
                if target_cal != ref_cal:
                    dataset = dataset.convert_calendar(target_cal)

            self.multiplot_ref_dataset_dict.update({model_value: dataset})
            self._update_multiplot_status_text("Overlay Plot Status >> Loaded reference model, add another or plot the overlay")
        elif self.multiplot_ref_keys_dropdown.value in self.multiplot_ref_dataset_dict:
            self._update_multiplot_warning_text("Warning >> Model has already been added, skipping duplicate")
        else:
            self._update_multiplot_warning_text(
                "Overlay Plot Status >> There is no dataset matching the user dataset in this model, please select another"
            )

        if self.multiplot_keys_dropdown.value != self.loaded_dataset_key:
            self._update_multiplot_status_text("Overlay Plot Status >> User dataset selection changed, reloading user dataset...")
            # Load selected dataset
            self.dataset = data._build_data_object(self.model_cat, self.multiplot_keys_dropdown.value)
            self.loaded_dataset_key = self.multiplot_keys_dropdown.value
            self.multiplot_plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
            self._update_multiplot_status_text("Overlay Plot Status >> New user dataset loaded, clearing loaded user models")
            self._clear_multiplot_data()

    def _ref_dataset_dropdown_click(self):
        """
        Loads selected reference model dataset from ref_data_keys_dropdown and creates new interactive plot. Private.
        """
        self._update_ref_status_text("Reference model status >> Loading reference dataset...")
        # Load selected access_nri catalog dataset
        self.ref_dataset = data._build_data_object(self.ref_model_cat, self.ref_data_keys_dropdown.value)
        self._update_ref_status_text("Reference model status >> Reference dataset successfully loaded.")
        # Check if plot already exists
        if not self.ref_figure_exists:

            self.ref_figure_exists = True
            # Create new plot
            self._ref_display_dataset_plot_ui()

        elif self.ref_figure_exists:

            # Update existing plot
            self._update_ref_dataset_plot_ui()

    def _ref_clear_data_click(self):
        """
        Clears and 'unloads' selected reference model dataset from widget container. Private.
        """

        # Update text box
        self._update_ref_status_text("Reference model status >> Data removed.")

        ui_components_to_remove = [
            "ref_data_keys_selection_row",
            "ref_plot_ui_row",
            "ref_plot_choices_row",
            "ref_slice_ui_row",
        ]

        # Remove all generated reference UI rows from the layout
        for attr in ui_components_to_remove:
            if hasattr(self, attr):
                component = getattr(self, attr)
                if component in self.widget_container:
                    self.widget_container.remove(component)

        # Clear the metadata text
        self.ref_model_metadata.value = ""

        # Remove reference data attributes
        if hasattr(self, "ref_model_cat"):
            del self.ref_model_cat
        if hasattr(self, "ref_dataset"):
            del self.ref_dataset

        self.ref_figure_exists = False

    def _ref_model_info_click(self):
        """
        Create string from the selected model metadata, and update the reference status text with that string. Private.
        """
        # Update text box
        self._update_ref_status_text("Reference model status >> Retrieving model metadata.")

        self.ref_model_metadata.value = (
            '<div style="color: var(--jp-ui-font-color1);">'
            + "<b>Model information:</b><br>"
            + "<b>Model:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["model"])
            + "<br>"
            + "<b>Short description:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["description"])
            + "<br>"
            + "<b>Nominal resolution:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["nominal_resolution"])
            + "<br>"
            + "<b>Parent experiment:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["parent_experiment"])
            + "<br>"
            + "<b>Long description:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["long_description"])
            + "<br>"
            + "<b>Contact:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["contact"])
            + "<br>"
            + "<b>Email:   </b>"
            + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata["email"])
            + "<br>"
        )

        # Update text box
        self._update_ref_status_text("")

    def _display_dataset_plot_ui(self):
        """
        Create interactive panel plot for user model dataset and add to widget_container. Private.
        """

        self.plot_variable_dropdown.name = "Available variables"
        self.plot_variable_dropdown.options = sorted(list(self.dataset.keys()))

        self.plot_type_dropdown.name = "Select plot type"
        self.plot_type_dropdown.options = ["Line", "Heatmap", "Animation"]
        self.variable_toggle.value = False

        self.select_variable_button.name = "Select variable and plot type"

        self.plot_ui_row = pn.Row(
            self.plot_variable_dropdown,
            self.plot_type_dropdown,
            self.select_variable_button,
            self.variable_toggle,
        )
        self.widget_container.append(self.plot_ui_row)

    def _ref_display_dataset_plot_ui(self):
        """
        Create interactive panel plot for reference model dataset and add to widget_container. Private.
        """

        self.ref_plot_variable_dropdown.name = "Available variables"
        self.ref_plot_variable_dropdown.options = sorted(list(self.ref_dataset.keys()))

        self.ref_plot_type_dropdown.name = "Select plot type"
        self.ref_plot_type_dropdown.options = ["Line", "Heatmap", "Animation"]
        self.ref_select_variable_button.name = "Select variable and plot type"

        self.ref_plot_ui_row = pn.Row(
            self.ref_plot_variable_dropdown,
            self.ref_plot_type_dropdown,
            self.ref_select_variable_button,
            self.ref_variable_toggle,
        )
        if hasattr(self, "ref_data_keys_selection_row") and self.ref_data_keys_selection_row in self.widget_container:
            insert_index = self.widget_container.index(self.ref_data_keys_selection_row) + 1
            self.widget_container.insert(insert_index, self.ref_plot_ui_row)
        else:
            self.widget_container.append(self.ref_plot_ui_row)

    def _display_plot_choices_ui(self):
        """
        Create interactive panel plot for user to choose plot options and add to widget_container. Private.
        """
        # Remove preexisting plot choices UI
        if hasattr(self, "plot_choices_row") and self.plot_choices_row in self.widget_container:
            self.widget_container.remove(self.plot_choices_row)

        # Find viable dimensions for axis selection
        dim_sizes = self.dataset[self._get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        self.x_axis_dropdown.name = "Select X-Axis dimension"
        self.x_axis_dropdown.options = sorted(viable_dims)
        show_plot_choices = True
        self.plot_button.name = "Plot data"

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.plot_type_dropdown.value == "Heatmap":
            # Check if enough dimensions to make heatmap, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                self._update_warning_text("Warning >> Not enough dimensions available for this variable to plot a Heatmap.")
                self.plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.y_axis_dropdown.name = "Select Y-Axis dimension"
                self.y_axis_dropdown.options = sorted(viable_dims)
                self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.y_axis_dropdown, self.plot_button)
        elif self.plot_type_dropdown.value == "Line":
            # If there is only 1 viable x-axis, plot automatically without user prompt to select x-axis.
            if len(viable_dims) == 1:
                self._update_warning_text("Only one valid x-axis dimension, plotting automatically.")
                self.x_axis_dropdown.value = viable_dims[0]
                show_plot_choices = False
                self._plot_data_button_click()
            else:
                self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.plot_button)
        elif self.plot_type_dropdown.value == "Animation":
            # Check if enough dimensions to make animation, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                self._update_warning_text("Warning >> Not enough dimensions available for this variable to plot an animation.")
                self.plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.y_axis_dropdown.name = "Select Y-Axis dimension"
                self.y_axis_dropdown.options = sorted(viable_dims)
                self.animation_axis_dropdown.name = "Select Z-Axis dimension"
                self.animation_axis_dropdown.options = sorted(viable_dims)
                self.plot_choices_row = pn.Row(
                    self.x_axis_dropdown,
                    self.y_axis_dropdown,
                    self.animation_axis_dropdown,
                    self.plot_button,
                )

        # If plotting hasn't automatically occurred (in the case of the line graph with only 1 plottable dimension)
        if show_plot_choices:
            # Insert the UI row under the variable selection even if there are plots already
            if hasattr(self, "plot_ui_row") and self.plot_ui_row in self.widget_container:
                insert_index = self.widget_container.index(self.plot_ui_row) + 1
                self.widget_container.insert(insert_index, self.plot_choices_row)
            else:
                self.widget_container.append(self.plot_choices_row)
            # self.widget_container.append(self.plot_pane)

    def _ref_display_plot_choices_ui(self):
        """
        Create interactive panel for user to choose plot options and add to widget_container. Private.
        """

        # Remove preexisting plot choices UI
        if hasattr(self, "ref_plot_choices_row") and self.ref_plot_choices_row in self.widget_container:
            self.widget_container.remove(self.ref_plot_choices_row)

        # Find viable dimensions for axis selection
        dim_sizes = self.ref_dataset[self._ref_get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        self.ref_x_axis_dropdown.name = "Select X-Axis dimension"
        self.ref_x_axis_dropdown.options = sorted(viable_dims)
        show_plot_choices = True
        self.ref_plot_button.name = "Plot data"

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.ref_plot_type_dropdown.value == "Heatmap":
            # Check if enough dimensions to make heatmap, if not, throw warning and don't let the user do it.
            if len(viable_dims) < 2:
                self._update_ref_warning_text("Warning >> Not enough dimensions available for this variable to plot a Heatmap.")
                self.ref_plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.ref_y_axis_dropdown.name = "Select Y-Axis dimension"
                self.ref_y_axis_dropdown.options = sorted(viable_dims)
                self.ref_plot_choices_row = pn.Row(
                    self.ref_x_axis_dropdown,
                    self.ref_y_axis_dropdown,
                    self.ref_plot_button,
                )
        elif self.ref_plot_type_dropdown.value == "Line":
            # Check if omly one viable dimension for line plot, if so plot it without options
            if len(viable_dims) == 1:
                show_plot_choices = False
                self._update_ref_warning_text("Only one valid x-axis dimension, plotting automatically.")
                self.ref_x_axis_dropdown.value = viable_dims[0]
                self._ref_plot_data_button_click()
            else:
                self.ref_plot_choices_row = pn.Row(self.ref_x_axis_dropdown, self.ref_plot_button)
        elif self.ref_plot_type_dropdown.value == "Animation":
            # Check if enough dimensions to make animation, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                self._update_ref_warning_text("Warning >> Not enough dimensions available for this variable to plot an animation.")
                self.ref_plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.ref_y_axis_dropdown.name = "Select Y-Axis dimension"
                self.ref_y_axis_dropdown.options = sorted(viable_dims)
                self.ref_animation_axis_dropdown.name = "Select Z-Axis dimension"
                self.ref_animation_axis_dropdown.options = sorted(viable_dims)
                self.ref_plot_choices_row = pn.Row(
                    self.ref_x_axis_dropdown,
                    self.ref_y_axis_dropdown,
                    self.ref_animation_axis_dropdown,
                    self.ref_plot_button,
                )

        if show_plot_choices:
            # Insert the UI row under the variable selection even if there are plots already
            if hasattr(self, "ref_plot_ui_row") and self.ref_plot_ui_row in self.widget_container:
                insert_index = self.widget_container.index(self.ref_plot_ui_row) + 1
                self.widget_container.insert(insert_index, self.ref_plot_choices_row)
            else:
                self.widget_container.append(self.ref_plot_choices_row)

    def _display_multiplot_plot_choices_ui(self):
        """
        Generate and display the UI components for selecting the multiplot x-axis. Private.
        """

        # Find viable dimensions for axis selection
        dim_sizes = self.dataset[self._multiplot_get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]
        show_plot_choices = True
        self.multiplot_x_axis_dropdown.name = "Select X-Axis dimension"
        self.multiplot_x_axis_dropdown.options = sorted(viable_dims)
        self.multiplot_analysis_choice_dropdown.name = "Select analysis type"
        self.multiplot_analysis_choice_dropdown.options = [
            "None (plot all loaded data)",
            "Plot Difference (Ref. - User data)",
            "Plot All Data & Difference",
        ]
        self.multiplot_plot_button.name = "Plot data"

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.multiplot_plot_type_dropdown.value == "Heatmap (grid)":
            # Check if enough dimensions to make heatmap, if not, throw warning and don't let the user do it.
            if len(viable_dims) < 2:
                self._update_multiplot_warning_text("Warning >> Not enough dimensions available for this variable to plot a Heatmap.")
                self.multiplot_plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.multiplot_y_axis_dropdown.name = "Select Y-Axis dimension"
                self.multiplot_y_axis_dropdown.options = sorted(viable_dims)
                self.multiplot_plot_choices_row = pn.Row(
                    self.multiplot_x_axis_dropdown,
                    self.multiplot_y_axis_dropdown,
                    self.multiplot_analysis_choice_dropdown,
                    self.multiplot_plot_button,
                )
        elif self.multiplot_plot_type_dropdown.value == "Line":
            # If there is only 1 viable x-axis, plot automatically without user prompt to select x-axis.
            # Also check that the check_bounds does not need to be prompted.
            needs_bounds_ui = self._multiplot_check_bounds()
            if len(viable_dims) == 1 and not needs_bounds_ui:
                show_plot_choices = True
                self._update_multiplot_warning_text("Only one valid x-axis dimension.")
                self.multiplot_plot_choices_row = pn.Row(self.multiplot_analysis_choice_dropdown, self.multiplot_plot_button)
                self.multiplot_x_axis_dropdown.value = viable_dims[0]
            elif len(viable_dims) == 1 and needs_bounds_ui:
                show_plot_choices = False
                self._prompt_bounds_ui()
            else:
                self.multiplot_plot_choices_row = pn.Row(
                    self.multiplot_x_axis_dropdown,
                    self.multiplot_analysis_choice_dropdown,
                    self.multiplot_plot_button,
                )

        # If plotting hasn't automatically occurred (in the case of the line graph with only 1 plottable dimension)
        if show_plot_choices:
            # Insert the UI row under the variable selection even if there are plots already
            if hasattr(self, "multiplot_type_selection_row") and self.multiplot_type_selection_row in self.widget_container:
                insert_index = self.widget_container.index(self.multiplot_type_selection_row) + 1
                self.widget_container.insert(insert_index, self.multiplot_plot_choices_row)
            else:
                self.widget_container.append(self.multiplot_plot_choices_row)

    def _check_plot_validity(self):
        """
        Check if the plot being created by the user is valid. Private.

        Returns
        -------
        plot_valid : bool
            True if the current plot configuration is valid, False otherwise.
        requires_slice : bool
            True if there are unplotted dimensions that require slicing, False otherwise.
        invalid_heatmap_data : bool
            True if a heatmap was requested but only one viable dimension exists, False otherwise.
        same_axes_chosen : bool
            True if a heatmap was requested with the same variable on both axes, False otherwise.
        """

        plot_valid = True
        requires_slice = False
        invalid_heatmap_data = False
        same_axes_chosen = False

        # Filter which dimensions can viably be plotted on an axis
        dim_sizes = self.dataset[self._get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        if self.plot_type_dropdown.value == "Animation":
            chosen_axes = (
                self.x_axis_dropdown.value,
                self.y_axis_dropdown.value,
                self.animation_axis_dropdown.value,
            )
        elif self.plot_type_dropdown.value == "Heatmap":
            chosen_axes = (self.x_axis_dropdown.value, self.y_axis_dropdown.value)
        else:
            chosen_axes = (self.x_axis_dropdown.value,)

        self.remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]
        # Check if existing slice widgets match the currently required dimensions
        if hasattr(self, "slice_widgets"):
            if set(self.slice_widgets.keys()) != set(self.remaining_dims):
                if hasattr(self, "slice_ui_row") and self.slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.slice_ui_row)
                del self.slice_ui_row
                del self.slice_widgets

        # If there are dimensions remaining in the dataset, and they are not already sliced by the user
        if len(self.remaining_dims) > 0 and not hasattr(self, "slice_widgets"):
            plot_valid = False
            requires_slice = True
        # If there is only one dimension plottable, and the user chose to plot a heatmap
        elif len(viable_dims) == 1 and self.plot_type_dropdown.value == "Heatmap":
            plot_valid = False
            invalid_heatmap_data = True
        # If the user has tried to plot the same variable on both axes
        elif len(set(chosen_axes)) != len(chosen_axes):
            plot_valid = False
            same_axes_chosen = True

        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen

    def _ref_check_plot_validity(self):
        """
        Check if the reference plot being created by the user is valid. Private.

        Returns
        -------
        plot_valid : bool
            True if the current plot configuration is valid, False otherwise.
        requires_slice : bool
            True if there are unplotted dimensions that require slicing, False otherwise.
        invalid_heatmap_data : bool
            True if a heatmap was requested but only one viable dimension exists, False otherwise.
        same_axes_chosen : bool
            True if a heatmap was requested with the same variable on both axes, False otherwise.
        """

        plot_valid = True
        requires_slice = False
        invalid_heatmap_data = False
        same_axes_chosen = False

        # Filter which dimensions can viably be plotted on an axis
        dim_sizes = self.ref_dataset[self._ref_get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        if self.ref_plot_type_dropdown.value == "Animation":
            chosen_axes = (
                self.ref_x_axis_dropdown.value,
                self.ref_y_axis_dropdown.value,
                self.ref_animation_axis_dropdown.value,
            )
        elif self.ref_plot_type_dropdown.value == "Heatmap":
            chosen_axes = (
                self.ref_x_axis_dropdown.value,
                self.ref_y_axis_dropdown.value,
            )
        else:
            chosen_axes = (self.ref_x_axis_dropdown.value,)

        self.ref_remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]
        # Check if existing reference slice widgets match the required dimensions
        if hasattr(self, "ref_slice_widgets"):
            if set(self.ref_slice_widgets.keys()) != set(self.ref_remaining_dims):
                if hasattr(self, "ref_slice_ui_row") and self.ref_slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.ref_slice_ui_row)
                del self.ref_slice_ui_row
                del self.ref_slice_widgets

        # If there are dimensions remaining in the dataset, and they are not already sliced by the user
        if len(self.ref_remaining_dims) > 0 and not hasattr(self, "ref_slice_widgets"):
            plot_valid = False
            requires_slice = True
        # If there is only one dimension plottable, and the user chose to plot a heatmap
        elif len(viable_dims) == 1 and self.ref_plot_type_dropdown.value == "Heatmap":
            plot_valid = False
            invalid_heatmap_data = True
        # If the user has tried to plot the same variable on both axes
        elif len(set(chosen_axes)) != len(chosen_axes):
            plot_valid = False
            same_axes_chosen = True

        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen

    def _check_multiplot_plot_validity(self):
        """
        Check if the current UI configuration allows for a valid plot. Private.

        Returns
        -------
        plot_valid : bool
            True if the plot can be generated immediately, False otherwise.
        requires_slice : bool
            True if the data has remaining dimensions requiring UI slice widgets.
        check_bounds : bool
            True if reference dataset bounds exceed the user dataset x-axis limits.
        """

        plot_valid = True
        requires_slice = False
        check_bounds = self._multiplot_check_bounds()

        # Filter which dimensions can viably be plotted on an axis
        dim_sizes = self.dataset[self._multiplot_get_selected_variable()].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        if self.multiplot_plot_type_dropdown.value == "Line":
            chosen_axes = (self.multiplot_x_axis_dropdown.value,)
        elif self.multiplot_plot_type_dropdown.value == "Heatmap (grid)":
            chosen_axes = (
                self.multiplot_x_axis_dropdown.value,
                self.multiplot_y_axis_dropdown.value,
            )

        self.multiplot_remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]
        # Check if existing reference slice widgets match the required dimensions
        if hasattr(self, "multiplot_slice_widgets"):
            if set(self.multiplot_slice_widgets.keys()) != set(self.multiplot_remaining_dims):
                if hasattr(self, "multiplot_slice_ui_row") and self.multiplot_slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.multiplot_slice_ui_row)
                del self.multiplot_slice_ui_row
                del self.multiplot_slice_widgets

        # Check if the variable is contained within each of the datasets. If it is not, remove them and inform the user
        invalid_datasets = {}
        for dataset in list(self.multiplot_ref_dataset_dict.keys()):
            if self._multiplot_get_selected_variable() not in self.multiplot_ref_dataset_dict[dataset]:
                invalid_datasets[dataset] = self.multiplot_ref_dataset_dict[dataset]
                del self.multiplot_ref_dataset_dict[dataset]

        if invalid_datasets:
            invalid_str = ", ".join(invalid_datasets.keys())
            self._update_multiplot_warning_text(
                f"Warning >> The following models were removed as they do not contain the selected variable: {invalid_str}"
            )

        # If there are dimensions remaining in the dataset, and they are not already sliced by the user
        if len(self.multiplot_remaining_dims) > 0 and not hasattr(self, "multiplot_slice_widgets"):
            plot_valid = False
            requires_slice = True

        # Ensure plot is not created if the user needs to be prompted about bounds.
        if check_bounds:
            plot_valid = False

        return plot_valid, requires_slice, check_bounds

    def _check_slice(self):
        """
        Check if the plot being created by the user requires dimensions to be sliced to generate a valid plot. Private.
        """

        # Filter dimensions to get the remaining dimensions not selected as the axes
        self.slice_widgets = {}
        ui_components = []

        # for each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in self.remaining_dims:
            # Extract coordinate values as options
            coord_values = list(self.dataset[dimension].values)
            options_dict = {self._round_slice_val(val): val for val in coord_values}
            dropdown = pn.widgets.DiscreteSlider(name=f"Slice {dimension} at:", options=options_dict)

            self.slice_widgets[dimension] = dropdown
            ui_components.append(dropdown)

        # Group them into a row
        self.slice_ui_row = pn.Row(*ui_components)

        # Insert the slice UI below the plot choices row
        if hasattr(self, "plot_choices_row") and self.plot_choices_row in self.widget_container:
            insert_index = self.widget_container.index(self.plot_choices_row) + 1
            self.widget_container.insert(insert_index, self.slice_ui_row)
        else:
            self.widget_container.append(self.slice_ui_row)

        # Update the UI text to prompt the user
        self.plot_button.name = "Confirm Slices & Plot"
        self._update_status_text("User model status >> Action required: Select slice values and click plot again.")

    def _ref_check_slice(self):
        """
        Check if the reference plot being created by the user requires dimensions to be sliced to generate a valid plot. Private.
        """

        # Filter dimensions to get the remaining dimensions not selected as the axes
        self.ref_slice_widgets = {}
        ref_ui_components = []

        # for each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in self.ref_remaining_dims:
            # Extract coordinate values as options
            coord_values = list(self.ref_dataset[dimension].values)
            options_dict = {self._round_slice_val(val): val for val in coord_values}
            dropdown = pn.widgets.DiscreteSlider(name=f"Slice {dimension} at:", options=options_dict)

            self.ref_slice_widgets[dimension] = dropdown
            ref_ui_components.append(dropdown)

        # Group them into a row
        self.ref_slice_ui_row = pn.Row(*ref_ui_components)

        # Insert the slice UI below the plot choices row
        if hasattr(self, "ref_plot_choices_row") and self.ref_plot_choices_row in self.widget_container:
            insert_index = self.widget_container.index(self.ref_plot_choices_row) + 1
            self.widget_container.insert(insert_index, self.ref_slice_ui_row)
        else:
            self.widget_container.append(self.ref_slice_ui_row)

        # Update the UI text to prompt the user
        self.ref_plot_button.name = "Confirm Slices & Plot"
        self._update_ref_status_text("User model status >> Action required: Select slice values and click plot again.")

    def _multiplot_check_slice(self):
        """
        Check if the overlay plot requires dimensions to be sliced and generate the slicing UI. Private.

        Dynamically creates dropdown widgets for any remaining dimensions that need to be sliced and
        inserts them into the widget container.
        """

        self.multiplot_slice_widgets = {}
        multiplot_ui_components = []

        # For each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in self.multiplot_remaining_dims:
            # Extract coordinate values as options
            coord_values = list(self.dataset[dimension].values)
            options_dict = {self._round_slice_val(val): val for val in coord_values}
            dropdown = pn.widgets.DiscreteSlider(name=f"Slice {dimension} at:", options=options_dict)

            self.multiplot_slice_widgets[dimension] = dropdown
            multiplot_ui_components.append(dropdown)

        # Group them into a row
        self.multiplot_slice_ui_row = pn.Row(*multiplot_ui_components)

        # Insert the slice UI below the plot choices row
        if hasattr(self, "multiplot_plot_choices_row") and self.multiplot_plot_choices_row in self.widget_container:
            insert_index = self.widget_container.index(self.multiplot_plot_choices_row) + 1
            self.widget_container.insert(insert_index, self.multiplot_slice_ui_row)
        else:
            self.widget_container.append(self.multiplot_slice_ui_row)

        # Update the UI text to prompt the user
        self.multiplot_plot_button.name = "Confirm Slices & Plot"
        self._update_multiplot_status_text("Overlay Plot >> Action required: Select slice values and click plot again.")

    def _round_slice_val(self, val):
        """
        Round numerical values to a maximum of 2 decimal places for display.

        Parameters
        ----------
        val : int, float, or str
            The value to be rounded.

        Returns
        -------
        str
            The rounded value as a string, or the original value as a string
            if it cannot be converted to a float.
        """

        try:
            return str(round(float(val), 2))
        except (ValueError, TypeError):
            return str(val)

    def _update_dataset_plot_ui(self):
        """
        Update exisiting user model dataset plot if new data are selected. Private.
        """

        self.plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
        self.plot_pane.object = None  # Clears the previous plot from the screen
        if hasattr(self, "fig"):
            plt.close(self.fig)
        if hasattr(self, "multiplot_ref_keys_selection_row"):
            self.multiplot_plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
            self.multiplot_keys_dropdown.value = self.keys_dropdown.value

    def _update_ref_dataset_keys_plot_ui(self):
        """
        Update exisiting reference model dataset keys if new data are selected. Private.
        """

        self.ref_data_keys_dropdown.options = sorted(list(self.ref_dataset.keys()))
        plt.close(self.ref_fig)

        self._update_ref_dataset_plot_ui()

    def _update_ref_dataset_plot_ui(self):
        """
        Update exisiting reference model dataset plot if new data are selected. Private.
        """

        self.ref_plot_variable_dropdown.options = sorted(list(self.ref_dataset.keys()))
        self.ref_plot_pane.object = None  # Clears the previous plot from the screen
        if hasattr(self, "ref_fig"):
            plt.close(self.ref_fig)

    def _plot_dataset(self, variable, x_axis):
        """
        Plot 2D time-series from model data. Private.

        Parameters
        ----------
        variable : str
            Model data variable as selected from panel dropdown.
        Returns
        ----------
        self.fig : matplotlib.pyplot.figure()
        """
        # Plot primary (user) model data
        self.fig, ax = plt.subplots(figsize=[8, 4])

        self.figure_exists = True
        # Slice the dataset if the user has selected any
        sliced_data = self.dataset.sel(**self.chosen_slices, method="nearest")

        # Add the slice information to the title, if it is sliced data
        sliced_data[variable].plot(x=x_axis, ax=ax)
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.chosen_slices.items()])
        title_text = sliced_data[variable].attrs.get("long_name", variable)
        caption_text = "User model \nDataset: " + self.keys_dropdown.value

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        self.fig.subplots_adjust(bottom=0.3)

        ax.grid()
        ax.legend()

        plt.close(self.fig)

        return self.fig

    def _plot_heatmap(self, variable, x_axis, y_axis):
        """
        Plot 2D heatmap from model data. Private.

        Parameters
        ----------
        variable : str
            Model data variable as selected from panel dropdown.
        x_axis : str
            X-axis as selected from the panel dropdown.
        y_axis : str
            Y-axis as selected from the panel dropdown.
        Returns
        ----------
        fig : matplotlib.pyplot.figure()
        """

        # Create figure and explicit axis
        self.fig, ax = plt.subplots(figsize=[8, 4])

        # Slice the dataset if the user has selected any
        heatmap_data = self.dataset.sel(**self.chosen_slices, method="nearest")

        # Plot the specific DataArray onto the explicit axis
        heatmap_data[variable].plot(x=x_axis, y=y_axis, ax=ax)

        # Add the slice information to the title, if it is sliced data
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.chosen_slices.items()])
        title_text = heatmap_data[variable].attrs.get("long_name", variable)
        caption_text = "User model \nDataset: " + self.keys_dropdown.value

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        self.fig.subplots_adjust(bottom=0.3)

        ax.grid()
        plt.close(self.fig)
        return self.fig

    def _plot_ref_dataset(self, ref_variable, x_axis):
        """
        Plot 2D time-series from reference model data. Private.

        Parameters
        ----------
        ref_variable : str
            Reference model data variable as selected from panel dropdown.
        x_axis : str
            X-axis as selected from the panel dropdown.

        Returns
        ----------
        ref_fig : matplotlib.pyplot.figure()
        """

        self.ref_fig, ax = plt.subplots(figsize=[8, 4])

        self.ref_figure_exists = True

        sliced_data = self.ref_dataset.sel(**self.ref_chosen_slices, method="nearest")

        # Plot all model variants if multiple exist
        if "member" in sliced_data.dims:

            for mem in sliced_data.member.values:

                sliced_data[ref_variable].sel(member=mem).plot(label=mem, x=x_axis, ax=ax)
        else:
            # Plot directly if no member dimension exists
            sliced_data[ref_variable].plot(x=x_axis, ax=ax)

        # Add the slice information to the title, if it is sliced data

        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.ref_chosen_slices.items()])
        title_text = sliced_data[ref_variable].attrs.get("long_name", ref_variable)
        caption_text = "Model: " + self.ref_keys_dropdown.value + "\nDataset: " + self.ref_data_keys_dropdown.value

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.ref_fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.ref_fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        self.ref_fig.subplots_adjust(bottom=0.3)
        ax.grid()
        ax.legend()

        plt.close(self.ref_fig)

        return self.ref_fig

    def _plot_ref_heatmap(self, ref_variable, x_axis, y_axis):
        """
        Plot 2D heatmap from model data. Private.

        Parameters
        ----------
        ref_variable : str
            Model data variable as selected from panel dropdown.
        x_axis : str
            X-axis as selected from the panel dropdown.
        y_axis : str
            Y-axis as selected from the panel dropdown.
        Returns
        ----------
        self.ref_fig : matplotlib.pyplot.figure()
        """

        # Create figure and explicit axis
        self.ref_fig, ax = plt.subplots(figsize=[8, 4])

        # Slice the dataset if the user has selected any
        heatmap_data = self.ref_dataset.sel(**self.ref_chosen_slices, method="nearest")

        # Plot the specific DataArray onto the explicit axis
        heatmap_data[ref_variable].plot(x=x_axis, y=y_axis, ax=ax)

        # Add the slice information to the title, if it is sliced data

        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.ref_chosen_slices.items()])
        title_text = heatmap_data[ref_variable].attrs.get("long_name", ref_variable)
        caption_text = "Model: " + self.ref_keys_dropdown.value + "\nDataset: " + self.ref_data_keys_dropdown.value

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"
            # Add the slice information to the title, if it is sliced data

        self.ref_fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.ref_fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        self.ref_fig.subplots_adjust(bottom=0.3)

        ax.grid()

        plt.close(self.ref_fig)
        return self.ref_fig

    def _plot_multiplot_dataset(self, variable, x_axis):
        """
        Plot 2D time-series overlaying the user model and selected reference models. Private.

        Parameters
        ----------
        variable : str
            Model data variable as selected from panel dropdown.
        x_axis : str
            X-axis as selected from the panel dropdown.

        Returns
        -------
        fig : matplotlib.figure.Figure
            The constructed figure containing the overlaid plots.
        """

        self._multiplot_check_bounds()

        # Scale the x-axis depending on how the user has selected the bounds to be constrained. Defaults to min-max of all datasets being plotted.
        if self.prompt_bounds_dropdown.value == "Constrain to user dataset bounds":
            x_min = self.dataset_min
            x_max = self.dataset_max
        else:
            x_min = self.multiplot_min
            x_max = self.multiplot_max

        fig, ax = plt.subplots(figsize=[8, 4])

        # Plot user data
        sliced_user_data = self.dataset.sel(**self.multiplot_chosen_slices, method="nearest")
        sliced_user_data[variable].plot(label=f"User dataset", x=x_axis, ax=ax, linewidth=2, color="black")

        # Loop through the dictionary adding each reference dataset
        for model_key, dataset in self.multiplot_ref_dataset_dict.items():

            # Apply slices if those dimensions exist in the user dataset
            valid_slices = {dim: val for dim, val in self.multiplot_chosen_slices.items() if dim in dataset.dims}
            sliced_data = dataset.sel(**valid_slices, method="nearest")

            # Plot all model variants if multiple exist
            if "member" in sliced_data.dims:
                for mem in sliced_data.member.values:
                    sliced_data[variable].sel(member=mem, method="nearest").plot(label=f"{model_key} (mem: {mem})", x=x_axis, ax=ax)
            else:
                # Plot directly if no member dimension exists
                sliced_data[variable].plot(label=model_key, x=x_axis, ax=ax)

        # Add the slice information to the caption text, if it is sliced data
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.multiplot_chosen_slices.items()])
        title_text = sliced_user_data[variable].attrs.get("long_name", variable)

        caption_text = ""

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        ax.set_xlim(x_min, x_max)
        fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        fig.subplots_adjust(bottom=0.15, right=0.7)
        ax.grid()

        ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))

        plt.close(fig)

        return fig

    def _plot_multiplot_heatmap_dataset(self, variable, x_axis, y_axis):
        """
        Plot 2D time-series overlaying the user model and selected reference models. Private.

        Parameters
        ----------
        variable : str
            Model data variable as selected from panel dropdown.
        x_axis : str
            X-axis as selected from the panel dropdown.

        Returns
        -------
        fig : matplotlib.figure.Figure
            The constructed figure of a number of heatmaps, laid out in a grid.
        """
        # get the number of reference variables, to calculate the grid size
        num_refs = len(self.multiplot_ref_dataset_dict)
        total_plots = 1 + num_refs

        # calculate grid dimensions
        if total_plots > 1:
            ncols = 2
        else:
            ncols = 1

        nrows = (total_plots + 1) // 2

        sliced_user_data = self.dataset.sel(**self.multiplot_chosen_slices, method="nearest")
        global_vmin = float(sliced_user_data[variable].min())
        global_vmax = float(sliced_user_data[variable].max())

        # Need to check min and max for given variable to keep colour consistent between different heatmaps
        for dataset in self.multiplot_ref_dataset_dict.values():
            valid_slices = {dim: val for dim, val in self.multiplot_chosen_slices.items() if dim in dataset.dims}
            sliced_ref = dataset.sel(**valid_slices, method="nearest")
            global_vmin = min(global_vmin, float(sliced_ref[variable].min()))
            global_vmax = max(global_vmax, float(sliced_ref[variable].max()))

        # Create grid
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=[6 * ncols, 4 * nrows])

        # Flatten axes array for easy iteration
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

        # Plot User Data
        sliced_user_data[variable].plot(
            x=x_axis,
            y=y_axis,
            ax=axes_flat[0],
            vmin=global_vmin,
            vmax=global_vmax,
            cmap="viridis",
            cbar_kwargs={"label": variable},
        )
        axes_flat[0].set_title("User Dataset")

        ax = 1
        for model_key, dataset in self.multiplot_ref_dataset_dict.items():
            valid_slices = {dim: val for dim, val in self.multiplot_chosen_slices.items() if dim in dataset.dims}
            sliced_ref = dataset.sel(**valid_slices, method="nearest")

            # If the reference data has members, plot the first one to avoid issues
            member_title = ""
            if "member" in sliced_ref.dims:
                sliced_ref = sliced_ref.isel(member=0)
                member_title = f" (mem: {dataset.member.values[0]})"

            sliced_ref[variable].plot(
                x=x_axis,
                y=y_axis,
                ax=axes_flat[ax],
                vmin=global_vmin,
                vmax=global_vmax,
                cmap="viridis",
                cbar_kwargs={"label": variable},
            )
            axes_flat[ax].set_title(f"{model_key}{member_title}")
            ax += 1

        # delete empty subplots remaining
        for i in range(total_plots, len(axes_flat)):
            fig.delaxes(axes_flat[i])

        # Add the slice information to the caption text, if it is sliced data
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.multiplot_chosen_slices.items()])
        if slice_str:
            fig.text(
                0.1,
                0.01,
                f"Sliced by: {slice_str}",
                wrap=True,
                horizontalalignment="left",
                fontsize=10,
            )
            fig.subplots_adjust(bottom=0.15, hspace=0.3)
        else:
            fig.subplots_adjust(hspace=0.3)

        plt.close(fig)

        return fig

    def _clear_multiplot_data(self):
        """
        Clears the reference datasets which have been loaded. Private
        """

        self.multiplot_ref_dataset_dict = {}
        self._update_multiplot_status_text("Overlay Plot Status >> Cleared loaded reference models")

    def _multiplot_check_bounds(self):
        """
        Calculate the absolute minimum and maximum x-axis bounds across all datasets. Private.

        Compares the user dataset bounds against all loaded reference datasets.
        Saves the global bounds as instance attributes for plotting.

        Returns
        -------
        bool
            True if the reference datasets exceed the user dataset bounds, False otherwise.
        """

        x_axis = self.multiplot_x_axis_dropdown.value
        if x_axis is None:
            return False

        # Get User data bounds from the primary user dataset
        self.dataset_min = self.dataset[x_axis].min().values
        self.dataset_max = self.dataset[x_axis].max().values

        global_min = self.dataset_min
        global_max = self.dataset_max

        # Track if the bounds need to be expanded
        bounds_widened = False

        # Iterate through the reference datasets to find the absolute min and max
        for ref_ds in self.multiplot_ref_dataset_dict.values():
            if x_axis in ref_ds:
                ref_min = ref_ds[x_axis].min().values
                ref_max = ref_ds[x_axis].max().values

                try:
                    # Attempt standard numerical or exact-calendar comparison first
                    if ref_min < global_min:
                        global_min = ref_min
                        bounds_widened = True
                    if ref_max > global_max:
                        global_max = ref_max
                        bounds_widened = True

                except TypeError:
                    # Raised when cftime calendars clash.
                    # Catch the error and fallback to comparing chronological tuples directly.
                    g_min_obj = global_min.item() if hasattr(global_min, "item") else global_min
                    r_min_obj = ref_min.item() if hasattr(ref_min, "item") else ref_min
                    g_max_obj = global_max.item() if hasattr(global_max, "item") else global_max
                    r_max_obj = ref_max.item() if hasattr(ref_max, "item") else ref_max

                    g_min_tup = (
                        g_min_obj.year,
                        g_min_obj.month,
                        g_min_obj.day,
                        g_min_obj.hour,
                        g_min_obj.minute,
                        g_min_obj.second,
                    )
                    r_min_tup = (
                        r_min_obj.year,
                        r_min_obj.month,
                        r_min_obj.day,
                        r_min_obj.hour,
                        r_min_obj.minute,
                        r_min_obj.second,
                    )

                    g_max_tup = (
                        g_max_obj.year,
                        g_max_obj.month,
                        g_max_obj.day,
                        g_max_obj.hour,
                        g_max_obj.minute,
                        g_max_obj.second,
                    )
                    r_max_tup = (
                        r_max_obj.year,
                        r_max_obj.month,
                        r_max_obj.day,
                        r_max_obj.hour,
                        r_max_obj.minute,
                        r_max_obj.second,
                    )

                    if r_min_tup < g_min_tup:
                        global_min = ref_min
                        bounds_widened = True
                    if r_max_tup > g_max_tup:
                        global_max = ref_max
                        bounds_widened = True
        # save the global variables so the plotting function can access them
        self.multiplot_min = global_min
        self.multiplot_max = global_max

        # Return True if the bounds were widened so the user is prompted, False otherwise
        return bounds_widened

    def _prompt_bounds_ui(self):
        """
        Generate and insert the UI row for selecting x-axis bounds constraints. Private.

        Configures the bounds dropdown options and determines the correct
        insertion point within the widget container based on the presence of
        other active UI components.
        """

        self.prompt_bounds_dropdown.name = "Choose how to constrain the x-axis bounds"
        self.prompt_bounds_dropdown.options = [
            "Constrain to user dataset bounds",
            "Constrain to min-max reference dataset bounds",
        ]

        current_layout = list(self.widget_container)
        # Default to appending at the end if no other UI elements match
        insert_index = len(current_layout)

        self.prompt_bounds_row = pn.Row(self.prompt_bounds_dropdown, self.prompt_bounds_button)

        # Determine the insertion index based on a hierarchy of existing UI elements
        if hasattr(self, "multiplot_slice_ui_row") and self.multiplot_slice_ui_row in current_layout:
            insert_index = current_layout.index(self.multiplot_slice_ui_row) + 1
        elif hasattr(self, "multiplot_plot_choices_row") and self.multiplot_plot_choices_row in current_layout:
            insert_index = current_layout.index(self.multiplot_plot_choices_row) + 1
        elif hasattr(self, "multiplot_type_selection_row") and self.multiplot_type_selection_row in current_layout:
            insert_index = current_layout.index(self.multiplot_type_selection_row) + 1
        elif hasattr(self, "multiplot_ref_keys_selection_row") and self.multiplot_ref_keys_selection_row in current_layout:
            insert_index = current_layout.index(self.multiplot_ref_keys_selection_row) + 1

        # Insert the new row into the extracted list
        current_layout.insert(insert_index, self.prompt_bounds_row)

        # Apply the slice assignment to force a front-end UI update
        self.widget_container[:] = current_layout

    def _update_multiplot_dataset(self):
        """
        Load a new user dataset based on the current dropdown selection and update UI components. Private.
        """

        self._update_multiplot_status_text("Overlay Plot Status >> Loading new user dataset...")
        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.multiplot_keys_dropdown.value)
        self.loaded_dataset_key = self.multiplot_keys_dropdown.value
        self.multiplot_plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
        self.keys_dropdown.value = self.loaded_dataset_key
        self.plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
        self._update_multiplot_status_text("Overlay Plot Status >> New user dataset loaded, clearing loaded user models")
        # Clear the loaded data, as different datasets from the selected models will need to be loaded.
        self._clear_multiplot_data()

    def _plot_animation(self, variable):
        """
        Generates an animated plot for the user dataset.

        Parameters
        ----------
        variable : str
            The name of the data variable to plot.

        Returns
        -------
        panel.Column
            A Panel layout containing the interactive hvplot animation
            and an HTML caption.
        """

        data = self.dataset.sel(**self.chosen_slices, method="nearest")
        plot_dataset = data[variable].load()

        # get the min and max variable values so that the heatmap is consistent for the whole animation
        vmin = float(plot_dataset.min())
        vmax = float(plot_dataset.max())

        x_dim = self.x_axis_dropdown.value
        y_dim = self.y_axis_dropdown.value

        # Assign coordinates if they are missing, necessary for SeaIce datasets
        if x_dim not in plot_dataset.coords:
            plot_dataset = plot_dataset.assign_coords({x_dim: range(plot_dataset.sizes[x_dim])})
        if y_dim not in plot_dataset.coords:
            plot_dataset = plot_dataset.assign_coords({y_dim: range(plot_dataset.sizes[y_dim])})

        plot = plot_dataset.hvplot.quadmesh(
            x=x_dim,
            y=y_dim,
            groupby=self.animation_axis_dropdown.value,
            dynamic=True,
            rasterize=True,
            widget_type="scrubber",
            widget_location="bottom",
            clim=(vmin, vmax),
            cmap="viridis",
            width=1200,
            height=600,
        )

        # Build caption string
        variable_text = plot_dataset.attrs.get("long_name", variable)
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.chosen_slices.items()])
        caption_text = "Variable: " + variable_text + "<br>User model<br>Dataset: " + self.keys_dropdown.value
        if slice_str:
            caption_text += f"<br>Sliced by: {slice_str}"

        caption_pane = pn.pane.HTML(f"<div style='font-size: 12px; margin-left: 10%; margin-top: 10px;'>{caption_text}</div>")

        # Return a Column with the plot on top and the caption underneath
        return pn.Column(pn.panel(plot, tight=True), caption_pane)

    def _plot_ref_animation(self):
        """
        Generates an animated plot for the reference dataset.

        Returns
        -------
        panel.Column
            A Panel layout containing the interactive hvplot animation
            and an HTML caption.
        """

        data = self.ref_dataset.sel(**self.ref_chosen_slices, method="nearest")
        plot_dataset = data[self._ref_get_selected_variable()].load()

        # get the min and max variable values so that the heatmap is consistent for the whole animation
        vmin = float(plot_dataset.min())
        vmax = float(plot_dataset.max())
        x_dim = self.x_axis_dropdown.value
        y_dim = self.y_axis_dropdown.value

        # Assign coordinates if they are missing, necessary for SeaIce datasets
        if x_dim not in plot_dataset.coords:
            plot_dataset = plot_dataset.assign_coords({x_dim: range(plot_dataset.sizes[x_dim])})
        if y_dim not in plot_dataset.coords:
            plot_dataset = plot_dataset.assign_coords({y_dim: range(plot_dataset.sizes[y_dim])})

        plot = plot_dataset.hvplot.quadmesh(
            x=x_dim,
            y=y_dim,
            groupby=self.ref_animation_axis_dropdown.value,
            dynamic=True,
            rasterize=True,
            widget_type="scrubber",
            widget_location="bottom",
            clim=(vmin, vmax),
            cmap="viridis",
            width=1200,
            height=600,
        )

        # Build caption string
        variable_text = plot_dataset.attrs.get("long_name", self._ref_get_selected_variable())
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.ref_chosen_slices.items()])
        caption_text = (
            "Variable: " + variable_text + "<br>Model: " + self.ref_keys_dropdown.value + "<br>Dataset: " + self.ref_data_keys_dropdown.value
        )
        if slice_str:
            caption_text += f"<br>Sliced by: {slice_str}"

        caption_pane = pn.pane.HTML(f"<div style='font-size: 12px; margin-left: 10%; margin-top: 10px;'>{caption_text}</div>")

        # Return a Column with the plot on top and the caption underneath
        return pn.Column(pn.panel(plot, tight=True), caption_pane)

    def _plot_multiplot_difference_heatmap(self, variable, x_axis, y_axis):
        """
        Plots a grid of difference heatmaps between reference datasets and the user dataset.

        Parameters
        ----------
        variable : str
            The name of the data variable to plot.
        x_axis : str
            The name of the dimension or coordinate to use for the x-axis.
        y_axis : str
            The name of the dimension or coordinate to use for the y-axis.

        Returns
        -------
        matplotlib.figure.Figure
            The formatted matplotlib Figure object containing the grid of difference heatmaps.
        """

        # get the number of reference variables, to calculate the grid size
        total_plots = len(self.multiplot_ref_dataset_dict)

        # calculate grid dimensions
        if total_plots > 1:
            ncols = 2
        else:
            ncols = 1

        nrows = (total_plots + 1) // 2

        sliced_user_data = self.dataset.sel(**self.multiplot_chosen_slices, method="nearest")
        global_vmin = 0
        global_vmax = 0
        plot_dict = {}

        # Need to check min and max for given variable to keep colour consistent between different heatmaps
        for key, dataset in self.multiplot_ref_dataset_dict.items():
            valid_slices = {dim: val for dim, val in self.multiplot_chosen_slices.items() if dim in dataset.dims}
            sliced_ref = dataset.sel(**valid_slices, method="nearest")
            diff_data = sliced_ref[variable] - sliced_user_data[variable]
            plot_dict[key] = diff_data
            global_vmin = min(global_vmin, float(diff_data.min()))
            global_vmax = max(global_vmax, float(diff_data.max()))

        abs_max = max(abs(global_vmin), abs(global_vmax))
        symmetric_vmin = -abs_max
        symmetric_vmax = abs_max

        # Create grid
        fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=[6 * ncols, 4 * nrows])

        # Flatten axes array for easy iteration
        axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

        ax = 0
        for model_key, current_diff_data in plot_dict.items():

            # If the reference data has members, plot the first one to avoid issues
            member_title = ""
            if "member" in current_diff_data.dims:
                current_diff_data = current_diff_data.isel(member=0)
                member_title = f" (mem: {current_diff_data.member.values})"

            # Plot current_diff_data
            current_diff_data.plot(
                x=x_axis,
                y=y_axis,
                ax=axes_flat[ax],
                vmin=symmetric_vmin,
                vmax=symmetric_vmax,
                cmap="RdBu_r",  # Diverging colormap (Red-Blue)
                cbar_kwargs={"label": f"Δ {variable}"},
            )
            axes_flat[ax].set_title(f"{model_key}{member_title} - User data")
            ax += 1

        # delete empty subplots remaining
        for i in range(total_plots, len(axes_flat)):
            fig.delaxes(axes_flat[i])

        # Add the slice information to the caption text, if it is sliced data
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.multiplot_chosen_slices.items()])
        if slice_str:
            fig.text(
                0.1,
                0.01,
                f"Sliced by: {slice_str}",
                wrap=True,
                horizontalalignment="left",
                fontsize=10,
            )
            fig.subplots_adjust(bottom=0.15, hspace=0.3)
        else:
            fig.subplots_adjust(hspace=0.3)

        plt.close(fig)

        return fig

    def _plot_multiplot_difference_dataset(self, variable, x_axis):
        """
        Plots the difference between reference datasets and the user dataset.

        Parameters
        ----------
        variable : str
            The name of the data variable to plot.
        x_axis : str
            The name of the dimension or coordinate to use for the x-axis.

        Returns
        -------
        matplotlib.figure.Figure
            The formatted matplotlib Figure object containing the difference plot.
        """

        self._multiplot_check_bounds()

        # Scale the x-axis depending on how the user has selected the bounds to be constrained. Defaults to min-max of all datasets being plotted.
        if self.prompt_bounds_dropdown.value == "Constrain to user dataset bounds":
            x_min = self.dataset_min
            x_max = self.dataset_max
        else:
            x_min = self.multiplot_min
            x_max = self.multiplot_max

        fig, ax = plt.subplots(figsize=[8, 4])

        # Plot user data
        sliced_user_data = self.dataset.sel(**self.multiplot_chosen_slices, method="nearest")

        # Loop through the dictionary adding each reference dataset
        for model_key, dataset in self.multiplot_ref_dataset_dict.items():

            # Apply slices if those dimensions exist in the user dataset
            valid_slices = {dim: val for dim, val in self.multiplot_chosen_slices.items() if dim in dataset.dims}
            sliced_data = dataset.sel(**valid_slices, method="nearest")
            plot_data = sliced_data - sliced_user_data

            # Plot all model variants if multiple
            if "member" in plot_data.dims:
                for mem in plot_data.member.values:
                    plot_data[variable].sel(member=mem, method="nearest").plot(label=f"{model_key} (mem: {mem})", x=x_axis, ax=ax)
            else:
                # Plot directly if no member dimension exists
                plot_data[variable].plot(label=model_key, x=x_axis, ax=ax)

        # Add the slice information to the caption text, if it is sliced data
        slice_str = ", ".join([f"{dim}: {self._round_slice_val(val)}" for dim, val in self.multiplot_chosen_slices.items()])
        title_text = "Δ "
        title_text += sliced_user_data[variable].attrs.get("long_name", variable)
        title_text += " (Ref. - User data)"
        caption_text = ""

        # Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        ax.set_xlim(x_min, x_max)
        fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        ax.axhline(0, color="k")  # horizontal line at 0
        fig.text(0.1, 0.01, caption_text, wrap=True, horizontalalignment="left", fontsize=10)
        fig.subplots_adjust(bottom=0.15, right=0.7)
        ax.grid()

        ax.legend(loc="center left", bbox_to_anchor=(1.05, 0.5))

        plt.close(fig)

        return fig
