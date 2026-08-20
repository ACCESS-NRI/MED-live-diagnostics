# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" UI class and functions """


import panel as pn
import matplotlib.pyplot as plt
import datetime

from med_diagnostics import data
from IPython.display import display

class UserInterface():
    
    """
    Primary class for user interface (UI) components and deployment
    """
    
    def __init__(self):
        
        """
        Initialise a UserInterface instance.
        """

        # Import panel extensions
        pn.extension()
        
        # Build and style panel widgets
        self.last_data_load_textbox = pn.widgets.StaticText(styles={'background': 'orange', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.warning_textbox = pn.widgets.StaticText(styles={'background': 'darkred', 'font-size': '18px', 'color': 'white', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.ref_status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.ref_warning_textbox = pn.widgets.StaticText(styles={'background': 'darkred', 'font-size': '18px', 'color': 'white', 'padding': '5px'}, margin=(10, 0, 10, 0))

        self.ref_model_metadata = pn.widgets.StaticText(styles={'color': 'white'})
        
        self.keys_dropdown = pn.widgets.Select()
        self.keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.plot_variable_dropdown = pn.widgets.Select()

        self.ref_keys_dropdown = pn.widgets.Select()
        self.ref_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        
        
        self.ref_data_keys_dropdown = pn.widgets.Select()
        self.ref_data_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.ref_plot_variable_dropdown = pn.widgets.Select()

        self.clear_ref_model_data_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 10))
        self.ref_model_info_button = pn.widgets.Button(styles={}, margin=(23, 10, 0, 0))

        self.plot_button = pn.widgets.Button(name='Plot Data', button_type='success', margin=(23, 0, 0, 10))
        self.plot_pane = pn.pane.Matplotlib(tight=True)

        self.ref_plot_button = pn.widgets.Button(name='Plot Reference', button_type='success', margin=(23, 0, 0, 10))
        self.ref_plot_pane = pn.pane.Matplotlib(tight=True)
                
        self.figure_exists = False
        self.ref_figure_exists = False

        #Additions for selecting plot type
        self.plot_type_dropdown = pn.widgets.Select()
        self.x_axis_dropdown = pn.widgets.Select()
        self.y_axis_dropdown = pn.widgets.Select()
        self.select_variable_button = pn.widgets.Button(name='Select Variable and Plot Type', button_type = "primary", margin=(23, 0, 0, 10))
        self.ref_plot_type_dropdown = pn.widgets.Select()
        self.ref_x_axis_dropdown = pn.widgets.Select()
        self.ref_y_axis_dropdown = pn.widgets.Select()
        self.ref_select_variable_button = pn.widgets.Button(name='Select Variable and Plot Type', button_type = "primary", margin=(23, 0, 0, 10))
        
        #Additions for plotting user data with reference model data
        self.multiplot_status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.multiplot_user_keys_dropdown = pn.widgets.Select()
        self.multiplot_user_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.multiplot_add_variable_dropdown = pn.widgets.Select()
        self.multiplot_select_user_variable_button = pn.widgets.Button(name='Select Variable', button_type = "primary", margin=(23, 0, 0, 10))

        self.multiplot_ref_keys_dropdown = pn.widgets.Select()
        self.multiplot_ref_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.multiplot_ref_plot_variable_dropdown = pn.widgets.Select()
        self.multiplot_select_ref_variable_button = pn.widgets.Button(name='Select Variable', button_type = "primary", margin=(23, 0, 0, 10))

        self.multiplot_plot_button = pn.widgets.Button(name='Plot Loaded Datasets (Overlayed)', button_type='success', margin=(23, 0, 0, 10))
        self.multiplot_plot_pane = pn.pane.Matplotlib(tight=True)
        self.clear_multiplot_data_button = pn.widgets.Button(name='Clear loaded data', button_type='danger', margin=(23, 0, 0, 10))
        self.multiplot_warning_textbox = pn.widgets.StaticText(styles={'background': 'darkred', 'font-size': '18px', 'color': 'white', 'padding': '5px'}, margin=(10, 0, 10, 0))
        
        # Initialise button listener functions
        @pn.depends(self.keys_dropdown.param.value)
        def _keys_button_click(event):
            
            self._keys_dropdown_click()

        #@pn.depends(self.plot_type_dropdown.param.value)
        #def _keys_button_click(event):
                    
            #self._plot_type_dropdown_click()
            
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
                self._update_warning_text("Warning >> Please select different values for the x and y axes")

                #Remove preexisting plot choices UI
                if hasattr(self, 'plot_choices_row') and self.plot_choices_row in self.widget_container:
                    self.widget_container.remove(self.plot_choices_row)
                if hasattr(self, 'slice_ui_row') and self.slice_ui_row in self.widget_container:
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
                self._update_ref_warning_text("Warning >> Please select different values for the x and y axes")
                if hasattr(self, 'ref_plot_choices_row') and self.ref_plot_choices_row in self.widget_container:
                    self.widget_container.remove(self.ref_plot_choices_row)
                if hasattr(self, 'ref_slice_ui_row') and self.ref_slice_ui_row in self.widget_container:
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
            #something
            print("To implement")
        
        def _clear_multiplot_data_button_click(event):
            #Clear overlay dictionary
            print("To implement")


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
        self.div_1 = pn.layout.Divider(styles={'color': 'white'}, visible=False)
        self.keys_selection_row = pn.Row(self.keys_dropdown, self.keys_button, visible=False)
        self.div_2 = pn.layout.Divider(styles={'color': 'white'}, visible=False)
        
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
        Update text displayed in _status_textbox widget. Private.
        
        Parameters
        ----------
        text : str
            Text to be displayed in ref_status_textbox
        """

        # Update ref_status_textbox with text
        self.multiplot_status_textbox.value = str(text)

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
        self.keys_dropdown.name = '1. Please select a dataset to monitor:'
        self.keys_dropdown.options = list(self.model_cat.keys())
        self.keys_button.name = 'Load dataset'
        self.keys_button.button_type = 'primary'
        
        # Unhide the widgets via property updates rather than structural appends
        self.div_1.visible = True
        self.keys_selection_row.visible = True
        self.div_2.visible = True
        
    def _display_reference_model_selection_ui(self):
        
        """
        Label, populate and append ACCESS reference model selection-related widgets to widget_container. Private.
        
        """

        # Add refrence data status text box
        self.widget_container.append(self.ref_status_textbox)
        self.widget_container.append(self.ref_warning_textbox)
        
        # Populate reference/comparison model widgets
        self.ref_keys_dropdown.name = '2. Select reference model (optional):'
        self.ref_keys_dropdown.options = self.access_nri_cat.keys()
        self.ref_keys_button.name = 'Load reference model'
        self.ref_keys_button.button_type = 'primary'
        
        self.clear_ref_model_data_button.name = 'Clear reference model'
        self.clear_ref_model_data_button.button_type = 'primary'

        self.ref_model_info_button.name = 'Reference model information'
        self.ref_model_info_button.button_type = 'primary'
        
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
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))

    def _display_multiplot_user_data_selection_ui(self):

        """
        Comment.

        """
        # Add overlay data status text box
        self.widget_container.append(self.multiplot_status_textbox)
        self.widget_container.append(self.multiplot_warning_textbox)
        self._update_multiplot_status_text("Overlay Plot >> Choose reference variables to compare with the current plot.")

        # Populate reference/comparison model widgets
        self.multiplot_ref_keys_dropdown.name = '3. Select one or more reference models to overlay (optional):'
        self.multiplot_ref_keys_dropdown.options = self.access_nri_cat.keys()
        self.multiplot_ref_keys_button.name = 'Add reference model'
        self.multiplot_ref_keys_button.button_type = 'primary'
        
        # Add reference/comparison widgets to ref_keys_selection_row
        self.multiplot_ref_keys_selection_row = pn.Row()
        self.multiplot_ref_keys_selection_row.append(self.multiplot_ref_keys_dropdown)
        self.multiplot_ref_keys_selection_row.append(self.multiplot_ref_keys_button)
        
        # Add ref_keys_selection_row to widget_container
        self.widget_container.append(self.multiplot_ref_keys_selection_row)
        
        # Add horizontal line divider to widget_container
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
    def _display_reference_dataset_selection_ui(self):
        
        """
        Label, populate and append ACCESS reference dataset selection-related widgets to widget_container. Private.
        
        """
        self._update_ref_status_text("Reference Model Status >> Select a model to load and plot data")
        # Populate reference/comparison dataset widgets
        self.ref_data_keys_dropdown.name = '2.1. Select reference dataset (optional):'
        self.ref_data_keys_dropdown.options = self.ref_model_cat.keys()
        self.ref_data_keys_button.name = 'Load reference dataset'
        self.ref_data_keys_button.button_type = 'primary'
        
        # Add reference/comparison widgets to ref_data_keys_selection_row
        self.ref_data_keys_selection_row = pn.Row()
        self.ref_data_keys_selection_row.append(self.ref_data_keys_dropdown)
        self.ref_data_keys_selection_row.append(self.ref_data_keys_button)
        
        # Add ref_data_keys_selection_row to widget_container
        self.widget_container.append(self.ref_data_keys_selection_row)
        
        # Add horizontal line divider to widget_container
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
    def _keys_dropdown_click(self):
        
        """
        Loads selected model dataset from keys_dropdown and creates new interactive plot. Private.
        """
        # Update text box
        self._update_status_text('User model status >> Loading data.')

        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.keys_dropdown.value)
        
        # Update text box
        self._update_status_text('User model status >> Data successfully loaded.')
        self.keys_button.name = "Load different dataset"

        # Check if plot already exists
        if self.figure_exists == False:
            
            self.figure_exists = True
            # Create new plot
            self._display_dataset_plot_ui()

        elif self.figure_exists == True:

            # Update existing plot
            self._update_dataset_plot_ui()

    def _plot_data_button_click(self):
        
        self._update_warning_text("")
        self.plot_button.name = "Add Plot"    
        self.select_variable_button.name = "Add new plot with different variable/ plot type"    
        self._update_status_text('User model status >> Generating plot...')

        #For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.chosen_slices = {}
        if hasattr(self, 'slice_widgets'):
            for dim, widget in self.slice_widgets.items():
                self.chosen_slices[dim] = widget.value

        # Based on plot type change function that is used
        if self.plot_type_dropdown.value == "Heatmap":
            x_axis = self.x_axis_dropdown.value
            y_axis = self.y_axis_dropdown.value
            fig = self._plot_heatmap(self.plot_variable_dropdown.value, x_axis, y_axis)
        elif self.plot_type_dropdown.value == "Line":
            x_axis = self.x_axis_dropdown.value
            fig = self._plot_dataset(self.plot_variable_dropdown.value, x_axis)
        
        # Create a new pane for the figure
        new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(name='Remove the above plot', button_type='danger', margin=(23, 0, 0, 10))
        
        # Group the plot and the button together
        plot_group = pn.Column(new_plot_pane, remove_btn, margin=(0, 0, 25, 0))
        
        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)
                
        remove_btn.on_click(_remove_this_plot)

        # remove the plot choices row since the plot has been created
        if hasattr(self, 'plot_choices_row') and self.plot_choices_row in self.widget_container:
            self.widget_container.remove(self.plot_choices_row)

        if hasattr(self, 'slice_ui_row') and self.slice_ui_row in self.widget_container:
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
         
    def _ref_plot_data_button_click(self):

        self._update_ref_warning_text("")    
        self.ref_plot_button.name = "Add Plot"    
        self.ref_select_variable_button.name = "Add new plot with different variable/ plot type"    
        self._update_ref_status_text('User model status >> Generating plot...')

        #For each of the slices, build a dictionary so that the slices can be accessed in the plot
        self.ref_chosen_slices = {}
        if hasattr(self, 'ref_slice_widgets'):
            for dim, widget in self.ref_slice_widgets.items():
                self.ref_chosen_slices[dim] = widget.value

        # Based on plot type change function that is used
        if self.ref_plot_type_dropdown.value == "Heatmap":
            x_axis = self.ref_x_axis_dropdown.value
            y_axis = self.ref_y_axis_dropdown.value
            fig = self._plot_ref_heatmap(self.ref_plot_variable_dropdown.value, x_axis, y_axis) #Need to check if I need a seperate function for reference heatmaps
        elif self.ref_plot_type_dropdown.value == "Line":
            x_axis = self.ref_x_axis_dropdown.value
            fig = self._plot_ref_dataset(self.ref_plot_variable_dropdown.value, x_axis)
        
        # Create a new pane for the figure
        new_plot_pane = pn.pane.Matplotlib(fig, tight=True)

        # Create a remove button for each plot that is added
        remove_btn = pn.widgets.Button(name='Remove the above plot', button_type='danger', margin=(23, 0, 0, 10))
        
        # Group the plot and the button together
        plot_group = pn.Column(new_plot_pane, remove_btn, margin=(0, 0, 25, 0))
        
        # Local callback to destroy this specific plot group
        def _remove_this_plot(event):
            if plot_group in self.widget_container:
                self.widget_container.remove(plot_group)
                
        remove_btn.on_click(_remove_this_plot)

        # remove the plot choices row since the plot has been created
        if hasattr(self, 'ref_plot_choices_row') and self.ref_plot_choices_row in self.widget_container:
            self.widget_container.remove(self.ref_plot_choices_row)

        if hasattr(self, 'ref_slice_ui_row') and self.ref_slice_ui_row in self.widget_container:
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
            
    def _ref_keys_dropdown_click(self):
        
        """
        Loads selected reference model from ref_keys_dropdown and display reference model dataset selection. Private.
        """

        # Update text box
        self._update_ref_status_text('Reference model status >> Loading data.')
        
        # Extract selected model catalog
        self.ref_model_cat = self.access_nri_cat.search(name=self.ref_keys_dropdown.value).to_source()

        # Update text box
        self._update_ref_status_text('Reference model status >> Data catalog successfully loaded.')

        if hasattr(self, 'ref_data_keys_selection_row') and self.ref_data_keys_selection_row in self.widget_container:
            # Just update the options in the existing dropdown to match the new model
            self.ref_data_keys_dropdown.options = list(self.ref_model_cat.keys())
        else:
            # Build and display the UI for the first time
            self._display_reference_dataset_selection_ui()

    def _multiplot_ref_keys_dropdown_click(self):
        """
        Loads selected reference model, and if it contains the correct dataset and variable, adds it to a dictionary to plot. Private.
        """
        self.multiplot_ref_dataset_dict = {}

        selected_ref_model_cat = self.access_nri_cat.search(name=self.multiplot_ref_keys_dropdown.value).to_source()

        if self.keys_dropdown.value in list(selected_ref_model_cat.keys()):
            self._update_multiplot_status_text("Overlay Plot Status >> Loading selected reference model and associated dataset")
            dataset = data._build_data_object(selected_ref_model_cat, self.keys_dropdown.value)
            self.multiplot_ref_dataset_dict.update({self.multiplot_ref_keys_dropdown.value : dataset})
            self._update_multiplot_status_text("Overlay Plot Status >> Loaded reference model, add another or plot the overlay")
        else:
            self._update_multiplot_status_text("Overlay Plot Status >> There is no dataset matching the user dataset in this model, please select another")
        
    def _ref_dataset_dropdown_click(self):
        
        """
        Loads selected reference model dataset from ref_data_keys_dropdown and creates new interactive plot. Private.
        """
        self._update_ref_status_text('Reference model status >> Loading reference dataset...')
        # Load selected access_nri catalog dataset
        self.ref_dataset = data._build_data_object(self.ref_model_cat, self.ref_data_keys_dropdown.value)
        self._update_ref_status_text('Reference model status >> Reference dataset successfully loaded.')
         # Check if plot already exists
        if self.ref_figure_exists == False:

            self.ref_figure_exists = True
            # Create new plot
            self._ref_display_dataset_plot_ui()
            
        elif self.ref_figure_exists == True:

            # Update existing plot
            self._update_ref_dataset_plot_ui()
            

    def _ref_clear_data_click(self):
        """
        Clears and 'unloads' selected reference model dataset from widget container. Private.
        """

        # Update text box
        self._update_ref_status_text('Reference model status >> Data removed.')

        ui_components_to_remove = [
            'ref_data_keys_selection_row', 
            'ref_plot_ui_row', 
            'ref_plot_choices_row', 
            'ref_slice_ui_row'
        ]

        # Remove all generated reference UI rows from the layout
        for attr in ui_components_to_remove:
            if hasattr(self, attr):
                component = getattr(self, attr)
                if component in self.widget_container:
                    self.widget_container.remove(component)

        # Clear the metadata text
        self.ref_model_metadata.value = ''

        # Remove reference data attributes
        if hasattr(self, 'ref_model_cat'):
            del self.ref_model_cat
        if hasattr(self, 'ref_dataset'):
            del self.ref_dataset

        self.ref_figure_exists = False


    def _ref_model_info_click(self):
        """
        Create string from the selected model metadata, and update the reference status text with that string. Private.
        """
        # Update text box
        self._update_ref_status_text('Reference model status >> Retrieving model metadata.')

        self.ref_model_metadata.value = '<div style="color: var(--jp-ui-font-color1);">' + \
                                        '<b>Model information:</b><br>' + \
                                        '<b>Model:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['model']) + '<br>' + \
                                        '<b>Short description:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['description']) + '<br>' + \
                                        '<b>Nominal resolution:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['nominal_resolution']) + '<br>' + \
                                        '<b>Parent experiment:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['parent_experiment']) + '<br>' + \
                                        '<b>Long description:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['long_description']) + '<br>' + \
                                        '<b>Contact:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['contact']) + '<br>' + \
                                        '<b>Email:   </b>' + str(self.access_nri_cat[self.ref_keys_dropdown.value].metadata['email']) + '<br>'

        # Update text box
        self._update_ref_status_text('')
        
    def _display_dataset_plot_ui(self):
        
        """
        Create interactive panel plot for user model dataset and add to widget_container. Private.
        """
        
        self.plot_variable_dropdown.name = 'Available variables'
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        
        self.plot_type_dropdown.name = 'Select plot type'
        self.plot_type_dropdown.options = ["Line", "Heatmap"]
        
        self.plot_ui_row = pn.Row(self.plot_variable_dropdown, self.plot_type_dropdown, self.select_variable_button)
        self.widget_container.append(self.plot_ui_row)
        #self.widget_container.append(self.plot_pane)
    
    def _ref_display_dataset_plot_ui(self):
            
        """
        Create interactive panel plot for reference model dataset and add to widget_container. Private.
        """
        
        self.ref_plot_variable_dropdown.name = 'Available variables'
        self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
        
        self.ref_plot_type_dropdown.name = 'Select plot type'
        self.ref_plot_type_dropdown.options = ["Line", "Heatmap"]
        
        self.ref_plot_ui_row = pn.Row(self.ref_plot_variable_dropdown, self.ref_plot_type_dropdown, self.ref_select_variable_button)
        if hasattr(self, 'ref_keys_selection_row') and self.ref_keys_selection_row in self.widget_container:
            insert_index = self.widget_container.index(self.ref_keys_selection_row) + 1
            self.widget_container.insert(insert_index, self.ref_plot_ui_row)
        else:
            self.widget_container.append(self.ref_plot_ui_row)
        
    def _display_plot_choices_ui(self):
            
            """
            Create interactive panel plot for user to choose plot options and add to widget_container. Private.
            """
            #Remove preexisting plot choices UI
            if hasattr(self, 'plot_choices_row') and self.plot_choices_row in self.widget_container:
                self.widget_container.remove(self.plot_choices_row)

            #Find viable dimensions for axis selection
            dim_sizes = self.dataset[list(self.dataset.keys())].sizes
            viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != 'nv']

            self.x_axis_dropdown.name = 'Select X-Axis dimension'
            self.x_axis_dropdown.options = viable_dims
            show_plot_choices = True

            #If the user chooses to plot a heatmap, allow them to choose the Y-axis
            if self.plot_type_dropdown.value == "Heatmap":
                #Check if enough dimensions to make heatmap, if not, throw error and don't let the user do it. 
                if len(viable_dims) < 2:
                    self._update_warning_text("Warning >> Not enough dimensions available for this variable to plot a Heatmap.")
                    self.plot_type_dropdown.value = "Line"
                    show_plot_choices = False
                else:
                    self.y_axis_dropdown.name = 'Select Y-Axis dimension'
                    self.y_axis_dropdown.options = viable_dims
                    self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.y_axis_dropdown, self.plot_button)
            elif self.plot_type_dropdown.value == "Line":
                #Check if enough dimensions to make heatmap, if not, throw warning and don't let the user do it. 
                if len(viable_dims) == 1:
                    self._update_warning_text("Only one valid x-axis dimension, plotting automatically.")
                    self.x_axis_dropdown.value = viable_dims[0]
                    show_plot_choices = False
                    self._plot_data_button_click()
                else:
                    self.plot_choices_row = pn.Row(self.x_axis_dropdown, self.plot_button)

            #If plotting hasn't automatically occurred (in the case of the line graph with only 1 plottable dimension)
            if show_plot_choices:    
                #Insert the UI row under the variable selection even if there are plots already
                if hasattr(self, 'plot_ui_row') and self.plot_ui_row in self.widget_container:
                    insert_index = self.widget_container.index(self.plot_ui_row) + 1
                    self.widget_container.insert(insert_index, self.plot_choices_row)
                else:
                    self.widget_container.append(self.plot_choices_row)
                #self.widget_container.append(self.plot_pane)

    def _ref_display_plot_choices_ui(self):
                
        """
        Create interactive panel plot for user to choose plot options and add to widget_container. Private.
        """
        
        #Remove preexisting plot choices UI
        if hasattr(self, 'ref_plot_choices_row') and self.ref_plot_choices_row in self.widget_container:
            self.widget_container.remove(self.ref_plot_choices_row)

        #Find viable dimensions for axis selection
        dim_sizes = self.ref_dataset[list(self.ref_dataset.keys())].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != 'nv']

        self.ref_x_axis_dropdown.name = 'Select X-Axis dimension'
        self.ref_x_axis_dropdown.options = viable_dims
        show_plot_choices = True

        #If the user chooses to plot a heatmap, allow them to choose the Y-axis
        if self.ref_plot_type_dropdown.value == "Heatmap":
            #Check if enough dimensions to make heatmap, if not, throw warning and don't let the user do it. 
            if len(viable_dims) < 2:
                self._update_ref_warning_text("Warning >> Not enough dimensions available for this variable to plot a Heatmap.")
                self.ref_plot_type_dropdown.value = "Line"
                show_plot_choices = False
            else:
                self.ref_y_axis_dropdown.name = 'Select Y-Axis dimension'
                self.ref_y_axis_dropdown.options = viable_dims
                self.ref_plot_choices_row = pn.Row(self.ref_x_axis_dropdown, self.ref_y_axis_dropdown, self.ref_plot_button)
        elif self.ref_plot_type_dropdown.value == "Line":
            #Check if omly one viable dimension for line plot, if so plot it without options
            if len(viable_dims) == 1:
                show_plot_choices = False
                self._update_ref_warning_text("Only one valid x-axis dimension, plotting automatically.")
                self.ref_x_axis_dropdown.value = viable_dims[0]
                self._ref_plot_data_button_click()
            else:
                self.ref_plot_choices_row = pn.Row(self.ref_x_axis_dropdown, self.ref_plot_button)
            
        if show_plot_choices:
            #Insert the UI row under the variable selection even if there are plots already
            if hasattr(self, 'ref_plot_ui_row') and self.ref_plot_ui_row in self.widget_container:
                insert_index = self.widget_container.index(self.ref_plot_ui_row) + 1
                self.widget_container.insert(insert_index, self.ref_plot_choices_row)
            else:
                self.widget_container.append(self.ref_plot_choices_row)
            #self.widget_container.append(self.plot_pane)


    def _check_plot_validity(self):
        """
        Check if the plot being created by the user is valid. Private.
        
        Returns
        ----------
        plot_valid : bool
        requires_slice : bool
        invalid_heatmap_data : bool
        same_axes_chosen : bool
        """

        plot_valid = True
        requires_slice = False
        invalid_heatmap_data = False
        same_axes_chosen = False

        #Filter which dimensions can viably be plotted on an axis
        dim_sizes = self.dataset[list(self.dataset.keys())].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != 'nv']
        
        if self.plot_type_dropdown.value == "Heatmap":
            chosen_axes = (self.x_axis_dropdown.value, self.y_axis_dropdown.value)
        else:
            chosen_axes = (self.x_axis_dropdown.value,)

        self.remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]
        # Check if existing slice widgets match the currently required dimensions
        if hasattr(self, 'slice_widgets'):
            if set(self.slice_widgets.keys()) != set(self.remaining_dims):
                if hasattr(self, 'slice_ui_row') and self.slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.slice_ui_row)
                del self.slice_ui_row
                del self.slice_widgets

        #If there are dimensions remaining in the dataset, and they are not already sliced by the user
        if len(self.remaining_dims) > 0 and not hasattr(self, 'slice_widgets'):
            plot_valid = False
            requires_slice = True
        #If there is only one dimension plottable, and the user chose to plot a heatmap
        elif len(viable_dims) == 1 and self.plot_type_dropdown.value == "Heatmap":
            plot_valid = False
            invalid_heatmap_data = True
        #If the user has tried to plot the same variable on both axes
        elif self.plot_type_dropdown.value == "Heatmap" and self.x_axis_dropdown.value == self.y_axis_dropdown.value:
            plot_valid = False
            same_axes_chosen = True

        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen

    def _ref_check_plot_validity(self):
        """
        Check if the reference plot being created by the user is valid. Private.
        
        Returns
        ----------
        plot_valid : bool
        requires_slice : bool
        invalid_heatmap_data : bool
        same_axes_chosen : bool
        """
        
        plot_valid = True
        requires_slice = False
        invalid_heatmap_data = False
        same_axes_chosen = False

        #Filter which dimensions can viably be plotted on an axis
        dim_sizes = self.ref_dataset[list(self.ref_dataset.keys())].sizes
        viable_dims = [dim for dim, size in dim_sizes.items() if size > 1 and dim != 'nv']
        
        if self.ref_plot_type_dropdown.value == "Heatmap":
            chosen_axes = (self.ref_x_axis_dropdown.value, self.ref_y_axis_dropdown.value)
        else:
            chosen_axes = (self.ref_x_axis_dropdown.value,)

        self.ref_remaining_dims = [dim for dim in viable_dims if dim not in chosen_axes]
        # Check if existing reference slice widgets match the required dimensions
        if hasattr(self, 'ref_slice_widgets'):
            if set(self.ref_slice_widgets.keys()) != set(self.ref_remaining_dims):
                if hasattr(self, 'ref_slice_ui_row') and self.ref_slice_ui_row in self.widget_container:
                    self.widget_container.remove(self.ref_slice_ui_row)
                del self.ref_slice_ui_row
                del self.ref_slice_widgets

        #If there are dimensions remaining in the dataset, and they are not already sliced by the user
        if len(self.ref_remaining_dims) > 0 and not hasattr(self, 'ref_slice_widgets'):
            plot_valid = False
            requires_slice = True
        #If there is only one dimension plottable, and the user chose to plot a heatmap
        elif len(viable_dims) == 1 and self.ref_plot_type_dropdown.value == "Heatmap":
            plot_valid = False
            invalid_heatmap_data = True
        #If the user has tried to plot the same variable on both axes
        elif self.ref_plot_type_dropdown.value == "Heatmap" and self.ref_x_axis_dropdown.value == self.ref_y_axis_dropdown.value:
            plot_valid = False
            same_axes_chosen = True

        return plot_valid, requires_slice, invalid_heatmap_data, same_axes_chosen
        
    
    def _check_slice(self):
        """
        Check if the plot being created by the user requires dimensions to be sliced to generate a valid plot. Private.
        """

        #Filter dimensions to get the remaining dimensions not selected as the axes
        self.slice_widgets = {}
        ui_components = []

        #for each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in self.remaining_dims:
            # Extract coordinate values as options
            coord_values = list(self.dataset[dimension].values)
            dropdown = pn.widgets.Select(name=f'Slice {dimension} at:', options=coord_values)
            
            self.slice_widgets[dimension] = dropdown
            ui_components.append(dropdown)
            
        # Group them into a row
        self.slice_ui_row = pn.Row(*ui_components)

        # Insert the slice UI below the plot choices row
        if hasattr(self, 'plot_choices_row') and self.plot_choices_row in self.widget_container:
            insert_index = self.widget_container.index(self.plot_choices_row) + 1
            self.widget_container.insert(insert_index, self.slice_ui_row)
        else:
            self.widget_container.append(self.slice_ui_row)
            
        # Update the UI text to prompt the user
        self.plot_button.name = "Confirm Slices & Plot"
        self._update_status_text('User model status >> Action required: Select slice values and click plot again.')

    def _ref_check_slice(self):
        """
        Check if the reference plot being created by the user requires dimensions to be sliced to generate a valid plot. Private.
        """
    
        #Filter dimensions to get the remaining dimensions not selected as the axes
        self.ref_slice_widgets = {}
        ref_ui_components = []

        #for each dimension remaining, add a dropdown to the widget row that will be added
        for dimension in self.ref_remaining_dims:
            # Extract coordinate values as options
            coord_values = list(self.ref_dataset[dimension].values)
            dropdown = pn.widgets.Select(name=f'Slice {dimension} at:', options=coord_values)
            
            self.ref_slice_widgets[dimension] = dropdown
            ref_ui_components.append(dropdown)
            
        # Group them into a row
        self.ref_slice_ui_row = pn.Row(*ref_ui_components)

        # Insert the slice UI below the plot choices row
        if hasattr(self, 'ref_plot_choices_row') and self.ref_plot_choices_row in self.widget_container:
            insert_index = self.widget_container.index(self.ref_plot_choices_row) + 1
            self.widget_container.insert(insert_index, self.ref_slice_ui_row)
        else:
            self.widget_container.append(self.ref_slice_ui_row)
            
        # Update the UI text to prompt the user
        self.ref_plot_button.name = "Confirm Slices & Plot"
        self._update_ref_status_text('User model status >> Action required: Select slice values and click plot again.')
        
        
    def _update_dataset_plot_ui(self):
        
        """
        Update exisiting user model dataset plot if new data are selected. Private.
        """
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        self.plot_pane.object = None  # Clears the previous plot from the screen
        if hasattr(self, 'fig'):
            plt.close(self.fig)
        
        
    def _update_ref_dataset_keys_plot_ui(self):
        
        """
        Update exisiting reference model dataset keys if new data are selected. Private.
        """
        
        self.ref_data_keys_dropdown.options = list(self.ref_dataset.keys())
        plt.close(self.ref_fig)
        
        self._update_ref_dataset_plot_ui()
       
        
    def _update_ref_dataset_plot_ui(self):
        
        """
        Update exisiting reference model dataset plot if new data are selected. Private.
        """
        
        self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
        self.ref_plot_pane.object = None  # Clears the previous plot from the screen
        if hasattr(self, 'ref_fig'):
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
        self.fig, ax = plt.subplots(figsize=[8,4])
        
        self.figure_exists = True
        # Slice the dataset if the user has selected any
        sliced_data = self.dataset.sel(**self.chosen_slices)

        #Add the slice information to the title, if it is sliced data
        sliced_data[variable].plot(x=x_axis, ax=ax)
        slice_str = ", ".join([f"{dim}: {val}" for dim, val in self.chosen_slices.items()])
        title_text = sliced_data[variable].attrs.get('long_name', variable)
        caption_text = "User model \nDataset: " + self.keys_dropdown.value

        #Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.fig.text(0.1, 0.01, caption_text, wrap=False, horizontalalignment='left', fontsize=10)    
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
        self.fig, ax = plt.subplots(figsize=[8,4])

        # Slice the dataset if the user has selected any
        heatmap_data = self.dataset.sel(**self.chosen_slices)

        # Plot the specific DataArray onto the explicit axis
        heatmap_data[variable].plot(x=x_axis, y=y_axis, ax=ax)

        #Add the slice information to the title, if it is sliced data
        slice_str = ", ".join([f"{dim}: {val}" for dim, val in self.chosen_slices.items()])
        title_text = heatmap_data[variable].attrs.get('long_name', variable)
        caption_text = "User model \nDataset: " + self.keys_dropdown.value

        #Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.fig.text(0.1, 0.01, caption_text, wrap=False, horizontalalignment='left', fontsize=10)    
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
        
        self.ref_fig, ax = plt.subplots(figsize=[8,4])
        
        self.ref_figure_exists = True

        sliced_data = self.ref_dataset.sel(**self.ref_chosen_slices)
        
        # Plot all model variants if multiple exist
        if "member" in sliced_data.dims:

            for mem in sliced_data.member.values:

                sliced_data[ref_variable].sel(member=mem).plot(label=mem, x=x_axis, ax=ax)
        else:
            # Plot directly if no member dimension exists
            sliced_data[ref_variable].plot(x=x_axis, ax=ax)     
        
         #Add the slice information to the title, if it is sliced data
        
        slice_str = ", ".join([f"{dim}: {val}" for dim, val in self.ref_chosen_slices.items()])
        title_text = sliced_data[ref_variable].attrs.get('long_name', ref_variable)
        caption_text = 'Model: ' + self.ref_keys_dropdown.value + '\nDataset: ' + self.ref_data_keys_dropdown.value

        #Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.ref_fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.ref_fig.text(0.1, 0.01, caption_text, wrap=False, horizontalalignment='left', fontsize=10)    
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
        self.ref_fig, ax = plt.subplots(figsize=[8,4])

        # Slice the dataset if the user has selected any
        heatmap_data = self.ref_dataset.sel(**self.ref_chosen_slices)

        # Plot the specific DataArray onto the explicit axis
        heatmap_data[ref_variable].plot(x=x_axis, y=y_axis, ax=ax)

        #Add the slice information to the title, if it is sliced data
        slice_str = ", ".join([f"{dim}: {val}" for dim, val in self.ref_chosen_slices.items()])
        title_text = heatmap_data[ref_variable].attrs.get('long_name', ref_variable)
        caption_text = 'Model: ' + self.ref_keys_dropdown.value + '\nDataset: ' + self.ref_data_keys_dropdown.value

        #Add details of slice to caption, if the data is sliced
        if slice_str:
            caption_text += f"\nSliced by: {slice_str}"

        self.ref_fig.tight_layout()
        ax.set_title(title_text, fontsize=14)
        self.ref_fig.text(0.1, 0.01, caption_text, wrap=False, horizontalalignment='left', fontsize=10)    
        self.ref_fig.subplots_adjust(bottom=0.3)

        ax.grid()
        
        plt.close(self.ref_fig)
        return self.ref_fig