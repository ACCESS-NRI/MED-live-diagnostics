# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" Session class functions for med-diagnostics live diagnostics """


import os
import intake
import panel as pn

from apscheduler.schedulers.background import BackgroundScheduler
from med_diagnostics import data, ui
from distributed import Client


class CreateModelDiagnosticsSession():
    
    """
    Primary class for starting a model diagnostics session
    """
    
    def __init__(self, model_type, model_path, period=None, timezone=None):
        
        """
        Initialise a CreateLiveSession instance to start a model diagnostics session.

        Parameters
        ----------
        model_type : str
            Type of ACCESS model in capitals (e.g. CM2, OM2).
        model_path : str
            Path to model output directory/files on Gadi.
        period : int/float/str, optional, default None
            Period in minutes for background scheduler to monitor model_path for new data. If period=None, defaults to 60.
        timezone : str, optional, default 'Australia/Canberra'
            Timezone required for scheduler in tinfo 'Region/Location' format. 
            
        """
        
        # Set local variables
        self.model_type = str(model_type).lower()
        # self.model_realm = str(model_realm)
        self.model_path = str(model_path)
        self.model_data = []
        
        self.period = float(period) if period != None else 60.0
        self.timezone = str(timezone) if timezone != None else 'Australia/Canberra'
        
        self.data_update = False
        
        # Start dask client
        self.client = Client(threads_per_worker=1)
        
        print()
        print('----------------------- Live diagnostics session started -----------------------')
        print()
        print('Model type:', str(model_type))
        print('Model data path:', self.model_path)
        print('Model data update period:', self.period, 'mins')
        print()
        print('Started dask client:', self.client.dashboard_link)
        print()
        print('--------------------------------------------------------------------------------')
        print()
        
        # Start UserUI instance and display initial status text
        self.ui = ui.UserInterface()
        self.ui._display_status_text()
        
        # Start data scheduler
        self._start_scheduler()
        
        # Get initial model data
        self._get_data()

        
    def _start_scheduler(self):
        
        """
        Start background scheduler to trigger model data retrieval function get_data() at nominated period. Private.
        """

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._get_data, 'interval', minutes=self.period, timezone=self.timezone)

        self.scheduler.start()
        
        
    def end_session(self):

        """
        Stop background scheduler and close dask client to end current CreateModelDiagnosticsSession instance.
        """

        self.scheduler.shutdown()
        self.client.close()

        self.ui.widget_container.clear()
        
        print('------------------------ Live diagnostics session ended ------------------------')
        
        
    def _get_data(self):
        
        """
        Check nominated model data path for new data. Private.
        """
        
        self.ui._update_status_text('User model status >> Building initial model data catalog. This can take a few minutes.')
        
        # Check for new data
        new_model_data = data._check_for_new_data(self.model_path, self.model_data, self.model_type)
        
        # Update status text
        self.ui._update_status_text('User model status >> Model data catalog built.')
        self.ui._update_last_data_load_text('Last model data catalog build >> ' + self.ui._get_current_time())
        
        if new_model_data == None:
            
            # Do nothing
            pass
            
        else:
            
            # Data loading procedure for initial step
            if self.data_update == False:
            
                # Update self.model_data with new data
                self.model_data = new_model_data

                # Load new catalog
                self.model_cat = data._load_new_catalog()
                
                # Load access_nri catalog for model comparison filtered by model type
                self.access_nri_cat = data._load_access_nri_catalog(self.model_type)

                # Generate UI
                self.ui._display_dataset_selection_ui(self.model_cat, self.access_nri_cat)
            
                self.data_update == True
                
                
            # Data loading procedure for update step
            elif self.data_update == True:
                
                self.ui._update_status_text('User model status >> New data found.')
                
                ## Need to work on UI updates during data update
                
            
#                 # Update self.model_data with new data
#                 self.model_data = new_model_data

#                 # Load new catalog
#                 self.model_cat = data._load_new_catalog()

#                 # Generate UI
#                 self.ui._display_dataset_selection_ui(self.model_cat)
            
        
    def return_model_data_catalog(self):
        
        """
        Convenience function to return currently loaded model data catalog.
        
        Returns
        ----------
        Intake-ESM datastore object
            Intake catalog of user model data.
        """
        
        return self.model_cat
    
    
    

        