# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

"""UI class and functions"""

import panel as pn
import matplotlib.pyplot as plt

from med_diagnostics import data, controller
from IPython.display import display


class UserInterface:
    """
    Primary class for user interface (UI) components and deployment
    """

    # Set up styles used for text boxes and buttons
    STYLES = {
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

    def __init__(self):
        """
        Initialise a UserInterface instance.
        """

        # Import panel extensions
        pn.extension()

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
        self.x_axis_dropdown, self.y_axis_dropdown, self.animation_axis_dropdown = (
            pn.widgets.Select(),
            pn.widgets.Select(),
            pn.widgets.Select(),
        )
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
        self.long_names, self.ref_long_names, self.multiplot_long_names = {}, {}, {}
        # Initialise button listener functions

        self.plot_button.on_click(self._plot_button_click)
        self.ref_plot_button.on_click(self._ref_plot_button_click)
        self.keys_button.on_click(self._keys_button_click)
        self.ref_keys_button.on_click(self._ref_keys_button_click)
        self.ref_data_keys_button.on_click(self._ref_data_keys_button_click)
        self.clear_ref_model_data_button.on_click(self._ref_clear_data_button_click)
        self.ref_model_info_button.on_click(self._ref_model_info_button_click)
        self.select_variable_button.on_click(self._select_variable_button_click)
        self.ref_select_variable_button.on_click(self._ref_select_variable_button_click)
        self.multiplot_ref_keys_button.on_click(self._multiplot_ref_keys_button_click)
        self.multiplot_plot_button.on_click(self._multiplot_plot_button_click)
        self.clear_multiplot_data_button.on_click(self._clear_multiplot_data_button_click)
        self.multiplot_keys_update_button.on_click(self._multiplot_keys_update_button_click)
        self.multiplot_select_variable_button.on_click(self._multiplot_select_variable_button_click)
        self.prompt_bounds_button.on_click(self._prompt_bounds_button_click)
        self.variable_toggle.param.watch(self._variable_toggle_click, "value")
        self.ref_variable_toggle.param.watch(self._ref_variable_toggle_click, "value")
        self.multiplot_variable_toggle.param.watch(self._multiplot_variable_toggle_click, "value")

    def _keys_button_click(self, event):
        """Event wrapper for the primary keys dropdown click."""

        self._keys_dropdown_click()

    def _ref_keys_button_click(self, event):
        """Event wrapper for the ref keys dropdown click."""
        self._ref_keys_dropdown_click()

    def _ref_data_keys_button_click(self, event):
        """Event wrapper for the ref keys button click."""
        self._ref_dataset_dropdown_click()

    def _ref_model_info_button_click(self, event):
        """Event wrapper for the ref info button click."""
        self._ref_model_info_click()

    def _ref_clear_data_button_click(self, event):
        """Event wrapper for the ref clear data button click."""
        self._ref_clear_data_click()

    def _plot_button_click(self, event):
        """Event wrapper for the plot data button click."""
        plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, *_ = self._check_plot_validity_helper(
            section="user"
        )
        self._plot_button_click_display_choices(
            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, section="user"
        )

    def _ref_plot_button_click(self, event):
        """Event wrapper for the ref plot data button click."""
        plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, *_ = self._check_plot_validity_helper(
            section="ref"
        )
        self._plot_button_click_display_choices(
            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, section="ref"
        )

    def _select_variable_button_click(self, event):
        """Event wrapper for the select variable button click."""
        self._display_plot_choices_ui()

    def _ref_select_variable_button_click(self, event):
        """Event wrapper for the ref select variable button click."""

        self._ref_display_plot_choices_ui()

    def _multiplot_ref_keys_button_click(self, event):
        """Event wrapper for the multiplot select variable button click."""

        self._multiplot_ref_keys_dropdown_click()

    def _multiplot_plot_button_click(self, event):
        """Event wrapper for the multiplot plot data button click."""
        plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, prompt_bounds = (
            self._check_plot_validity_helper(section="multiplot")
        )

        self._plot_button_click_display_choices(
            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, prompt_bounds, section="multiplot"
        )

    def _clear_multiplot_data_button_click(self, event):
        """Event wrapper for the multiplot clear data button click."""

        self._clear_multiplot_data()

    def _multiplot_keys_update_button_click(self, event):
        """Event wrapper for the multiplot update keys button click."""

        self._update_multiplot_dataset()

    def _multiplot_select_variable_button_click(self, event):
        """Event wrapper for the multiplot select variable button click."""

        self._display_multiplot_plot_choices_ui()

    def _prompt_bounds_button_click(self, event):
        """Event wrapper for the prompt bounds button click."""

        self._multiplot_plot_data_button_click()

    def _variable_toggle_click(self, event):
        """Event wrapper for the variable toggle."""

        self.long_names = controller.variable_toggle_change(
            self.variable_toggle, self.plot_variable_dropdown, self.dataset
        )

    def _ref_variable_toggle_click(self, event):
        """Event wrapper for the ref variable toggle."""
        self.ref_long_names = controller.variable_toggle_change(
            self.ref_variable_toggle, self.ref_plot_variable_dropdown, self.ref_dataset
        )

    def _multiplot_variable_toggle_click(self, event):
        """Event wrapper for the multiplot variable toggle."""
        self.multiplot_long_names = controller.variable_toggle_change(
            self.multiplot_variable_toggle, self.multiplot_plot_variable_dropdown, self.dataset
        )

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

        controller.update_textbox_text(
            self.status_textbox,
            "User model status >> Waiting for initial model data catalog to be built. This can take a few minutes.",
        )
        # Display widget_container in notebook
        display(self.widget_container)
        print()

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

        controller.update_textbox_text(
            self.ref_status_textbox, "Reference Model Status >> Select a model to load and plot data"
        )
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
        priority_insert_list = ["ref_model_metadata", "ref_keys_selection_row"]

        # Insert the UI under the first item of this list that exists. If none exist, then append.
        self._safe_add_to_widget(
            self.widget_container, priority_insert_list, self.ref_data_keys_selection_row, append=True
        )

    def _display_multiplot_user_data_selection_ui(self):
        """
        Displays the selection user interface for producing plots that overlay user and reference models. Private
        """

        # Add overlay data status text box
        self.widget_container.append(self.multiplot_status_textbox)
        self.widget_container.append(self.multiplot_warning_textbox)
        controller.update_textbox_text(
            self.multiplot_status_textbox,
            "Overlay Plot >> Choose reference variables to compare with the current plot.",
        )

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
        self.multiplot_plot_variable_dropdown.value = self._get_variable_helper(section="user")
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
        controller.update_textbox_text(self.status_textbox, "User model status >> Loading data.")

        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.keys_dropdown.value)
        self.loaded_dataset_key = self.keys_dropdown.value

        # Update text box
        controller.update_textbox_text(self.status_textbox, "User model status >> Data successfully loaded.")
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
        controller.update_textbox_text(self.status_textbox, "User model status >> Generating plot...")
        fig_animated = None
        fig = None

        # For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.chosen_slices = {}
        if hasattr(self, "slice_widgets"):
            for dim, widget in self.slice_widgets.items():
                self.chosen_slices[dim] = widget.value

        variable = self._get_variable_helper("user")
        # Based on plot type change function that is used
        if self.plot_type_dropdown.value == "Heatmap":
            x_axis = self.x_axis_dropdown.value
            y_axis = self.y_axis_dropdown.value
            fig = self._plot_dataset_helper(is_ref=False, plot_type="Heatmap")
        elif self.plot_type_dropdown.value == "Line":
            fig = self._plot_dataset_helper(is_ref=False)
        elif self.plot_type_dropdown.value == "Animation":
            fig_animated = self._plot_dataset_helper(is_ref=False, plot_type="Animation")
        if fig_animated:
            new_plot_pane = fig_animated
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        plot_group = self._add_remove_btn(new_plot_pane)
        # remove the plot choices row since the plot has been created
        self._safe_remove_widget_object(self.widget_container, "plot_choices_row")
        self._safe_remove_widget_object(self.widget_container, "slice_ui_row")
        self._safe_remove_widget_object(self.widget_container, "slice_widgets")

        appended = self._safe_add_to_widget(
            self.widget_container, ["ref_status_textbox"], plot_group, append=True, above=True
        )
        # Check if the reference UI already exists
        if appended:
            self._display_reference_model_selection_ui()
            self._display_multiplot_user_data_selection_ui()

        controller.update_textbox_text(self.status_textbox, "User model status >> Plot created")

        controller.update_textbox_text(self.warning_textbox, "")

    def _ref_plot_data_button_click(self):
        """
        Triggers plotting of the reference dataset after the plot data button fis clicked
        """

        self.ref_plot_button.name = "Add Plot"
        self.ref_select_variable_button.name = "Add new plot with different variable/ plot type"
        controller.update_textbox_text(self.ref_status_textbox, "Reference model status >> Generating plot...")
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
            variable = self._get_variable_helper("ref")
            fig = self._plot_dataset_helper(is_ref=True, plot_type="Heatmap")
        elif self.ref_plot_type_dropdown.value == "Line":
            fig = self._plot_dataset_helper(is_ref=True)
        elif self.ref_plot_type_dropdown.value == "Animation":
            fig_animated = self._plot_dataset_helper(is_ref=True, plot_type="Animation")

        if fig_animated:
            new_plot_pane = fig_animated
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        plot_group = self._add_remove_btn(new_plot_pane)

        # remove the plot choices row since the plot has been created
        self._safe_remove_widget_object(self.widget_container, "ref_plot_choices_row")
        self._safe_remove_widget_object(self.widget_container, "ref_slice_ui_row")
        self._safe_remove_widget_object(self.widget_container, "ref_slice_widgets")

        # Add plot above the multiplot widgets
        self._safe_add_to_widget(
            self.widget_container, ["multiplot_status_textbox"], plot_group, append=True, above=True
        )
        controller.update_textbox_text(self.ref_status_textbox, "Reference model status >> Plot created")
        controller.update_textbox_text(self.ref_warning_textbox, "")

    def _multiplot_plot_data_button_click(self):
        """
        Triggers the plotting of the overlay data plot once the multiplot plot data button has been pressed. Private
        """

        self.multiplot_plot_button.name = "Select"
        controller.update_textbox_text(self.multiplot_status_textbox, "Plot Overlay Status >> Generating plot...")
        self.multiplot_x_axis_dropdown.name = "Select X-Axis"
        self.multiplot_y_axis_dropdown.name = "Select Y-Axis"
        fig = None
        fig1 = None

        # remove the plot choices row since the plot has been created
        self._safe_remove_widget_object(self.widget_container, "multiplot_plot_choices_row")
        self._safe_remove_widget_object(self.widget_container, "prompt_bounds_row")

        variable = self._get_variable_helper("multiplot")
        # For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.multiplot_chosen_slices = {}
        if hasattr(self, "multiplot_slice_widgets"):
            for dim, widget in self.multiplot_slice_widgets.items():
                self.multiplot_chosen_slices[dim] = widget.value
        # Based on plot type change function that is used
        ui_plot_type = self.multiplot_plot_type_dropdown.value
        helper_plot_type = "Heatmap" if ui_plot_type == "Heatmap (grid)" else "Line"

        # Generate the figures based on the analysis choice
        analysis_choice = self.multiplot_analysis_choice_dropdown.value
        fig, fig1, fig2 = None, None, None

        if analysis_choice == "Plot All Data & Difference":
            fig1 = self._multiplot_plot_dataset_helper(plot_type=helper_plot_type)
            fig2 = self._multiplot_plot_dataset_helper(plot_diff=True, plot_type=helper_plot_type)
        elif analysis_choice == "Plot Difference (Ref. - User data)":
            fig = self._multiplot_plot_dataset_helper(plot_diff=True, plot_type=helper_plot_type)
        else:  # "None (plot all loaded data)"
            fig = self._multiplot_plot_dataset_helper(plot_type=helper_plot_type)

        if fig1:
            pane1 = pn.pane.Matplotlib(fig1, tight=True)
            pane2 = pn.pane.Matplotlib(fig2, tight=True)
            new_plot_pane = pn.Column(pane1, pane2)
        else:
            # Create a new pane for the figure
            new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        plot_group = self._add_remove_btn(new_plot_pane)

        self._safe_remove_widget_object(self.widget_container, "multiplot_slice_ui_row")
        self._safe_remove_widget_object(self.widget_container, "multiplot_slice_widgets")

        self.widget_container.append(plot_group)

        controller.update_textbox_text(self.multiplot_status_textbox, "Overlay plot status >> Plot created")
        controller.update_textbox_text(self.multiplot_warning_textbox, "")

    def _ref_keys_dropdown_click(self):
        """
        Loads selected reference model from ref_keys_dropdown and display reference model dataset selection. Private.
        """

        # Update text box
        controller.update_textbox_text(self.ref_status_textbox, "Reference model status >> Loading data.")

        # Extract selected model catalog
        self.ref_model_cat = self.access_nri_cat.search(name=self.ref_keys_dropdown.value).to_source()

        # Update text box
        controller.update_textbox_text(
            self.ref_status_textbox, "Reference model status >> Data catalog successfully loaded."
        )

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

        controller.update_textbox_text(self.multiplot_warning_textbox, "")

        selected_ref_model_cat = self.access_nri_cat.search(name=self.multiplot_ref_keys_dropdown.value).to_source()

        if (
            self.multiplot_keys_dropdown.value in list(selected_ref_model_cat.keys())
            and not self.multiplot_ref_keys_dropdown.value in self.multiplot_ref_dataset_dict
        ):
            model_value = self.multiplot_ref_keys_dropdown.value
            controller.update_textbox_text(
                self.multiplot_status_textbox, "Overlay Plot Status >> Loading reference dataset..."
            )
            self.multiplot_ref_dataset_dict = controller.add_to_dataset_dict(
                self.multiplot_ref_dataset_dict,
                model_value,
                selected_ref_model_cat,
                self.multiplot_keys_dropdown.value,
                self.dataset,
            )
            controller.update_textbox_text(
                self.multiplot_status_textbox,
                "Overlay Plot Status >> Loaded reference model, add another or plot the overlay",
            )
        elif self.multiplot_ref_keys_dropdown.value in self.multiplot_ref_dataset_dict:
            controller.update_textbox_text(
                self.multiplot_warning_textbox, "Warning >> Model has already been added, skipping duplicate"
            )
        else:
            controller.update_textbox_text(
                self.multiplot_warning_textbox,
                "Overlay Plot Status >> There is no dataset matching the user dataset in this model, please select another",
            )

        if self.multiplot_keys_dropdown.value != self.loaded_dataset_key:
            controller.update_textbox_text(
                self.multiplot_status_textbox,
                "Overlay Plot Status >> User dataset selection changed, reloading user dataset...",
            )
            # Load selected dataset
            self.dataset = data._build_data_object(self.model_cat, self.multiplot_keys_dropdown.value)
            self.loaded_dataset_key = self.multiplot_keys_dropdown.value
            self.multiplot_plot_variable_dropdown.options = sorted(list(self.dataset.keys()))

            controller.update_textbox_text(
                self.multiplot_status_textbox,
                "Overlay Plot Status >> New user dataset loaded, clearing loaded user models",
            )
            self._clear_multiplot_data()

    def _ref_dataset_dropdown_click(self):
        """
        Loads selected reference model dataset from ref_data_keys_dropdown and creates new interactive plot. Private.
        """
        controller.update_textbox_text(
            self.ref_status_textbox, "Reference model status >> Loading reference dataset..."
        )
        # Load selected access_nri catalog dataset
        self.ref_dataset = data._build_data_object(self.ref_model_cat, self.ref_data_keys_dropdown.value)
        controller.update_textbox_text(
            self.ref_status_textbox, "Reference model status >> Reference dataset successfully loaded."
        )
        # Check if plot already exists
        if not self.ref_figure_exists:
            # Display ref plot ui
            self._ref_display_dataset_plot_ui()

        elif self.ref_figure_exists:
            # Update existing plot ui
            self.ref_plot_variable_dropdown.options = sorted(list(self.ref_dataset.keys()))

    def _ref_clear_data_click(self):
        """
        Clears and 'unloads' selected reference model dataset from widget container. Private.
        """

        # Update text box
        controller.update_textbox_text(self.ref_status_textbox, "Reference model status >> Data removed.")

        ui_components_to_remove = [
            "ref_data_keys_selection_row",
            "ref_plot_ui_row",
            "ref_plot_choices_row",
            "ref_slice_ui_row",
        ]

        # Remove all generated reference UI rows from the layout
        for attr in ui_components_to_remove:
            self._safe_remove_widget_object(self.widget_container, attr)

        # Clear the metadata text
        self.ref_model_metadata.value = ""

        # Remove reference data attributes
        self._safe_remove_widget_object(self.widget_container, "ref_model_cat")
        self._safe_remove_widget_object(self.widget_container, "ref_dataset")

        self.ref_figure_exists = False

    def _ref_model_info_click(self):
        """
        Create string from the selected model metadata, and update the reference status text with that string. Private.
        """
        # Update text box
        controller.update_textbox_text(self.ref_status_textbox, "Reference model status >> Retrieving model metadata.")
        # Generate the metadata string
        self.ref_model_metadata.value = controller.get_metadata(
            self.access_nri_cat[self.ref_keys_dropdown.value].metadata
        )
        # Update text box
        controller.update_textbox_text(self.ref_status_textbox, "")

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
        self._safe_add_to_widget(
            self.widget_container, ["ref_data_keys_selection_row"], self.ref_plot_ui_row, append=True
        )

    def _display_plot_choices_ui(self):
        """
        Create interactive panel plot for user to choose plot options and add to widget_container. Private.
        """
        # Remove preexisting plot choices UI
        self._safe_remove_widget_object(self.widget_container, "plot_choices_row")

        variable = self._get_variable_helper("user")

        # Find viable dimensions for axis selection
        dim_sizes = self.dataset[variable].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        self.x_axis_dropdown.name = "Select X-Axis dimension"
        self.x_axis_dropdown.options = sorted(viable_dims)
        show_plot_choices = True
        self.plot_button.name = "Plot data"

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.plot_type_dropdown.value == "Heatmap":
            # Check if enough dimensions to make heatmap, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                controller.update_textbox_text(
                    self.warning_textbox,
                    "Warning >> Not enough dimensions available for this variable to plot a Heatmap.",
                )
                self.plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.y_axis_dropdown.name = "Select Y-Axis dimension"
                self.y_axis_dropdown.options = sorted(viable_dims)
                self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.y_axis_dropdown, self.plot_button)
        elif self.plot_type_dropdown.value == "Line":
            # If there is only 1 viable x-axis, plot automatically without user prompt to select x-axis.
            if len(viable_dims) == 1:
                controller.update_textbox_text(
                    self.warning_textbox, "Only one valid x-axis dimension, plotting automatically."
                )
                self.x_axis_dropdown.value = viable_dims[0]
                show_plot_choices = False
                self._plot_data_button_click()
            else:
                self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.plot_button)
        elif self.plot_type_dropdown.value == "Animation":
            # Check if enough dimensions to make animation, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                controller.update_textbox_text(
                    self.warning_textbox,
                    "Warning >> Not enough dimensions available for this variable to plot an animation.",
                )
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
            self._safe_add_to_widget(
                self.widget_container,
                ["plot_ui_row"],
                self.plot_choices_row,
                append=True,
                above=False,
            )

    def _ref_display_plot_choices_ui(self):
        """
        Create interactive panel for user to choose plot options and add to widget_container. Private.
        """

        # Remove preexisting plot choices UI
        self._safe_remove_widget_object(self.widget_container, "ref_plot_choices_row")

        variable = self._get_variable_helper("ref")
        # Find viable dimensions for axis selection
        dim_sizes = self.ref_dataset[variable].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"]

        self.ref_x_axis_dropdown.name = "Select X-Axis dimension"
        self.ref_x_axis_dropdown.options = sorted(viable_dims)
        show_plot_choices = True
        self.ref_plot_button.name = "Plot data"

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.ref_plot_type_dropdown.value == "Heatmap":
            # Check if enough dimensions to make heatmap, if not, throw warning and don't let the user do it.
            if len(viable_dims) < 2:
                controller.update_textbox_text(
                    self.ref_warning_textbox,
                    "Warning >> Not enough dimensions available for this variable to plot a Heatmap.",
                )
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
                controller.update_textbox_text(
                    self.ref_warning_textbox, "Only one valid x-axis dimension, plotting automatically."
                )
                self.ref_x_axis_dropdown.value = viable_dims[0]
                self._ref_plot_data_button_click()
            else:
                self.ref_plot_choices_row = pn.Row(self.ref_x_axis_dropdown, self.ref_plot_button)
        elif self.ref_plot_type_dropdown.value == "Animation":
            # Check if enough dimensions to make animation, if not, throw error and don't let the user do it.
            if len(viable_dims) < 2:
                controller.update_textbox_text(
                    self.ref_warning_textbox,
                    "Warning >> Not enough dimensions available for this variable to plot an animation.",
                )
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
            self._safe_add_to_widget(
                self.widget_container, ["ref_plot_ui_row"], self.ref_plot_choices_row, append=True, above=False
            )

    def _display_multiplot_plot_choices_ui(self):
        """
        Generate and display the UI components for selecting the multiplot x-axis. Private.
        """
        # Find viable dimensions for axis selection
        dim_sizes = self.dataset[self._get_variable_helper("multiplot")].sizes
        viable_dims = sorted([dim for dim, size in dim_sizes.items() if size > 1 and dim != "nv"])

        self.multiplot_x_axis_dropdown.name = "Select X-Axis dimension"
        self.multiplot_x_axis_dropdown.options = viable_dims
        self.multiplot_analysis_choice_dropdown.name = "Select analysis type"
        self.multiplot_analysis_choice_dropdown.options = [
            "None (plot all loaded data)",
            "Plot Difference (Ref. - User data)",
            "Plot All Data & Difference",
        ]
        self.multiplot_plot_button.name = "Plot data"

        plot_type = self.multiplot_plot_type_dropdown.value

        # If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if plot_type == "Heatmap (grid)":
            if len(viable_dims) < 2:
                controller.update_textbox_text(
                    self.multiplot_warning_textbox,
                    "Warning >> Not enough dimensions available for this variable to plot a Heatmap.",
                )
                self.multiplot_plot_type_dropdown.value = "Line"
                return  # Stop generating the heatmap UI; the dropdown change will trigger a new callback

            self.multiplot_y_axis_dropdown.name = "Select Y-Axis dimension"
            self.multiplot_y_axis_dropdown.options = viable_dims
            self.multiplot_plot_choices_row = pn.Row(
                self.multiplot_x_axis_dropdown,
                self.multiplot_y_axis_dropdown,
                self.multiplot_analysis_choice_dropdown,
                self.multiplot_plot_button,
            )
        elif plot_type == "Line":
            if len(viable_dims) == 1:
                self.multiplot_x_axis_dropdown.value = viable_dims[0]

            x_axis = self.multiplot_x_axis_dropdown.value

            # Check bounds safely
            needs_bounds_ui, self.global_min, self.global_max, self.dataset_min, self.dataset_max = (
                controller.check_bounds(self.dataset, x_axis, self.multiplot_ref_dataset_dict)
            )

            if len(viable_dims) == 1 and needs_bounds_ui:
                self._prompt_bounds_ui()
                return  # Stop generating the plot choices UI, wait for user bounds input

            # Build the UI Row dynamically (omit X-axis dropdown if there is only 1 option)
            row_widgets = [self.multiplot_analysis_choice_dropdown, self.multiplot_plot_button]
            if len(viable_dims) > 1:
                row_widgets.insert(0, self.multiplot_x_axis_dropdown)

            self.multiplot_plot_choices_row = pn.Row(*row_widgets)

        self._safe_add_to_widget(
            self.widget_container, ["multiplot_type_selection_row"], self.multiplot_plot_choices_row, append=True
        )

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

    def _clear_multiplot_data(self):
        """
        Clears the reference datasets which have been loaded. Private
        """

        self.multiplot_ref_dataset_dict = {}
        controller.update_textbox_text(
            self.multiplot_status_textbox, "Overlay Plot Status >> Cleared loaded reference models"
        )

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
        priority_list = [
            "multiplot_slice_ui_row",
            "multiplot_plot_choices_row",
            "multiplot_type_selection_row",
            "multiplot_ref_keys_selection_row",
        ]

        # Insert the slice UI below the plot choices row
        self._safe_add_to_widget(self.widget_container, priority_list, self.prompt_bounds_row, append=True)

    def _update_multiplot_dataset(self):
        """
        Load a new user dataset based on the current dropdown selection and update UI components. Private.
        """

        controller.update_textbox_text(
            self.multiplot_status_textbox, "Overlay Plot Status >> Loading new user dataset..."
        )
        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.multiplot_keys_dropdown.value)
        self.loaded_dataset_key = self.multiplot_keys_dropdown.value
        self.multiplot_plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
        self.keys_dropdown.value = self.loaded_dataset_key
        self.plot_variable_dropdown.options = sorted(list(self.dataset.keys()))
        controller.update_textbox_text(
            self.multiplot_status_textbox, "Overlay Plot Status >> New user dataset loaded, clearing loaded user models"
        )
        # Clear the loaded data, as different datasets from the selected models will need to be loaded.
        self._clear_multiplot_data()

    def _plot_dataset_helper(self, is_ref=False, plot_type="Line"):
        """
        Plot either the user or reference dataset based on the current UI state.

        Parameters
        ----------
        is_ref : bool, optional
            Whether to plot the reference dataset (True) or the user dataset (False).
            Defaults to False.
        is_multiplot : bool, optional
            Whether the plot is part of a multiplot view. Defaults to False.

        Returns
        -------
        matplotlib.figure.Figure
            The generated Matplotlib figure instance.
        """

        if is_ref:
            variable = self._get_variable_helper("ref")

            if plot_type == "Animation":
                y_axis = self.ref_y_axis_dropdown.value
                z_axis = self.ref_animation_axis_dropdown.value
                figure = controller.plot_animation(
                    self.ref_dataset,
                    self.ref_keys_dropdown.value,
                    variable,
                    self.ref_chosen_slices,
                    self.ref_x_axis_dropdown.value,
                    y_axis,
                    z_axis,
                    is_ref=True,
                )
            else:
                # Handles both Line (y_axis=None) and Heatmap (y_axis=value)
                y_axis = self.ref_y_axis_dropdown.value if plot_type == "Heatmap" else None
                figure = controller.plot_dataset(
                    self.ref_dataset,
                    self.ref_data_keys_dropdown.value,
                    variable,
                    self.ref_x_axis_dropdown.value,
                    self.ref_chosen_slices,
                    is_ref,
                    self.ref_keys_dropdown.value,
                    plot_type=plot_type,
                    y_axis=y_axis,
                )

            self.ref_figure_exists = True
            self.ref_fig = figure

        else:
            variable = self._get_variable_helper("user")

            if plot_type == "Animation":
                y_axis = self.y_axis_dropdown.value
                z_axis = self.animation_axis_dropdown.value
                figure = controller.plot_animation(
                    self.dataset,
                    self.keys_dropdown.value,
                    variable,
                    self.chosen_slices,
                    self.x_axis_dropdown.value,
                    y_axis,
                    z_axis,
                    is_ref=False,
                )
            else:
                # Handles both Line and Heatmap
                y_axis = self.y_axis_dropdown.value if plot_type == "Heatmap" else None
                figure = controller.plot_dataset(
                    self.dataset,
                    self.keys_dropdown.value,
                    variable,
                    self.x_axis_dropdown.value,
                    self.chosen_slices,
                    is_ref,
                    plot_type=plot_type,
                    y_axis=y_axis,
                )

            self.figure_exists = True
            self.fig = figure

        return figure

    def _get_variable_helper(self, section="user"):
        """
        Retrieve the selected dataset variable key for the specified UI section.

        Parameters
        ----------
        section : str, optional
            The section of the UI to query. Valid options are "user", "ref", or
            "multiplot". Defaults to "user".

        Returns
        -------
        str
            The resolved internal dataset variable key.
        """

        if section == "ref":
            return controller.get_selected_variable(
                self.ref_variable_toggle, self.ref_plot_variable_dropdown, self.ref_long_names
            )
        elif section == "multiplot":
            return controller.get_selected_variable(
                self.multiplot_variable_toggle, self.multiplot_plot_variable_dropdown, self.multiplot_long_names
            )
        else:
            return controller.get_selected_variable(self.variable_toggle, self.plot_variable_dropdown, self.long_names)

    def _safe_remove_widget_object(self, widget_container, item_to_remove):
        """
        Safely remove a widget from a container and delete its corresponding attribute.

        Checks if the UI instance possesses the specified attribute. If it does,
        removes the component from the provided widget container and deletes the
        attribute from the class instance to reset the state.

        Parameters
        ----------
        widget_container : panel.layout.Panel or list
            The UI container from which the widget should be removed.
        item_to_remove : str
            The string name of the attribute to remove and delete.
        """

        if hasattr(self, item_to_remove):
            component = getattr(self, item_to_remove)
            if component in widget_container:
                widget_container.remove(component)

            delattr(self, item_to_remove)

    def _safe_add_to_widget(self, widget_container, target_attributes, item_to_add, append=False, above=False):
        """
        Insert a UI component into a container relative to the first matching target attribute.

        Iterates through a prioritised list of target attribute strings. Upon finding the
        first target that exists and is currently rendered in the container, it inserts the
        new item either directly above or below it.

        Parameters
        ----------
        widget_container : panel.layout.Panel or list
            The UI container to modify.
        target_attributes : list of str
            A prioritised list of attribute names to search for within the container.
        item_to_add : object
            The Panel UI component to insert into the container.
        append : bool, optional
            If True, appends the new item to the end of the container if none of the
            target attributes are found. Defaults to False.
        above : bool, optional
            If True, inserts the new item directly above the found target. If False,
            inserts it directly below. Defaults to False.

        Returns
        -------
        bool
            True if the item was appended to the bottom (meaning no targets were found
            but append was True), False otherwise.
        """

        for attr_name in target_attributes:
            target = getattr(self, attr_name, None)

            # If the attribute exists and is currently rendered on screen
            if target is not None and target in widget_container:
                insert_index = widget_container.index(target)
                if above:
                    insert_index -= 1
                else:
                    insert_index += 1
                widget_container.insert(insert_index, item_to_add)
                return False  # Item was successfully inserted

        # If it found none of the targets, append to the bottom
        if append:
            widget_container.append(item_to_add)
            return True

        return False

    def _check_slice(self, section="user"):
        """
        Check if the plot requires dimensions to be sliced and generate the slicing UI. Private.

        Dynamically inspects the remaining unselected dimensions for the specified section,
        creates discrete slider widgets for coordinate selection, groups them into a row,
        and inserts the row into the widget container below the plot choices. It also updates
        the section's plot button label and status text to prompt the user.

        Parameters
        ----------
        section : str, optional
            The UI section being evaluated. Valid options are "user", "ref", or
            "multiplot". Defaults to "user".
        """

        if section == "multiplot":
            remaining_dims = self.multiplot_remaining_dims
            dataset = self.dataset
        elif section == "ref":
            remaining_dims = self.ref_remaining_dims
            dataset = self.ref_dataset
        elif section == "user":
            remaining_dims = self.remaining_dims
            dataset = self.dataset

        # Filter dimensions to get the remaining dimensions not selected as the axes
        ui_components = []
        slice_widgets = {}

        # for each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in remaining_dims:
            # Extract coordinate values as options
            coord_values = list(dataset[dimension].values)
            options_dict = {controller.round_slice_val(val): val for val in coord_values}
            dropdown = pn.widgets.DiscreteSlider(name=f"Slice {dimension} at:", options=options_dict)

            slice_widgets[dimension] = dropdown
            ui_components.append(dropdown)

        # Group them into a row
        slice_ui_row = pn.Row(*ui_components)

        if section == "multiplot":
            self.multiplot_slice_widgets = slice_widgets
            self.multiplot_slice_ui_row = slice_ui_row
            position = ["multiplot_plot_choices_row"]
            button = self.multiplot_plot_button
            textbox = self.multiplot_status_textbox
            status_prefix = "Overlay Plot"
        elif section == "ref":
            self.ref_slice_widgets = slice_widgets
            self.ref_slice_ui_row = slice_ui_row
            position = ["ref_plot_choices_row"]
            button = self.ref_plot_button
            textbox = self.ref_status_textbox
            status_prefix = "Reference model status"
        elif section == "user":
            self.slice_widgets = slice_widgets
            self.slice_ui_row = slice_ui_row
            position = ["plot_choices_row"]
            button = self.plot_button
            textbox = self.status_textbox
            status_prefix = "User model status"

        # Insert the slice UI below the plot choices row
        self._safe_add_to_widget(self.widget_container, position, slice_ui_row, append=True)

        # Update the UI text to prompt the user
        button.name = "Confirm Slices & Plot"
        controller.update_textbox_text(
            textbox, f"{status_prefix} >> Action required: Select slice values and click plot again."
        )

    def _check_plot_validity_helper(self, section="user"):
        """
        Gather section-specific widget configurations and delegate plot validation to the controller.

        Inspects the dropdown values and active datasets for the specified UI section,
        evaluates slice widget states, and coordinates layout cleanups if dataset dimensions
        or slice requirements have changed.

        Parameters
        ----------
        section : str, optional
            The UI section being evaluated. Valid options are "user", "ref", or
            "multiplot". Defaults to "user".

        Returns
        -------
        tuple of (bool, bool, bool, bool)
            A 4-tuple containing:
            - plot_valid : bool
              True if the configuration is valid and ready to plot.
            - requires_slice : bool
              True if unplotted dimensions require slicing.
            - invalid_heatmap_data : bool
              True if the chosen plot type lacks sufficient viable dimensions or axes.
            - same_axes_chosen : bool
              True if identical axes were selected.
        """
        prompt_bounds = False
        if section == "ref":
            dataset = self.ref_dataset
            plot_type = self.ref_plot_type_dropdown.value
            x = self.ref_x_axis_dropdown.value
            y = self.ref_y_axis_dropdown.value
            z = self.ref_animation_axis_dropdown.value
            widget_attr, row_attr = "ref_slice_widgets", "ref_slice_ui_row"
        elif section == "multiplot":
            dataset = self.dataset
            plot_type = self.multiplot_plot_type_dropdown.value
            x = self.multiplot_x_axis_dropdown.value
            y = self.multiplot_y_axis_dropdown.value
            z = None
            widget_attr, row_attr = "multiplot_slice_widgets", "multiplot_slice_ui_row"
            # ONLY check bounds if it's a Line plot!
            if plot_type == "Line":
                prompt_bounds, self.global_min, self.global_max, self.dataset_min, self.dataset_max = (
                    controller.check_bounds(
                        self.dataset, self.multiplot_x_axis_dropdown.value, self.multiplot_ref_dataset_dict
                    )
                )
            else:
                prompt_bounds = False
        else:
            dataset = self.dataset
            plot_type = self.plot_type_dropdown.value
            x = self.x_axis_dropdown.value
            y = self.y_axis_dropdown.value
            z = self.animation_axis_dropdown.value
            widget_attr, row_attr = "slice_widgets", "slice_ui_row"

        variable = self._get_variable_helper(section)
        has_slice_widgets = hasattr(self, widget_attr)
        existing_keys = list(getattr(self, widget_attr).keys()) if has_slice_widgets else []

        plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, remaining_dims = (
            controller.check_plot_validity(
                dataset=dataset,
                variable=variable,
                plot_type=plot_type,
                x=x,
                y=y,
                z=z,
                has_slice_widgets=has_slice_widgets,
            )
        )

        # Handle UI cleanup if slice requirements changed
        if has_slice_widgets and existing_keys != remaining_dims:
            self._safe_remove_widget_object(self.widget_container, row_attr)
            self._safe_remove_widget_object(self.widget_container, widget_attr)
            # Re-evaluate with no slice widgets now that they are cleared
            plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, remaining_dims = (
                controller.check_plot_validity(
                    dataset=dataset, variable=variable, plot_type=plot_type, x=x, y=y, z=z, has_slice_widgets=False
                )
            )

        # Save remaining dims back to the correct attribute on self
        if section == "ref":
            self.ref_remaining_dims = remaining_dims
        elif section == "multiplot":
            self.multiplot_remaining_dims = remaining_dims
            if prompt_bounds:
                plot_valid = False
        else:
            self.remaining_dims = remaining_dims

        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, prompt_bounds

    def _plot_button_click_display_choices(
        self, plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen, prompt_bounds=False, section="user"
    ):
        """
        Handle UI state transitions and displays based on plot validation results.
        """
        # Map section strings to the correct instance attributes
        if section == "ref":
            warning_box = self.ref_warning_textbox
            plot_type_dd = self.ref_plot_type_dropdown
            choices_row = "ref_plot_choices_row"
            slice_row = "ref_slice_ui_row"
            slice_widgets_attr = "ref_slice_widgets"
            plot_action = self._ref_plot_data_button_click
            display_choices = self._ref_display_plot_choices_ui  # or whatever your ref plot choices method is called
            self.chosen_slices = {}  # or ref_chosen_slices if separated
        elif section == "multiplot":
            warning_box = self.multiplot_warning_textbox
            plot_type_dd = self.multiplot_plot_type_dropdown
            choices_row = "multiplot_plot_choices_row"
            slice_row = "multiplot_slice_ui_row"
            slice_widgets_attr = "multiplot_slice_widgets"
            plot_action = self._multiplot_plot_data_button_click
            display_choices = self._display_multiplot_plot_choices_ui
            self.chosen_slices = {}
        else:
            warning_box = self.warning_textbox
            plot_type_dd = self.plot_type_dropdown
            choices_row = "plot_choices_row"
            slice_row = "slice_ui_row"
            slice_widgets_attr = "slice_widgets"
            plot_action = self._plot_data_button_click
            display_choices = self._display_plot_choices_ui
            self.chosen_slices = {}

        if plot_valid:
            plot_action()
        elif requires_slice:
            self._check_slice(section=section)
        elif invalid_heatmap_data:
            controller.update_textbox_text(
                warning_box,
                "Warning >> The dataset only has one plottable dimension. Defaulting to line plot.",
            )
            plot_type_dd.value = "Line"
            if not section == "multiplot":
                plot_action()
        elif same_axes_chosen:
            controller.update_textbox_text(
                warning_box, "Warning >> Please ensure different values are selected for each axis."
            )

            # Remove preexisting plot choices UI using strings
            self._safe_remove_widget_object(self.widget_container, choices_row)
            self._safe_remove_widget_object(self.widget_container, slice_row)
            self._safe_remove_widget_object(self.widget_container, slice_widgets_attr)

            display_choices()

        elif prompt_bounds:
            self._prompt_bounds_ui()

    def _add_remove_btn(self, plot_pane):

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(**self.STYLES.get("remove_button"))
        remove_btn.name = "Remove Plot"
        # Group the plot and the button together
        plot_group = pn.Column(plot_pane, remove_btn, margin=(0, 0, 25, 0))

        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)

        remove_btn.on_click(_remove_this_plot)

        return plot_group

    def _multiplot_plot_dataset_helper(self, plot_diff=False, plot_type="Line"):            
        variable = self._get_variable_helper(section="multiplot")
        x_axis = self.multiplot_x_axis_dropdown.value

        # Plot directly, passing plot_diff dynamically
        if plot_type == "Line":
            _, self.global_min, self.global_max, self.dataset_min, self.dataset_max = controller.check_bounds(
                self.dataset, x_axis, self.multiplot_ref_dataset_dict
            )

            # Set x_min and x_max using the newly unpacked variables
            if self.prompt_bounds_dropdown.value == "Constrain to user dataset bounds":
                x_min = self.dataset_min
                x_max = self.dataset_max
            else:
                x_min = self.global_min  
                x_max = self.global_max 
            return controller.plot_multiplot_dataset(
                self.dataset,
                variable,
                self.multiplot_ref_dataset_dict,
                self.multiplot_chosen_slices,
                x_axis,
                x_min,
                x_max,
                plot_diff=plot_diff
            )
        else:
            return controller.plot_multiplot_heatmap_dataset(
                self.dataset,
                variable,
                self.multiplot_chosen_slices,
                x_axis,
                self.multiplot_y_axis_dropdown.value,
                plot_diff=plot_diff
            )
