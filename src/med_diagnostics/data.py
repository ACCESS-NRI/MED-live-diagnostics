# Copyright 2023 ACCESS-NRI and contributors. See the top-level COPYRIGHT file for details.
# SPDX-License-Identifier: Apache-2.0

""" Data IO functions """


import os
import time
import access_nri_intake
import intake

from access_nri_intake.source.builders import AccessCm2Builder, AccessOm2Builder, AccessCm3Builder, AccessOm3Builder, AccessEsm15Builder, AccessEsm16Builder, Mom6Builder
from access_nri_intake.experiment import use_datastore
from access_nri_intake.aliases import AliasedESMCatalog
        
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

    # Let the intake catalog _use_datastore function handle checking the directory and loading/rebuilding the catalog
    ds = _build_new_catalog(model_path, model_type)
    
    # Get the current list of files directly from the catalog's dataframe
    current_model_data = ds.df['path'].tolist()
    
    # Check if the catalog contains new/different files compared to the previous list of files. If so, return the new list of files; otherwise, return None.
    if current_model_data != model_data:
        return current_model_data
    else:
        return None
        
def _build_new_catalog(model_path, model_type):
    
    """
    Build new intake ESM datastore from user model data found in model_path.
    Uses intake datastore builder for the specified model_type. 
    Saves new catalog file to user home. Private.
    
    Parameters
    ----------
    model_path : str
        Path to model output directory/files on Gadi.
    model_type : str
        Type of ACCESS model (e.g. CM2, OM2).
    """
    
    #Match the model type to the correct type of builder
    match model_type:
        case 'cm2':
            model_type_builder = AccessCm2Builder
        case 'om2':
            model_type_builder = AccessOm2Builder
        case 'cm3':
            model_type_builder = AccessCm3Builder
        case 'om3':
            model_type_builder = AccessOm3Builder
        case 'esm15':
            model_type_builder = AccessEsm15Builder
        case 'esm16':
            model_type_builder = AccessEsm16Builder
        case 'mom6':
            model_type_builder = Mom6Builder

    # Set builder kwargs based on model type, if model_type is one of the builders that requires the ensemble argument, set it to False, otherwise set it to an empty dictionary.
    if model_type_builder in [AccessEsm15Builder, AccessEsm16Builder, AccessCm2Builder, AccessCm3Builder]:
        builder_kwargs_set = {'ensemble': False}
    else:
        builder_kwargs_set = {}

    # Use the matched builder to build the new catalog in the users working directory.
    ds = use_datastore(
            experiment_dir=model_path,
            catalog_dir = os.getcwd(),
            builder = model_type_builder,
            datastore_name = "live_diagnostics_tmp_catalog",
            description = "Temporary catalog for live diagnostics",
            builder_kwargs = builder_kwargs_set
        )
        
    return ds

    
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
    model_cat : Intake-ESM datastore object or AliasedESMCatalog object
        Intake catalog of user or reference model data.
    key : str
        model_cat dictionary key - in this case the selected dropdown value.
        
    Returns
    ----------
    dataset : xarray object
        Dask xarray object.
    """

    #If the model_cat is an AliasedESMCatalog, unwrap it to get the raw esm_datastore (intake_esm.core.esm_datastore) object. Reference models are stored as AliasedESMCatalog objects, so this is necessary for loading reference model data.
    if isinstance(model_cat, AliasedESMCatalog):
        model_cat = model_cat.unwrap()

    open_kwargs = {
        'use_cftime': True,
        'chunks': {} 
    }
    combine_kwargs = { 
        'compat' : 'override',
        'data_vars': 'minimal',
        'coords': 'minimal'
    }
    # Standard Intake catalog approach for getting dataset
    dataset = model_cat[key](xarray_open_kwargs=open_kwargs, xarray_combine_by_coords_kwargs=combine_kwargs).to_dask()
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
