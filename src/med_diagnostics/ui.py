# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" UI functions """


import panel as pn
import matplotlib.pyplot as plt

from med_diagnostics import data

# import warnings
# warnings.filterwarnings("ignore")

pn.extension()


class UserUI():
    
    def __init__(self):
        
        #self.model_cat = model_cat
        
        # Build panel widgets
        self.status_textbox = pn.widgets.StaticText(styles={'background': 'lightblue', 'font-size': '18px', 'color': 'black', 'padding': '5px'}, margin=(10, 0, 10, 0))
        self.keys_dropdown = pn.widgets.Select()
        self.keys_button = pn.widgets.Button(styles={}, margin=(10, 0, 20, 0))
        self.plot_variable_dropdown = pn.widgets.Select()
        
        # Initialise button listener functions
        @pn.depends(self.keys_dropdown.param.value)
        def _keys_button_click(event):
            
            self._keys_dropdown_click()
            
        self.keys_button.on_click(_keys_button_click)
            
        # Display selected widgets
        #self._display_dataset_selection_ui()
        
        
    def _display_status_text(self):
        
        self.widget_container = pn.Column()
        self.widget_container.append(self.status_textbox)
        display(self.widget_container)
        print()
        
    def _update_status_text(self, text):
        
        self.status_textbox.value = str(text)
        
        
    def _display_dataset_selection_ui(self, model_cat):
        
        """
        
        """
        
        self.model_cat = model_cat
        #self.dataset = dataset
        
        self.keys_dropdown.name = 'Please select a dataset to monitor:'
        self.keys_dropdown.options = self.model_cat.keys()
        self.keys_button.name = 'Load dataset'
        self.keys_button.button_type = 'primary'
        
        # Add dataset selection dropdown and button to widget widget_container
        # if self.data_update == False:
            
        self.widget_container.append(self.keys_dropdown)
        self.widget_container.append(self.keys_button)
            
#         elif self.data_update == True:
            
#             pass
        
        print()
        print('--------------------------------------------------------------------------------')
        print()
        
        
    def _keys_dropdown_click(self):
        
        """
        
        """

        # Load selected dataset
        self.dataset = data._build_data_object(self.model_cat, self.keys_dropdown.value)
        
        # Update text box
        self._update_status_text('Status >> Plotting selected data.')
        
        # Check if plot already exists
        if len(self.widget_container) == 5:
            
            # Update existing plot
            self._update_dataset_plot_ui()
            
        else:
        
            # Create new plot
            self._display_dataset_plot_ui()
        
        
    def _display_dataset_plot_ui(self):
        
        """
        
        """
        
        self.plot_variable_dropdown.name = 'Available variables'
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        
        self.interactive_plot = pn.bind(self._plot_dataset, self.plot_variable_dropdown)
        
        self.widget_container.append(self.plot_variable_dropdown)
        self.widget_container.append(self.interactive_plot)
        
        
    def _update_dataset_plot_ui(self):
        
        """
        
        """
        
        self.plot_variable_dropdown.options = list(self.dataset.keys())
        plt.close(self.fig)
        
        
    def _plot_dataset(self, variable):
        
        """
        
        """
        
        self.fig = plt.figure(figsize=[10,5])
        self.dataset[variable].plot()

        plt.title(self.dataset[variable].attrs['long_name'], fontsize=14)

        plt.grid()
        plt.tight_layout()

        plt.close(self.fig)

        return self.fig
