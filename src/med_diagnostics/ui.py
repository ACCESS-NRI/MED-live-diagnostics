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
        self.ref_status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))

        self.ref_model_metadata = pn.widgets.StaticText(styles={'color': 'white'})
        
        self.keys_dropdown = pn.widgets.Select()
        self.keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.plot_variable_dropdown = pn.widgets.Select()
        
        self.ref_keys_dropdown = pn.widgets.Select()
        self.ref_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.ref_plot_variable_dropdown = pn.widgets.Select()
        
        self.ref_data_keys_dropdown = pn.widgets.Select()
        self.ref_data_keys_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 0))
        self.ref_data_plot_variable_dropdown = pn.widgets.Select()

        self.clear_ref_model_data_button = pn.widgets.Button(styles={}, margin=(23, 0, 0, 10))
        self.ref_model_info_button = pn.widgets.Button(styles={}, margin=(23, 10, 0, 0))

        self.plot_button = pn.widgets.Button(name='Plot Data', button_type='success', margin=(23, 0, 0, 10))
        self.plot_pane = pn.pane.Matplotlib(tight=True)

        self.ref_plot_button = pn.widgets.Button(name='Plot Reference', button_type='success', margin=(23, 0, 0, 10))
        self.ref_plot_pane = pn.pane.Matplotlib(tight=True)
                
        self.figure_exists = False
        self.ref_figure_exists = False
        
        
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

            self._update_status_text('User model status >> Generating plot...')
            fig = self._plot_dataset(self.plot_variable_dropdown.value)
            self.plot_pane.object = fig
            self._update_status_text('User model status >> Plot generated.')

            if self.plot_pane not in self.widget_container:
                self.widget_container.append(self.plot_pane)
                self._display_reference_model_selection_ui()
            
        def _ref_plot_button_click(event):
            self._update_ref_status_text('Reference model status >> Generating plot...')
            fig = self._plot_ref_dataset(self.ref_plot_variable_dropdown.value)
            self.ref_plot_pane.object = fig
            self._update_ref_status_text('Reference model status >> Plot generated.')

            if self.ref_plot_pane not in self.widget_container:
                self.widget_container.append(self.ref_plot_pane)

        self.plot_button.on_click(_plot_button_click)
        self.ref_plot_button.on_click(_ref_plot_button_click)  
        self.keys_button.on_click(_keys_button_click)
        self.ref_keys_button.on_click(_ref_keys_button_click)
        self.ref_data_keys_button.on_click(_ref_data_keys_button_click)
        self.clear_ref_model_data_button.on_click(_ref_clear_data_button_click)
        self.ref_model_info_button.on_click(_ref_model_info_button_click)

            
            
    def _display_status_text(self):
        
        """
        Create widget_container then add status_textbox and last_data_load_textbox widgets. Private.
        """
        
        # Create panel column
        self.widget_container = pn.Column()
        
        # Append widget_container with textbox widgets
        self.widget_container.append(self.last_data_load_textbox)
        self.widget_container.append(self.status_textbox)

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
        
        # UNHIDE the widgets via property updates rather than structural appends
        self.div_1.visible = True
        self.keys_selection_row.visible = True
        self.div_2.visible = True

        #print(self.widget_container)
        
        
    def _display_reference_model_selection_ui(self):
        
        """
        Label, populate and append ACCESS reference model selection-related widgets to widget_container. Private.
        
        """

        # Add refrence data status text box
        self.widget_container.append(self.ref_status_textbox)
        
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
        
        
    def _display_reference_dataset_selection_ui(self):
        
        """
        Label, populate and append ACCESS reference dataset selection-related widgets to widget_container. Private.
        
        """
        
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
        
        # Check if plot already exists
        if self.figure_exists == False:
            
            self.figure_exists = True
            # Create new plot
            self._display_dataset_plot_ui()
            
            # Add ui for loading optional reference dataset
            #self._display_reference_model_selection_ui()

            
        elif self.figure_exists == True:

            # Update existing plot
            self._update_dataset_plot_ui()
            
            
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

        self._display_reference_dataset_selection_ui()
                    
        
        
    def _ref_dataset_dropdown_click(self):
        
        """
        Loads selected reference model dataset from ref_data_keys_dropdown and creates new interactive plot. Private.
        """
        self._update_ref_status_text('Reference model status >> Loading reference dataset...')
        # Load selected access_nri catalog dataset
        self.ref_dataset = data._build_data_object(self.ref_model_cat, self.ref_data_keys_dropdown.value)
        self._update_ref_status_text('Reference model status >> Reference dataset successfully loaded.')
         # Check if plot already exists
        if not self.ref_figure_exists:

            self.ref_figure_exists = True
            # Create new plot
            self._display_ref_dataset_plot_ui()
            
        elif self.ref_figure_exists == True:

            # Update existing plot
            self._update_ref_dataset_plot_ui()
            

    def _ref_clear_data_click(self):
        """
        Clears and 'unloads' selected reference model dataset from widget container. Private.
        """

        # Update text box
        self._update_ref_status_text('Reference model status >> Data removed.')

        # Remove reference model widgets from container one at a time
        self.widget_container.pop(-1)
        self.widget_container.pop(-1)
        self.widget_container.pop(-1)
        self.widget_container.pop(-1)

        # Remove reference model ref_model_cat
        del self.ref_model_cat
        
        # Remove reference dataset ref_dataset
        del self.ref_dataset

        self.ref_figure_exists = False


    def _ref_model_info_click(self):

        # Update text box
        self._update_ref_status_text('Reference model status >> Retrieving model metadata.')

        # self.ref_model_metadata.value = self.access_nri_cat[self.ref_keys_dropdown.value].metadata['description']

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
        
        plot_ui_row = pn.Row(self.plot_variable_dropdown, self.plot_button)
        self.widget_container.append(plot_ui_row)
        #self.widget_container.append(self.plot_pane)
        
        
    def _display_ref_dataset_plot_ui(self):
        
        """
        Create interactive panel plot for reference model dataset and add to widget_container. Private.
        """
        
        self.ref_plot_variable_dropdown.name = 'Available reference variables'
        self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
        
        ref_plot_ui_row = pn.Row(self.ref_plot_variable_dropdown, self.ref_plot_button)
        self.widget_container.append(ref_plot_ui_row)
        #self.widget_container.append(self.ref_plot_pane)
        
        
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
        
        
    def _plot_dataset(self, variable):
        
        """
        Plot 2D time-series from model data. Private.
        
        Parameters
        ----------
        variable : str
            Model data variable as selected from panel dropdown. 
        Returns
        ----------
        fig : matplotlib.pyplot.figure()
        ref_fig : matplotlib.pyplot.figure()
        """
        # Plot primary (user) model data
        self.fig = plt.figure(figsize=[8,4])
        
        self.figure_exists = True
        
        self.dataset[variable].plot()
        
        plt.title(self.dataset[variable].attrs['long_name'], fontsize=14)

        plt.grid()
        plt.legend()
        plt.tight_layout()

        plt.close(self.fig)

        return self.fig
            


    def _plot_ref_dataset(self, ref_variable):
        
        """
        Plot 2D time-series from reference model data. Private.
        
        Parameters
        ----------
        ref_variable : str
            Reference model data variable as selected from panel dropdown.
            
        Returns
        ----------
        ref_fig : matplotlib.pyplot.figure()
        """
        
        self.ref_fig = plt.figure(figsize=[8,4])
        
        self.ref_figure_exists = True
        
        # Plot all model variants if multiple exist
        if "member" in self.ref_dataset.dims:

            for mem in self.ref_dataset.member.values:

                self.ref_dataset[ref_variable].sel(member=mem).plot(label=mem)
        else:
            # Plot directly if no member dimension exists
            self.ref_dataset[ref_variable].plot()        
        
        plt.title(self.ref_dataset[ref_variable].attrs['long_name'], fontsize=14)

        plt.grid()
        plt.legend()
        plt.tight_layout()

        plt.close(self.ref_fig)

        return self.ref_fig

        
        