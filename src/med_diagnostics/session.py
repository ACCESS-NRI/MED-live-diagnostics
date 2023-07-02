# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" Session class functions for med-diagnostics live diagnostics """


import os
import intake
import panel as pn

from apscheduler.schedulers.background import BackgroundScheduler
from med_diagnostics import data, ui
from distributed import Client

# import warnings
# warnings.filterwarnings("ignore")


class CreateLiveSession():
    
    def __init__(self, model_type, model_realm, model_path, period=None, timezone=None):
        
        self.model_type = str(model_type)
        self.model_realm = str(model_realm)
        self.model_path = str(model_path)
        self.model_data = []
        
        self.period = float(period) if period != None else 10.0
        self.timezone = str(timezone) if timezone != None else 'Australia/Canberra'
        
        self.data_update = False
        
        # Start dask client
        self.client = Client(threads_per_worker=1)
        
        print()
        print('----------------------- Live diagnostics session started -----------------------')
        print()
        print('Model type:', self.model_type)
        print('Model realm:', self.model_realm)
        print('Model data path:', self.model_path)
        print('Model data update period:', self.period, 'mins')
        print()
        print('Started dask client:', self.client.dashboard_link)
        print()
        print('--------------------------------------------------------------------------------')
        print()
        # print('Importing and building initial model data catalog. This can take a few minutes.')
        # print()
        
        self.ui = ui.UserUI()
        self.ui._display_status_text()
        self.ui._update_status_text('Status >> Importing and building initial model data catalog. This can take a few minutes.')
        print()
        
        # Start data scheduler
        self._start_scheduler()
        
        # Get initial model data
        self._get_data()

        
    def _start_scheduler(self):
        
        """
        Function to start apscheduler to trigger live model data retrieval at nominated interval. Private.
        
        """

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._get_data, 'interval', minutes=self.period, timezone=self.timezone)

        self.scheduler.start()
        
        
    def end_session(self):

        """
        Function to stop apscheduler from triggering live model data retrieval at nominated period.
        """

        self.scheduler.shutdown()
        self.client.close()
        
        print('------------------------ Live diagnostics session ended ------------------------')
        
        
    def _get_data(self):
        
        """
        
        """
        
        new_model_data = data._check_for_new_data(self.model_path, self.model_data)
        
        if new_model_data == None:
            
            # Do nothing
            pass
            
        else:
            
            # Data loading procedure for initial step
            if self.data_update == False:
            
                self.data_update == True
                #self.ui._update_status_text('>> New data found. Updating catalog.')
                
                
            # Data loading procedure for update step
            elif self.data_update == True:
                
                self.ui._update_status_text('>> New data found. Updating catalog.')
                
            
            # Update self.model_data with new data
            self.model_data = new_model_data

            # Load new catalog
            self.model_cat = data._load_new_catalog()
            
            # Load selected dataset
            # self.dataset = data._build_data_object(self.model_cat) 

            # Generate UI
            self.ui._display_dataset_selection_ui(self.model_cat)
            
            
            
    def _build_session_ui(self):
        
        pass
            
        
    def return_model_data_catalog(self):
        
        """
        Function to return currently loaded model data catalog
        
        """
        
        return self.model_cat
    
    
    

        