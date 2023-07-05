# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" UI functions """


import panel as pn
import matplotlib.pyplot as plt
import datetime

from med_diagnostics import data

# import warnings
# warnings.filterwarnings("ignore")

pn.extension()


class UserUI():
    
    def __init__(self):
        
        # Build panel widgets
        self.last_data_load_textbox = pn.widgets.StaticText(styles={'background': 'orange', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        
        self.keys_dropdown = pn.widgets.Select()
        self.keys_button = pn.widgets.Button(styles={}, margin=(10, 0, 20, 0))
        self.plot_variable_dropdown = pn.widgets.Select()
        
        self.ref_keys_dropdown = pn.widgets.Select()
        self.ref_keys_button = pn.widgets.Button(styles={}, margin=(10, 0, 20, 0))
        self.ref_plot_variable_dropdown = pn.widgets.Select()
        
        self.ref_data_keys_dropdown = pn.widgets.Select()
        self.ref_data_keys_button = pn.widgets.Button(styles={}, margin=(10, 0, 20, 0))
        self.ref_data_plot_variable_dropdown = pn.widgets.Select()
        
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
            
            
        self.keys_button.on_click(_keys_button_click)
        self.ref_keys_button.on_click(_ref_keys_button_click)
        self.ref_data_keys_button.on_click(_ref_data_keys_button_click)
            
            
        
    def _display_status_text(self):
        
        self.widget_container = pn.Column()
        
        self.widget_container.append(self.last_data_load_textbox)
        self.widget_container.append(self.status_textbox)
        display(self.widget_container)
        print()
        
        
    def _update_status_text(self, text):
        
        self.status_textbox.value = str(text)
        
        
    def _update_last_data_load_text(self, text):
        
        self.last_data_load_textbox.value = str(text)
        
        
    def _get_current_time(self):
        
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        
    def _display_dataset_selection_ui(self, model_cat, acccess_nri_cat):
        
        """
        
        """
        
        self.model_cat = model_cat
        self.access_nri_cat = acccess_nri_cat
        
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
        # Add user model widgets
        self.keys_dropdown.name = '1. Please select a dataset to monitor:'
        self.keys_dropdown.options = self.model_cat.keys()
        self.keys_button.name = 'Load dataset'
        self.keys_button.button_type = 'primary'
        
        self.keys_selection_row = pn.Row()
        self.keys_selection_row.append(self.keys_dropdown)
        self.keys_selection_row.append(self.keys_button)
        
        self.widget_container.append(self.keys_selection_row)
        
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
        
    def _display_reference_model_selection_ui(self):
        
        """
        
        """
        
        # Add comparison model widgets
        self.ref_keys_dropdown.name = '2. Select reference model (optional):'
        self.ref_keys_dropdown.options = self.access_nri_cat.keys()
        self.ref_keys_button.name = 'Load model'
        self.ref_keys_button.button_type = 'primary'
        
        self.ref_keys_selection_row = pn.Row()
        self.ref_keys_selection_row.append(self.ref_keys_dropdown)
        self.ref_keys_selection_row.append(self.ref_keys_button)
        
        self.widget_container.append(self.ref_keys_selection_row)
        
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
        
    def _display_reference_dataset_selection_ui(self):
        
        """
        
        """
        
        # Add comparison model widgets
        self.ref_data_keys_dropdown.name = '2. Select reference dataset (optional):'
        self.ref_data_keys_dropdown.options = self.ref_model_cat.keys()
        self.ref_data_keys_button.name = 'Load dataset'
        self.ref_data_keys_button.button_type = 'primary'
        
        self.ref_data_keys_selection_row = pn.Row()
        self.ref_data_keys_selection_row.append(self.ref_data_keys_dropdown)
        self.ref_data_keys_selection_row.append(self.ref_data_keys_button)
        
        self.widget_container.append(self.ref_data_keys_selection_row)
        
        self.widget_container.append(pn.layout.Divider(styles={'color': 'white'}))
        
        
    def _keys_dropdown_click(self):
        
        """
        
        """
        
        # Update text box
        self._update_status_text('Status >> Loading data.')

        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.keys_dropdown.value)
        
        # Update text box
        self._update_status_text('Status >> Data loaded.')
        
        # Check if plot already exists
        if self.figure_exists == False:

            # Create new plot
            self._display_dataset_plot_ui()
            
            # Add ui for loading optional reference dataset
            self._display_reference_model_selection_ui()
            
        elif self.figure_exists == True:

            # Update existing plot
            self._update_dataset_plot_ui()
            
            
    def _ref_keys_dropdown_click(self):
        
        """
        
        """
        
        print('_ref_keys_dropdown_click')
        
        # Extract selected model catalog
        self.ref_model_cat = self.access_nri_cat.search(name=self.ref_keys_dropdown.value).to_source()
        
        # Check if plot already exists
        if self.ref_figure_exists == False:

            # Create new plot
            self._display_reference_dataset_selection_ui()
            
        elif self.ref_figure_exists == True:

            # Update existing plot
            self._update_ref_dataset_keys_plot_ui()
        
        
        
    def _ref_dataset_dropdown_click(self):
        
        print('_ref_dataset_dropdown_click')
        
        # Load selected access_nri catalog dataset
        self.ref_dataset = data._build_data_object(self.ref_model_cat, self.ref_data_keys_dropdown.value)
        
        # Check if plot already exists
        if self.ref_figure_exists == False:

            # Create new plot
            self._display_ref_dataset_plot_ui()
            
        elif self.ref_figure_exists == True:

            # Update existing plot
            self._update_ref_dataset_plot_ui()
        
        
        
    def _display_dataset_plot_ui(self):
        
        """
        
        """
        
        self.plot_variable_dropdown.name = 'Available variables'
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        
        self.interactive_plot = pn.bind(self._plot_dataset, self.plot_variable_dropdown)
        
        self.widget_container.append(self.plot_variable_dropdown)
        self.widget_container.append(self.interactive_plot)
        
        
    def _display_ref_dataset_plot_ui(self):
        
        """
        
        """
        
        self.ref_plot_variable_dropdown.name = 'Available reference variables'
        self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
        
        self.ref_interactive_plot = pn.bind(self._plot_dataset, self.plot_variable_dropdown, self.ref_plot_variable_dropdown)
        
        self.widget_container.append(self.ref_plot_variable_dropdown)
        self.widget_container.append(self.ref_interactive_plot)
        
        
    def _update_dataset_plot_ui(self):
        
        """
        
        """
        
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        plt.close(self.fig)
        
        
    def _update_ref_dataset_keys_plot_ui(self):
        
        """
        
        """
        
        print('updating model keys')
        
        self.ref_data_keys_dropdown.options = list(self.ref_model_cat.keys())
        plt.close(self.ref_fig)
        
        self._update_ref_dataset_plot_ui()
       
        
    def _update_ref_dataset_plot_ui(self):
        
        """
        
        """ 
        
        print('updating dataset keys')
        
        self.ref_plot_variable_dropdown.options = list(self.ref_dataset.keys())
        self.ref_plot_variable_dropdown.value = list(self.ref_dataset.keys())[0]
        plt.close(self.ref_fig)
        
        
    def _plot_dataset(self, variable, ref_variable=None):
        
        """
        
        """
        
        if ref_variable == None:
            
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
            
        else:
            
            # Plot reference model
            self.ref_fig = plt.figure(figsize=[8,4])
            
            self.ref_figure_exists = True
            
            # Plot all model variants if multiple exist
            if "member" in self.ref_dataset.dims:

                for mem in self.ref_dataset.member.values:

                    self.ref_dataset[ref_variable].sel(member=mem).plot(label=mem)
            
            plt.title(self.ref_dataset[ref_variable].attrs['long_name'], fontsize=14)

            plt.grid()
            plt.legend()
            plt.tight_layout()

            plt.close(self.ref_fig)

            return self.ref_fig
        
        
