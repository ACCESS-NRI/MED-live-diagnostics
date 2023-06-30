# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" Data IO functions for med-diagnostics """


import os
import time
import intake

#from access_nri_intake.esmcat.builders import AccessCm2Builder
from access_nri_intake.source.builders import AccessCm2Builder

# import warnings
# warnings.filterwarnings("ignore")
  
        
def _check_for_new_data(model_path, model_data):
    
    """
    
    """
    
    # Return contents of nominated model data directory
    current_model_data = [f for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f))]
    
    # Check if any files have changed
    if current_model_data != model_data:
        
        #print('New data detected - updating catalog. This can take a few minutes.')
        
        new_model_data = current_model_data
        
        # Re-build ESM catalog to include new data
        _build_new_catalog(model_path)
        
        return new_model_data
        
    else:
        
        #print('No new data found')
        
        return None
    

        
def _build_new_catalog(model_path):
    
    """
    
    """
    
    builder = AccessCm2Builder(path=model_path).build()
    builder.save(name="live_diagnostics_tmp_catalog", description="Temporary catalog for live diagnostics", directory=os.getcwd())
    
    
def _load_new_catalog():
            
    """

    """

    model_cat = intake.open_esm_datastore(os.path.join(os.getcwd(), "live_diagnostics_tmp_catalog.json"), columns_with_iterables=["variable"])
    
    return model_cat


def _start_dask_cluster():
    
    """
    
    """
    
    from distributed import Client

    client = Client(threads_per_worker=1)
    
    return(client.dashboard_link)


def _build_data_object(model_cat, key):

    # Load dataset using dask to xarray object
    
    print(key)
    dataset = model_cat[key](xarray_open_kwargs=dict(use_cftime=True)).to_dask()
    
    return dataset



