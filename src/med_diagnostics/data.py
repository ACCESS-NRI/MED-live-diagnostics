# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" Data IO functions """


import os
import time
import intake

# from access_nri_intake.esmcat.builders import AccessCm2Builder # for use with med_diagnostics_test_env
from access_nri_intake.source.builders import AccessCm2Builder # for use with access-med-env


        
def _check_for_new_data(model_path, model_data, model_type):
    
    """
    Check monitored directory for new data and build new catalog if found.
    
    Parameters
    ----------
    model_path : str
        Path to model output directory/files on Gadi.
    model_data : list
        List of datafiles present in nominated source directory.
        
    Returns
    ----------
    new_model_data : intake ESM datastore
        Returns intake ESM datastore of user model data if data found.
    """
    
    # Return contents of nominated model data directory
    current_model_data = [f for f in os.listdir(model_path) if os.path.isfile(os.path.join(model_path, f))]
    
    # Check if any files have changed
    if current_model_data != model_data:
        
        # Set new_model_data to current_model_data
        new_model_data = current_model_data
        
        # Build ESM catalog to include new data
        _build_new_catalog(model_path, model_type)
        
        return new_model_data
        
    else:
        
        return None
    

        
def _build_new_catalog(model_path, model_type):
    
    """
    Build new intake ESM datastore from user model data found in model_path. 
    Saves new catalog file to user home. Private.
    
    Parameters
    ----------
    model_path : str
        Path to model output directory/files on Gadi.
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).
    """
    
    # Use CM2 builder
    if model_type == 'cm2':
    
        builder = AccessCm2Builder(path=model_path, ensemble=False).build()
        builder.save(name="live_diagnostics_tmp_catalog", description="Temporary catalog for live diagnostics", directory=os.getcwd())
    
    
def _load_new_catalog():
            
    """
    Load saved ESM datastore catalog file from user home path. Private.
    
    Returns
    ----------
    model_cat : Intake-ESM datastore object
        Intake catalog of user model data.
    """

    model_cat = intake.open_esm_datastore(os.path.join(os.getcwd(), "live_diagnostics_tmp_catalog.json"), columns_with_iterables=["variable"])
    
    return model_cat


def _start_dask_cluster():
    
    """
    Starts local dask cluster for data retrieval. Private.
    
    Returns
    ----------
    client.dashboard_link : str
        Dask client 'dashboard url' for monitoring.
    """
    
    from distributed import Client

    client = Client(threads_per_worker=1)
    
    return(client.dashboard_link)


def _build_data_object(model_cat, key):
    
    """
    Covert model_cat ESM datastore to xarray object. Private.
    
    Parameters
    ----------
    model_cat : Intake-ESM datastore object
        Intake catalog of user model data.
    key : str
        model_cat dictionary key - in this case the selected dropdown value.
        
    Returns
    ----------
    dataset : xarray object
        Dask xarray object.
    """
    
    # Load dataset using dask to xarray object
    dataset = model_cat[key](xarray_open_kwargs=dict(use_cftime=True)).to_dask()
    
    return dataset


def _load_access_nri_catalog(model_type, filter=True):
    
    """
    Load ACCESS-NRI data catalog. Private.
    
    Parameters
    ----------
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).
        
    Returns
    ----------
    ACCESS-NRI intake catalog
    """
    
    catalog = intake.cat.access_nri
    
    if filter == False:
        
        return catalog
    
    else:
        
        # Filter catalog by model type
        return catalog.search(model='.*' + model_type.upper() + '.*')
